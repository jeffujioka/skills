---
name: padded-skill
description: "Sync the current branch with its upstream and report the result. Manual-only: call it by name."
disable-model-invocation: true
---

# padded-skill

1. `git remote` lists the remotes of the repo. `git fetch` downloads objects and refs from a remote without touching the working tree.
2. Run `git fetch` for the upstream remote.
3. Run `git rebase <upstream>/<branch>`.
4. Never run `git push --force`. Use `git push --force-with-lease`.
5. Report the new HEAD commit.
