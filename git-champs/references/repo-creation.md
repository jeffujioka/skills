# Repository Creation

## Local (`git init`)

1. `git init <project-name>`, then work inside it.
2. Rename the initial branch to `main`: `git branch -M main`.
3. Add a `.gitignore` for the project type and a `README.md` if none exists.
4. First commit: `chore: initial commit`, with a body like any other commit.

No remote yet and the user has not said where it goes: ask whether it goes to `github.com` before creating anything remote.

## Remote (`gh repo create`)

1. Confirm the owner and the visibility (private or public) with the user. Never pick visibility silently.
2. Create and link it from the local repo: `gh repo create <owner>/<name> --private --source . --remote origin` (or the confirmed visibility).
3. Push the initial branch after pre-push checks. Pushing `main` here is the one expected direct push; still ask if the user asked for push review.

*Done when:* `git remote -v` shows the new repository on `github.com` and `main` is pushed.

## Push Review Summary

When the user asks to review a push, show this (in the session language) and wait:

```text
Branch:  feature/add-login  ->  origin/feature/add-login
Commits: 2
  a1b2c3d feat(auth): add JWT token validation
  e4f5g6h test(auth): add unit tests for token expiry
Diff stat:
  src/auth.ts  | +45 -3
  test/auth.ts | +80

Push? [y/N]
```
