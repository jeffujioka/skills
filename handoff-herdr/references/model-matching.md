# Model matching

Match the wanted model against the target harness's model list.

1. Split both names into tokens on `.`, `-`, `_`, space, and `/`.
2. Ignore the provider prefix, a trailing `[1m]`, and a trailing `-YYYYMMDD`.
3. A candidate matches when the wanted tokens appear in it as a contiguous run.
4. If exactly one candidate equals the wanted tokens in full, it wins over the others.
5. A bare family name (`haiku`) matches several candidates: that is a pick-list, not a match.

Examples:

- `haiku 5.5`, `haiku-5.5`, and `haiku.5.5` all match `claude-haiku-5-5`. None matches `claude-haiku-4-5`.
- `claude-sonnet-5-5` matches `claude-sonnet-5.5` and `claude-sonnet-5.5-1m`. The first equals the wanted tokens in full, so it wins.
- `claude-sonnet-5-5` on opencode matches `github-copilot/claude-sonnet-5.5` and `openrouter/anthropic/claude-sonnet-5.5`: two matches, so the user picks.

Use the winning candidate's full value (with provider prefix and any `[1m]`) for the model flag, unchanged.
