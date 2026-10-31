#!/usr/bin/env python3
"""Print VoiceStudio backend status as JSON: health, cloning engines, saved voice profiles.

Usage: check_backend.py
Exit 1 with a message when the backend is unreachable.
"""
import json

import voicestudio as vs


def main() -> None:
    health = vs.get_json("/health")
    tts = vs.get_json("/engines/tts")
    engines = [
        {
            "id": e["id"],
            "name": e.get("display_name"),
            "installed": bool(e.get("available")),
            "instruct": e.get("instruct_vocabulary"),
            "max_ref_seconds": e.get("max_ref_seconds"),
            "one_click_install": bool(e.get("one_click_install")),
        }
        for e in tts.get("backends", [])
        if e.get("supports_cloning")
    ]
    profiles = [
        {"id": p["id"], "name": p["name"], "language": p.get("language"), "kind": p.get("kind")}
        for p in vs.get_json("/profiles")
        if not p.get("is_demo")
    ]
    print(json.dumps(
        {"url": vs.BASE_URL, "health": health, "active_engine": tts.get("active"),
         "cloning_engines": engines, "profiles": profiles},
        ensure_ascii=False, indent=2,
    ))


if __name__ == "__main__":
    main()
