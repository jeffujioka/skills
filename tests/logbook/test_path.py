"""logbook path.sh finds agent-env and keeps the shared folder."""

import os
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness-kit"))

from harness_home import env_for, install_agent_env, install_skill, make_home  # noqa: E402

SESSIONS = Path(".omp") / "agent" / "sessions" / "-p"


def mtime(path, day):
    stamp = datetime(2026, 11, day).timestamp()
    os.utime(path, (stamp, stamp))


class PathTest(unittest.TestCase):
    def setUp(self):
        self.home = make_home(self)
        self.skill = install_skill(self.home, "logbook")
        self.cwd = self.home / "proj"
        self.cwd.mkdir()
        self.slug = str(self.cwd).replace("/", "-").replace(" ", "-")
        self.logbook = self.home / ".local" / "state" / "agents" / "logbooks" / self.slug / "r1"
        self.old = self.home / ".local" / "state" / "opencode" / "projects"

    def root_env(self):
        return {
            "AGENT_HARNESS": "omp",
            "PI_SESSION_ID": "r1",
            "PI_SESSION_FILE": str(self.home / SESSIONS / "2026-11-14T10-00-00-000Z_r1.jsonl"),
        }

    def run_path(self, extra=None, local_bin_on_path=True):
        return subprocess.run(
            ["bash", str(self.skill / "scripts" / "path.sh")],
            capture_output=True,
            text=True,
            env=env_for(self.home, extra, local_bin_on_path=local_bin_on_path),
            cwd=self.cwd,
        )

    def assert_prints_logbook(self, result, stderr=""):
        self.assertEqual((result.returncode, result.stderr), (0, stderr))
        self.assertEqual(result.stdout, f"{self.logbook}\n")
        self.assertTrue(self.logbook.is_dir())

    def test_agent_env_off_path(self):
        install_agent_env(self.home)
        self.assert_prints_logbook(self.run_path(self.root_env(), local_bin_on_path=False))

    def test_subagent_shares_parent_folder(self):
        install_agent_env(self.home)
        self.assert_prints_logbook(self.run_path(self.root_env()))
        subagent = {
            "AGENT_HARNESS": "omp",
            "PI_SESSION_ID": "s2",
            "PI_SESSION_FILE": str(self.home / SESSIONS / "2026-11-14T10-00-00-000Z_r1" / "Sub.jsonl"),
        }
        self.assert_prints_logbook(self.run_path(subagent))

    def test_old_folder_unchanged(self):
        install_agent_env(self.home)
        old = self.old / self.slug / "ses_a"
        old.mkdir(parents=True)
        (old / "progress.md").write_text("old")
        mtime(old / "progress.md", 1)
        mtime(old, 1)

        def snapshot():
            return sorted(
                (str(p.relative_to(self.old)), p.is_file() and p.read_bytes(), p.stat().st_mtime)
                for p in self.old.rglob("*")
            )

        before = snapshot()
        self.assertEqual(self.run_path(self.root_env()).returncode, 0)
        self.assertEqual(snapshot(), before)

    def test_pointer_to_newest_old_folder(self):
        install_agent_env(self.home)
        for slug, name, day in ((self.slug, "ses_a", 1), (self.slug, "ses_b", 10), ("-other", "ses_c", 12)):
            folder = self.old / slug / name
            folder.mkdir(parents=True)
            mtime(folder, day)
        pointer = (
            f"Older logbook for this project: {self.old / self.slug / 'ses_b'};"
            " copy its files here to continue it.\n"
        )
        self.assert_prints_logbook(self.run_path(self.root_env()), pointer)
        self.assertEqual(list(self.logbook.iterdir()), [])
        (self.logbook / "progress.md").write_text("new")
        self.assert_prints_logbook(self.run_path(self.root_env()))

    def test_old_slug_folder_without_subfolders(self):
        install_agent_env(self.home)
        (self.old / self.slug).mkdir(parents=True)
        self.assert_prints_logbook(self.run_path(self.root_env()))

    def test_agent_env_missing_stops(self):
        result = self.run_path(self.root_env())
        self.assertEqual(
            (result.returncode, result.stderr),
            (
                1,
                "agent-env not found: harness-kit is not installed. Ask your agent to run the"
                " harness-kit skill, then start a new session.\n",
            ),
        )
        self.assertFalse((self.home / ".local" / "state" / "agents").exists())


if __name__ == "__main__":
    unittest.main()
