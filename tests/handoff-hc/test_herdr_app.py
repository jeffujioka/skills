"""handoff-hc's herdr-app.sh reaches herdr-app here or over ssh, and keeps its arguments intact."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "handoff-hc" / "scripts" / "herdr-app.sh"

# Records its arguments as JSON lines in $RECORD.
RECORDER = """#!/usr/bin/env bash
python3 - "$@" >>"$RECORD" <<'PY'
import json, sys
print(json.dumps(["%s", *sys.argv[1:]]))
PY
"""

# An ssh that runs the last argument, the remote command, in a shell, as sshd would.
FAKE_SSH = """#!/usr/bin/env bash
python3 - "$@" >>"$RECORD" <<'PY'
import json, sys
print(json.dumps(["ssh", *sys.argv[1:-1]]))
PY
bash -c "${@: -1}"
"""


class HerdrAppTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name) / "home"
        self.bin = Path(tmp.name) / "bin"
        self.home.mkdir()
        self.bin.mkdir()
        self.record = Path(tmp.name) / "record.jsonl"
        self.record.touch()

    def stub(self, directory, name, body):
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text(body)
        path.chmod(0o755)

    def run_script(self, *args):
        env = {
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "RECORD": str(self.record),
        }
        return subprocess.run(
            ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env
        )

    def recorded(self):
        return [json.loads(line) for line in self.record.read_text().splitlines()]

    def write_host(self, line):
        config = self.home / ".config" / "handoff-hc"
        config.mkdir(parents=True)
        (config / "herdr-app-host").write_text(line + "\n")

    def test_herdr_app_on_path_runs_here(self):
        self.stub(self.bin, "herdr-app", RECORDER % "herdr-app")
        self.stub(self.bin, "ssh", FAKE_SSH)
        result = self.run_script("ls")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [["herdr-app", "ls"]])

    def test_reaches_herdr_app_over_ssh_with_arguments_intact(self):
        self.stub(self.bin, "ssh", FAKE_SSH)
        self.stub(self.home / ".local" / "bin", "herdr-app", RECORDER % "herdr-app")
        self.write_host("me@desk")
        payload = json.dumps(
            {"pane": "bs/p1", "argv": ["omp", "Read /tmp/a b.md and continue from it."]}
        )
        result = self.run_script("do", "pane.split", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.recorded(),
            [["ssh", "-o", "BatchMode=yes", "me@desk"], ["herdr-app", "do", "pane.split", payload]],
        )

    def test_destination_may_carry_ssh_options(self):
        self.stub(self.bin, "ssh", FAKE_SSH)
        self.stub(self.home / ".local" / "bin", "herdr-app", RECORDER % "herdr-app")
        self.write_host("-p 2222 me@desk")
        result = self.run_script("ls")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.recorded()[0], ["ssh", "-o", "BatchMode=yes", "-p", "2222", "me@desk"]
        )

    def test_unreachable_without_a_host_file_exits_3(self):
        self.stub(self.bin, "ssh", FAKE_SSH)
        result = self.run_script("ls")
        self.assertEqual(result.returncode, 3)
        self.assertIn("ssh destination", result.stderr)
        self.assertIn(str(self.home / ".config/handoff-hc/herdr-app-host"), result.stderr)
        self.assertEqual(self.recorded(), [])


if __name__ == "__main__":
    unittest.main()
