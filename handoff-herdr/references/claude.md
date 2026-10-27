# claude

- **Model list**: no list command. Candidates are the aliases `opus`, `sonnet`, `haiku`, plus the values of `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL` under `env` in `~/.claude/settings.json` (grep them; skip any that are absent). A wanted model whose ID starts with `claude-` is accepted as is without matching.
- **Reasoning flag**: `--effort <level>`. Accepted: `low`, `medium`, `high`, `xhigh`, `max`.
- **Start**: `herdr agent start handoff-<slug> --kind claude --pane <pane-id> -- --model <model> --effort <level>`. Omit a flag whose value is unknown.
