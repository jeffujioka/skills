# When MCP is OK as Fallback

Use GitHub MCP tools only when `gh` genuinely can't accomplish the task.

## Valid fallback cases

- **Specialized search filters** that `gh search` doesn't support
- **Downloading workflow artifacts** — MCP's `download_workflow_run_artifact` has no clean `gh` equivalent beyond `gh run download`
- **Complex GraphQL queries** where `gh api graphql` would be awkward and the MCP tool already structures the query

Even in these cases, consider whether `gh api` with a custom endpoint could work first — it often can.
