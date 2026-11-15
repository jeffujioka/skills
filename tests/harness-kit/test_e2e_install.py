"""End-to-end: the harness-kit skill installs, and claude and opencode run nested in omp.

Needs claude, omp and opencode with the developer's credentials; every run uses a temporary HOME.
"""

import json
import re
import shutil
import subprocess
import unittest

from harness_home import MODELS, REPO, copy_credentials, env_for, make_home

HARNESSES = ("claude", "omp", "opencode")
INSTALL = REPO / "harness-kit" / "scripts" / "install.sh"
SKILL_PROMPT = (
    "Use the harness-kit skill to install harness-kit. "
    "The developer's answer to its question is: yes, install."
)
AGENT_ENV_PROMPT = "Run this exact shell command and reply with its output only: agent-env"
NESTED_IN_OMP = {"PI_SESSION_ID": "omp-outer", "AGENT_HARNESS": "omp"}


def strings_in(value):
    """Every string inside a decoded JSON value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings_in(item)


@unittest.skipIf(
    any(shutil.which(harness) is None for harness in HARNESSES),
    "claude, omp and opencode must all be installed",
)
class SkillInstallsEndToEnd(unittest.TestCase):
    def make(self, *credentials):
        home = make_home(self, harnesses=HARNESSES)
        for harness in credentials:
            copy_credentials(home, harness)
        return home

    def run_install(self, home, mode):
        return subprocess.run(
            ["bash", str(INSTALL), mode],
            capture_output=True,
            text=True,
            env=env_for(home),
            cwd=home,
        )

    def installed(self, *credentials):
        home = self.make(*credentials)
        result = self.run_install(home, "install")
        self.assertEqual(result.returncode, 0, result.stderr)
        return home

    def test_skill_installs_after_one_answer(self):
        home = self.make("claude")
        shutil.copytree(REPO / "harness-kit", home / ".claude" / "skills" / "harness-kit")
        result = subprocess.run(
            [
                "claude", "-p", "--output-format", "stream-json", "--verbose",
                "--dangerously-skip-permissions", "--model", MODELS["claude"],
                SKILL_PROMPT,
            ],
            cwd=home,
            env=env_for(home),
            capture_output=True,
            text=True,
            timeout=600,
        )
        commands = []
        for line in result.stdout.splitlines():
            event = json.loads(line)
            if event.get("type") != "assistant":
                continue
            for block in event["message"].get("content", []):
                if block.get("type") == "tool_use" and block.get("name") == "Bash":
                    commands.append(block["input"].get("command", ""))
        # The skill quotes the script path, so the command reads `install.sh" plan`.
        plans = [i for i, command in enumerate(commands) if re.search(r'install\.sh"?\s+plan', command)]
        installs = [i for i, command in enumerate(commands) if re.search(r'install\.sh"?\s+install', command)]
        self.assertTrue(plans, f"no install.sh plan in {commands}\n{result.stderr}")
        self.assertTrue(installs, f"no install.sh install in {commands}\n{result.stderr}")
        self.assertLess(plans[0], installs[0], commands)
        check = self.run_install(home, "check")
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_claude_nested_in_omp(self):
        home = self.installed("claude")
        result = subprocess.run(
            [
                "claude", "-p", "--output-format", "json",
                "--dangerously-skip-permissions", "--model", MODELS["claude"],
                AGENT_ENV_PROMPT,
            ],
            cwd=home,
            env=env_for(home, NESTED_IN_OMP),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        reply = json.loads(result.stdout)
        session = reply["session_id"]
        output = reply["result"]
        self.assertRegex(output, r"(?m)^AGENT_HARNESS=claude$")
        self.assertRegex(output, rf"(?m)^AGENT_SESSION_ID={re.escape(session)}$")
        self.assertRegex(output, rf"(?m)^AGENT_ROOT_SESSION_ID={re.escape(session)}$")

    def test_opencode_nested_in_omp(self):
        home = self.installed("opencode")
        project = home / "work" / "project"
        project.mkdir(parents=True)
        result = subprocess.run(
            [
                "opencode", "run", "--standalone", "--auto", "--format", "json",
                "-m", MODELS["opencode"],
                AGENT_ENV_PROMPT,
            ],
            cwd=project,
            env=env_for(home, NESTED_IN_OMP),
            capture_output=True,
            text=True,
            timeout=300,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
        sessions = {event["sessionID"] for event in events if "sessionID" in event}
        self.assertEqual(len(sessions), 1, result.stdout)
        session = sessions.pop()
        output = "\n".join(text for event in events for text in strings_in(event))
        self.assertRegex(output, r"(?m)^AGENT_HARNESS=opencode$")
        self.assertRegex(output, rf"(?m)^AGENT_SESSION_ID={re.escape(session)}$")
        self.assertRegex(output, rf"(?m)^AGENT_ROOT_SESSION_ID={re.escape(session)}$")


if __name__ == "__main__":
    unittest.main()
