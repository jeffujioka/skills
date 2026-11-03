# Start From the Base Branch

For a commit, push or pull request requested while on the base branch (`main`, `master`, or the target of `origin/HEAD`) with uncommitted work. Creating the branch and committing is local and reversible: do it without a question (rule 6). Only the push needs approval.

Paths below are relative to this skill dir; run the scripts with the target repo as working directory.

## Steps

1. **Split the diff.** Read `git status` and the full diff. Changes that belong to the user's request go in the commit; every other change is a leftover. Cannot tell which is which: ask, as a numbered list of files or hunks.
2. **Name the branch** `<type>/<kebab-summary>`: `<type>` is the Conventional Commit type of the commit you are about to make, the summary is 2-5 lowercase words from its description, with no scope and no ticket key. The name must not exist in `git branch --all`. Example: `fix(zsh): make ctrl+l clear the scrollback too` gives `fix/ctrl-l-clear-scrollback`.
3. **Create it from HEAD:** `git switch -c <name>`. The working tree, leftovers included, comes along unchanged.
4. **Stage only the related changes.**
   - Whole files: `git add <path>`.
   - A file with related and unrelated hunks: list them, then stage by number. `git add -p` needs a TTY and does not work for an agent.

     ```sh
     bash scripts/stage-hunks.sh --list zshrc      # 1: @@ ... first changed line
     bash scripts/stage-hunks.sh zshrc 1           # stage hunk 1 only
     ```

     The script applies the filtered diff to the index with `git apply --cached --recount`; `--recount` is required because the line counts in the remaining hunk headers are stale once hunks are dropped. The working tree is not touched. Changes close together form one hunk: add `-U0` (`stage-hunks.sh -U0 zshrc 1`) to split them.
   - Check `git diff --cached`: it holds only the related change.
5. **Commit** per Conventional Commits. Leave the leftovers uncommitted and untouched: no stash, checkout or reset here.
6. **Local commits already on the base branch** come along into the new branch; the base stays ahead of its remote. Report it; do not reset the base branch.

## Feeding `gh-pr-create`

Leftover tracked changes make `gh-pr-create` ask its dirty-tree question (step 1). When a pull request follows, answer it in advance: show the push summary and that menu in one message, with two separate answers, default option 2 (stash around the create command, then pop):

```text
Push? [y/N]
Leftovers (not in the PR): zprofile, zshrc
<the four dirty-tree options from gh-pr-create step 1>
Reply with both, for example: y 2
```

A push approval never approves the leftover option, or the reverse; an answer missing either part gets the missing question asked again. After the reply, push, then continue with `gh-pr-create` from its step 1; it does not ask the leftover question a second time.
