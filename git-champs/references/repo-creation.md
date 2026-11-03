# Repository Creation

## Local (`git init`)

1. `git init <project-name>`, then work inside it.
2. Rename the initial branch to `main`: `git branch -M main`.
3. Add a `.gitignore` for the project type and a `README.md` if none exists.
4. First commit: `chore: initial commit`, with a body like any other commit.

No remote yet and the user has not said where it goes: ask whether it goes to `github.com` before creating anything remote.

## Remote (`gh repo create`)

1. Confirm the owner and the visibility (private or public) with the user. Never pick visibility silently.
2. Show the command and wait for approval, then create and link it from the local repo: `gh repo create <owner>/<name> --private --source . --remote origin` (or the confirmed visibility).
3. Push `main` after pre-push checks and the push summary approval. A request to create and publish the repository authorizes this first direct push of `main`; no other push of `main`.

*Done when:* `git remote -v` shows the new repository on `github.com` and `main` is pushed.
