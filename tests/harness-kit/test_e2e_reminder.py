"""End-to-end: after a real compaction each harness passes on the logbook reminder.

Needs claude, omp and opencode with the developer's credentials. Every run uses a temporary
HOME, and each harness gets a compaction threshold for that session only (spec D17).
"""

import json
import os
import shutil
import signal
import sqlite3
import subprocess
import unittest

from harness_home import (
    MODELS,
    REPO,
    copy_credentials,
    env_for,
    install_skill,
    make_home,
    write_filler,
)

HARNESSES = ("claude", "omp", "opencode")
INSTALL = REPO / "harness-kit" / "scripts" / "install.sh"
TURN_TIMEOUT = 600
LOGBOOK_PROMPT = (
    "Run `bash ~/.agents/skills/logbook/scripts/path.sh`, then create progress.md in the folder "
    "it prints holding the lines `## Next` and `- finish`, and reply with the folder"
)
QUOTE_PROMPT = "Quote the line of your context that starts with Context was compacted., or reply none"


def filler_prompt(command):
    return f"Run `{command}` and reply ok"


def run_turn(command, project, env):
    """Run one harness turn; on timeout kill its whole process group."""
    process = subprocess.Popen(
        command,
        cwd=project,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=TURN_TIMEOUT)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        raise AssertionError(f"timed out after {TURN_TIMEOUT}s: {command}\n{stdout[-4000:]}\n{stderr[-4000:]}")
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def describe(*turns):
    return "\n".join(
        f"--- exit {turn.returncode}\nstdout:\n{turn.stdout[-4000:]}\nstderr:\n{turn.stderr[-4000:]}"
        for turn in turns
    )


@unittest.skipIf(
    any(shutil.which(harness) is None for harness in HARNESSES),
    "claude, omp and opencode must all be installed",
)
class ReminderAfterCompaction(unittest.TestCase):
    def setup_harness(self, harness):
        """A temp HOME with harness-kit installed, the harness's credentials and the logbook skill."""
        home = make_home(self, harnesses=HARNESSES)
        # Credentials first: claude's copy rewrites ~/.claude/settings.json, which install then extends.
        copy_credentials(home, harness)
        install = subprocess.run(
            ["bash", str(INSTALL), "install"],
            capture_output=True,
            text=True,
            env=env_for(home),
            cwd=home,
        )
        self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
        install_skill(home, "logbook")
        project = home.parent.parent / "project"
        project.mkdir()
        filler = write_filler(project / "filler.txt")
        return home, project, filler

    def reminder(self, home, project, session_variables, turns):
        """agent-env's reminder for the session, which exists once turn 1 wrote progress.md."""
        result = subprocess.run(
            [str(home / ".local" / "bin" / "agent-env"), "compact-reminder"],
            capture_output=True,
            text=True,
            env=env_for(home, session_variables),
            cwd=project,
        )
        self.assertEqual(result.returncode, 0, result.stderr + describe(*turns))
        reminder = result.stdout.strip()
        self.assertTrue(reminder, f"no progress.md in the session's logbook\n{describe(*turns)}")
        return reminder

    def test_claude_compaction_reminder(self):
        home, project, filler = self.setup_harness("claude")
        # The window has a 100k floor, so the percent override sets the threshold below it. claude keeps at
        # most 128000 characters of bash output inline (bashOutputMaxChars), so it reads 2000 filler lines.
        env = env_for(home, {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "100000", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "30"})
        command = [
            "claude", "-p", "--settings", json.dumps({"bashOutputMaxChars": 128000}), "--output-format", "json",
            "--dangerously-skip-permissions", "--model", MODELS["claude"],
        ]

        first = run_turn([*command, LOGBOOK_PROMPT], project, env)
        self.assertEqual(first.returncode, 0, describe(first))
        session = json.loads(first.stdout)["session_id"]
        resume = [*command, "--resume", session]
        second = run_turn([*resume, filler_prompt(f"head -n 2000 {filler}")], project, env)
        third = run_turn([*resume, QUOTE_PROMPT], project, env)
        turns = (first, second, third)

        reminder = self.reminder(home, project, {"AGENT_HARNESS": "claude", "CLAUDE_CODE_SESSION_ID": session}, turns)
        folder = reminder.split("`")[1].rsplit("/", 1)[0]
        self.assertEqual(third.returncode, 0, describe(*turns))
        reply = json.loads(third.stdout)["result"]
        self.assertIn("Context was compacted.", reply, describe(*turns))
        self.assertIn(folder, reply, describe(*turns))

    def test_omp_compaction_reminder(self):
        home, project, filler = self.setup_harness("omp")
        config = home.parent.parent / "compact.yml"
        config.write_text("compaction:\n  thresholdTokens: 20000\n")
        env = env_for(home)
        command = [
            "omp", "-p", "--config", str(config), "--tools", "bash", "--auto-approve",
            "--model", MODELS["omp"],
        ]

        first = run_turn([*command, LOGBOOK_PROMPT], project, env)
        second = run_turn([*command, "--continue", filler_prompt(f"cat {filler}")], project, env)
        third = run_turn([*command, "--continue", QUOTE_PROMPT], project, env)
        turns = (first, second, third)

        logs = sorted((home / ".omp" / "agent" / "sessions").glob("*/*.jsonl"))
        self.assertEqual(len(logs), 1, f"session files: {logs}\n{describe(*turns)}")
        log = logs[0]
        session = log.stem.split("_", 1)[1]
        reminder = self.reminder(
            home, project,
            {"AGENT_HARNESS": "omp", "PI_SESSION_ID": session, "PI_SESSION_FILE": str(log)},
            turns,
        )
        entries = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
        types = [entry.get("type") for entry in entries]
        self.assertIn("compaction", types, describe(*turns))
        after_compaction = entries[types.index("compaction") + 1:]
        self.assertTrue(
            any(
                entry.get("type") == "custom_message"
                and entry.get("customType") == "harness-kit-reminder"
                and entry.get("content") == reminder
                for entry in after_compaction
            ),
            f"entries after compaction: {after_compaction}\n{describe(*turns)}",
        )

    def test_opencode_compaction_reminder(self):
        home, project, filler = self.setup_harness("opencode")
        (project / "opencode.json").write_text(json.dumps({"compaction": {"auto": True, "buffer": "99%"}}))
        env = env_for(home)
        command = [
            "opencode", "run", "--standalone", "--auto", "--format", "json",
            "-m", MODELS["opencode"],
        ]

        first = run_turn([*command, LOGBOOK_PROMPT], project, env)
        second = run_turn([*command, "--continue", filler_prompt(f"cat {filler}")], project, env)
        third = run_turn([*command, "--continue", QUOTE_PROMPT], project, env)
        turns = (first, second, third)

        sessions = {
            event["sessionID"]
            for line in first.stdout.splitlines()
            if line.startswith("{")
            for event in [json.loads(line)]
            if "sessionID" in event
        }
        self.assertEqual(len(sessions), 1, describe(*turns))
        session = sessions.pop()
        reminder = self.reminder(home, project, {"AGENT_HARNESS": "opencode", "OPENCODE_SESSION_ID": session}, turns)
        database = home / ".local" / "share" / "opencode" / "opencode.db"
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            values = [
                row[0]
                for row in connection.execute(
                    "SELECT value FROM instruction_entry"
                    " WHERE session_id = ? AND key = 'harness-kit-compact-reminder' AND removed = 0",
                    (session,),
                )
            ]
        # The value is stored JSON-encoded (harness-kit/references/opencode.md).
        self.assertIn(reminder, [json.loads(value) for value in values], f"{values}\n{describe(*turns)}")


if __name__ == "__main__":
    unittest.main()
