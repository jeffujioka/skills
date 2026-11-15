"""install.sh plans and installs the harness-kit artefacts for the harnesses found."""

import json
import os
import shutil
import subprocess
import unittest

from harness_home import REPO, env_for, make_home

INSTALL = REPO / "harness-kit" / "scripts" / "install.sh"
HOOK_COMMAND = 'bash "$HOME/.claude/hooks/harness-kit-session-start.sh"'
ENTRY = {"hooks": [{"type": "command", "command": HOOK_COMMAND}]}
JQ_MISSING = (
    "harness-kit: jq not found; it is needed to edit ~/.claude/settings.json. "
    "Install jq, then run harness-kit again."
)


def files_under(home):
    return sorted(
        os.path.join(root, name)
        for root, _, names in os.walk(home)
        for name in names
        if not root.startswith(str(home / "test-bin"))
    )


class InstallTest(unittest.TestCase):
    def make(self, harnesses=("claude", "omp"), without=("opencode",)):
        self.home = make_home(self, harnesses=harnesses, without=without)
        return self.home

    def run_install(self, *args, local_bin_on_path=True):
        return subprocess.run(
            ["bash", str(INSTALL), *args],
            capture_output=True,
            text=True,
            env=env_for(self.home, local_bin_on_path=local_bin_on_path),
            cwd=self.home,
        )

    def settings(self):
        return json.loads((self.home / ".claude" / "settings.json").read_text())

    def test_plan_then_install_for_found_harnesses(self):
        home = self.make()
        before = files_under(home)
        result = self.run_install("plan")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "harness-kit 0.1.0 would write:",
                "~/.local/bin/agent-env: prints the harness and session ids that logbook, captain-away and handoff-hc read",
                "~/.claude/settings.json: gains one SessionStart entry that runs the claude hook; other entries stay",
                "~/.claude/hooks/harness-kit-session-start.sh: sets AGENT_HARNESS=claude for the session's shell commands and names the logbook after compaction and shows a notice that it did",
                "~/.omp/agent/extensions/harness-kit.ts: sets AGENT_HARNESS=omp on commands that run agent-env or a skills script and adds the logbook reminder to the session after compaction and shows a notice",
                "opencode not found: nothing is written for it",
            ],
        )
        self.assertEqual(files_under(home), before)

        result = self.run_install("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        for path, executable in (
            (home / ".local" / "bin" / "agent-env", True),
            (home / ".claude" / "hooks" / "harness-kit-session-start.sh", True),
            (home / ".omp" / "agent" / "extensions" / "harness-kit.ts", False),
        ):
            self.assertIn("harness-kit 0.1.0", path.read_text(), path)
            self.assertNotIn("@VERSION@", path.read_text(), path)
            if executable:
                self.assertEqual(path.stat().st_mode & 0o777, 0o755, path)
        self.assertEqual(self.settings(), {"hooks": {"SessionStart": [ENTRY]}})
        self.assertFalse((home / ".config" / "opencode" / "plugins" / "harness-kit.ts").exists())

    def test_foreign_agent_env_kept(self):
        home = self.make()
        agent_env = home / ".local" / "bin" / "agent-env"
        agent_env.write_text("#!/bin/sh\necho mine\n")
        result = self.run_install("plan")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "~/.local/bin/agent-env: foreign (no harness-kit marker), kept unless you confirm "
            "replacing it; the consumer skills would run it as agent-env",
            result.stdout.splitlines(),
        )

        result = self.run_install("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("kept foreign ~/.local/bin/agent-env", result.stdout.splitlines())
        self.assertEqual(agent_env.read_text(), "#!/bin/sh\necho mine\n")

        result = self.run_install("install", "--replace", "~/.local/bin/agent-env")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("replaced foreign ~/.local/bin/agent-env", result.stdout.splitlines())
        self.assertIn("harness-kit 0.1.0", agent_env.read_text())

    def test_path_warning(self):
        self.make()
        result = self.run_install("plan", local_bin_on_path=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            '~/.local/bin is not on PATH; add this line to your shell profile: '
            'export PATH="$HOME/.local/bin:$PATH"',
            result.stdout.splitlines(),
        )

    def test_settings_absent(self):
        home = self.make()
        self.assertFalse((home / ".claude" / "settings.json").exists())
        result = self.run_install("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.settings(), {"hooks": {"SessionStart": [ENTRY]}})

    def test_settings_kept(self):
        home = self.make()
        pre_tool_use = [{"matcher": "Bash", "hooks": [{"type": "command", "command": "true"}]}]
        (home / ".claude").mkdir()
        (home / ".claude" / "settings.json").write_text(
            json.dumps({"env": {"FOO": "1"}, "hooks": {"PreToolUse": pre_tool_use}})
        )
        result = self.run_install("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.settings(),
            {
                "env": {"FOO": "1"},
                "hooks": {"PreToolUse": pre_tool_use, "SessionStart": [ENTRY]},
            },
        )

    def test_jq_missing(self):
        home = self.make(without=("jq",))
        before = files_under(home)
        for command in ("plan", "install"):
            result = self.run_install(command)
            self.assertEqual(result.returncode, 1, command)
            self.assertIn(JQ_MISSING, result.stderr, command)
            self.assertEqual(files_under(home), before, command)

    def test_second_install_changes_nothing(self):
        home = self.make(harnesses=("claude", "omp", "opencode"), without=())
        pre_tool_use = [{"matcher": "Bash", "hooks": [{"type": "command", "command": "true"}]}]
        other_start = {"hooks": [{"type": "command", "command": "echo other"}]}
        (home / ".claude").mkdir()
        (home / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"PreToolUse": pre_tool_use, "SessionStart": [other_start]}})
        )
        watched = [
            home / ".claude" / "settings.json",
            home / ".local" / "bin" / "agent-env",
            home / ".claude" / "hooks" / "harness-kit-session-start.sh",
            home / ".omp" / "agent" / "extensions" / "harness-kit.ts",
            home / ".config" / "opencode" / "plugins" / "harness-kit" / "index.ts",
            home / ".config" / "opencode" / "plugins" / "harness-kit" / "tui.ts",
        ]
        result = self.run_install("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        first = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in watched}

        result = self.run_install("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "unchanged ~/.local/bin/agent-env",
                "unchanged ~/.claude/settings.json",
                "unchanged ~/.claude/hooks/harness-kit-session-start.sh",
                "unchanged ~/.omp/agent/extensions/harness-kit.ts",
                "unchanged ~/.config/opencode/plugins/harness-kit/index.ts",
                "unchanged ~/.config/opencode/plugins/harness-kit/tui.ts",
            ],
        )
        self.assertEqual(
            {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in watched}, first
        )
        self.assertEqual(
            self.settings(),
            {"hooks": {"PreToolUse": pre_tool_use, "SessionStart": [other_start, ENTRY]}},
        )

    def test_older_marker_replaced(self):
        home = self.make()
        source = (REPO / "harness-kit" / "omp" / "harness-kit.ts").read_text()
        extension = home / ".omp" / "agent" / "extensions" / "harness-kit.ts"
        extension.parent.mkdir(parents=True)
        extension.write_text(source.replace("@VERSION@", "0.0.1"))
        result = self.run_install("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "replaced ~/.omp/agent/extensions/harness-kit.ts (0.0.1 -> 0.1.0)",
            result.stdout.splitlines(),
        )
        self.assertEqual(extension.read_text(), source.replace("@VERSION@", "0.1.0"))

    def test_check_reports_missing_agent_env(self):
        home = self.make(harnesses=("claude", "omp", "opencode"), without=())
        self.assertEqual(self.run_install("install").returncode, 0)
        (home / ".local" / "bin" / "agent-env").unlink()
        result = self.run_install("check")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "agent-env: missing (~/.local/bin/agent-env)",
                "claude-hook: installed 0.1.0 (~/.claude/hooks/harness-kit-session-start.sh)",
                "omp-extension: installed 0.1.0 (~/.omp/agent/extensions/harness-kit.ts)",
                "opencode-plugin: installed 0.1.0 (~/.config/opencode/plugins/harness-kit/index.ts)",
                "opencode-tui: installed 0.1.0 (~/.config/opencode/plugins/harness-kit/tui.ts)",
                "Run the harness-kit skill's install to repair.",
            ],
        )

    def test_remove_keeps_other_session_start_hook(self):
        home = self.make(harnesses=("claude", "omp", "opencode"), without=())
        before = {
            "hooks": {
                "SessionStart": [
                    {"matcher": "startup", "hooks": [{"type": "command", "command": "echo other"}]}
                ]
            }
        }
        (home / ".claude").mkdir()
        (home / ".claude" / "settings.json").write_text(json.dumps(before))
        self.assertEqual(self.run_install("install").returncode, 0)
        result = self.run_install("remove")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "removed the SessionStart entry from ~/.claude/settings.json",
            result.stdout.splitlines(),
        )
        for path in (
            home / ".local" / "bin" / "agent-env",
            home / ".claude" / "hooks" / "harness-kit-session-start.sh",
            home / ".omp" / "agent" / "extensions" / "harness-kit.ts",
            home / ".config" / "opencode" / "plugins" / "harness-kit.ts",
        ):
            self.assertFalse(path.exists(), path)
        self.assertEqual(self.settings(), before)

    def test_remove_keeps_foreign(self):
        home = self.make()
        agent_env = home / ".local" / "bin" / "agent-env"
        agent_env.write_bytes(b"#!/bin/sh\necho mine\n")
        self.assertEqual(self.run_install("install").returncode, 0)
        result = self.run_install("remove")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("kept foreign ~/.local/bin/agent-env", result.stdout.splitlines())
        self.assertEqual(agent_env.read_bytes(), b"#!/bin/sh\necho mine\n")

    def test_remove_drops_emptied_lists(self):
        home = self.make()
        (home / ".claude").mkdir()
        (home / ".claude" / "settings.json").write_text("{}")
        self.assertEqual(self.run_install("install").returncode, 0)
        result = self.run_install("remove")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.settings(), {})

    def test_check_lists_later_harness(self):
        home = self.make(harnesses=("claude",), without=("omp", "opencode"))
        self.assertEqual(self.run_install("install").returncode, 0)
        (home / "test-bin" / "opencode").symlink_to(shutil.which("opencode"))
        result = self.run_install("check")
        self.assertEqual(result.returncode, 1, result.stderr)
        lines = result.stdout.splitlines()
        self.assertIn("omp-extension: skipped, omp not found", lines)
        self.assertIn("opencode-plugin: missing (~/.config/opencode/plugins/harness-kit/index.ts)", lines)
        self.assertIn("opencode-tui: missing (~/.config/opencode/plugins/harness-kit/tui.ts)", lines)

    def test_settings_mode_and_link_kept(self):
        home = self.make()
        before = {"env": {"TOKEN": "secret"}}
        target = home / "dotfiles" / "settings.json"
        target.parent.mkdir()
        target.write_text(json.dumps(before))
        target.chmod(0o600)
        (home / ".claude").mkdir()
        link = home / ".claude" / "settings.json"
        link.symlink_to(target)
        for command, expected in (
            ("install", {**before, "hooks": {"SessionStart": [ENTRY]}}),
            ("remove", before),
        ):
            result = self.run_install(command)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(link.is_symlink(), command)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600, command)
            self.assertEqual(json.loads(target.read_text()), expected, command)

    def test_foreign_plan_line_per_artefact(self):
        home = self.make(harnesses=("claude", "omp", "opencode"), without=())
        for target in (
            ".local/bin/agent-env",
            ".claude/hooks/harness-kit-session-start.sh",
            ".omp/agent/extensions/harness-kit.ts",
            ".config/opencode/plugins/harness-kit/index.ts",
            ".config/opencode/plugins/harness-kit/tui.ts",
        ):
            (home / target).parent.mkdir(parents=True, exist_ok=True)
            (home / target).write_text("mine\n")
        result = self.run_install("plan")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        kept = "foreign (no harness-kit marker), kept unless you confirm replacing it"
        for line in (
            f"~/.local/bin/agent-env: {kept}; the consumer skills would run it as agent-env",
            f"~/.claude/hooks/harness-kit-session-start.sh: {kept}; "
            "the harness-kit SessionStart entry would run it at every claude session start",
            f"~/.omp/agent/extensions/harness-kit.ts: {kept}; omp would load it as the harness-kit extension",
            f"~/.config/opencode/plugins/harness-kit/index.ts: {kept}; opencode would load it as the harness-kit plugin",
            f"~/.config/opencode/plugins/harness-kit/tui.ts: {kept}; opencode would load it as the TUI part of the harness-kit plugin",
        ):
            self.assertIn(line, lines)

    def test_modes_come_from_the_table(self):
        home = self.make(harnesses=("claude", "omp", "opencode"), without=())
        kit = home.parent.parent / "kit" / "harness-kit"
        shutil.copytree(REPO / "harness-kit", kit)
        for path in kit.rglob("*"):
            if path.is_file():
                path.chmod(0o644)
        result = subprocess.run(
            ["bash", str(kit / "scripts" / "install.sh"), "install"],
            capture_output=True,
            text=True,
            env=env_for(home),
            cwd=home,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for target, mode in (
            (".local/bin/agent-env", 0o755),
            (".claude/hooks/harness-kit-session-start.sh", 0o755),
            (".omp/agent/extensions/harness-kit.ts", 0o644),
            (".config/opencode/plugins/harness-kit/index.ts", 0o644),
            (".config/opencode/plugins/harness-kit/tui.ts", 0o644),
        ):
            self.assertEqual((home / target).stat().st_mode & 0o777, mode, target)

    def test_newer_marker_kept(self):
        home = self.make()
        self.assertEqual(self.run_install("install").returncode, 0)
        source = (REPO / "harness-kit" / "omp" / "harness-kit.ts").read_text()
        extension = home / ".omp" / "agent" / "extensions" / "harness-kit.ts"
        extension.write_text(source.replace("@VERSION@", "0.2.0"))
        newer = extension.read_bytes()
        result = self.run_install("plan")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "~/.omp/agent/extensions/harness-kit.ts: newer (harness-kit 0.2.0), kept",
            result.stdout.splitlines(),
        )
        result = self.run_install("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "kept newer ~/.omp/agent/extensions/harness-kit.ts (0.2.0)", result.stdout.splitlines()
        )
        self.assertEqual(extension.read_bytes(), newer)
        result = self.run_install("check")
        self.assertEqual(result.returncode, 1, result.stderr)
        lines = result.stdout.splitlines()
        self.assertIn("omp-extension: newer 0.2.0 (~/.omp/agent/extensions/harness-kit.ts)", lines)
        self.assertNotIn("Run the harness-kit skill's install to repair.", lines)

    def test_plan_shows_unchanged_and_replaced(self):
        home = self.make()
        self.assertEqual(self.run_install("install").returncode, 0)
        source = (REPO / "harness-kit" / "omp" / "harness-kit.ts").read_text()
        extension = home / ".omp" / "agent" / "extensions" / "harness-kit.ts"
        extension.write_text(source.replace("@VERSION@", "0.0.1"))
        result = self.run_install("plan")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "harness-kit 0.1.0 would write:",
                "~/.local/bin/agent-env: unchanged",
                "~/.claude/settings.json: unchanged",
                "~/.claude/hooks/harness-kit-session-start.sh: unchanged",
                "~/.omp/agent/extensions/harness-kit.ts: replaced (0.0.1 -> 0.1.0); sets AGENT_HARNESS=omp "
                "on commands that run agent-env or a skills script and adds the logbook reminder to the session after compaction and shows a notice",
                "opencode not found: nothing is written for it",
            ],
        )


if __name__ == "__main__":
    unittest.main()
