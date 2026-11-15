"""logbook no longer offers compaction and documents each harness."""

import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "logbook"


class SkillTest(unittest.TestCase):
    def test_no_compaction_left(self):
        for script in ("compact.sh", "compaction-status.sh"):
            self.assertFalse((SKILL / "scripts" / script).exists(), script)
        text = (SKILL / "SKILL.md").read_text()
        self.assertNotIn("## Compact on request", text)
        self.assertNotIn("compact.sh", text)
        description = re.search(r"^description: (.*)$", text, re.M).group(1)
        self.assertNotIn("compact or compress", description)
        for harness in ("claude", "omp", "opencode"):
            ref = f"references/{harness}.md"
            self.assertTrue((SKILL / ref).is_file(), ref)
            self.assertIn(f"]({ref})", text)
        opencode = (SKILL / "references" / "opencode.md").read_text()
        for name in ("compact.sh", "compaction-status.sh", "/compact"):
            self.assertIn(name, opencode)


if __name__ == "__main__":
    unittest.main()
