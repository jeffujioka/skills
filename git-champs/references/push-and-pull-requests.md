# Push and Pull Requests

## Sync

- Clean working tree: `git fetch --all --prune`, then `git pull --rebase`.
- Dirty working tree: ask before `git pull --rebase --autostash`, and warn that re-applying the stash can still conflict.

## Pre-Push Checks

1. Run the repo's existing tests and linters; fix failures first. None exist or they cannot run: report the check as skipped, with the reason.
2. Branch behind its base: rebase.
3. Rebase conflicts: resolve, stage, `git rebase --continue`. User wants to stop: `git rebase --abort`, never an extra commit mid-rebase.
4. Confirm the branch is not `main` or `master`. On one: create a feature branch first, unless the user authorized direct integration.

*Done when:* checks pass or are reported as skipped, the branch is up to date with its base, and it is a feature branch.

## Push

- Default flow: commit on a feature branch, show the push summary, push after approval, then open the pull request.
- Interactive cleanup (`git rebase -i --autosquash`) before the first push is fine when intentional.
- Rewriting an already-pushed feature branch needs explicit force-push authorization and `--force-with-lease`.
- Avoid squash merge unless the user asks for it.

## Pull Request Title

A Conventional Commit-style title is fine when it is also clear.

## Protected Branches and Hotfixes

- `main` and `master` are protected: no direct push without explicit authorization, even for docs-only changes; never force-push.
- Do not bypass review or checks unless the user asks for an urgent hotfix exception.
- Hotfix exception: keep the change narrow and call out the follow-up work.
