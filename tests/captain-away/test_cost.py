"""captain-away cost.sh reports the run's cost on claude, omp and opencode through agent-env."""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness-kit"))

from harness_home import env_for, install_agent_env, install_skill, make_home  # noqa: E402


def comma_locale(test):
    """Return env variables that make bash's printf write a comma decimal point, or skip.

    An installed locale is used when there is one; else de_DE.UTF-8 is built with localedef
    into a temporary LOCPATH folder under /tmp. The probe is bash's own printf, the reader
    that cost.sh must keep away from the locale (`locale -a` is not reliable on every host).
    """
    names = ("de_DE.UTF-8", "pt_BR.UTF-8", "fr_FR.UTF-8")

    def writes_comma(extra):
        result = subprocess.run(
            ["bash", "-c", "printf '%.1f' 1"], capture_output=True, text=True, env={**os.environ, **extra}
        )
        return result.stdout == "1,0"

    for name in names:
        if writes_comma({"LC_ALL": name}):
            return {"LC_ALL": name}
    localedef = shutil.which("localedef")
    if localedef:
        folder = tempfile.mkdtemp(prefix="locale-", dir="/tmp")
        test.addCleanup(shutil.rmtree, folder, True)
        sources = {"I18NPATH": "/usr/share/i18n"} if os.path.isdir("/usr/share/i18n") else {}
        subprocess.run(
            [localedef, "-c", "-i", "de_DE", "-f", "UTF-8", f"{folder}/de_DE.UTF-8"],
            capture_output=True,
            env={**os.environ, **sources},
        )
        built = {"LC_ALL": "de_DE.UTF-8", "LOCPATH": folder}
        if writes_comma(built):
            return built
    test.skipTest("no locale with a comma decimal point is installed, and localedef cannot build de_DE.UTF-8")


SESSIONS = Path(".omp") / "agent" / "sessions" / "-p"
ROOT = "2026-11-14T10-00-00-000Z_r1"


def assistant(total):
    return {"type": "message", "message": {"role": "assistant", "usage": {"cost": {"total": total}}}}


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records))
    return path


def stub_agent_env(home, harness, sources=""):
    """Replace <home>/.local/bin/agent-env with a stub printing harness and root-source sources."""
    target = Path(home) / ".local" / "bin" / "agent-env"
    target.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "${1-}" == root-source ]]; then cat <<\'EOF\'\n'
        f"{sources}EOF\n"
        f"else echo AGENT_HARNESS={harness}; fi\n"
    )
    target.chmod(0o755)


class CostTest(unittest.TestCase):
    def setUp(self):
        self.home = make_home(self)
        install_skill(self.home, "logbook")
        self.skill = install_skill(self.home, "captain-away")
        install_agent_env(self.home)

    def run_cost(self, extra):
        return subprocess.run(
            ["bash", str(self.skill / "scripts" / "cost.sh")],
            capture_output=True,
            text=True,
            env=env_for(self.home, extra),
            cwd=self.home,
        )

    def transcript(self, records):
        return write_jsonl(self.home / ".claude" / "projects" / "-p" / "c1.jsonl", records)

    def test_claude_estimate(self):
        self.transcript([
            {"type": "cost-state", "totalCostUSD": 0.5},
            {"type": "user"},
            {"type": "cost-state", "totalCostUSD": 1.25},
        ])
        result = self.run_cost({"CLAUDE_CODE_SESSION_ID": "c1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "1.25 (estimate)\n")

    def test_omp_includes_subagents(self):
        root = write_jsonl(self.home / SESSIONS / f"{ROOT}.jsonl", [
            {"type": "session"},
            assistant(0.6),
            {"type": "message", "message": {"role": "user"}},
            assistant(0.4),
        ])
        sub = write_jsonl(self.home / SESSIONS / ROOT / "Sub.jsonl", [assistant(0.5)])
        for session_id, session_file in (("r1", root), ("s1", sub)):
            result = self.run_cost({"PI_SESSION_ID": session_id, "PI_SESSION_FILE": str(session_file)})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "1.50\n")

    def test_opencode_includes_children(self):
        db = self.home / ".local" / "share" / "opencode" / "opencode.db"
        db.parent.mkdir(parents=True)
        with sqlite3.connect(db) as connection:
            connection.execute("create table session_v2 (id text primary key, parent_id text, cost real)")
            connection.executemany(
                "insert into session_v2 values (?, ?, ?)",
                [("o1", None, 2.0), ("o2", "o1", 0.25), ("o9", None, 9.0)],
            )
        connection.close()
        for session_id in ("o1", "o2"):
            result = self.run_cost({"OPENCODE_SESSION_ID": session_id})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "2.25\n")

    def test_missing_cost_field(self):
        transcript = self.transcript([{"type": "user"}])
        result = self.run_cost({"CLAUDE_CODE_SESSION_ID": "c1"})
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"cost.sh: no cost-state.totalCostUSD in {transcript}", result.stderr)

        root = write_jsonl(self.home / SESSIONS / f"{ROOT}.jsonl", [{"type": "message", "message": {"role": "assistant"}}])
        result = self.run_cost({"PI_SESSION_ID": "r1", "PI_SESSION_FILE": str(root)})
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"cost.sh: no usage.cost.total in {root}", result.stderr)

    def test_comma_decimal_locale(self):
        locale_env = comma_locale(self)
        self.transcript([{"type": "cost-state", "totalCostUSD": 1.25}])
        result = self.run_cost({"CLAUDE_CODE_SESSION_ID": "c1", **locale_env})
        self.assertEqual((result.returncode, result.stdout), (0, "1.25 (estimate)\n"), result.stderr)

        root = write_jsonl(self.home / SESSIONS / f"{ROOT}.jsonl", [assistant(1.5)])
        result = self.run_cost({"PI_SESSION_ID": "r1", "PI_SESSION_FILE": str(root), **locale_env})
        self.assertEqual((result.returncode, result.stdout), (0, "1.50\n"), result.stderr)

        db = self.home / ".local" / "share" / "opencode" / "opencode.db"
        db.parent.mkdir(parents=True)
        with sqlite3.connect(db) as connection:
            connection.execute("create table session_v2 (id text primary key, parent_id text, cost real)")
            connection.execute("insert into session_v2 values ('o1', null, 2.25)")
        connection.close()
        result = self.run_cost({"OPENCODE_SESSION_ID": "o1", **locale_env})
        self.assertEqual((result.returncode, result.stdout), (0, "2.25\n"), result.stderr)

    def test_claude_skips_unparseable_line(self):
        transcript = self.transcript([{"type": "cost-state", "totalCostUSD": 1.25}])
        with transcript.open("a") as log:
            log.write('{"type": "cost-state", "totalCost')
        result = self.run_cost({"CLAUDE_CODE_SESSION_ID": "c1"})
        self.assertEqual((result.returncode, result.stdout), (0, "1.25 (estimate)\n"), result.stderr)

    def test_omp_skips_unparseable_line(self):
        root = write_jsonl(self.home / SESSIONS / f"{ROOT}.jsonl", [assistant(0.6), assistant(0.4)])
        with root.open("a") as log:
            log.write('{"type": "message", "message": {"role": "assis')
        result = self.run_cost({"PI_SESSION_ID": "r1", "PI_SESSION_FILE": str(root)})
        self.assertEqual((result.returncode, result.stdout), (0, "1.00\n"), result.stderr)

    def test_opencode_missing_session(self):
        db = self.home / ".local" / "share" / "opencode" / "opencode.db"
        db.parent.mkdir(parents=True)
        with sqlite3.connect(db) as connection:
            connection.execute("create table session_v2 (id text primary key, parent_id text, cost real)")
            connection.execute("insert into session_v2 values ('o1', null, 2.25)")
        connection.close()
        stub_agent_env(self.home, "opencode", f"DB={db}\nSESSION=o6\nSESSION=o1\nSESSION=o5\n")
        result = self.run_cost({})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, f"cost.sh: sessions not found in session_v2 of {db}: o5 o6\n")

    def test_unknown_harness(self):
        stub_agent_env(self.home, "other")
        result = self.run_cost({})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "cost.sh: unknown harness other (claude, omp, opencode)\n")

    def test_logbook_missing(self):
        shutil.rmtree(self.home / ".agents" / "skills" / "logbook")
        result = self.run_cost({"CLAUDE_CODE_SESSION_ID": "c1"})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "cost.sh: needs the logbook skill beside captain-away\n")


if __name__ == "__main__":
    unittest.main()
