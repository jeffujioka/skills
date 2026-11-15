"""End-to-end: another team installs harness-kit and runs logbook and captain-away as their SKILL.md write them."""

import json
import os
import re
import sqlite3
import subprocess
import unittest
from pathlib import Path

from harness_home import REPO, env_for, install_skill, make_home

SKILLS = ("logbook", "captain-away", "hc-handoff", "harness-kit")
COST = re.compile(r"^[0-9]+\.[0-9]{2}( \(estimate\))?$")


def code_block(skill_md, heading):
    """The first fenced bash block under heading in skill_md."""
    section = skill_md.split(f"## {heading}\n", 1)[1]
    return re.search(r"```bash\n(.*?)```", section, re.DOTALL).group(1)


def assistant(cost):
    return json.dumps({"type": "message", "message": {"role": "assistant", "usage": {"cost": {"total": cost}}}})


def fixtures(home):
    """The session variables each harness's hook would set, with that harness's cost source."""
    transcript = home / ".claude" / "projects" / "-x" / "c1.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_text(json.dumps({"type": "cost-state", "totalCostUSD": 1.234}) + "\n")

    folder = home / ".omp" / "agent" / "sessions" / "-p"
    root = folder / "2026-11-14T10-00-00-000Z_r1.jsonl"
    sub = folder / "2026-11-14T10-00-00-000Z_r1" / "Sub.jsonl"
    sub.parent.mkdir(parents=True)
    root.write_text(assistant(0.5) + "\n")
    sub.write_text(assistant(0.25) + "\n")

    db = home / ".local" / "share" / "opencode" / "opencode.db"
    db.parent.mkdir(parents=True)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "create table session_v2(id text primary key, parent_id text, cost real not null default 0)"
        )
        connection.executemany(
            "insert into session_v2(id, parent_id, cost) values (?, ?, ?)",
            [("o1", None, 1.0), ("o2", "o1", 0.5)],
        )
    connection.close()

    return {
        "claude": {"AGENT_HARNESS": "claude", "CLAUDE_CODE_SESSION_ID": "c1"},
        "omp": {"AGENT_HARNESS": "omp", "PI_SESSION_ID": "s2", "PI_SESSION_FILE": str(sub)},
        "opencode": {"AGENT_HARNESS": "opencode", "OPENCODE_SESSION_ID": "o2"},
    }


class AnotherTeamTest(unittest.TestCase):
    def test_another_team_installs(self):
        home = make_home(self, harnesses=("claude", "omp", "opencode"), user="otherdev")
        env = env_for(home)
        self.assertEqual((env["USER"], env["LOGNAME"]), ("otherdev", "otherdev"))
        result = subprocess.run(
            ["bash", str(REPO / "harness-kit" / "scripts" / "install.sh"), "install"],
            capture_output=True, text=True, env=env, cwd=home,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        skills = home / ".agents" / "skills"
        for name in SKILLS:
            install_skill(home, name)

        folder_block = code_block((skills / "logbook" / "SKILL.md").read_text(), "Folder")
        cost_block = code_block((skills / "captain-away" / "SKILL.md").read_text(), "Cost cap")
        folder_script = folder_block.replace("<skill dir>", str(skills / "logbook")) + 'echo "$LOGBOOK"\n'
        cost_script = cost_block.replace("<skill dir>", str(skills / "captain-away"))
        project = home.parent.parent / "project"
        project.mkdir()
        slug = str(project).replace("/", "-")
        logbooks = home / ".local" / "state" / "agents" / "logbooks" / slug

        for harness, variables in fixtures(home).items():
            with self.subTest(harness=harness):
                run_env = env_for(home, variables)
                folder = subprocess.run(
                    ["bash", "-c", folder_script], capture_output=True, text=True, env=run_env, cwd=project
                )
                self.assertEqual(folder.returncode, 0, folder.stderr)
                printed = Path(folder.stdout.strip())
                self.assertEqual(printed.parent, logbooks)
                self.assertTrue(printed.is_dir())
                cost = subprocess.run(
                    ["bash", "-c", cost_script], capture_output=True, text=True, env=run_env, cwd=project
                )
                self.assertEqual(cost.returncode, 0, cost.stderr)
                self.assertRegex(cost.stdout.strip(), COST)

        developer = os.environ.get("USER") or Path.home().name
        for name in SKILLS:
            for path in (skills / name).rglob("*"):
                if not path.is_file():
                    continue
                text = path.read_text(errors="replace")
                for leak in (developer, "/home/", "/Users/"):
                    with self.subTest(file=str(path.relative_to(skills)), leak=leak):
                        self.assertNotIn(leak, text)


if __name__ == "__main__":
    unittest.main()
