#!/usr/bin/env python3
"""Run a skill's evals headless on a chosen harness, then grade them.

Usage: run_evals.py <skill-dir> --harness claude|omp [--model haiku]
                    [--reasoning high] [--runs 10] [--pass-rate 0.7]
                    [--judge sonnet] [--timeout SECS] [--jobs N] [--out DIR]
                    [--scenarios 0,2] [--baseline]

--harness names the harness that starts the runs and the judge. Each scenario
in <skill-dir>/evals/evals.json runs --runs times on one model, each run in its
own scratch dir under /tmp/ that holds a copy of the skill and the scenario's
files. The live skill is never touched. A judge model grades each behavior from
the condensed transcript.

A scenario passes when every run passes each `required_behavior`, and at least
ceil(runs * pass-rate) runs pass every behavior. --baseline runs the same
queries without the skill, to measure what the skill must fix.

Exit: 0 every scenario passed, 1 a scenario failed or a run broke, 2 usage error.
"""
import argparse
import concurrent.futures
import datetime
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_TIMEOUT = 1800  # a full create run takes many tool calls; 30 min bounds a stuck one
DEFAULT_JOBS = 3  # three runs in parallel keeps rate limits and local load modest
DEFAULT_RUNS = 10  # enough repeats to see a behavior that slips one run in three
DEFAULT_PASS_RATE = 0.7  # 7 of 10: a ~90% reliable scenario passes 99% of the time
JUDGE_TIMEOUT = 600  # the judge only reads; 10 min is generous
JUDGE_ATTEMPTS = 2  # the judge only reads, and now and then emits malformed JSON; one retry keeps that off the score
MAX_TOOL_TEXT = 1500  # chars kept per tool input or result, so the judge prompt stays bounded
MAX_FILE_TEXT = 6000  # chars of each final file shown to the judge; skills are small text files
NESTED_ENV = "RUN_EVALS_NESTED"  # set for each run; an eval inside an eval would multiply runs and cost
SANDBOX_NOTE = ("Bash runs only `python3 <file>` and `chmod +x <file>` with an absolute path inside {work}. "
                "Any other command, including `ls` and `python3 -c`, is refused; a refusal blocks only that "
                "command, so run the scripts the skill names in that form.")
BASELINE_PROMPT = """{sandbox} No user is available to answer. If you need an answer from \
the user before you can go on, stop there and state the question.

Request: {query}"""
RUN_PROMPT = """Read {skill_md} and follow it to handle the request below. \
{sandbox} No user is available to answer. If the skill needs an answer from the user \
before it can go on, stop there and state the question.

Request: {query}"""
JUDGE_PROMPT = """You grade one run of an agent skill. For each expected \
behavior, decide pass or fail from the transcript and the final files \
only. A behavior the transcript does not show is a fail. Write the \
evidence first, quoting it briefly, then set pass to what that evidence \
shows. Give one result per behavior, in the order listed. Reply with only \
this JSON:
{{"results": [{{"behavior": "...", "evidence": "...", "pass": true}}]}}

<expected_behaviors>
{behaviors}
</expected_behaviors>

<final_files>
{files}
</final_files>

<transcript>
{transcript}
</transcript>"""


def die(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def clip(text):
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    return text if len(text) <= MAX_TOOL_TEXT else text[:MAX_TOOL_TEXT] + " [...]"


def tool_text(body):
    if isinstance(body, list):
        return "\n".join(b.get("text", "") for b in body if isinstance(b, dict))
    return body or ""


def user_env():
    """Process env plus the `env` block of the Claude Code user settings.

    The claude isolation flags drop the user setting source, and with it that
    block; it often holds the auth and endpoint (ANTHROPIC_BASE_URL,
    ANTHROPIC_AUTH_TOKEN, model mappings). Passed as the child env, it keeps
    the CLI logged in while user hooks, plugins, skills and MCP servers stay out.
    """
    config_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    try:
        block = json.loads((config_dir / "settings.json").read_text(encoding="utf-8")).get("env")
    except (OSError, json.JSONDecodeError, AttributeError):
        block = None
    extra = {k: str(v) for k, v in block.items()} if isinstance(block, dict) else {}
    return {**os.environ, **extra}


class Claude:
    name = "claude"
    isolation = [  # keep user hooks, plugins, skills and MCP servers out of the run
        "--setting-sources", "project,local",
        "--disable-slash-commands",
        "--strict-mcp-config",
        "--no-session-persistence",
    ]
    no_background = [  # a scheduled wakeup or monitor keeps the headless run alive until timeout
        "--disallowedTools", "ScheduleWakeup", "CronCreate", "Monitor",
    ]

    def __init__(self):
        self.env = {**user_env(), NESTED_ENV: "1"}

    def run_cmd(self, prompt, model, reasoning, work, run_dir):
        effort = ["--effort", reasoning] if reasoning else []
        return ["claude", "-p", prompt, "--model", model, *effort, "--output-format", "stream-json", "--verbose",
                *self.isolation, *self.no_background, "--permission-mode", "acceptEdits",
                "--allowedTools", "Read", "Write", "Edit", "Glob", "Grep", f"Bash(python3 {work}/*)",
                "Bash(python3 _skill/*)", f"Bash(chmod +x {work}/*)"]

    def judge_cmd(self, prompt_file, model):
        """Return (cmd, stdin text)."""
        cmd = ["claude", "-p", "--model", model, "--output-format", "json", *self.isolation]
        return cmd, prompt_file.read_text(encoding="utf-8")

    def judge_reply(self, stdout):
        return json.loads(stdout).get("result", "")

    def condense(self, jsonl_path):
        """Turn stream-json into readable lines; drop thinking blocks."""
        lines, cost = [], None
        for ev in read_jsonl(jsonl_path):
            kind = ev.get("type")
            if kind == "result":
                cost = ev.get("total_cost_usd")
                continue
            if kind not in ("assistant", "user"):
                continue
            content = ev.get("message", {}).get("content", [])
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            for block in content:
                btype = block.get("type")
                if btype == "text" and kind == "assistant":
                    lines.append(f"ASSISTANT: {block['text']}")
                elif btype == "tool_use":
                    lines.append(f"TOOL_CALL {block.get('name')}: {clip(block.get('input'))}")
                elif btype == "tool_result":
                    flag = " (error)" if block.get("is_error") else ""
                    lines.append(f"TOOL_RESULT{flag}: {clip(tool_text(block.get('content')))}")
        return "\n".join(lines), cost


class Omp:
    name = "omp"
    isolation = [  # keep user skills, extensions, rules, context files and LSP out of the run
        "--no-session", "--no-skills", "--no-extensions", "--no-rules", "--no-context-files",
        "--no-title", "--no-lsp", "--no-pty",
    ]
    tools = "read,write,edit,glob,grep,bash"  # explicit list also keeps MCP, task and eval tools out

    def __init__(self):
        self.env = {**os.environ, NESTED_ENV: "1"}

    def run_cmd(self, prompt, model, reasoning, work, run_dir):
        # Exec-tier calls need approval, which print mode refuses; the patterns
        # allow only the sandboxed commands. Background jobs would outlive the run.
        overlay = {
            "tools": {"approvalMode": "write"},
            "async": {"enabled": False},
            "bash": {"autoBackground": {"enabled": False}, "patterns": [
                {"match": f"python3 {work}/*", "approval": "allow"},
                {"match": "python3 _skill/*", "approval": "allow"},
                {"match": f"chmod +x {work}/*", "approval": "allow"},
            ]},
        }
        config = run_dir / "omp-config.yml"
        config.write_text(json.dumps(overlay, indent=2) + "\n", encoding="utf-8")  # JSON is valid YAML
        thinking = ["--thinking", reasoning] if reasoning else []
        return ["omp", "-p", "--mode", "json", "--model", model, *thinking, *self.isolation,
                "--tools", self.tools, "--config", str(config), prompt]

    def judge_cmd(self, prompt_file, model):
        # @file keeps a long prompt out of argv, where one argument is capped at 128 KiB
        return ["omp", "-p", "--mode", "json", "--model", model, *self.isolation, "--no-tools",
                f"@{prompt_file}"], None

    def judge_reply(self, stdout):
        texts = [c["text"] for ev in parse_jsonl(stdout) if ev.get("type") == "message_end"
                 and ev["message"].get("role") == "assistant"
                 for c in ev["message"].get("content", []) if c.get("type") == "text"]
        return texts[-1] if texts else ""

    def condense(self, jsonl_path):
        """Turn omp json events into readable lines; drop thinking blocks."""
        lines, cost = [], 0.0
        for ev in read_jsonl(jsonl_path):
            if ev.get("type") != "message_end":
                continue
            msg = ev.get("message", {})
            role = msg.get("role")
            if role == "assistant":
                cost += (msg.get("usage", {}).get("cost") or {}).get("total") or 0
                for block in msg.get("content", []):
                    if block.get("type") == "text":
                        lines.append(f"ASSISTANT: {block['text']}")
                    elif block.get("type") == "toolCall":
                        lines.append(f"TOOL_CALL {block.get('name')}: {clip(block.get('arguments'))}")
            elif role == "toolResult":
                flag = " (error)" if msg.get("isError") else ""
                lines.append(f"TOOL_RESULT{flag}: {clip(tool_text(msg.get('content')))}")
        return "\n".join(lines), round(cost, 6)


HARNESSES = {"claude": Claude, "omp": Omp}


def parse_jsonl(text):
    for raw in text.splitlines():
        try:
            yield json.loads(raw)
        except json.JSONDecodeError:
            continue


def read_jsonl(path):
    return parse_jsonl(path.read_text(encoding="utf-8", errors="replace"))


def load_scenarios(skill_dir):
    path = skill_dir / "evals" / "evals.json"
    if not path.is_file():
        die(f"{path} not found; write the evals first (step 3)")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON: {e}")
    if not isinstance(data, list) or not data:
        die(f"{path} must hold a non-empty JSON array")
    for i, s in enumerate(data):
        if not s.get("query") or not (s.get("expected_behavior") or s.get("required_behavior")):
            die(f"{path} scenario {i}: needs 'query' and 'expected_behavior' or 'required_behavior'")
    return data


def behaviors(scenario):
    """Return [(text, required)], required behaviors first."""
    return ([(b, True) for b in scenario.get("required_behavior", [])]
            + [(b, False) for b in scenario.get("expected_behavior", [])])


def runs_needed(runs, pass_rate):
    return math.ceil(round(runs * pass_rate, 9))  # round first: 10 * 0.7 is 7.000000000000001


def prepare(skill_dir, scenario, work, with_skill=True):
    """Copy the skill and the scenario's files into an empty scratch dir."""
    copy = work / "_skill" / skill_dir.name
    if with_skill:
        shutil.copytree(skill_dir, copy, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    prefix = Path("evals/files")
    for rel in scenario.get("files", []):
        src = skill_dir / rel
        if not src.is_file():
            raise FileNotFoundError(f"fixture not found: {rel}")
        rel_path = Path(rel)
        dest_rel = rel_path.relative_to(prefix) if rel_path.parts[:2] == prefix.parts else rel_path.name
        dest = work / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return copy


def file_list(work):
    """Final files with their text, so the judge sees content the clipped transcript hides."""
    parts = []
    for p in sorted(work.rglob("*")):
        rel = p.relative_to(work)
        if not p.is_file() or "_skill" in rel.parts:
            continue
        try:
            body = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            body = "(binary or unreadable)"
        if len(body) > MAX_FILE_TEXT:
            body = body[:MAX_FILE_TEXT] + " [...]"
        parts.append(f"=== {rel}\n{body}")
    return "\n".join(parts) or "(none)"


def last_json(text):
    """Return the last top-level JSON object in text, or None."""
    dec, found, i = json.JSONDecoder(), None, 0
    while i < len(text):
        if text[i] == "{":
            try:
                val, end = dec.raw_decode(text, i)
                found, i = val, end
                continue
            except json.JSONDecodeError:
                pass
        i += 1
    return found


def run_one(harness, skill_dir, scenario, idx, rep, args, out):
    run_dir = out / f"{idx}-r{rep}{'-baseline' if args.baseline else ''}"
    work = run_dir / "work"
    work.mkdir(parents=True)
    result = {"scenario": idx, "run": rep, "dir": str(run_dir), "passed": [], "error": None}
    try:
        copy = prepare(skill_dir, scenario, work, with_skill=not args.baseline)
    except (OSError, FileNotFoundError) as e:
        result["error"] = str(e)
        return result
    sandbox = SANDBOX_NOTE.format(work=work)
    if args.baseline:
        prompt = BASELINE_PROMPT.format(sandbox=sandbox, query=scenario["query"])
    else:
        prompt = RUN_PROMPT.format(skill_md=copy / "SKILL.md", sandbox=sandbox, query=scenario["query"])
    cmd = harness.run_cmd(prompt, args.model, args.reasoning, work, run_dir)
    transcript = run_dir / "transcript.jsonl"
    try:
        with transcript.open("w") as fh, (run_dir / "stderr.txt").open("w") as err:
            proc = subprocess.run(cmd, cwd=work, stdout=fh, stderr=err, timeout=args.timeout, env=harness.env)
        result["exit"] = proc.returncode
    except subprocess.TimeoutExpired:
        result["error"] = f"run timed out after {args.timeout}s"
    text, result["cost_usd"] = harness.condense(transcript)
    (run_dir / "transcript.txt").write_text(text, encoding="utf-8")
    if not text:
        result["error"] = result["error"] or "empty transcript; see stderr.txt"
        return result

    wanted = behaviors(scenario)
    prompt_file = run_dir / "judge-prompt.md"
    prompt_file.write_text(JUDGE_PROMPT.format(
        behaviors="\n".join(f"{n}. {b}" for n, (b, _) in enumerate(wanted, 1)),
        files=file_list(work), transcript=text), encoding="utf-8")
    for attempt in range(1, JUDGE_ATTEMPTS + 1):
        results, result["error"] = judge(harness, prompt_file, args.judge, run_dir, len(wanted), attempt)
        if results is not None:
            result["results"] = results
            result["passed"] = [bool(r.get("pass")) for r in results]
            break
    return result


def judge(harness, prompt_file, model, run_dir, count, attempt):
    """Return (results, None), or (None, error) when the reply is unusable."""
    judge_cmd, stdin = harness.judge_cmd(prompt_file, model)
    try:
        proc = subprocess.run(judge_cmd, input=stdin, capture_output=True, text=True, timeout=JUDGE_TIMEOUT,
                              cwd=run_dir, env=harness.env)
        (run_dir / f"judge-reply-{attempt}.txt").write_text(proc.stdout + proc.stderr, encoding="utf-8")
        verdict = last_json(harness.judge_reply(proc.stdout))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, AttributeError, KeyError) as e:
        return None, f"judge failed: {e}"
    results = verdict.get("results") if isinstance(verdict, dict) else None
    if not isinstance(results, list) or len(results) != count:
        return None, f"judge returned {len(results) if isinstance(results, list) else 'no'} results for {count} behaviors"
    return results, None


def grade(scenario, runs, needed):
    """Summarize one scenario's runs. A run that broke fails every behavior."""
    wanted = behaviors(scenario)
    counts = [0] * len(wanted)
    full = 0
    for r in runs:
        passed = r["passed"] if not r["error"] and len(r["passed"]) == len(wanted) else [False] * len(wanted)
        counts = [c + p for c, p in zip(counts, passed)]
        full += all(passed)
    required_ok = all(c == len(runs) for c, (_, req) in zip(counts, wanted) if req)
    return {
        "runs_passed": full,
        "runs": len(runs),
        "needed": needed,
        "ok": required_ok and full >= needed,
        "behaviors": [{"behavior": b, "required": req, "passed": c} for c, (b, req) in zip(counts, wanted)],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("skill_dir")
    ap.add_argument("--harness", required=True, choices=sorted(HARNESSES), help="harness that starts the runs")
    ap.add_argument("--model", default="haiku", help="model for the runs; a name the harness accepts")
    ap.add_argument("--reasoning", default="high", help="reasoning level (claude --effort, omp --thinking)")
    ap.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="runs per scenario")
    ap.add_argument("--pass-rate", type=float, default=DEFAULT_PASS_RATE,
                    help="share of runs that must pass every behavior")
    ap.add_argument("--judge", default="sonnet", help="model that grades the transcripts")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="seconds per run")
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS, help="runs in parallel")
    ap.add_argument("--out", help="results dir (default: new dir under /tmp/)")
    ap.add_argument("--baseline", action="store_true", help="run the queries without the skill")
    ap.add_argument("--scenarios", help="comma-separated scenario indexes to run (default: all)")
    args = ap.parse_args()
    if args.runs < 1 or not 0 < args.pass_rate <= 1:
        die("--runs must be at least 1 and --pass-rate in (0, 1]")

    if os.environ.get(NESTED_ENV):
        die("no login is available for eval runs inside an eval run; "
            "report the evals as written, not run, with that reason")
    skill_dir = Path(args.skill_dir).expanduser().resolve()
    if not (skill_dir / "SKILL.md").is_file():
        die(f"{skill_dir}/SKILL.md not found")
    name = args.harness
    if not shutil.which(name):
        die(f"{name} CLI not found; run step 7 by hand as SKILL.md describes")
    harness = HARNESSES[name]()
    scenarios = load_scenarios(skill_dir)
    wanted = {int(x) for x in args.scenarios.split(",")} if args.scenarios else None
    picked = [i for i in range(len(scenarios)) if wanted is None or i in wanted]
    needed = runs_needed(args.runs, args.pass_rate)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix=f"evals-{skill_dir.name}-{stamp}-", dir="/tmp"))
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(i, rep) for rep in range(1, args.runs + 1) for i in picked]  # rounds, so early output covers every scenario
    print(f"results: {out}  harness: {name}  model: {args.model} ({args.reasoning})  "
          f"runs: {len(jobs)}  pass: {needed}/{args.runs} per scenario", flush=True)

    by_scenario = {i: [] for i in picked}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_one, harness, skill_dir, scenarios[i], i, rep, args, out) for i, rep in jobs]
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            status = r["error"] or f"{sum(r['passed'])}/{len(r['passed'])} behaviors passed"
            print(f"scenario {r['scenario']} run {r['run']}: {status}", flush=True)
            by_scenario[r["scenario"]].append(r)

    summary = {"harness": name, "model": args.model, "reasoning": args.reasoning, "judge": args.judge,
               "baseline": args.baseline, "scenarios": []}
    for i in picked:
        runs = sorted(by_scenario[i], key=lambda r: r["run"])
        g = grade(scenarios[i], runs, needed)
        summary["scenarios"].append({"scenario": i, "query": scenarios[i]["query"], **g, "details": runs})
        print(f"\nscenario {i}: {g['runs_passed']}/{g['runs']} runs passed every behavior (need {needed}): "
              f"{'PASS' if g['ok'] else 'FAIL'}")
        for b in g["behaviors"]:
            print(f"  {'required' if b['required'] else 'expected'} {b['passed']:>3}/{g['runs']}  {b['behavior']}")
        for r in runs:
            if r["error"] or not all(r["passed"]):
                print(f"  run {r['run']}: {r['dir']}/transcript.txt")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ok = all(s["ok"] for s in summary["scenarios"])
    print(f"\n{'PASS' if ok else 'FAIL'}: details in {out}/summary.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
