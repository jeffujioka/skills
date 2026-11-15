"""Spike (spec D17): the omp and opencode compaction events deliver the reminder.

Each test runs a throwaway session in a temporary HOME whose compaction
threshold is set for that session only, so compaction fires on the filler.
"""

import json
import shutil
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness_home import MODELS, REPO, copy_credentials, env_for, make_home, write_filler  # noqa: E402

SPIKES = REPO / "tests" / "harness-kit" / "spikes"
SPIKE_REMINDER = (
    "Context was compacted. Read `~/.local/state/agents/logbooks/spike/r1/progress.md`, "
    "`decisions.md`, `needs-you.md` before anything else; continue from `## Next`."
)
TURN_TIMEOUT = 900


def run_turn(command, project, env):
    return subprocess.run(
        command, cwd=project, env=env, capture_output=True, text=True, timeout=TURN_TIMEOUT
    )


def describe(*turns):
    return "\n".join(
        f"--- exit {turn.returncode}\nstdout:\n{turn.stdout[-4000:]}\nstderr:\n{turn.stderr[-4000:]}"
        for turn in turns
    )


class CompactionSpike(unittest.TestCase):
    def test_omp_session_compact_appends_reminder(self):
        home = make_home(self, harnesses=("omp",))
        copy_credentials(home, "omp")
        tmp = home.parent.parent
        project = tmp / "project"
        project.mkdir()
        filler = write_filler(project / "filler.txt")
        config = tmp / "compact.yml"
        # omp keeps at most 50 KiB of bash output inline (about 23k tokens of filler),
        # so 40000 is never crossed; 20000 is.
        config.write_text("compaction:\n  thresholdTokens: 20000\n")
        command = [
            "omp", "-p", "--config", str(config), "--no-extensions",
            "-e", str(SPIKES / "omp-reminder.ts"),
            "--no-skills", "--no-rules", "--no-context-files", "--tools", "bash",
            "--auto-approve", "--model", MODELS["omp"],
        ]
        env = env_for(home)

        first = run_turn([*command, f"Run cat {filler} and reply ok"], project, env)
        second = run_turn([*command, "--continue", "Reply ok"], project, env)

        entries = [
            json.loads(line)
            for log in (home / ".omp" / "agent" / "sessions").rglob("*.jsonl")
            for line in log.read_text().splitlines()
            if line.strip()
        ]
        types = [entry.get("type") for entry in entries]
        self.assertIn("compaction", types, describe(first, second))
        after_compaction = entries[types.index("compaction") + 1:]
        self.assertTrue(
            any(
                entry.get("type") == "custom_message"
                and SPIKE_REMINDER in json.dumps(entry.get("content"), ensure_ascii=False)
                for entry in after_compaction
            ),
            f"entry types: {types}\n{describe(first, second)}",
        )

    def test_opencode_compaction_ended_puts_instruction(self):
        home = make_home(self, harnesses=("opencode",))
        copy_credentials(home, "opencode")
        project = home.parent.parent / "project"
        plugins = project / ".opencode" / "plugins"
        plugins.mkdir(parents=True)
        shutil.copyfile(SPIKES / "opencode-reminder.ts", plugins / "opencode-reminder.ts")
        # opencode's auto check fires only near a 99% buffer for this filler.
        (project / "opencode.json").write_text(
            json.dumps({"compaction": {"auto": True, "buffer": "99%"}})
        )
        filler = write_filler(project / "filler.txt")
        command = [
            "opencode", "run", "--standalone", "--auto", "--format", "json",
            "-m", MODELS["opencode"],
        ]
        env = env_for(home)

        first = run_turn([*command, f"Run cat {filler} and reply ok"], project, env)
        second = run_turn(
            [*command, "--continue",
             "Quote the line of your instructions that starts with Context was compacted."],
            project, env,
        )

        database = home / ".local" / "share" / "opencode" / "opencode.db"
        self.assertTrue(database.is_file(), describe(first, second))
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            rows = connection.execute(
                "SELECT e.value, b.value FROM instruction_entry e"
                " JOIN session_v2 s ON s.id = e.session_id"
                " LEFT JOIN instruction_blob b ON b.hash = e.value"
                " WHERE e.key = 'harness-kit-compact-reminder' AND e.removed = 0"
                " AND s.directory = ?",
                (str(project),),
            ).fetchall()
        self.assertTrue(
            any(SPIKE_REMINDER in (value or "") for row in rows for value in row),
            f"instruction entries: {rows}\n{describe(first, second)}",
        )


if __name__ == "__main__":
    unittest.main()
