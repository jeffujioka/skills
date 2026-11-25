# opencode reference

Verified with: opencode 2.3.0, run as `opencode run --standalone` in a temporary HOME, so nothing touches the real opencode config or database.

## Plugin

- A plugin is a module whose default export is `{ id: string, setup(ctx) }`. opencode loads a single file from `<project>/.opencode/plugins/<file>.ts` and from `~/.config/opencode/plugins/<file>.ts`, but a single file has only a server part. harness-kit installs a folder, `~/.config/opencode/plugins/harness-kit/`, whose `index.ts` is the server part and whose `tui.ts` is the TUI part (a local plugin folder without `package.json` uses `server` or `index`, and `tui`, at its root). The log line `msg="loading plugin" id=<path>` confirms the load.
- `setup` must return without awaiting the event loop. Start the subscription loop with `(async () => { for await (...) {...} })()` and do not await it.

## Event: `session.compaction.ended`

Subscribe with `ctx.event.subscribe({ types: ["session.compaction.ended"] })`, an async iterable. The verified event shape:

```json
{
  "id": "evt_…",
  "created": 1794693323262,
  "type": "session.compaction.ended",
  "durable": { "aggregateID": "ses_…", "seq": 9, "version": 1 },
  "location": { "directory": "<project folder>" },
  "metadata": { "keepID": "msg_…" },
  "data": {
    "sessionID": "ses_…",
    "reason": "auto",
    "model": {
      "id": "claude-haiku-5.5",
      "providerID": "github-copilot",
      "variant": "default"
    },
    "text": "<the compaction summary>",
    "cost": 0.0,
    "tokens": {}
  }
}
```

- Session id: `event.data.sessionID`.
- `metadata` is present only on some compactions.
- The session's folder is `(await ctx.session.get({ sessionID })).directory`, the same value as `event.location.directory`.

## Calls that worked

- `ctx.session.get({ sessionID })` returns the session row, including `directory`.
- `ctx.session.instructions.entry.put({ sessionID, key, value })` attaches or replaces a durable instruction entry. The change is announced at the next step boundary. The model saw the entry on the next turn.

## Notice for the user: a toast in the TUI part

- A toast is a small box that opencode draws in a corner of the terminal UI for a few seconds. It is not stored and the model never sees it.
- The server part has no toast call. The toast comes from the TUI part, `tui.ts`, with the same `{ id, setup(context) }` shape: `context.data.on("session.compaction.ended", handler)` and `context.ui.toast.show({ message, variant: "info" })`. The `data.session.get(sessionID)` result gives the folder; without it the handler uses `context.location` or `context.data.location.default()`.
- The TUI part runs `agent-env compact-reminder` itself, as the server part does, and shows `harness-kit: logbook reminder sent to the model (<logbook folder>)` only when it prints a reminder.
- Headless `opencode run` loads no TUI part. A real TUI in a temporary HOME under tmux showed the toast in the top right corner after `/compact`.

## Where the reminder shows up

- The table `instruction_entry` in `~/.local/share/opencode/opencode.db` gets the row `(session_id, key = 'harness-kit-compact-reminder', value, removed = 0)`. `value` is the JSON-encoded string, for example `"Context was compacted. …"`, stored inline rather than through `instruction_blob`.
- The model receives it as part of its instructions. Asked to quote it, haiku refused ("The compaction note itself is a harness message"), so tests assert on the stored entry, not on the reply.

## Session-only threshold

- Use the project's `opencode.json`: `{"compaction": {"auto": true, "buffer": "99%"}}`. `opencode debug config` lists it as a config source.
- `buffer` values of `80%`, `90%` and `95%` never fired with the 3000-line filler, whose context was about 46k tokens, mostly cache reads. `99%` fires, sometimes more than once in a turn.
- `opencode run` truncates long tool output, much like omp does.

## Check by hand

In a session whose logbook folder holds `progress.md`, let a compaction run, for example with the threshold above. Then `sqlite3 ~/.local/share/opencode/opencode.db "select value from instruction_entry where key = 'harness-kit-compact-reminder' and removed = 0"` prints the reminder for that session.
