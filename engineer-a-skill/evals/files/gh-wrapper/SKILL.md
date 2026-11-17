---
name: gh-wrapper
description: "List the open pull requests assigned to the user with gh. Manual-only: call it by name."
disable-model-invocation: true
---

# gh-wrapper

Lists open pull requests assigned to the user. Read-only.

1. Run `bash scripts/list-prs.sh <owner/repo>`.
2. Print one line per PR: number, title, URL.

*Done when:* every open assigned PR is listed.
