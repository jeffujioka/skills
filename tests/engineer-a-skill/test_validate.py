import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "engineer-a-skill" / "scripts"))
import run_evals  # noqa: E402
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

    def test_untagged_fence_message_mentions_tagging_as_text(self):
        skill = make_skill({
            "SKILL.md": FM + "Body.\n\n```\nfor f in *; do rm \"$f\"; done\n```\n",
        })
        self.addCleanup_tmp(skill)
        findings = validate.validate(skill)
        messages = [item[3] for item in findings.items if item[1] == "R07"]
        self.assertTrue(
            any("tag non-shell blocks as text" in m for m in messages),
            messages,
        )

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


class FalsePositiveTests(SkillTestCase):
    def test_number_with_unit_not_dated(self):
        skill = make_skill({
            "SKILL.md": FM + "Read buffers in 2048 byte chunks.\n",
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R11", ids)

    def test_hyphenated_number_not_dated(self):
        skill = make_skill({
            "SKILL.md": FM + "Use in 2048-byte blocks.\n",
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R11", ids)

    def test_real_year_dated(self):
        skill = make_skill({
            "SKILL.md": FM + "Valid as of 2025.\n",
        })
        self.addCleanup_tmp(skill)
        self.assertIn(("FAIL", "R11"), rules(skill))

    def test_month_year_dated(self):
        skill = make_skill({
            "SKILL.md": FM + "Deprecated before March 2026.\n",
        })
        self.addCleanup_tmp(skill)
        self.assertIn(("FAIL", "R11"), rules(skill))

    def test_iso_date_as_of_dated(self):
        skill = make_skill({
            "SKILL.md": FM + "as of 2025-06-01 the API changed\n",
        })
        self.addCleanup_tmp(skill)
        self.assertIn(("FAIL", "R11"), rules(skill))

    def test_iso_date_in_dated(self):
        skill = make_skill({
            "SKILL.md": FM + "Deprecated in 2025-03.\n",
        })
        self.addCleanup_tmp(skill)
        self.assertIn(("FAIL", "R11"), rules(skill))

    def test_number_with_pixels_not_dated(self):
        skill = make_skill({
            "SKILL.md": FM + "Use in 2048x2048 images.\n",
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R11", ids)

    def test_password_label_not_secret(self):
        skill = make_skill({
            "SKILL.md": FM + "Set password: required in the form.\n",
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R10", ids)

    def test_quoted_password_secret(self):
        secret = "pass" + "word"
        skill = make_skill({
            "SKILL.md": FM + f'{secret}: "hunter22"\n',
        })
        self.addCleanup_tmp(skill)
        self.assertIn(("FAIL", "R10"), rules(skill))

    def test_quoted_env_var_ref_not_secret(self):
        secret = "TOKEN"
        skill = make_skill({
            "SKILL.md": FM + f'{secret}="${{GITHUB_TOKEN}}"\n',
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R10", ids)

    def test_quoted_dollar_var_ref_not_secret(self):
        secret = "api_" + "key"
        skill = make_skill({
            "SKILL.md": FM + f'{secret}: "$API_KEY"\n',
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R10", ids)

    def test_quoted_angle_placeholder_not_secret(self):
        secret = "pass" + "word"
        skill = make_skill({
            "SKILL.md": FM + f'{secret}: "<your-password>"\n',
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R10", ids)

    def test_quoted_asterisk_placeholder_not_secret(self):
        secret = "secret"
        skill = make_skill({
            "SKILL.md": FM + f'{secret}: "********"\n',
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R10", ids)

    def test_quoted_all_caps_placeholder_not_secret(self):
        secret = "to" + "ken"
        skill = make_skill({
            "SKILL.md": FM + f'{secret}: "YOUR_TOKEN"\n',
        })
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R10", ids)

    def test_mixed_unquoted_key_secret(self):
        prefix = "api_" + "key"
        value = "abc123def456"
        skill = make_skill({
            "SKILL.md": FM + f"{prefix}={value}\n",
        })
        self.addCleanup_tmp(skill)
        self.assertIn(("FAIL", "R10"), rules(skill))


class LimitTests(SkillTestCase):
    def test_body_limit_excludes_frontmatter(self):
        # Frontmatter with 10 x-pad lines + 495 body lines = 505 total lines
        # But body is only 495, so should NOT trigger R03
        fm_lines = ["---", "name: probe", 'description: "Use when testing."']
        for i in range(10):
            fm_lines.append("x-pad: 1")
        fm_lines.append("---")
        fm_text = "\n".join(fm_lines) + "\n"

        body_lines = ["Body line."] * 495
        skill_md = fm_text + "\n".join(body_lines) + "\n"

        skill = make_skill({"SKILL.md": skill_md})
        self.addCleanup_tmp(skill)
        ids = {rule_id for _, rule_id in rules(skill)}
        self.assertNotIn("R03", ids)

    def test_body_over_500_fails(self):
        # Minimal frontmatter + 501 body lines should trigger R03
        fm_text = FM
        body_lines = ["Body line."] * 501
        skill_md = fm_text + "\n".join(body_lines) + "\n"

        skill = make_skill({"SKILL.md": skill_md})
        self.addCleanup_tmp(skill)
        self.assertIn(("FAIL", "R03"), rules(skill))


class EvalsTests(SkillTestCase):
    def test_eval_fixture_breaking_rules_is_skipped(self):
        skill = make_skill({
            "evals/files/bad/SKILL.md": "---\nname: Bad_Skill\ndescription: I help you.\n---\n"
            "Run `scripts\\x.py` before 2024. <<FILL>>\n",
        })
        self.addCleanup_tmp(skill)
        self.assertEqual(set(), rules(skill))

    def test_secret_in_eval_fixture_still_fails(self):
        skill = make_skill({"evals/files/x.md": 'password = "hunter2hunter2"\n'})
        self.addCleanup_tmp(skill)
        self.assertIn(("FAIL", "R10"), rules(skill))


class WhenClauseTests(SkillTestCase):
    def test_manual_only_call_by_name_counts_as_when(self):
        fm = ('---\nname: probe\ndescription: "Probes things. Manual-only: call it by name."\n'
              "disable-model-invocation: true\n---\n")
        skill = make_skill({"SKILL.md": fm + "Body.\n"})
        self.addCleanup_tmp(skill)
        self.assertNotIn(("WARN", "W02"), rules(skill))


class RunEvalsTests(SkillTestCase):
    def test_last_json_skips_draft_and_nested_values(self):
        text = 'draft {"results": []} then {"results": [{"pass": true, "x": {"y": 1}}]} done'
        self.assertEqual({"results": [{"pass": True, "x": {"y": 1}}]}, run_evals.last_json(text))

    def test_prepare_copies_skill_and_strips_fixture_prefix(self):
        skill = make_skill({"evals/files/bad-skill/SKILL.md": "x\n"})
        self.addCleanup_tmp(skill)
        work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, work, ignore_errors=True)
        copy = run_evals.prepare(skill, {"files": ["evals/files/bad-skill/SKILL.md"]}, work)
        self.assertTrue((copy / "SKILL.md").is_file())
        self.assertTrue((work / "bad-skill" / "SKILL.md").is_file())

    def test_prepare_baseline_skips_skill_copy(self):
        skill = make_skill({"evals/files/bad-skill/SKILL.md": "x\n"})
        self.addCleanup_tmp(skill)
        work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, work, ignore_errors=True)
        copy = run_evals.prepare(skill, {"files": ["evals/files/bad-skill/SKILL.md"]}, work, with_skill=False)
        self.assertFalse(copy.exists())
        self.assertTrue((work / "bad-skill" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
