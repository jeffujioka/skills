---
name: refresh-palace
description: "Catches a project's memory palace wing up with new omp sessions of its checkout and worktrees. Scripts pick and audit the sessions; subagents distil short drawers (decisions, causes and fixes, preferences); the skill files them. Works for any repo through a profile. Manual-only: call it by name with the profile name."
disable-model-invocation: true
---

# refresh-palace

A palace wing holds short notes distilled from the omp sessions of one project.
It does not update itself. This skill adds the sessions newer than the last refresh.
Call it as `refresh-palace <profile>`. Ask for the profile name if none is given.

Never run `mempalace mine --mode convos` on omp logs. It files raw JSON and half sentences.

Everything deterministic is in one script, `scripts/rp.py`. It prints counts, paths and cwds, never transcript text. Do not read transcripts yourself except for the spot-check in step 4.

## Terms

- Skill dir: the directory of this `SKILL.md`. Resolve it to an absolute path first. `RP` below means `python3 <skill-dir>/scripts/rp.py`.
- Profile: `~/.config/mempalace/refresh/<name>.json`: wing, project roots, worktree globs, git remote, known docs, extra rooms, and the cwds you confirmed or ignored. Run `RP show <name>`.
- Work dir: `$TMPDIR/refresh-<name>` (`/tmp` if `TMPDIR` is unset). The script prints it.
- Watermark: `last_session_ts` in `~/.config/mempalace/refresh/<name>.state.json`. Sessions at or before it are done. No state file: every session is new.

## Needs

- `python3`, `git`, `mempalace` (check: `mempalace --version`).
- The bash command `mcp__mempalace_palace_exec` (omp). Run `mcp__mempalace_palace_exec --help` for its flags.

## Checklist

Copy into the todo tool. Tick each step.

```text
- [ ] 1 Check      - [ ] 2 Prepare    - [ ] 3 Distil
- [ ] 4 Review     - [ ] 5 File       - [ ] 6 Watermark
- [ ] 7 Report
```

Stop only when:

- Step 2 prints `nothing new`.
- A step fails and the fix is outside this skill. Name the failing command.
- Step 5 reports errors you cannot fix.

When step 7 is done, stop. Do not add tests, docs or extra review rounds. Do not commit anything.

## 0. New project

No profile for the name? Create one, then continue at step 1:

1. Ask the developer for the wing name and the checkout path or paths.
2. Run `RP init <name> --wing <wing> --root <path> [--glob '<worktree glob>'] [--description '<one line>']`.
3. Show the developer its `known_docs candidates` and git worktree lines. Add the ones they accept with `--known-docs` on a fresh `init`, or by editing the profile.

Profile names are lowercase slugs (`skills`, `champ-skills`). The wing may differ, e.g. `jfujiok-skills`. The palace rejects `/` in a wing name.

## 1. Check

1. Run `mempalace status`.
2. Run `cp -a ~/.config/mempalace/palace ~/.config/mempalace/palace.bak-$(date +%F)`. Skip if that folder exists.

Done when: status lists the profile's wing, or this is its first run, and the backup folder exists.

## 2. Prepare

Run `RP prepare <name>`.

- It audits every session newer than the watermark by cwd. It exits 3 and lists the cwds that need a decision:
  - `PENDING-NEW`: a worktree glob matched a cwd not seen before.
  - `PENDING-SUSPECT`: not matched, but git (worktree list, common dir, remote) or the directory name ties it to the project. Typical: a sibling dir like `<root>-sdd`.
  - `PENDING-MISMATCH`: matched, but the checkout's git remote differs from the profile's.
  - `weak signal` lines are information only.
- Put each pending cwd to the developer: include it (`RP confirm <name> <cwd>...`) or exclude it (`RP ignore <name> <cwd>...`). The answer is saved in the profile, so each cwd is asked once. Then run `prepare` again.
- It skips sessions touched in the last 30 minutes: that is the running session.
- It writes plain transcripts, `batch-N.list` (about 400 KB each), `run.json` and `contract.md` in the work dir, and deletes the previous run's files.
- No state file and a first run? It takes every session. Pass `--since YYYY-MM-DDTHH-MM-SS` to start later.

Done when: it lists the batches, or prints `nothing new` and you stop.

## 3. Distil

1. Start one `task` subagent per batch, all in one `tasks[]` call.
2. Tell each: read `<work>/contract.md`, distil the sessions in `<work>/batch-N.list`, write `<work>/out-N.jsonl`, and call no mempalace tool.
3. Wait for all of them.

Done when: every `out-N.jsonl` exists.

## 4. Review

1. Run `RP check <name>`. It validates every drawer's schema, scans for secrets, lists rooms not yet known, and writes a spot-check sample.
2. Secret hits: run `RP check <name> --drop-flagged` to delete them.
3. Schema errors: fix the file or delete the line.
4. `NEW ROOM` lines: for each, ask the developer to approve it (`RP rooms <name> add <room>`) or fold it into another room (`RP rooms <name> map <old> <new>`; add the target first if it is new). Approved rooms are saved in the profile.
5. Read `<work>/sample.txt`: each line is a drawer and the transcript that should support it. Open the 5 to 10 it lists, not the rest. Fix or delete a drawer the transcript does not support.
6. Run `RP check <name>` again.

Done when: `check` exits 0 and no spot-checked drawer is unsupported.

## 5. File

Filing is one sequential step. Concurrent writers corrupt the index.

1. Run `RP build <name>`. It writes `<work>/ck-N.json`. It exits 4 while an unknown room remains.
2. For each payload run `mcp__mempalace_palace_exec @<work>/ck-N.json`.
3. Read the result. `errors` must be empty. `duplicates` are fine: the palace skips them.
4. Run `mempalace status` and compare the drawer count.
5. Search once for a fact you filed (below).

Done when: every payload returned empty `errors`, the count grew, and the search finds the fact.

## 6. Watermark

Run `RP done <name>` only after step 5 is done.

Done when: it prints `watermark -> <timestamp>`.

## 7. Report

Print: drawers added per room, and each drawer you doubt, with its title. Name each cwd confirmed, ignored or room approved in this run.

## Searching the palace

Search with `max_distance` 0.55 to 0.6, and the profile's wing:

```text
mcp__mempalace_palace_query -j '{"target":"search","query":"<few keywords>","wing":"<wing>","limit":3,"max_distance":0.6}'
```

Without `max_distance` the palace returns its top results even when unrelated.

## Not covered

- Sessions of other harnesses (OpenCode on the Mac, Claude Code) and subagent sessions.
- Worktrees that never had an omp session.
- Moving drawers already filed into another room: `mcp__mempalace_palace_exec` `update_drawer` per drawer; no bulk rename.
- The knowledge graph, tunnels and diary: plain search does not need them.
