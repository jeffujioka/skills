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
