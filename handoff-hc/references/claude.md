# claude

- **Model list**: no list command. A family name alone (`opus`, `sonnet`, `haiku`): pass it as is, no matching. claude resolves the name itself, to the value of `ANTHROPIC_DEFAULT_<FAMILY>_MODEL` under `env` in `~/.claude/settings.json` when set. Report the header line from `hc read` (step 8), because an unset env value leaves the name at claude's own default.
- **Family with a version, or a full name**: candidates are the values of `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL` (grep only those three keys from the file; skip any that are absent). Match them with the step 3 rules. A wanted model whose ID starts with `claude-` is accepted as is without matching.
- **Reasoning flag**: `--effort <level>`. Accepted: `low`, `medium`, `high`, `xhigh`, `max`. claude ignores an unknown value with a warning and uses its default, so a bad level is silent: check the header says `with <level> effort`.
- **Argv**: `claude --model <model> --effort <level> "<first task>"`. The trailing argument is the first message. Omit a flag whose value is unknown.
- **Trust dialog**: in a folder claude has not seen, it blocks on `Is this a project you created or one you trust?` and `hc get` shows no status. The decision is the user's: do not answer it. Tell the user to run `hc attach handoff-<slug>`.
