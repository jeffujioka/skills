# omp

- **Model list**: `omp models` (table, grouped by provider) or `omp models --json` (each entry has `selector` = `<provider>/<id>` and a `thinking` array). Filter with `omp models <pattern>`. Pass the selector to `--model`.
- **Reasoning flag**: `--thinking <level>`. Accepted globally: `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, `auto`. Each model's `thinking` array lists what it supports; carry the current level only if the chosen model lists it.
- **Start**: `herdr agent start handoff-<slug> --kind omp --pane <pane-id> -- --model <provider/id> --thinking <level>`. Omit a flag whose value is unknown.
