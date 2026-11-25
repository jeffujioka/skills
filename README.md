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

- **git-champs** — Git workflow for `github.com` repos: Conventional Commits with a mandatory body, feature branches only, no direct push to `main`; pushes and repository creation (`gh repo create`) run only after approval; on the base branch with uncommitted work it branches and commits only the related hunks (`stage-hunks.sh`); hands pull request creation to `gh-pr-create`.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s git-champs
  ```

- **github-cli** — Work with GitHub through the `gh` CLI: PRs, issues, CI, code search and `gh api`.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s github-cli
  ```

- **gh-pr-create** — Create a GitHub pull request with `gh` from the current branch with no approval step: commits the related uncommitted changes (via `git-champs`), pushes the feature branch, fills the repo's PR template and creates the PR; it overrides `git-champs` on approvals. Unrelated uncommitted files stay out of the PR with a warning in the final reply. Gaps become `TODO:` lines. Nothing to PR (on the base branch or zero commits ahead) is detected first; the base branch is resolved, never guessed; the base branch is never pushed.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s gh-pr-create
  ```

- **hc-handoff** — Hand off the current conversation to a new terminal started through `hc` (herdr-core), placed in the caller's Herdr workspace: on the current harness by default, or on a named one (opencode, claude, omp), carrying the model and reasoning level over when the target supports them. Requires the `handoff` skill and harness-kit.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s hc-handoff
  ```

- **harness-kit** — Installs the agent environment that logbook, captain-away and hc-handoff need: a claude `SessionStart` hook, an omp extension and an opencode plugin that set `AGENT_HARNESS` in the agent's shell commands, and `agent-env`, which prints the harness, session id and root session id. The omp extension also asks GitHub Copilot for 1h prompt-cache entries on Claude models in the main session (opt out with `HARNESS_KIT_COPILOT_CACHE=5m`). Lists every file it would write, asks once, installs only for the harnesses found; also checks and removes what it installed.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s harness-kit
  ```

- **hire** — Run a task on a subagent pinned to a chosen model and reasoning level, by rank (intern to yoda) or raw `model#effort`. Manual-only: call it by name.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s hire
  ```

- **captain-away** — Unattended runs: the agent decides every open question itself, never pushes, merges, deletes or writes to Jira/Confluence, caps spend, and leaves a report for when you return. Needs harness-kit.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s captain-away
  ```

- **logbook** — Keeps a session's progress, decisions and blocked actions on disk so context compaction loses no state. Needs harness-kit.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s logbook
  ```

- **debrief** — Distil the current session into a terse, LLM-readable summary saved to `.agents/debriefs/`, so a later session keeps decisions and failed attempts. Manual-only: call it by name.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s debrief
  ```

- **engineer-a-skill** — Create, edit or audit an agent skill against authoring rules, 5.5 model notes and guardrails: batched intake, scaffold, evals first, write, then validate with a script (frontmatter, size, one-level references, oversized code blocks, secrets; CLI-first, no wrapper scripts) and run the evals headless on claude or omp (the user picks), 10 runs per scenario on one model, graded by a judge. Edit mode asks about an unclear request first, then offers to keep, adjust or revert. Audit mode changes nothing, reports numbered findings, then asks whether to apply them (all or some), adjust a fix, ask a question or challenge a finding. Manual-only: call it by name; never auto-loads.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s engineer-a-skill
  ```

- **engineer-an-agents** — Engineer a lean `AGENTS.md` (or `CLAUDE.md`) for a repo. Audits an existing file with three questions: remove what the model can work out, remove what does not apply to every prompt, move important task-specific rules into linked reference files (`docs/agents/`), and flag reusable procedures as skill candidates. With no file, drafts one from the repo's own manifests, configs, CI and git history. Edits only the context file and `docs/agents/`; keeps a backup in `/tmp`; commits nothing. Manual-only: call it by name; never auto-loads.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s engineer-an-agents
  ```

- **obsidian-capture-troubleshooting** — Capture a solved problem as a note in an Obsidian vault's `Troubleshooting/` folder (symptom, cause, fix, verification). User-invoked only; stores the vault path in `~/.local/state/skills/obsidian-capture-troubleshooting/vault-path`. Needs the `obsidian-markdown` skill.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s obsidian-capture-troubleshooting
  ```

- **dublagem** — Speak a text in a voice cloned from a reference audio through a local [VoiceStudio](https://github.com/debpalash/VoiceStudio) backend: picks the cleanest reference window, generates line by line, retries bad lines with other seeds (transcript and noise checks), joins into one WAV, then tunes with you. Never installs engines; creates a voice profile only after approval. Needs `ffmpeg`. Call with `@dublagem`; never auto-loads.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s dublagem
  ```

- **refresh-palace** — Manual-only: catches a project's memory-palace wing up with new omp sessions of its checkout and worktrees, for any repo through a profile. A reference script (`rp.py`) helps pick and audit sessions by cwd (flagging unconfirmed worktrees, sibling dirs and remote mismatches) and check drawers; the skill states the goals and the rules that do not bend (secret scan, backup, approved rooms). Subagents distil short drawers (decisions, causes and fixes, preferences); the skill files them and moves a watermark. Call with `/skill:refresh-palace <profile>`; never auto-loads. Needs `python3`, `git` and `mempalace`.

  ```sh
  npx skills@latest add https://github.com/jeffujioka/skills.git -s refresh-palace
  ```

## Development

Markdown, JSON and TypeScript are formatted and linted with [Biome](https://biomejs.dev); Markdown is also linted (not formatted) with [rumdl](https://rumdl.dev). Fixtures under `**/evals/files/` are excluded.

```sh
npm install        # pinned Biome
uv tool install rumdl pre-commit
npm run check      # biome check + rumdl check
npm run fix        # biome check --write
pre-commit run --all-files
```
