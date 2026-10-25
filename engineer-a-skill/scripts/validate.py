#!/usr/bin/env python3
"""Validate an agent skill directory.

Usage: validate.py <skill-dir>
Exit: 0 no FAIL (warnings allowed), 1 at least one FAIL, 2 usage error.
"""
import json
import os
import re
import sys
from pathlib import Path

RESERVED = ("claude", "anthropic")
MAX_NAME = 64  # Anthropic frontmatter limit
MAX_DESC = 1024  # Anthropic frontmatter limit
MAX_BODY_LINES = 500  # Anthropic: keep SKILL.md body under 500 lines
MAX_REF_LINES_NO_TOC = 100  # Anthropic: longer reference files need a table of contents
MAX_FENCE_LINES = 3  # house rule: longer snippets belong in scripts/
MAX_EMPHASIS = 3  # house rule: shouting words per file before a warning
MAX_SCAN_BYTES = 1_000_000  # skip large files in the secret scan

NAME_RE = re.compile(r"^[a-z0-9-]+$")
XML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
PATH_RE = re.compile(r"`((?:scripts|references|templates)/[\w.-]+(?:/[\w.-]+)*)`")
FENCE_OPEN_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*([\w+#.-]*)")
FENCE_CLOSE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*$")
FIRST_PERSON_CS_RE = re.compile(r"\bI(?:'m|'ll|'ve|'d)?\b")
SECOND_PERSON_RE = re.compile(r"\b(?:my|you|your|we|our)\b", re.I)
WHEN_RE = re.compile(
    r"\b(?:use when|use for|call by hand|when|whenever|triggers? on|if the user)\b", re.I
)
EMPHASIS_RE = re.compile(r"\b(?:MUST NOT|MUST|NEVER|ALWAYS|CRITICAL|IMPORTANT|DO NOT)\b")
REASONING_RE = re.compile(
    r"think step[- ]by[- ]step"
    r"|\b(?:write|show|explain|output|print)\s+(?:out\s+)?(?:your|its|the)\s+"
    r"(?:reasoning|thinking|thought process)\b"
    r"|<thinking>",
    re.I,
)
DATED_RE = re.compile(
    r"\b(?:before|after|until|since|as of|by|in|starting)\s+(?:[A-Za-z]+\s+)?20\d{2}\b", re.I
)
PLACEHOLDER_RE = re.compile(r"<<FILL|\{\{\w+\}\}")
SECRET_RES = [
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36}")),
    ("GitLab token", re.compile(r"glpat-[\w-]{20}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10}")),
    ("API secret key", re.compile(r"\bsk-[A-Za-z0-9]{20}")),
    (
        "hardcoded credential",
        re.compile(
            r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*['\"]?[A-Za-z0-9/+_-]{8}"
        ),
    ),
]
TERM_GROUPS = [
    ("skill dir", "skill directory", "skill folder"),
    ("frontmatter", "front matter"),
    ("validator", "linter"),
    ("manual-only", "user-invoked", "manual only"),
]
NON_CODE_LANGS = {
    "", "text", "txt", "plaintext", "markdown", "md", "yaml", "yml", "json", "xml",
    "toml", "ini", "diff", "output", "csv", "html",
}
SHELL_LANGS = {"bash", "sh", "shell", "zsh", "console", "fish"}
SHELL_KEYWORD_RE = re.compile(r"^\s*(?:for|while|until|if|case|select|function|then|do|done|fi|esac)\b")
QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")


class Findings:
    def __init__(self):
        self.items = []

    def fail(self, rule, where, msg):
        self.items.append(("FAIL", rule, where, msg))

    def warn(self, rule, where, msg):
        self.items.append(("WARN", rule, where, msg))

    def count(self, level):
        return sum(1 for item in self.items if item[0] == level)


def parse_frontmatter(lines):
    """Return (fields, body_start_index) or (None, 0) when frontmatter is absent."""
    if not lines or lines[0].strip() != "---":
        return None, 0
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, 0
    fields = {}
    i = 1
    while i < end:
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, raw = m.group(1), m.group(2).strip()
        cont = []
        i += 1
        while i < end and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
            cont.append(lines[i].strip())
            i += 1
        if raw[:1] in ("|", ">"):
            sep = "\n" if raw[0] == "|" else " "
            value = sep.join(c for c in cont if c)
        else:
            value = " ".join([raw] + [c for c in cont if c])
            if value[:1] == '"':
                try:
                    value = json.loads(value)
                except ValueError:
                    value = value.strip('"')
            elif value[:1] == "'" and value[-1:] == "'":
                value = value[1:-1].replace("''", "'")
        fields[key] = value
    return fields, end + 1


def scan_fences(lines):
    """Return (fences, inside) with fences = [(lang, first_line_no, body_lines)]."""
    fences, inside = [], set()
    i = 0
    while i < len(lines):
        m = FENCE_OPEN_RE.match(lines[i])
        if not m:
            i += 1
            continue
        mark, lang = m.group(1), m.group(2).lower()
        j = i + 1
        while j < len(lines):
            c = FENCE_CLOSE_RE.match(lines[j])
            if c and c.group(1)[0] == mark[0] and len(c.group(1)) >= len(mark):
                break
            j += 1
        fences.append((lang, i + 1, lines[i + 1 : j]))
        inside.update(range(i, min(j + 1, len(lines))))
        i = j + 1
    return fences, inside


def prose_lines(lines, inside):
    """Yield (line_no, text) for lines outside fences, inline code removed."""
    for idx, line in enumerate(lines):
        if idx not in inside:
            yield idx + 1, INLINE_CODE_RE.sub("", line)


def check_name(name, dir_name=None):
    problems = []
    if not name:
        return ["name is empty"]
    if len(name) > MAX_NAME:
        problems.append(f"name is {len(name)} chars (max {MAX_NAME})")
    if not NAME_RE.match(name):
        problems.append("name must use only lowercase letters, digits and hyphens")
    for word in RESERVED:
        if word in name:
            problems.append(f"name contains reserved word '{word}'")
    if dir_name is not None and name != dir_name:
        problems.append(f"name '{name}' differs from directory name '{dir_name}'")
    return problems


def check_frontmatter(fields, skill_md, f):
    where = f"{skill_md.name}:1"
    if fields is None:
        f.fail("R00", where, "missing frontmatter (--- block at top of file)")
        return
    for problem in check_name(fields.get("name", ""), skill_md.parent.name):
        f.fail("R01", where, problem)
    desc = fields.get("description", "")
    if not desc.strip():
        f.fail("R02", where, "description is empty")
        return
    if len(desc) > MAX_DESC:
        f.fail("R02", where, f"description is {len(desc)} chars (max {MAX_DESC})")
    if XML_TAG_RE.search(desc):
        f.fail("R02", where, "description contains XML tags")
    plain = INLINE_CODE_RE.sub("", desc)
    if FIRST_PERSON_CS_RE.search(plain) or SECOND_PERSON_RE.search(plain):
        f.fail("R02", where, "description must be third person (found I/my/you/your/we/our)")
    if not WHEN_RE.search(desc):
        f.warn("W02", where, "description has no 'when' clause (Use when... / Call by hand...)")
    flag = fields.get("disable-model-invocation")
    if flag is not None and flag.strip().lower() not in ("true", "false"):
        f.fail("R00", where, "disable-model-invocation must be true or false")


def check_fences(rel, lines, f):
    fences, _ = scan_fences(lines)
    for lang, first, body in fences:
        if lang in NON_CODE_LANGS:
            continue
        code = [ln for ln in body if ln.strip()]
        where = f"{rel}:{first}"
        if len(code) > MAX_FENCE_LINES:
            f.fail(
                "R07", where,
                f"{lang} block has {len(code)} lines (max {MAX_FENCE_LINES}); move it to scripts/",
            )
        if lang not in SHELL_LANGS:
            continue
        for offset, ln in enumerate(body):
            bare = QUOTED_RE.sub("''", ln).replace("\\;", "")
            at = f"{rel}:{first + 1 + offset}"
            if "&&" in bare or "||" in bare:
                f.fail("R07", at, "'&&' and '||' are forbidden; use separate commands or a script")
            if ";" in bare:
                f.fail("R07", at, "';' chaining is forbidden; use one command per line")
            if "<<" in bare:
                f.fail("R07", at, "heredocs are forbidden; move to scripts/")
            if SHELL_KEYWORD_RE.match(bare):
                f.fail("R07", at, "loops and conditionals are forbidden; move to scripts/")


def check_references(skill_dir, rel_path, text_lines, is_skill_md, f):
    local_dir = (skill_dir / rel_path).parent
    for n, line in enumerate(text_lines, 1):
        for target in LINK_RE.findall(line):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target):
                continue
            dest = (local_dir / target).resolve()
            where = f"{rel_path}:{n}"
            if not dest.exists():
                f.fail("R08", where, f"linked file not found: {target}")
            elif not is_skill_md and dest.suffix == ".md":
                f.fail("R04", where, f"reference links to another .md ({target}); keep references one level deep")
        for target in PATH_RE.findall(line):
            if not (skill_dir / target).exists():
                f.fail("R08", f"{rel_path}:{n}", f"referenced file not found: {target}")


def check_scripts(skill_dir, f):
    scripts = skill_dir / "scripts"
    if not scripts.is_dir():
        return
    for path in sorted(scripts.rglob("*")):
        if not path.is_file():
            continue
        with open(path, "rb") as fh:
            head = fh.read(2)
        if head == b"#!" and not os.access(path, os.X_OK):
            f.fail("R09", str(path.relative_to(skill_dir)), "script has a shebang but is not executable (chmod +x)")


def check_secrets_and_placeholders(skill_dir, f):
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.stat().st_size > MAX_SCAN_BYTES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(skill_dir)
        in_templates = rel.parts[0] == "templates"
        for n, line in enumerate(text.splitlines(), 1):
            for label, rx in SECRET_RES:
                if rx.search(line):
                    f.fail("R10", f"{rel}:{n}", f"possible secret ({label}); remove it, read it at runtime instead")
            if not in_templates and path.suffix == ".md" and PLACEHOLDER_RE.search(line):
                f.fail("R12", f"{rel}:{n}", "unfilled scaffold placeholder")


def check_unreferenced(skill_dir, skill_text, f):
    for sub in ("references", "templates", "scripts"):
        d = skill_dir / sub
        if not d.is_dir():
            continue
        for path in sorted(d.rglob("*")):
            if "__pycache__" in path.parts:
                continue
            if path.is_file() and path.name not in skill_text and str(path.relative_to(skill_dir)) not in skill_text:
                f.warn("W05", str(path.relative_to(skill_dir)), "file is not mentioned in SKILL.md")


def validate(skill_dir):
    f = Findings()
    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    fields, _ = parse_frontmatter(lines)
    check_frontmatter(fields, skill_md, f)

    if len(lines) > MAX_BODY_LINES:
        f.fail("R03", "SKILL.md", f"{len(lines)} lines (max {MAX_BODY_LINES}); split into reference files")

    docs = [(Path("SKILL.md"), lines, True)]
    for path in sorted(skill_dir.rglob("*.md")):
        rel = path.relative_to(skill_dir)
        if rel.name == "SKILL.md" and len(rel.parts) == 1:
            continue
        if rel.parts[0] in ("templates", "node_modules", ".git"):
            continue
        ref_lines = path.read_text(encoding="utf-8").splitlines()
        if len(ref_lines) > MAX_REF_LINES_NO_TOC and not any(
            re.match(r"^#{1,3}\s+Contents\b", ln, re.I) for ln in ref_lines
        ):
            f.fail("R05", str(rel), f"{len(ref_lines)} lines with no '## Contents' section")
        docs.append((rel, ref_lines, False))

    all_prose = []
    for rel, dlines, is_skill_md in docs:
        _, inside = scan_fences(dlines)
        check_references(skill_dir, rel, dlines, is_skill_md, f)
        emphasis = 0
        for n, line in prose_lines(dlines, inside):
            if re.search(r"[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+", line):
                f.fail("R06", f"{rel}:{n}", "backslash path; use forward slashes")
            if DATED_RE.search(line):
                f.fail("R11", f"{rel}:{n}", "time-sensitive phrase; move to an 'old patterns' note or drop")
            if REASONING_RE.search(line):
                f.warn("W03", f"{rel}:{n}", "instruction asks for reasoning in the output (refusal risk)")
            emphasis += len(EMPHASIS_RE.findall(line))
            all_prose.append(line.lower())
        if emphasis > MAX_EMPHASIS:
            f.warn("W01", str(rel), f"{emphasis} emphasis words (max {MAX_EMPHASIS}); use plain imperatives")
        if is_skill_md:
            check_fences(str(rel), dlines, f)

    blob = "\n".join(all_prose)
    for group in TERM_GROUPS:
        used = [t for t in group if t in blob]
        if len(used) > 1:
            f.warn("W04", "SKILL.md", f"mixed terms for one concept: {', '.join(used)}; pick one")

    check_scripts(skill_dir, f)
    check_secrets_and_placeholders(skill_dir, f)
    check_unreferenced(skill_dir, text, f)
    return f


def main(argv):
    if len(argv) != 2:
        print("usage: validate.py <skill-dir>", file=sys.stderr)
        return 2
    skill_dir = Path(argv[1]).resolve()
    if not (skill_dir / "SKILL.md").is_file():
        print(f"error: {skill_dir}/SKILL.md not found", file=sys.stderr)
        return 2
    f = validate(skill_dir)
    def order(item):
        file, _, line = item[2].partition(":")
        return (item[0] != "FAIL", file, int(line) if line.isdigit() else 0)

    for level, rule, where, msg in sorted(f.items, key=order):
        print(f"{level} {rule} {where}: {msg}")
    fails, warns = f.count("FAIL"), f.count("WARN")
    if fails:
        print(f"FAILED: {fails} fail, {warns} warn")
        return 1
    print(f"OK: 0 fail, {warns} warn")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
