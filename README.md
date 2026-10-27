# Agent Skills

A collection of agent skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code), [Copilot CLI](https://githubnext.com/projects/copilot-cli/), and other AI coding assistants.

## Install

### By agent

```sh
# Claude Code
npx skills@latest add https://github.com/jeffujioka/skills.git -s <skill-name> -a claude-code

# Copilot CLI
npx skills@latest add https://github.com/jeffujioka/skills.git -s <skill-name> -a copilot

# Codex
npx skills@latest add https://github.com/jeffujioka/skills.git -s <skill-name> -a codex

# Claude Code + Copilot CLI + Codex
npx skills@latest add https://github.com/jeffujioka/skills.git -s <skill-name> -a claude-code copilot codex
```

### All agents

```sh
# project-local (all agents auto-detected)
npx skills@latest add https://github.com/jeffujioka/skills.git -s <skill-name>

# global
npx skills@latest add https://github.com/jeffujioka/skills.git -s <skill-name> -g

# all skills, all agents
npx skills@latest add https://github.com/jeffujioka/skills.git --all

# all skills, all agents, global
npx skills@latest add https://github.com/jeffujioka/skills.git --all -g
```

## Skills

### Tooling

- **github-cli** — Work with GitHub through the `gh` CLI: PRs, issues, CI, code search and `gh api`.
	```sh
	npx skills@latest add https://github.com/jeffujioka/skills.git -s github-cli
	```

- **gh-pr-create** — Create a GitHub pull request with `gh` from the current branch: find the repo's PR template, fill it, show the draft, create only after approval.
	```sh
	npx skills@latest add https://github.com/jeffujioka/skills.git -s gh-pr-create
	```

- **handoff-herdr** — Hand off the current conversation to a new Herdr tab, pane, or workspace: on the current harness by default, or on a named one (opencode, claude, omp), carrying the model and reasoning level over when the target supports them. Requires the `herdr` and `handoff` skills.
	```sh
	npx skills@latest add https://github.com/jeffujioka/skills.git -s handoff-herdr
	```

- **hire** — Run a task on a subagent pinned to a chosen model and reasoning level, by rank (intern to cto) or raw `model#effort`.
	```sh
	npx skills@latest add https://github.com/jeffujioka/skills.git -s hire
	```

- **captain-away** — Unattended runs: the agent decides every open question itself, never pushes, merges, deletes or writes to Jira/Confluence, caps spend, and leaves a report for when you return.
	```sh
	npx skills@latest add https://github.com/jeffujioka/skills.git -s captain-away
	```

- **logbook** — Keeps a session's progress, decisions and blocked actions on disk so context compaction loses no state; also compacts on request.
	```sh
	npx skills@latest add https://github.com/jeffujioka/skills.git -s logbook
	```

- **engineer-a-skill** — Create, edit or audit an agent skill against authoring rules, 5.5 model notes and guardrails: batched intake, scaffold, evals first, write, then validate with a script (frontmatter, size, one-level references, embedded-command limits, secrets) and run the evals headless per model with a judge. Audit mode is report-only. Manual-only: call it by name; never auto-loads.
	```sh
	npx skills@latest add https://github.com/jeffujioka/skills.git -s engineer-a-skill
	```
