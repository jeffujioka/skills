#!/usr/bin/env python3
"""Run a skill's evals headless with the Claude Code CLI, then grade them.

Usage: run_evals.py <skill-dir> [--models haiku,sonnet,opus] [--judge sonnet]
                    [--timeout SECS] [--jobs N] [--out DIR] [--baseline]

Each scenario in <skill-dir>/evals/evals.json runs once per model, in its own
scratch dir under /tmp/ that holds a copy of the skill and the scenario's
files. The live skill is never touched. A judge model grades each expected
behavior from the condensed transcript. --baseline runs the same queries
without the skill, to measure what the skill must fix.

Exit: 0 every behavior passed, 1 at least one failed or a run broke, 2 usage error.
"""
import argparse
import concurrent.futures
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_TIMEOUT = 1800  # a full create run takes many tool calls; 30 min bounds a stuck one
DEFAULT_JOBS = 3  # three runs in parallel keeps rate limits and local load modest
JUDGE_TIMEOUT = 600  # the judge only reads; 10 min is generous
MAX_TOOL_TEXT = 1500  # chars kept per tool input or result, so the judge prompt stays bounded
ISOLATION = [  # keep user hooks, plugins, skills and MCP servers out of the run
    "--setting-sources", "project,local",
    "--disable-slash-commands",
    "--strict-mcp-config",
    "--no-session-persistence",
]
NO_BACKGROUND = [  # a scheduled wakeup or monitor keeps the headless run alive until timeout
    "--disallowedTools", "ScheduleWakeup", "CronCreate", "Monitor",
]
SANDBOX_NOTE = "Bash allows only `python3` and `chmod +x` on files inside {work}."
BASELINE_PROMPT = """{sandbox} No user is available to answer. If you need an answer from \
the user before you can go on, stop there and state the question.

Request: {query}"""
RUN_PROMPT = """Read {skill_md} and follow it to handle the request below. \
{sandbox} No user is available to answer. If the skill needs an answer from the user \
before it can go on, stop there and state the question.

Request: {query}"""
JUDGE_PROMPT = """You grade one run of an agent skill. For each expected \
behavior, decide pass or fail from the transcript and the final file list \
only. A behavior the transcript does not show is a fail. Quote short \
evidence. Reply with only this JSON:
{{"results": [{{"behavior": "...", "pass": true, "evidence": "..."}}]}}

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
        if not s.get("query") or not s.get("expected_behavior"):
            die(f"{path} scenario {i}: needs 'query' and 'expected_behavior'")
    return data


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


def clip(text):
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    return text if len(text) <= MAX_TOOL_TEXT else text[:MAX_TOOL_TEXT] + " [...]"


def condense(jsonl_path):
    """Turn stream-json into readable lines; drop thinking blocks."""
    lines, cost = [], None
    for raw in jsonl_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
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
                body = block.get("content")
                if isinstance(body, list):
                    body = "\n".join(b.get("text", "") for b in body if isinstance(b, dict))
                flag = " (error)" if block.get("is_error") else ""
                lines.append(f"TOOL_RESULT{flag}: {clip(body or '')}")
    return "\n".join(lines), cost


def file_list(work):
    return "\n".join(
        str(p.relative_to(work)) for p in sorted(work.rglob("*"))
        if p.is_file() and "_skill" not in p.relative_to(work).parts
    ) or "(none)"


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


def run_one(skill_dir, scenario, idx, model, args, out):
    run_dir = out / f"{model}-{idx}{'-baseline' if args.baseline else ''}"
    work = run_dir / "work"
    work.mkdir(parents=True)
    result = {"scenario": idx, "model": model, "query": scenario["query"], "results": [], "error": None}
    try:
        copy = prepare(skill_dir, scenario, work, with_skill=not args.baseline)
    except (OSError, FileNotFoundError) as e:
        result["error"] = str(e)
        return result
    if args.baseline:
        prompt = BASELINE_PROMPT.format(sandbox=SANDBOX_NOTE.format(work=work), query=scenario["query"])
    else:
        prompt = RUN_PROMPT.format(skill_md=copy / "SKILL.md", sandbox=SANDBOX_NOTE.format(work=work),
                                   query=scenario["query"])
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "stream-json", "--verbose",
           *ISOLATION, *NO_BACKGROUND, "--permission-mode", "acceptEdits",
           "--allowedTools", "Read", "Write", "Edit", "Glob", "Grep", f"Bash(python3 {work}/*)", "Bash(python3 _skill/*)",
           f"Bash(chmod +x {work}/*)"]
    transcript = run_dir / "transcript.jsonl"
    try:
        with transcript.open("w") as fh, (run_dir / "stderr.txt").open("w") as err:
            proc = subprocess.run(cmd, cwd=work, stdout=fh, stderr=err, timeout=args.timeout)
        result["exit"] = proc.returncode
    except subprocess.TimeoutExpired:
        result["error"] = f"run timed out after {args.timeout}s"
    text, result["cost_usd"] = condense(transcript)
    (run_dir / "transcript.txt").write_text(text, encoding="utf-8")
    if not text:
        result["error"] = result["error"] or "empty transcript; see stderr.txt"
        return result

    judge_prompt = JUDGE_PROMPT.format(
        behaviors="\n".join(f"- {b}" for b in scenario["expected_behavior"]),
        files=file_list(work), transcript=text)
    try:
        proc = subprocess.run(
            ["claude", "-p", "--model", args.judge, "--output-format", "json", *ISOLATION],
            input=judge_prompt, capture_output=True, text=True, timeout=JUDGE_TIMEOUT, cwd=run_dir)
        verdict = last_json(json.loads(proc.stdout).get("result", ""))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, AttributeError) as e:
        result["error"] = f"judge failed: {e}"
        return result
    if not verdict or not isinstance(verdict.get("results"), list):
        result["error"] = "judge returned no results JSON"
        return result
    result["results"] = verdict["results"]
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("skill_dir")
    ap.add_argument("--models", default="haiku,sonnet,opus", help="comma-separated model aliases")
    ap.add_argument("--judge", default="sonnet", help="model that grades the transcripts")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="seconds per run")
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS, help="runs in parallel")
    ap.add_argument("--out", help="results dir (default: new dir under /tmp/)")
    ap.add_argument("--baseline", action="store_true", help="run the queries without the skill")
    ap.add_argument("--scenarios", help="comma-separated scenario indexes to run (default: all)")
    args = ap.parse_args()

    skill_dir = Path(args.skill_dir).expanduser().resolve()
    if not (skill_dir / "SKILL.md").is_file():
        die(f"{skill_dir}/SKILL.md not found")
    if not shutil.which("claude"):
        die("claude CLI not found; run step 7 by hand as SKILL.md describes")
    scenarios = load_scenarios(skill_dir)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix=f"evals-{skill_dir.name}-{stamp}-", dir="/tmp"))
    out.mkdir(parents=True, exist_ok=True)
    wanted = {int(x) for x in args.scenarios.split(",")} if args.scenarios else None
    jobs = [(s, i, m) for m in models for i, s in enumerate(scenarios) if wanted is None or i in wanted]
    print(f"results: {out}  runs: {len(jobs)}", flush=True)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_one, skill_dir, s, i, m, args, out) for s, i, m in jobs]
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            passed = sum(1 for x in r["results"] if x.get("pass"))
            status = r["error"] or f"{passed}/{len(r['results'])} passed"
            print(f"{r['model']:<8} scenario {r['scenario']}: {status}", flush=True)
            results.append(r)

    results.sort(key=lambda r: (r["model"], r["scenario"]))
    (out / "summary.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ok = all(not r["error"] and r["results"] and all(x.get("pass") for x in r["results"]) for r in results)
    print(f"{'PASS' if ok else 'FAIL'}: details in {out}/summary.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
