#!/usr/bin/env python3
"""Pick the cleanest reference window from a recording, cut it, transcribe it.

Usage: pick_reference.py <audio> <out-dir> --language "<name>" [--max-seconds N] [--min-seconds N]

Writes <out-dir>/ref.wav (48 kHz mono) and <out-dir>/ref.json, prints ref.json.
Windows start and end on natural pauses; the pick has the fewest clipped
samples, then the longest duration within the limits.
"""
import argparse
import json
import re
import struct
import wave
from pathlib import Path

import voicestudio as vs

# Silence detection: -35 dB and 0.35 s split speech at breath pauses in phone
# and WhatsApp recordings without cutting inside words.
SILENCE_DB = -35
# VoiceStudio's docs suggest 8-15 s reference recordings; 20 s is OmniVoice's
# reference cap and was enough for VoxCPM2 in practice.
DEFAULT_MIN_S = 8.0
DEFAULT_MAX_S = 20.0


def pauses(path: Path) -> list[tuple[float, float]]:
    out = vs.ffmpeg("-v", "info", "-i", str(path), "-af",
                    f"silencedetect=noise={SILENCE_DB}dB:d={SILENCE_MIN_S}", "-f", "null", "-")
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return list(zip(starts, ends + [None] * (len(starts) - len(ends))))


def samples(path: Path) -> tuple[list[int], int]:
    with wave.open(str(path)) as w:
        n, rate = w.getnframes(), w.getframerate()
        return list(struct.unpack(f"<{n}h", w.readframes(n))), rate


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--language", required=True, help='VoiceStudio language name, e.g. "Portuguese (Brazil)"')
    ap.add_argument("--min-seconds", type=float, default=DEFAULT_MIN_S)
    ap.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_S)
    args = ap.parse_args()

    vs.require_ffmpeg()
    if not args.audio.is_file():
        vs.die(f"reference audio not found: {args.audio}")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    full = args.out_dir / "source.wav"
    vs.to_wav(args.audio, full)
    data, rate = samples(full)
    duration = len(data) / rate

    gaps = pauses(full)
    # Speech can start at 0 or at the end of a pause; it can end at the start
    # of a pause or at the end of the file.
    starts = sorted({0.0} | {e for _, e in gaps if e is not None})
    ends = sorted({duration} | {s for s, _ in gaps if s > 0})

    def clipped(a: float, b: float) -> int:
        return sum(1 for x in data[int(a * rate):int(b * rate)] if abs(x) >= vs.CLIP_LEVEL)

    candidates = [
        {"start": round(a, 2), "end": round(b, 2), "seconds": round(b - a, 2), "clipped": clipped(a, b)}
        for a in starts for b in ends
        if args.min_seconds <= b - a <= args.max_seconds
    ]
    if candidates:
        pick = min(candidates, key=lambda c: (c["clipped"], -c["seconds"]))
        fallback = None
    else:
        end = min(duration, args.max_seconds)
        pick = {"start": 0.0, "end": round(end, 2), "seconds": round(end, 2), "clipped": clipped(0, end)}
        fallback = f"no pause-aligned window between {args.min_seconds}s and {args.max_seconds}s; used the first {end:.1f}s"

    ref = args.out_dir / "ref.wav"
    vs.to_wav(args.audio, ref, pick["start"], pick["end"])
    result = {
        "source": str(args.audio),
        "source_seconds": round(duration, 2),
        "source_clipped": clipped(0, duration),
        "window": pick,
        "fallback": fallback,
        "ref_audio": str(ref),
        "ref_text": vs.transcribe(ref, args.language),
        "language": args.language,
        "candidates_considered": len(candidates),
        "cleanest_alternatives": sorted(candidates, key=lambda c: (c["clipped"], -c["seconds"]))[1:4],
    }
    full.unlink()
    (args.out_dir / "ref.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
