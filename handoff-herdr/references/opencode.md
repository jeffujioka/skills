# opencode

- **Model list**: `opencode models`. Each line is `<provider>/<model>`.
- **Reasoning**: no flag. It rides on the model variant: `<provider/model>#<variant>`. Carry the current level only if it is a variant the model offers; otherwise omit `#variant`.
- **Start**: the TUI has no model flag (`agent start` rejects `--model`), so seed a session that carries the model, then open it. Both steps must hit the same server.
  - **Server.** Run `zsh -ic 'alias occ'` (the user's alias for the OpenChamber server) and strip ANSI codes. If it contains `opencode --server <url>`, use `<url>` and `occ` below; otherwise use plain `opencode` with no `--server`.
  - **Seed.** The server password (`OPENCODE_PASSWORD`) exists only in the user's interactive shell, so run the seed through it, discarding stderr and stdin: `zsh -ic "opencode run [--server <url>] -m <provider/model>[#variant] --title handoff-<slug> --format json ready" 2>/dev/null </dev/null | grep -a -o 'ses_[A-Za-z0-9]*' | head -1`. The output is the session ID (the JSON line holds it twice, so `head -1`). Write the server flag after `run` (`occ run` expands to an invalid order). Done when the ID is non-empty. With no model chosen, omit `-m`.
  - **Open, plain opencode:** `herdr agent start handoff-<slug> --kind opencode --pane <pane-id> -- --session <sessionID>`.
  - **Open, with `occ`:** `agent start` runs plain `opencode` and cannot use the alias. Run `herdr pane run <pane-id> "occ --session <sessionID>"`, wait until `herdr agent list` shows the pane as an `opencode` agent, then `herdr agent rename <pane-id> handoff-<slug>`.
