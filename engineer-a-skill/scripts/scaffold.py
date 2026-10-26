#!/usr/bin/env python3
"""Create <dir>/<name>/SKILL.md from the templates.

Usage: scaffold.py <dir> <name> --invocation auto|manual --description TEXT
Exit: 0 created, 1 refused (bad name, bad description, target exists), 2 usage error.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import MAX_DESC, check_name  # noqa: E402

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dir", help="existing directory that will contain the new skill")
    ap.add_argument("name")
    ap.add_argument("--invocation", required=True, choices=("auto", "manual"))
    ap.add_argument("--description", required=True)
    args = ap.parse_args()

    parent = Path(args.dir).expanduser().resolve()
    if not parent.is_dir():
        print(f"error: {parent} is not a directory", file=sys.stderr)
        return 1
    problems = check_name(args.name)
    if len(args.description) > MAX_DESC:
        problems.append(f"description is {len(args.description)} chars (max {MAX_DESC})")
    if not args.description.strip():
        problems.append("description is empty")
    if problems:
        for p in problems:
            print(f"error: {p}", file=sys.stderr)
        return 1

    target = parent / args.name
    if target.exists():
        print(f"error: {target} exists; edit it instead of scaffolding", file=sys.stderr)
        return 1

    front = (TEMPLATES / f"frontmatter-{args.invocation}.txt").read_text(encoding="utf-8")
    body = (TEMPLATES / "SKILL.md.tmpl").read_text(encoding="utf-8")
    description = json.dumps(args.description, ensure_ascii=False)
    front = front.replace("{{name}}", args.name).replace("{{description}}", description)
    body = body.replace("{{name}}", args.name)

    target.mkdir()
    (target / "SKILL.md").write_text(front + "\n" + body, encoding="utf-8")
    print(f"created {target}/SKILL.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
