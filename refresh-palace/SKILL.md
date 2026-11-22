---
name: refresh-palace
description: "Catches a project's memory palace wing up with new omp sessions of its checkout and worktrees. Distils short drawers (decisions, causes and fixes, preferences) with subagents and files them; scripts/rp.py is a reference toolbox for the mechanical parts. Works for any repo through a profile. Manual-only: call it by name with the profile name."
disable-model-invocation: true
---

# refresh-palace

A palace wing holds short notes distilled from the omp sessions of one project.
It does not update itself. This skill adds the sessions newer than the last refresh.
Call it as `refresh-palace <profile>`. Ask for the profile name if none is given.

You own the outcome. `scripts/rp.py` is a reference for the mechanical parts: use it as written, adapt it, or do a step by hand when the situation calls for it. Its output explains what it found; it does not make the decisions below. The rules in "Rules that do not bend" are the exception.

## Rules that do not bend

- **Never run `mempalace mine --mode convos` on omp logs.** It files raw JSON and half sentences.
- **No secret reaches the palace.** Tokens, keys, passwords and URLs with credentials are scanned for before filing, in every drawer. A hit is removed or reworded, never filed. `rp.py check` and `build` do this with a pattern list; if you file without the script, scan the drawers yourself.
- **Back up the palace before the first write of the day.** A refresh writes through `checkpoint` calls into one shared index. A half-failed call can corrupt it, and deleting drawers is not an undo. Copy the folder: `cp -a ~/.config/mempalace/palace ~/.config/mempalace/palace.bak-$(date +%F)`. Skip when that folder exists.
- **A new room is the developer's decision.** Show the room and a sample drawer; never add one on your own.
- **A cwd you cannot tie to the project is the developer's decision.** Ask once; the answer is saved in the profile.
- **File one payload at a time.** Concurrent writers corrupt the index.
- **Move the watermark last,** only after every payload was filed with empty `errors`, and never past a session that was not mined (a pending cwd, a running session).
- **Do not commit anything, and add no tests or docs,** unless the developer asks.

## Terms

- Skill dir: the directory of this `SKILL.md`. `RP` below means `python3 <skill-dir>/scripts/rp.py`; run it with no arguments for the command list.
- Profile: `~/.config/mempalace/refresh/<name>.json`: wing, project roots, worktree globs, git remote, known docs, extra rooms, and the cwds you confirmed or ignored. `RP show <name>` prints it.
- Work dir: `$TMPDIR/refresh-<name>` (`/tmp` if `TMPDIR` is unset).
- Watermark: `last_session_ts` in `~/.config/mempalace/refresh/<name>.state.json`. Sessions starting at or before it are done. No state file: every session is new.
- Rooms: the fixed ones (`tooling`, `architecture`, `workflow`, `testing`, `security`, `config`, `process`) plus the ones the profile adds.

## Needs

- `python3`, `git`, `mempalace` (check: `mempalace --version`).
- The bash command `mcp__mempalace_palace_exec` (omp). Run `mcp__mempalace_palace_exec --help` for its flags.

## The work, in order

Track the steps in the todo tool. Stop when step 2 finds nothing new, when a failure is outside this skill (name the failing command), or when filing reports errors you cannot fix. After step 7, stop.

### 0. New project

No profile for the name? Create one before step 1.

1. Ask the developer for the wing name and the checkout path or paths. The palace rejects `/` in a wing name.
2. Ask what the project's sessions mostly do, and propose 2 or 3 subject rooms that fit (for a dotfiles or tooling vault: `agent-harness`, `dev-env`, `terminal`; for a code project the fixed rooms are enough). The developer approves them.
3. `RP init <name> --wing <wing> --root <path> [--glob '<worktree glob>'] [--description '<one line>'] [--room <room>]...`. It prints git worktrees and `known_docs` candidates; add the ones the developer accepts (`--known-docs`, or edit the profile). Names are lowercase slugs.

### 1. Check

Run `mempalace status`; the profile's wing should be listed unless this is the first run. Make the backup (rule above).

### 2. Find the new sessions

Goal: a transcript set that covers every new session of this project, and nothing else.

`RP audit <name>` lists the sessions newer than the watermark by cwd:

- `member`: under a root, or a cwd you confirmed.
- `PENDING-NEW`: a worktree glob matched a cwd not seen before.
- `PENDING-SUSPECT`: not matched, but git (worktree list, common dir, remote) or the directory name ties it to the project, e.g. a sibling `<root>-sdd`.
- `PENDING-MISMATCH`: matched, but the checkout's git remote differs from the profile's.
- `weak signal`: information only.

Resolve every pending cwd before you run `prepare`: put each to the developer, include it (`RP confirm <name> <cwd>...`) or exclude it (`RP ignore <name> <cwd>...`), and wait for the answer. Do not read its transcripts to decide, and do not distil or file anything meanwhile. (`prepare` would only defer the sessions at or after a pending cwd, so running it early wastes the run.) Then audit again.

Then `RP prepare <name>` writes plain transcripts, `batch-N.list` (about 400 KB each), `known-docs.txt`, `run.json` and `contract.md` into the work dir. What it does:

- Skips the session touched in the last 30 minutes (this one) and defers every session at or after a pending or running one, so the watermark cannot skip it.
- Keeps skill invocations (`> /skill:name request`), a time marker before each user turn, and short `[tool error]` and `[command]` excerpts: the plain user/assistant text alone loses what the developer asked and the exact failure.
- Refuses to delete unfiled drafts (`out-*.jsonl`) unless `--force`.
- First run: takes every session. `--since YYYY-MM-DDTHH-MM-SS` starts later.

Done when you have the transcripts and batches, or `nothing new`: say so and stop.

### 3. Distil

Goal: one `out-N.jsonl` per batch, each drawer one durable fact the transcript supports.

Start one `task` subagent per batch, all in one `tasks[]` call. Tell each: read `<work>/contract.md`, distil the sessions in `<work>/batch-N.list`, write `<work>/out-N.jsonl`, call no mempalace tool. Wait for all of them.

The contract is the quality bar. If a batch is unusual (a research-heavy project, no preferences), adjust the contract text in the work dir for that run rather than fighting it in the review.

### 4. Review

Goal: every drawer is true, durable, safe and in the right room before it goes in.

`RP check <name>` reports schema problems, secret hits, rooms not yet known, drawers whose backticked tokens do not appear in their cited transcript, and writes `sample.txt`. Act on it:

- Secret hit: remove or reword the drawer (`--drop-flagged` deletes it).
- Schema problem: fix the line.
- Unknown room: ask the developer to approve it (`RP rooms <name> add <room>`) or fold it (`RP rooms <name> map <old> <new>`).
- Ungrounded tokens, medium or low confidence, and a wrong `session` id are the usual signs of a bad drawer. Open each listed transcript. Check, for every drawer in `sample.txt`: the cited session is the one that states the fact, the wording is the transcript's, and the kind fits (a `decision` needs the developer's own answer).
- Look at the room spread. If one room holds most drawers, the contract steered wrongly; re-room by subject.

Done when you would stand behind every drawer. Run `check` again after fixes.

### 5. File

`RP build <name>` writes `<work>/ck-N.json` and holds drawers with a secret hit or an unapproved room (`HELD` lines). For each payload, one after another:

1. `mcp__mempalace_palace_exec @<work>/ck-N.json`.
2. Read the result. `errors` must be empty. `duplicates` are fine: the palace skips them.

Then `mempalace status` (the count grew) and one search for a fact you filed (below).

Done when every payload returned empty `errors` and the search finds the fact.

### 6. Watermark

`RP done <name>` prints `watermark -> <timestamp>` and renames `out-N.jsonl` to `filed-N.jsonl`. Run it only after step 5 is done.

### 7. Report

Print: drawers added per room, each drawer you doubt (with its title), each cwd confirmed or ignored and each room approved in this run, and anything you adapted from the script.

## Fixing filed drawers

A drawer that is wrong or in the wrong room: delete it (`mcp__mempalace_palace_exec --action delete_drawer --drawer-id <id>`; ids from `mcp__mempalace_palace_query -j '{"target":"drawers","wing":"<wing>","limit":50}'`) and file the corrected one through `build`. `update_drawer` per drawer also works; there is no bulk rename.

## Searching the palace

Search with `max_distance` 0.55 to 0.6, and the profile's wing:

```text
mcp__mempalace_palace_query -j '{"target":"search","query":"<few keywords>","wing":"<wing>","limit":3,"max_distance":0.6}'
```

Without `max_distance` the palace returns its top results even when unrelated.

## Not covered

- Sessions of other harnesses (OpenCode on the Mac, Claude Code) and subagent sessions.
- Worktrees that never had an omp session.
- The knowledge graph, tunnels and diary: plain search does not need them.
