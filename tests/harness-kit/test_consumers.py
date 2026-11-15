"""The skills that consume agent-env stop with one sentence when harness-kit is missing."""

import re
import subprocess
import unittest

from harness_home import REPO, env_for, install_skill, make_home

SENTENCE = (
    "agent-env not found: harness-kit is not installed. "
    "Ask your agent to run the harness-kit skill, then start a new session."
)


class ConsumersTest(unittest.TestCase):
    def test_agent_env_missing(self):
        home = make_home(self)
        skills = home / ".agents" / "skills"
        install_skill(home, "logbook")
        install_skill(home, "captain-away")
        for script in (skills / "logbook" / "scripts" / "path.sh", skills / "captain-away" / "scripts" / "cost.sh"):
            with self.subTest(script=script.name):
                result = subprocess.run(
                    ["bash", str(script)], capture_output=True, text=True, env=env_for(home), cwd=home
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, SENTENCE + "\n")
                self.assertFalse((home / ".local" / "state" / "agents").exists())

        text = (REPO / "handoff-hc" / "SKILL.md").read_text()
        step2 = re.search(r"^2\. .*$", text, re.MULTILINE).group(0)
        self.assertIn(SENTENCE, step2)
        for stale in ("OPENCODE=1", "CLAUDECODE=1", ".foreground.name"):
            self.assertNotIn(stale, step2)

    def test_handoff_stops_when_agent_env_fails(self):
        text = (REPO / "handoff-hc" / "SKILL.md").read_text()
        step2 = re.search(r"^2\. .*$", text, re.MULTILINE).group(0)
        stops = text.split("## Stops", 1)[1].split("\n## ", 1)[0]
        self.assertIn("If `agent-env` exits non-zero, stop and show its stderr", step2)
        self.assertIn("`agent-env` exits non-zero (step 2)", stops)


if __name__ == "__main__":
    unittest.main()
