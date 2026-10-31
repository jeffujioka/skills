#!/usr/bin/env python3
"""Save a reference as a VoiceStudio voice profile. Run only after the user approved it.

Usage: create_profile.py <out-dir> --name "<profile name>"

Reads ref_audio, ref_text and language from <out-dir>/ref.json; prints the new profile id.
"""
import argparse
import json
from pathlib import Path

import voicestudio as vs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--name", required=True)
    args = ap.parse_args()

    ref_json = args.out_dir / "ref.json"
    if not ref_json.is_file():
        vs.die(f"{ref_json} not found; run pick_reference.py first")
    ref = json.loads(ref_json.read_text())
    fields = {"name": args.name, "kind": "clone", "language": ref["language"], "ref_text": ref["ref_text"]}
    raw = vs.post_form("/profiles", fields, {"ref_audio": Path(ref["ref_audio"])})
    profile = json.loads(raw)
    print(json.dumps({"id": profile["id"], "name": profile["name"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
