#!/usr/bin/env python3
"""Generate a dublagem line by line from <out-dir>/job.json, check each take, join into final.wav.

Usage:
  dub.py <out-dir>                      generate missing lines, then join
  dub.py <out-dir> --redo 2,5           new takes for lines 2 and 5 (other seeds), then join
  dub.py <out-dir> --pick 3=99          use the seed-99 take for line 3, then join

Each take is transcribed and its noise floor measured. A take that does not
pass both checks triggers the retry seeds; the best take wins (closest
transcript, then lowest noise floor). Writes takes/, lines/, final.wav and
report.json; prints the report.
"""
import argparse
import json
import re
from pathlib import Path

import voicestudio as vs

# Transcript match needed to accept a take without retries. Measured on
# Portuguese takes: clean takes scored 0.96-1.0, mispronounced names 0.83-0.98,
# so 0.97 flags most bad takes and accepts the ASR's own spelling drift.
SIMILARITY_OK = 0.97
# Noise floor needed to accept a take. Clean VoxCPM2 and OmniVoice takes
# measured -45 to -84 dB; takes heard as noisy measured -34 to -35 dB.
NOISE_FLOOR_OK_DB = -40.0
# Fades remove onset clicks: VoxCPM2 lines can start at -13 dBFS in the first 5 ms.
FADE_IN_S = 0.01
FADE_OUT_S = 0.03
# Broadcast speech loudness; evens out level jumps between separately generated lines.
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"
# New seeds per --redo: three more takes balance choice against generation time.
REDO_NEW_SEEDS = 3
DEFAULT_RETRY_SEEDS = [7, 13, 99, 123, 2024]
TAG_RE = re.compile(r"\[([^\]]+)\]")


def load_job(out: Path) -> dict:
    path = out / "job.json"
    if not path.is_file():
        vs.die(f"{path} not found; write it from templates/job.json first")
    job = json.loads(path.read_text())
    for key in ("engine", "language", "voice", "lines"):
        if key not in job:
            vs.die(f"job.json is missing '{key}'")
    voice = job["voice"]
    if "profile_id" not in voice and "ref_audio" not in voice:
        vs.die("job.json voice needs 'profile_id' or 'ref_audio' (+ 'ref_text')")
    if "ref_audio" in voice:
        ref = Path(voice["ref_audio"])
        voice["ref_audio"] = ref if ref.is_absolute() else out / ref
        if not voice["ref_audio"].is_file():
            vs.die(f"reference audio not found: {voice['ref_audio']}")
    return job


def check_engine(job: dict) -> str:
    engines = {e["id"]: e for e in vs.get_json("/engines/tts").get("backends", [])}
    engine = engines.get(job["engine"])
    if engine is None:
        vs.die(f"unknown engine '{job['engine']}'; known: {', '.join(sorted(engines))}")
    if not engine.get("available"):
        vs.die(f"engine '{job['engine']}' is not installed; install it in VoiceStudio Model Catalogue")
    vocab = engine.get("instruct_vocabulary") or ""
    if vocab != "tags":
        # Only OmniVoice tokenizes reaction tags; other engines speak them as words.
        for i, line in enumerate(job["lines"], 1):
            for tag in TAG_RE.findall(line):
                if not tag.startswith("pause"):
                    vs.die(f"line {i}: tag [{tag}] would be spoken aloud by {job['engine']}; remove it")
    return vocab


def generate(job: dict, text: str, seed: int, dest: Path) -> None:
    fields = {"text": text, "language": job["language"], "seed": str(seed), "engine": job["engine"]}
    if job.get("instruct"):
        fields["instruct"] = job["instruct"]
    voice, files = job["voice"], None
    if "profile_id" in voice:
        fields["profile_id"] = voice["profile_id"]
    else:
        files = {"ref_audio": voice["ref_audio"]}
        if voice.get("ref_text"):
            fields["ref_text"] = voice["ref_text"]
    dest.write_bytes(vs.post_form("/generate", fields, files, vs.GENERATE_TIMEOUT_S))


def evaluate(job: dict, text: str, take: Path) -> dict:
    heard = vs.transcribe(take, job["language"])
    return {
        "heard": heard,
        "similarity": round(vs.similarity(text, heard), 3),
        "noise_floor_db": round(vs.noise_floor_db(take), 1),
    }


def passes(result: dict) -> bool:
    return result["similarity"] >= SIMILARITY_OK and result["noise_floor_db"] <= NOISE_FLOOR_OK_DB


def take_path(out: Path, n: int, seed: int) -> Path:
    return out / "takes" / f"{n:02d}_seed{seed}.wav"


def ensure_take(job: dict, out: Path, report: dict, n: int, seed: int) -> dict:
    key = f"{n:02d}"
    takes = report.setdefault("takes", {}).setdefault(key, {})
    path = take_path(out, n, seed)
    if str(seed) not in takes or not path.is_file():
        text = job["lines"][n - 1]
        generate(job, text, seed, path)
        takes[str(seed)] = evaluate(job, text, path)
        r = takes[str(seed)]
        print(f"line {key} seed {seed}: similarity {r['similarity']} noise {r['noise_floor_db']} dB | {r['heard']}", flush=True)
    return takes[str(seed)]


def best_seed(report: dict, n: int, exclude: set[int]) -> int:
    takes = report["takes"][f"{n:02d}"]
    options = [(int(s), r) for s, r in takes.items() if int(s) not in exclude]
    return min(options, key=lambda o: (-round(o[1]["similarity"], 2), o[1]["noise_floor_db"]))[0]


def choose(job: dict, out: Path, report: dict, n: int, seeds: list[int]) -> None:
    for seed in seeds:
        if passes(ensure_take(job, out, report, n, seed)):
            break
    report.setdefault("chosen", {})[f"{n:02d}"] = best_seed(report, n, set())


def join(out: Path, report: dict, gap: float, count: int) -> Path:
    inputs, filters = [], []
    for i in range(count):
        seed = report["chosen"][f"{i + 1:02d}"]
        inputs += ["-i", str(take_path(out, i + 1, seed))]
        filters.append(
            f"[{i}:a]aresample=48000,aformat=channel_layouts=mono,"
            f"afade=t=in:d={FADE_IN_S},areverse,afade=t=in:d={FADE_OUT_S},areverse,"
            f"apad=pad_dur={gap}[a{i}]"
        )
    labels = "".join(f"[a{i}]" for i in range(count))
    graph = ";".join(filters) + f";{labels}concat=n={count}:v=0:a=1,{LOUDNORM},aresample=48000[out]"
    final = out / "final.wav"
    vs.ffmpeg("-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]", str(final))
    return final


def parse_list(value: str | None) -> list[int]:
    return [int(x) for x in value.split(",") if x.strip()] if value else []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--redo", help="comma-separated line numbers to retake with new seeds")
    ap.add_argument("--pick", action="append", default=[], help="LINE=SEED, use an existing take")
    args = ap.parse_args()

    vs.require_ffmpeg()
    out = args.out_dir
    job = load_job(out)
    check_engine(job)
    (out / "takes").mkdir(parents=True, exist_ok=True)
    report_path = out / "report.json"
    report = json.loads(report_path.read_text()) if report_path.is_file() else {}

    lines = job["lines"]
    base = int(job.get("seed", 42))
    retry = [int(s) for s in job.get("retry_seeds", DEFAULT_RETRY_SEEDS)]
    redo = set(parse_list(args.redo))
    for n in redo:
        if not 1 <= n <= len(lines):
            vs.die(f"--redo line {n} out of range 1-{len(lines)}")

    # Takes are reused only while the settings and the line text that made them are unchanged.
    signature = {k: str(job.get(k)) for k in ("engine", "language", "instruct", "voice")}
    if report.get("signature") != signature:
        report = {"signature": signature}
    report.setdefault("takes", {})
    report.setdefault("chosen", {})
    report.setdefault("lines", {})

    for n in range(1, len(lines) + 1):
        key = f"{n:02d}"
        if report["lines"].get(key) != lines[n - 1]:
            report["takes"].pop(key, None)
            report["chosen"].pop(key, None)
            report["lines"][key] = lines[n - 1]
        if n in redo:
            tried = {int(s) for s in report["takes"].get(key, {})}
            current = report["chosen"].get(key)
            fresh, candidate = [], base
            while len(fresh) < REDO_NEW_SEEDS:
                candidate += 1000
                if candidate not in tried:
                    fresh.append(candidate)
            for seed in fresh:
                ensure_take(job, out, report, n, seed)
            report["chosen"][key] = best_seed(report, n, {current} if current is not None else set())
        elif key not in report["chosen"]:
            choose(job, out, report, n, [base, *retry])
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    for spec in args.pick:
        line, _, seed = spec.partition("=")
        key = f"{int(line):02d}"
        if seed not in report.get("takes", {}).get(key, {}):
            vs.die(f"--pick {spec}: no take with seed {seed} for line {key}")
        report["chosen"][key] = int(seed)

    final = join(out, report, float(job.get("gap_seconds", 0.3)), len(lines))
    report["final"] = str(final)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(f"\nfinal: {final}")
    print("line  seed  similarity  noise_dB  pass  heard")
    for n in range(1, len(lines) + 1):
        key = f"{n:02d}"
        seed = report["chosen"][key]
        r = report["takes"][key][str(seed)]
        print(f"{key}    {seed:<5} {r['similarity']:<11} {r['noise_floor_db']:<9} {'yes' if passes(r) else 'NO':<5} {r['heard']}")


if __name__ == "__main__":
    main()
