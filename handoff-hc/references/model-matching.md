# Model matching

Match the wanted model against the target harness's model list.

1. Split both names into tokens on `.`, `-`, `_`, space, and `/`.
2. Ignore the provider prefix, a trailing `[1m]`, and a trailing `-YYYYMMDD`.
3. A candidate matches when the wanted tokens appear in it as a contiguous run.
4. If exactly one candidate equals the wanted tokens in full, it wins over the others.
5. Several candidates left that differ only by provider: the one whose provider equals the current model's provider wins. None equal: pick-list.
6. Several candidates left that differ only by a context suffix (`-1m`, `[1m]`): the one without the suffix wins, unless the user named the suffix or the wanted model is the current model carried over with it.

## Family names

A family name alone (`opus`, `sonnet`, `haiku`) selects the newest version:

1. Keep the candidates that contain the family token.
2. The version is the run of numeric tokens after the family (`sonnet-5.5` is 5.5, `sonnet-5` is 5, `opus-4.8` is 4.8). Drop candidates without a version (`-latest` aliases) and candidates with other tokens after the version besides the context suffix (`-fast`).
3. Keep the candidates with the highest version (compare numeric token by numeric token; `5.5` is above `5`, which is above `4.8`).
4. Apply rules 5 and 6 to what is left.

A family with a version (`sonnet 5.5`) is an ordinary name: rules 1-6 above.

Examples:

- `haiku 5.5`, `haiku-5.5`, and `haiku.5.5` all match `claude-haiku-5-5`. None matches `claude-haiku-4-5`.
- `claude-sonnet-5-5` matches `claude-sonnet-5.5` and `claude-sonnet-5.5-1m`. The first equals the wanted tokens in full, so it wins.
- `sonnet` on omp, from the list `claude-sonnet-4.6`, `claude-sonnet-5`, `claude-sonnet-5.5`, `claude-sonnet-5.5-1m`: highest version is 5.5, rule 6 drops the `-1m` one, result `github-copilot/claude-sonnet-5.5`.
- `opus` on opencode with `github-copilot/claude-opus-5.5`, `openrouter/anthropic/claude-opus-5.5`, `openrouter/~anthropic/claude-opus-latest`: the `-latest` alias has no version and drops. The other two differ by provider: the current model's provider wins, else the user picks.
- `claude-sonnet-5-5` on opencode matches `github-copilot/claude-sonnet-5.5` and `openrouter/anthropic/claude-sonnet-5.5`. If the current model is on neither provider, the user picks.

Use the winning candidate's full value (with provider prefix and any `[1m]`) for the model flag, unchanged.
