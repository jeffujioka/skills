"""agent-env prints the session contract on claude, omp and opencode."""

import sqlite3
import subprocess
import threading
import time
import unittest
from pathlib import Path

from harness_home import REPO, env_for, make_home

AGENT_ENV = REPO / "harness-kit" / "bin" / "agent-env"


def contract(harness, session, root):
    return f"AGENT_HARNESS={harness}\nAGENT_SESSION_ID={session}\nAGENT_ROOT_SESSION_ID={root}\n"


def make_db(home):
    db = Path(home) / ".local" / "share" / "opencode" / "opencode.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "create table session_v2(id text primary key, parent_id text, cost real not null default 0)"
        )
        connection.executemany(
            "insert into session_v2(id, parent_id) values (?, ?)",
            [("o1", None), ("o2", "o1"), ("o3", "o2")],
        )
    connection.close()
    return db


class AgentEnvTest(unittest.TestCase):
    def setUp(self):
        self.home = make_home(self)

    def run_agent_env(self, extra, *args, cwd=None):
        return subprocess.run(
            ["bash", str(AGENT_ENV), *args],
            capture_output=True,
            text=True,
            env=env_for(self.home, extra),
            cwd=cwd,
        )

    def assert_logbook_dir(self, name):
        cwd = self.home / name
        cwd.mkdir()
        folder = self.home / ".omp" / "agent" / "sessions" / "-p"
        result = self.run_agent_env(
            {
                "AGENT_HARNESS": "omp",
                "PI_SESSION_ID": "s2",
                "PI_SESSION_FILE": str(folder / "2026-11-14T10-00-00-000Z_r1" / "Sub.jsonl"),
            },
            "logbook-dir",
            cwd=cwd,
        )
        slug = str(cwd).replace("/", "-").replace(" ", "-")
        logbooks = self.home / ".local" / "state" / "agents" / "logbooks"
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertEqual(result.stdout, f"{logbooks / slug / 'r1'}\n")
        self.assertFalse(logbooks.exists())
        return slug

    def test_logbook_dir(self):
        self.assert_logbook_dir("proj")

    def test_logbook_dir_cwd_with_spaces(self):
        self.assertTrue(self.assert_logbook_dir("my project").endswith("-my-project"))

    def test_unknown_command(self):
        result = self.run_agent_env({"PI_SESSION_ID": "s1"}, "frobnicate")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "agent-env: unknown command frobnicate\n")

    def run_compact_reminder(self):
        cwd = self.home / "proj"
        cwd.mkdir(exist_ok=True)
        folder = self.home / ".omp" / "agent" / "sessions" / "-p"
        result = self.run_agent_env(
            {
                "AGENT_HARNESS": "omp",
                "PI_SESSION_ID": "s2",
                "PI_SESSION_FILE": str(folder / "2026-11-14T10-00-00-000Z_r1" / "Sub.jsonl"),
            },
            "compact-reminder",
            cwd=cwd,
        )
        slug = str(cwd).replace("/", "-").replace(" ", "-")
        logbook = self.home / ".local" / "state" / "agents" / "logbooks" / slug / "r1"
        return result, logbook

    def test_compact_reminder_with_progress(self):
        _, logbook = self.run_compact_reminder()
        logbook.mkdir(parents=True)
        (logbook / "progress.md").write_text("## Next\n")
        result, _ = self.run_compact_reminder()
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertEqual(
            result.stdout,
            f"Context was compacted. Read `{logbook}/progress.md`, `decisions.md`, "
            "`needs-you.md` before anything else; continue from `## Next`.\n",
        )

    def test_compact_reminder_without_progress(self):
        result, logbook = self.run_compact_reminder()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        self.assertFalse(logbook.parent.parent.exists())
        logbook.mkdir(parents=True)
        (logbook / "decisions.md").write_text("")
        result, _ = self.run_compact_reminder()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        self.assertEqual([p.name for p in logbook.iterdir()], ["decisions.md"])

    def assert_prints(self, extra, harness, session, root):
        result = self.run_agent_env(extra)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertEqual(result.stdout, contract(harness, session, root))

    def assert_fails(self, extra, message):
        result = self.run_agent_env(extra)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, f"agent-env: {message}\n")

    def test_claude_ids(self):
        self.assert_prints(
            {"AGENT_HARNESS": "claude", "CLAUDE_CODE_SESSION_ID": "c1", "PI_SESSION_ID": "s9"},
            "claude", "c1", "c1",
        )

    def test_omp_subagent_root(self):
        folder = self.home / ".omp" / "agent" / "sessions" / "-p"
        self.assert_prints(
            {
                "AGENT_HARNESS": "omp",
                "PI_SESSION_ID": "s2",
                "PI_SESSION_FILE": str(folder / "2026-11-14T10-00-00-000Z_r1" / "Sub.jsonl"),
            },
            "omp", "s2", "r1",
        )
        self.assert_prints(
            {
                "AGENT_HARNESS": "omp",
                "PI_SESSION_ID": "r1",
                "PI_SESSION_FILE": str(folder / "2026-11-14T10-00-00-000Z_r1.jsonl"),
            },
            "omp", "r1", "r1",
        )

    def test_opencode_subagent_root(self):
        make_db(self.home)
        self.assert_prints(
            {"AGENT_HARNESS": "opencode", "OPENCODE_SESSION_ID": "o3"}, "opencode", "o3", "o1"
        )

    def test_fallback_without_hook(self):
        self.assert_prints({"PI_SESSION_ID": "s1"}, "omp", "s1", "s1")

    def test_no_session_file_is_own_root(self):
        self.assert_prints(
            {"AGENT_HARNESS": "omp", "PI_SESSION_ID": "s1", "PI_SESSION_FILE": ""}, "omp", "s1", "s1"
        )

    def test_opencode_db_locked(self):
        db = make_db(self.home)
        locked = threading.Event()

        def hold_lock():
            connection = sqlite3.connect(db, isolation_level=None)
            connection.execute("BEGIN EXCLUSIVE")
            locked.set()
            time.sleep(1)
            connection.execute("COMMIT")
            connection.close()

        holder = threading.Thread(target=hold_lock)
        holder.start()
        locked.wait()
        try:
            self.assert_prints(
                {"AGENT_HARNESS": "opencode", "OPENCODE_SESSION_ID": "o3"}, "opencode", "o3", "o1"
            )
        finally:
            holder.join()

    def run_root_source(self, extra):
        result = self.run_agent_env(extra, "root-source")
        return result.returncode, result.stdout, result.stderr

    def test_root_source_claude(self):
        claude = {"AGENT_HARNESS": "claude", "CLAUDE_CODE_SESSION_ID": "c1"}
        projects = self.home / ".claude" / "projects"
        self.assertEqual(
            self.run_root_source(claude),
            (1, "", f"agent-env: no transcript {projects}/*/c1.jsonl\n"),
        )
        transcript = projects / "-x" / "c1.jsonl"
        transcript.parent.mkdir(parents=True)
        transcript.write_text("")
        self.assertEqual(self.run_root_source(claude), (0, f"TRANSCRIPT={transcript}\n", ""))

    def test_root_source_claude_several_transcripts(self):
        projects = self.home / ".claude" / "projects"
        first, second = projects / "-a" / "c1.jsonl", projects / "-b" / "c1.jsonl"
        for transcript in (first, second):
            transcript.parent.mkdir(parents=True)
            transcript.write_text("")
        self.assertEqual(
            self.run_root_source({"AGENT_HARNESS": "claude", "CLAUDE_CODE_SESSION_ID": "c1"}),
            (1, "", f"agent-env: several transcripts for session c1: {first} {second}\n"),
        )

    def test_root_source_omp(self):
        folder = self.home / ".omp" / "agent" / "sessions" / "-p"
        root = folder / "2026-11-14T10-00-00-000Z_r1.jsonl"
        sub = folder / "2026-11-14T10-00-00-000Z_r1" / "Sub.jsonl"
        omp = {"AGENT_HARNESS": "omp", "PI_SESSION_ID": "s2", "PI_SESSION_FILE": str(sub)}
        self.assertEqual(self.run_root_source(omp), (1, "", f"agent-env: {root} not found\n"))
        sub.parent.mkdir(parents=True)
        root.write_text("")
        sub.write_text("")
        self.assertEqual(self.run_root_source(omp), (0, f"JSONL={root}\nJSONL={sub}\n", ""))

    def test_root_source_opencode(self):
        db = make_db(self.home)
        with sqlite3.connect(db) as connection:
            connection.executemany(
                "insert into session_v2(id, parent_id) values (?, ?)", [("o4", "o1"), ("o9", None)]
            )
        connection.close()
        self.assertEqual(
            self.run_root_source({"AGENT_HARNESS": "opencode", "OPENCODE_SESSION_ID": "o3"}),
            (0, f"DB={db}\nSESSION=o1\nSESSION=o2\nSESSION=o3\nSESSION=o4\n", ""),
        )

    def test_errors(self):
        self.assert_fails(
            {"AGENT_HARNESS": "claude"},
            "CLAUDE_CODE_SESSION_ID is not set (AGENT_HARNESS=claude)",
        )
        self.assert_fails(
            {"AGENT_HARNESS": "codex"}, "unknown AGENT_HARNESS=codex (claude, omp, opencode)"
        )
        self.assert_fails(
            {"CLAUDE_CODE_SESSION_ID": "c1", "PI_SESSION_ID": "s1"},
            "AGENT_HARNESS is unset and several harness session variables are set: "
            "CLAUDE_CODE_SESSION_ID PI_SESSION_ID",
        )
        self.assert_fails(
            {},
            "AGENT_HARNESS is unset and no harness session variable is set "
            "(CLAUDE_CODE_SESSION_ID, PI_SESSION_ID, OPENCODE_SESSION_ID)",
        )
        self.assert_fails(
            {"AGENT_HARNESS": "omp", "PI_SESSION_ID": "s1", "PI_SESSION_FILE": "/x/notes.jsonl"},
            "PI_SESSION_FILE /x/notes.jsonl has no <ts>_<root id> name",
        )
        db = self.home / ".local" / "share" / "opencode" / "opencode.db"
        opencode = {"AGENT_HARNESS": "opencode", "OPENCODE_SESSION_ID": "o9"}
        self.assert_fails(opencode, f"{db} not found")
        db.parent.mkdir(parents=True)
        db.write_text("not a database\n" * 100)
        result = self.run_agent_env(opencode)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertRegex(result.stderr, rf"\Aagent-env: sqlite3 {db}: [^\n]+\n\Z")
        db.unlink()
        with sqlite3.connect(db) as connection:
            connection.execute("create table other(id text)")
        connection.close()
        self.assert_fails(opencode, f"table session_v2 not found in {db}")
        db.unlink()
        make_db(self.home)
        self.assert_fails(opencode, f"session o9 not found in session_v2 of {db}")


if __name__ == "__main__":
    unittest.main()
