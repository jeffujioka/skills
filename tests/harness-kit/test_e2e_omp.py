"""End-to-end: omp run nested inside a claude session (needs omp and its credentials)."""

import re
import shutil
import subprocess
import unittest
from pathlib import Path

from harness_home import (
    MODELS,
    REPO,
    copy_credentials,
    env_for,
    install_agent_env,
    install_skill,
    make_home,
)

PROMPT = (
    "Run this exact shell command and reply with its output only: "
    "agent-env; bash ~/.agents/skills/logbook/scripts/path.sh"
)


@unittest.skipIf(shutil.which("omp") is None, "omp is not installed")
class OmpNestedInClaude(unittest.TestCase):
    def test_omp_nested_in_claude(self):
        home = make_home(self, harnesses=("omp",))
        copy_credentials(home, "omp")
        install_agent_env(home)
        install_skill(home, "logbook")
        project = home / "work" / "project"
        project.mkdir(parents=True)
        env = env_for(
            home,
            {
                "CLAUDECODE": "1",
                "AGENT_HARNESS": "claude",
                "CLAUDE_CODE_SESSION_ID": "claude-outer",
            },
        )
        result = subprocess.run(
            [
                "omp", "-p", "--no-session", "--no-extensions",
                "-e", str(REPO / "harness-kit" / "omp" / "harness-kit.ts"),
                "--tools", "bash", "--auto-approve",
                "--model", MODELS["omp"],
                PROMPT,
            ],
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = result.stdout
        self.assertIn("AGENT_HARNESS=omp", output, result.stderr)
        match = re.search(r"^AGENT_SESSION_ID=(\S+)$", output, re.MULTILINE)
        self.assertIsNotNone(match, output)
        session = match.group(1)
        self.assertNotEqual(session, "claude-outer")
        self.assertRegex(output, rf"(?m)^AGENT_ROOT_SESSION_ID={re.escape(session)}$")
        slug = str(project).replace("/", "-").replace(" ", "-")
        logbook = Path(home) / ".local" / "state" / "agents" / "logbooks" / slug / session
        self.assertRegex(output, rf"(?m)^{re.escape(str(logbook))}$")


if __name__ == "__main__":
    unittest.main()
