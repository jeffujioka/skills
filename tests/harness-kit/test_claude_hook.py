"""The claude SessionStart hook sets AGENT_HARNESS through CLAUDE_ENV_FILE."""

import json
import subprocess
import unittest

from harness_home import REPO, env_for, install_agent_env, make_home

HOOK = REPO / "harness-kit" / "claude" / "session-start.sh"


class ClaudeHookTest(unittest.TestCase):
    def setUp(self):
        self.home = make_home(self)
        self.payload = json.dumps(
            {
                "session_id": "c1",
                "cwd": str(self.home),
                "source": "startup",
                "hook_event_name": "SessionStart",
            }
        )

    def run_hook(self, extra):
        return subprocess.run(
            ["bash", str(HOOK)],
            input=self.payload,
            capture_output=True,
            text=True,
            env=env_for(self.home, extra),
            cwd=self.home,
        )

    def test_env_file_sets_claude(self):
        env_file = self.home / "claude-env.sh"
        for _ in range(2):
            result = self.run_hook({"CLAUDE_ENV_FILE": str(env_file)})
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(env_file.read_text(), "export AGENT_HARNESS=claude\n")

        install_agent_env(self.home)
        result = subprocess.run(
            ["bash", "-c", 'source "$CLAUDE_ENV_FILE"; agent-env'],
            capture_output=True,
            text=True,
            env=env_for(
                self.home,
                {
                    "CLAUDE_ENV_FILE": str(env_file),
                    "AGENT_HARNESS": "omp",
                    "PI_SESSION_ID": "s9",
                    "CLAUDE_CODE_SESSION_ID": "c1",
                },
            ),
            cwd=self.home,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "AGENT_HARNESS=claude\nAGENT_SESSION_ID=c1\nAGENT_ROOT_SESSION_ID=c1\n",
        )

    def test_no_env_file(self):
        before = sorted(p for p in self.home.rglob("*"))
        result = self.run_hook({})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(sorted(p for p in self.home.rglob("*")), before)

    def run_compact(self, cwd, source="compact", progress=True):
        install_agent_env(self.home)
        cwd.mkdir(parents=True, exist_ok=True)
        slug = str(cwd).replace("/", "-").replace(" ", "-")
        logbook = self.home / ".local" / "state" / "agents" / "logbooks" / slug / "c1"
        if progress:
            logbook.mkdir(parents=True)
            (logbook / "progress.md").write_text("# progress\n")
        self.payload = json.dumps(
            {"session_id": "c1", "cwd": str(cwd), "source": source}
        )
        result = self.run_hook({})
        self.assertEqual(result.returncode, 0, result.stderr)
        return result, logbook

    def assert_reminder(self, result, logbook):
        output = json.loads(result.stdout)
        self.assertEqual(list(output), ["systemMessage", "hookSpecificOutput"])
        self.assertEqual(
            output["systemMessage"],
            f"harness-kit: logbook reminder sent to the model ({logbook})",
        )
        self.assertEqual(
            output["hookSpecificOutput"]["hookEventName"], "SessionStart"
        )
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn(f"`{logbook}/progress.md`", context)

    def test_compact_with_logbook(self):
        result, logbook = self.run_compact(self.home / "proj")
        self.assert_reminder(result, logbook)

    def test_compact_without_logbook(self):
        result, _ = self.run_compact(self.home / "proj", progress=False)
        self.assertEqual(result.stdout, "")

    def test_startup_adds_no_reminder(self):
        result, _ = self.run_compact(self.home / "proj", source="startup")
        self.assertEqual(result.stdout, "")

    def test_compact_cwd_with_spaces(self):
        cwd = self.home / "my project"
        result, logbook = self.run_compact(cwd)
        self.assertIn("-my-project", str(logbook))
        self.assert_reminder(result, logbook)


if __name__ == "__main__":
    unittest.main()
