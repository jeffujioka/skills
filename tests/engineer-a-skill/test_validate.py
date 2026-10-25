import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "engineer-a-skill" / "scripts"))
import validate  # noqa: E402

FM = '---\nname: probe\ndescription: "Probes things. Use when testing."\n---\n'


def make_skill(files: dict[str, str], name: str = "probe") -> Path:
    tmp = Path(tempfile.mkdtemp())
    skill_dir = tmp / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    if "SKILL.md" not in files:
        files = dict(files)
        files["SKILL.md"] = FM + "One-line body.\n"
    for rel, content in files.items():
        path = skill_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return skill_dir


def rules(skill: Path) -> set[tuple[str, str]]:
    findings = validate.validate(skill)
    return {(item[0], item[1]) for item in findings.items}


class SkillTestCase(unittest.TestCase):
    def addCleanup_tmp(self, skill: Path):
        self.addCleanup(shutil.rmtree, skill.parent, ignore_errors=True)


class FenceTests(SkillTestCase):
    def test_untagged_fence_with_loop_fails(self):
        skill = make_skill({
            "SKILL.md": FM + "Body.\n\n```\nfor f in *; do rm \"$f\"; done\n```\n",
        })
        self.addCleanup_tmp(skill)
        self.assertIn(("FAIL", "R07"), rules(skill))

    def test_untagged_fence_over_3_lines_fails(self):
        skill = make_skill({
            "SKILL.md": FM + "Body.\n\n```\na\nb\nc\nd\n```\n",
        })
        self.addCleanup_tmp(skill)
        self.assertIn(("FAIL", "R07"), rules(skill))

    def test_text_fence_exempt(self):
        skill = make_skill({
            "SKILL.md": FM + "Body.\n\n```text\na\nb\nc\nd\ne\n```\n",
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R07", ids)


class NestingTests(SkillTestCase):
    def test_backticked_md_path_in_reference_fails(self):
        skill = make_skill({
            "SKILL.md": FM + "See `references/a.md`.\n",
            "references/a.md": "See `references/b.md`.\n",
            "references/b.md": "x\n",
        })
        self.addCleanup_tmp(skill)
        self.assertIn(("FAIL", "R04"), rules(skill))

    def test_backticked_script_path_in_reference_ok(self):
        skill = make_skill({
            "SKILL.md": FM + "See `references/a.md`.\n",
            "references/a.md": "See `scripts/run.py`.\n",
            "scripts/run.py": "x\n",
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R04", ids)

    def test_backticked_md_path_in_skill_md_ok(self):
        skill = make_skill({
            "SKILL.md": FM + "See `references/a.md`.\n",
            "references/a.md": "x\n",
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R04", ids)


if __name__ == "__main__":
    unittest.main()
