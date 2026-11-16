"""omp-agent.sh writes, removes and sweeps the short-lived omp agent files that hire dispatches."""

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "hire" / "scripts" / "omp-agent.sh"


class OmpAgentTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.agents = self.home / ".omp" / "agent" / "agents"

    def run_script(self, *args):
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": str(self.home)},
        )

    def test_create_writes_a_pinned_agent_and_prints_its_name(self):
        result = self.run_script("create", "github-copilot/claude-opus-5.5-1m", "xhigh")
        self.assertEqual(result.returncode, 0, result.stderr)
        name = result.stdout.strip()
        self.assertRegex(name, r"^hire-opus-5\.5-1m-xhigh-[0-9a-f]{6}$")
        text = (self.agents / f"{name}.md").read_text()
        self.assertIn(f"name: {name}\n", text)
        self.assertIn("model: github-copilot/claude-opus-5.5-1m\n", text)
        self.assertIn("thinking-level: xhigh\n", text)

    def test_two_creates_get_distinct_names(self):
        first = self.run_script("create", "github-copilot/claude-haiku-5.5-1m", "low").stdout.strip()
        second = self.run_script("create", "github-copilot/claude-haiku-5.5-1m", "low").stdout.strip()
        self.assertNotEqual(first, second)

    def test_remove_deletes_only_that_agent(self):
        keep = self.run_script("create", "github-copilot/claude-haiku-5.5-1m", "low").stdout.strip()
        gone = self.run_script("create", "github-copilot/claude-haiku-5.5-1m", "low").stdout.strip()
        result = self.run_script("remove", gone)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.stem for p in self.agents.iterdir()), [keep])

    def test_remove_refuses_a_name_hire_did_not_make(self):
        self.agents.mkdir(parents=True)
        (self.agents / "scout.md").write_text("x")
        result = self.run_script("remove", "scout")
        self.assertEqual(result.returncode, 2)
        self.assertTrue((self.agents / "scout.md").exists())

    def test_create_sweeps_hire_files_older_than_a_day(self):
        self.agents.mkdir(parents=True)
        stale = self.agents / "hire-opus-5.5-1m-high-abcdef.md"
        other = self.agents / "my-agent.md"
        for path in (stale, other):
            path.write_text("x")
            old = time.time() - 2 * 86400
            os.utime(path, (old, old))
        self.run_script("create", "github-copilot/claude-opus-5.5-1m", "high")
        self.assertFalse(stale.exists())
        self.assertTrue(other.exists())

    def test_create_rejects_a_bad_level(self):
        result = self.run_script("create", "github-copilot/claude-opus-5.5-1m", "xmax")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.agents.exists() and any(self.agents.iterdir()))


if __name__ == "__main__":
    unittest.main()
