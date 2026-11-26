#!/usr/bin/env python3
"""Check that a rebuilt README renders on GitHub: links, images and assets.

usage: check_readme.py FILE.md [FILE.md ...]

Per file, reports each problem as `file:line: message` and exits 1 when any
exists. Checked: local links and images exist, images have alt text, no tags
GitHub strips (script, style, iframe), image assets stay under 5 MB, SVG assets
load nothing external and hold no script.
"""
import re
import sys
from pathlib import Path

MAX_ASSET_BYTES = 5 * 1024 * 1024  # a bigger image slows the repository page for every visitor
STRIPPED_TAGS = re.compile(r"<\s*(script|style|iframe)\b", re.I)
MD_REF = re.compile(r"(!?)\[([^\]]*)\]\(\s*<?([^)\s>]+)")
HTML_ATTR = re.compile(r"""\b(src|href|srcset)\s*=\s*["']([^"']+)["']""", re.I)
IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
SVG_BAD = re.compile(r"<\s*script\b|<\s*foreignObject\b|(?:href|src)\s*=\s*[\"']https?://|url\(\s*[\"']?https?://", re.I)
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


def is_local(ref):
    return not re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", ref, re.I)


def refs(text):
    """Yield (line, kind, ref, alt) for every local reference in text."""
    for n, line in enumerate(text.splitlines(), 1):
        for bang, alt, ref in MD_REF.findall(line):
            yield n, "image" if bang else "link", ref, alt
        for m in IMG_TAG.finditer(line):
            alt = re.search(r"""\balt\s*=\s*["']([^"']*)["']""", m.group(0), re.I)
            src = re.search(r"""\bsrc\s*=\s*["']([^"']+)["']""", m.group(0), re.I)
            if src:
                yield n, "image", src.group(1), alt.group(1) if alt else None
        for name, ref in HTML_ATTR.findall(line):
            if name.lower() == "href":
                yield n, "link", ref, None
            elif name.lower() == "srcset":
                for part in ref.split(","):
                    yield n, "asset", part.strip().split()[0], None
            elif not IMG_TAG.search(line):  # <source src=...> inside <picture>
                yield n, "asset", ref, None


def check_file(path):
    problems = []
    text = path.read_text()
    for n, line in enumerate(text.splitlines(), 1):
        if STRIPPED_TAGS.search(line):
            problems.append(f"{path}:{n}: GitHub strips <script>, <style> and <iframe>; remove the tag")
    for n, kind, ref, alt in refs(text):
        if not is_local(ref):
            continue
        target_ref = re.split(r"[#?]", ref)[0]
        if not target_ref:
            continue
        target = (path.parent / target_ref).resolve()
        if not target.exists():
            problems.append(f"{path}:{n}: {kind} target {ref} does not exist")
            continue
        if kind == "image" and (alt is None or not alt.strip()):
            problems.append(f"{path}:{n}: image {ref} has no alt text")
        if target.is_file() and target.suffix.lower() in IMAGE_EXT:
            size = target.stat().st_size
            if size > MAX_ASSET_BYTES:
                problems.append(f"{path}:{n}: {ref} is {size // 1024} KB; shrink it under {MAX_ASSET_BYTES // 1024} KB")
            if target.suffix.lower() == ".svg" and SVG_BAD.search(target.read_text(errors="replace")):
                problems.append(f"{path}:{n}: {ref} holds a script, foreignObject or external URL; GitHub blocks them in <img>")
    return problems


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) > 1 else 2)
    problems = []
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.is_file():
            print(f"check_readme: {arg} not found", file=sys.stderr)
            sys.exit(2)
        problems += check_file(path)
    for p in problems:
        print(p)
    print(f"check_readme: {len(problems)} problem(s) in {len(sys.argv) - 1} file(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
