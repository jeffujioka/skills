# omp reference

Verified with: omp 18.20.0 for the reminder, omp 18.22.2 for the 1h cache. Both run as `omp -p` in a temporary HOME, so nothing touches the real `~/.omp`.

## Extension

- An extension is a module whose default export is `function (pi)`. It is loaded with `-e <file>` (`--no-extensions` still honours explicit `-e` paths) or from `~/.omp/agent/extensions/`.
- Calling `pi.sendMessage` while the extension is loading throws. Call it from event handlers only.

## Route for the reminder: `session_compact` + `pi.sendMessage`

`session.compacting` is not the route:

- It runs, and receives `{ sessionId, messages }`. Its `context` lines only feed an LLM summarizer as `<additional-context>`.
- With the default `compaction.methodOrder` (`remote, snapcompact, handoff, shake, soft`), `snapcompact` wins. It writes a verbatim archive and drops the lines.
- `handoff` drops them too, and `soft` paraphrases them.

The working route:

```ts
pi.on('session_compact', (event, ctx) => {
  pi.sendMessage(
    { customType: 'harness-kit-reminder', content: REMINDER, display: false },
    { deliverAs: 'steer' },
  );
});
```

- `event` keys: `type`, `compactionEntry`, `fromExtension`. The event carries no session id.
- `ctx.sessionManager.getSessionId()`: the session id, such as `01a1dc11-…`.
- `ctx.cwd`: the session's working folder.
- `ctx.sessionManager.getSessionFile()`: `~/.omp/agent/sessions/<cwd slug>/<ts>_<session id>.jsonl`.
- Delivery mode: `"steer"` delivers into the running turn when compaction ran mid-turn, and appends at once when idle. `"nextTurn"` waits for a turn that `omp -p` never starts, so the message is lost when the process exits.

## Notice for the user

After `pi.sendMessage`, the handler calls `ctx.ui.notify("harness-kit: logbook reminder sent to the model (<logbook folder>)", "info")` when `ctx.hasUI` is true. `display: false` keeps the reminder itself out of the screen; the notice is a transient line that is not stored in the session and that the model never sees. Print mode (`omp -p`) has no UI, so it shows nothing.

## Where the reminder shows up

In the session jsonl, after the `"type":"compaction"` entry (written by `method: "snapcompact"` with the default method order): a `"type":"custom_message"` entry with `customType: "harness-kit-reminder"`, `display: false`, `attribution: "agent"` and the reminder as `content`. omp rebuilds that entry into the model's context as a `custom` role message.

## Session-only threshold

- Pass an overlay: `omp --config <tmp>/compact.yml` with `compaction: {thresholdTokens: 20000}`.
- The bash tool keeps at most 50 KiB of output inline. The size is fixed: `tools.artifactSpillThreshold` does not change it for bash. A `cat` of the 3000-line filler therefore brings the context to only about 27k tokens, and 40000 never fires.
- In print mode the default async (speculative) compaction for `soft`/`handoff` is aborted when the process exits. `snapcompact`, the default winner, runs synchronously.

## Check by hand

In a session whose logbook folder holds `progress.md`, let a compaction run, for example with the threshold above. In the session jsonl, after the `"type":"compaction"` entry, a `"type":"custom_message"` entry with `customType` `harness-kit-reminder` holds the reminder.

## 1h cache for Copilot Claude

The extension hooks `before_provider_request` and `after_provider_response`.

- `before_provider_request` receives `{ payload }` and `ctx` with `ctx.model` (`provider`, `id`) and `ctx.agent.kind` (`"main"` or `"sub"`). The handler returns the payload itself.
- It applies when `ctx.agent.kind` is `"main"`, `ctx.model.provider` is `github-copilot`, `ctx.model.id` starts with `claude`, and `HARNESS_KIT_COPILOT_CACHE` is not `5m`.
- It sets `ttl: "1h"` on every `cache_control: {type: "ephemeral"}` marker in the payload.
- The extension is also loaded into each subagent session, so the `ctx.agent.kind` check is what keeps subagents on 5-minute entries.
- Cache warming replays the real request through the same hook. The change is deterministic, so the replay stays byte-identical and still hits the cache.

Why omp sends 5-minute entries: its model catalog marks every Copilot Claude model `supportsLongCacheRetention: false`, so `providers.cacheRetention: long` falls back to 5 minutes there.

Measured on `github-copilot/claude-haiku-5.5-1m` with a 38k-token unique prompt and the extension loaded through `-e`: the usage block reports `"cttl":{"ephemeral1h":38597}`. A separate probe sent a 53k-token prompt twice 6 min 56 s apart: the second request read all 53331 tokens from the cache. Not measured: Sonnet and Opus on Copilot.

Refusal fallback: after a 400 or 422 to a request that carried 1h entries, the extension sends no more 1h entries in that session and calls `ctx.ui.notify` with a warning. Covered by a unit test only; Copilot never refused a 1h entry in the probes.

Cost ratio from Anthropic's price list: a 1h write is 2 times the input price, a 5-minute write 1.25 times (1.6 times as much); a read is the same for both.
