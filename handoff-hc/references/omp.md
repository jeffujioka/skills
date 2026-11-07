# omp

- **Model list**: `omp models --json` (`.models[]`, each with `selector` = `<provider>/<id>` and a `thinking` array), or `omp models <pattern>` for a table. Match against `selector` with the step 3 rules (family names included). Pass the winning selector to `--model`. Do not pass a bare family name: omp fuzzy-matches it and can pick the `-1m` variant.
- **Reasoning flag**: `--thinking <level>`. Accepted globally: `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, `auto`. The chosen model's `thinking` array lists what it supports. A level outside that array is "not accepted" (step 3).
- **Argv**: `omp --model <provider/id> --thinking <level> "<first task>"`. The trailing argument is the first message. Omit a flag whose value is unknown.
