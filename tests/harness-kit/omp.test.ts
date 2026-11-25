import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { chmodSync, copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import harnessKit, {
  compactReminderEnv,
  longCacheRejected,
  reminderContext,
  rewriteToolCall,
  setLongCache,
  wantsLongCache,
} from "../../harness-kit/omp/harness-kit.ts";

describe("omp harness-kit extension", () => {
  test("rewrites agent-env", () => {
    expect(rewriteToolCall({ toolName: "bash", input: { command: "agent-env", timeout: 30 } })).toEqual({
      input: { command: "export AGENT_HARNESS=omp; agent-env", timeout: 30 },
    });
  });

  test("rewrites a skills script", () => {
    const command = "bash ~/.agents/skills/logbook/scripts/path.sh";
    expect(rewriteToolCall({ toolName: "bash", input: { command } })).toEqual({
      input: { command: `export AGENT_HARNESS=omp; ${command}` },
    });
  });

  test("leaves other commands alone", () => {
    expect(rewriteToolCall({ toolName: "bash", input: { command: "ls -la" } })).toBeUndefined();
    expect(rewriteToolCall({ toolName: "bash", input: { command: "cat docs/skills/x.md" } })).toBeUndefined();
    expect(rewriteToolCall({ toolName: "read", input: { path: "agent-env" } })).toBeUndefined();
  });

  test("builds the agent-env environment", () => {
    const file = "/h/.omp/agent/sessions/-p/2026-11-14T10-00-00-000Z_r1/Sub.jsonl";
    const base = { AGENT_HARNESS: "claude", PATH: "/bin", X: undefined };
    expect(compactReminderEnv(base, "s2", file)).toEqual({
      AGENT_HARNESS: "omp",
      PATH: "/bin",
      PI_SESSION_ID: "s2",
      PI_SESSION_FILE: file,
    });
    expect(compactReminderEnv(base, "s2", undefined)).toEqual({
      AGENT_HARNESS: "omp",
      PATH: "/bin",
      PI_SESSION_ID: "s2",
      PI_SESSION_FILE: "",
    });
  });

  test("trims a reminder", () => {
    expect(reminderContext("Context was compacted. Read x\n")).toBe("Context was compacted. Read x");
  });

  test("adds nothing without a reminder", () => {
    expect(reminderContext("")).toBeUndefined();
    expect(reminderContext("\n")).toBeUndefined();
  });
});

type Handler = (event: unknown, ctx: unknown) => unknown;
type Sent = { message: { customType: string; content: string; display: boolean }; options: { deliverAs: "steer" } };

function peer() {
  const handlers: Record<string, Handler> = {};
  const sent: Sent[] = [];
  return {
    handlers,
    sent,
    on(event: string, handler: Handler) {
      handlers[event] = handler;
    },
    sendMessage(message: Sent["message"], options: Sent["options"]) {
      sent.push({ message, options });
    },
  };
}

const notices: { message: string; type?: string }[] = [];

function sessionContext(cwd: string, sessionFile: string | undefined, hasUI = true) {
  return {
    cwd,
    hasUI,
    ui: { notify: (message: string, type?: string) => notices.push({ message, type }) },
    sessionManager: { getSessionId: () => "s2", getSessionFile: () => sessionFile },
  };
}

describe("omp session_compact", () => {
  let tmp: string;
  let home: string;
  let project: string;
  const realHome = process.env.HOME;

  beforeEach(() => {
    tmp = mkdtempSync("/tmp/harness-kit-omp-");
    home = join(tmp, "home");
    project = join(tmp, "project");
    mkdirSync(join(home, ".local/bin"), { recursive: true });
    mkdirSync(project);
    notices.length = 0;
    const agentEnv = join(home, ".local/bin/agent-env");
    copyFileSync(join(import.meta.dir, "../../harness-kit/bin/agent-env"), agentEnv);
    chmodSync(agentEnv, 0o755);
    process.env.HOME = home;
  });

  afterEach(() => {
    process.env.HOME = realHome;
    rmSync(tmp, { recursive: true, force: true });
  });

  test("sends the reminder after compaction", async () => {
    const file = join(home, ".omp/agent/sessions/-p/2026-11-14T10-00-00-000Z_r1/s2.jsonl");
    const logbook = join(home, ".local/state/agents/logbooks", project.replaceAll("/", "-"), "r1");
    mkdirSync(logbook, { recursive: true });
    writeFileSync(join(logbook, "progress.md"), "# Progress\n");
    const pi = peer();
    harnessKit(pi);
    await pi.handlers.session_compact({}, sessionContext(project, file));
    expect(pi.sent).toHaveLength(1);
    expect(pi.sent[0].options).toEqual({ deliverAs: "steer" });
    expect(pi.sent[0].message.customType).toBe("harness-kit-reminder");
    expect(pi.sent[0].message.display).toBe(false);
    expect(pi.sent[0].message.content).toStartWith("Context was compacted.");
    expect(pi.sent[0].message.content).toContain(`${logbook}/progress.md`);
    expect(pi.sent[0].message.content).not.toEndWith("\n");
    expect(notices).toEqual([
      { message: `harness-kit: logbook reminder sent to the model (${logbook})`, type: "info" },
    ]);
  });

  test("shows no notice without a UI", async () => {
    const logbook = join(home, ".local/state/agents/logbooks", project.replaceAll("/", "-"), "s2");
    mkdirSync(logbook, { recursive: true });
    writeFileSync(join(logbook, "progress.md"), "# Progress\n");
    const pi = peer();
    harnessKit(pi);
    await pi.handlers.session_compact({}, sessionContext(project, undefined, false));
    expect(pi.sent).toHaveLength(1);
    expect(notices).toEqual([]);
  });

  test("sends nothing without a logbook", async () => {
    const pi = peer();
    harnessKit(pi);
    await pi.handlers.session_compact({}, sessionContext(project, undefined));
    expect(pi.sent).toEqual([]);
    expect(notices).toEqual([]);
  });

  test("survives a failed agent-env", async () => {
    rmSync(join(home, ".local/bin/agent-env"));
    const pi = peer();
    harnessKit(pi);
    await expect(pi.handlers.session_compact({}, sessionContext(project, undefined))).resolves.toBeUndefined();
    expect(pi.sent).toEqual([]);
  });
});

const copilotSonnet = { provider: "github-copilot", id: "claude-sonnet-5.5-1m" };
const main = { kind: "main" };

function anthropicPayload() {
  return {
    model: "claude-sonnet-5.5-1m",
    system: [{ type: "text", text: "rules", cache_control: { type: "ephemeral" } }],
    messages: [
      { role: "user", content: [{ type: "text", text: "hi", cache_control: { type: "ephemeral" } }] },
      { role: "assistant", content: [{ type: "text", text: "no marker" }] },
    ],
  };
}

describe("omp 1h cache for Copilot Claude", () => {
  beforeEach(() => {
    notices.length = 0;
  });

  test("sets ttl 1h on every ephemeral marker", () => {
    const payload = anthropicPayload();
    expect(setLongCache(payload)).toBe(2);
    expect(payload.system[0].cache_control).toEqual({ type: "ephemeral", ttl: "1h" });
    expect(payload.messages[0].content[0].cache_control).toEqual({ type: "ephemeral", ttl: "1h" });
    expect(payload.messages[1].content[0]).toEqual({ type: "text", text: "no marker" });
  });

  test("counts no marker in a payload without one", () => {
    expect(setLongCache({ model: "m", messages: [{ role: "user", content: "hi" }] })).toBe(0);
  });

  test("applies to the main session on a Copilot Claude model only", () => {
    expect(wantsLongCache({ model: copilotSonnet, agent: main }, {})).toBe(true);
    expect(wantsLongCache({ model: copilotSonnet, agent: { kind: "sub" } }, {})).toBe(false);
    expect(wantsLongCache({ model: { provider: "github-copilot", id: "gpt-5.5" }, agent: main }, {})).toBe(false);
    expect(wantsLongCache({ model: { provider: "anthropic", id: "claude-sonnet-5.5" }, agent: main }, {})).toBe(false);
    expect(wantsLongCache({ agent: main }, {})).toBe(false);
  });

  test("HARNESS_KIT_COPILOT_CACHE=5m opts out", () => {
    expect(wantsLongCache({ model: copilotSonnet, agent: main }, { HARNESS_KIT_COPILOT_CACHE: "5m" })).toBe(false);
  });

  test("only a refused request that carried 1h counts as a refusal", () => {
    expect(longCacheRejected(400, true)).toBe(true);
    expect(longCacheRejected(422, true)).toBe(true);
    expect(longCacheRejected(400, false)).toBe(false);
    expect(longCacheRejected(429, true)).toBe(false);
    expect(longCacheRejected(200, true)).toBe(false);
  });

  test("returns the payload with 1h markers, then stops after a refusal", () => {
    const pi = peer();
    harnessKit(pi);
    const ctx = { ...sessionContext("/p", undefined), model: copilotSonnet, agent: main };
    const first = anthropicPayload();
    expect(pi.handlers.before_provider_request({ payload: first }, ctx)).toBe(first);
    expect(first.system[0].cache_control).toEqual({ type: "ephemeral", ttl: "1h" });
    pi.handlers.after_provider_response({ status: 400 }, ctx);
    expect(notices).toEqual([
      { message: "harness-kit: Copilot refused the 1h cache; back to 5m for this session", type: "warning" },
    ]);
    const second = anthropicPayload();
    expect(pi.handlers.before_provider_request({ payload: second }, ctx)).toBeUndefined();
    expect(second.system[0].cache_control).toEqual({ type: "ephemeral" });
  });

  test("a refusal of a request without 1h changes nothing", () => {
    const pi = peer();
    harnessKit(pi);
    const ctx = { ...sessionContext("/p", undefined), model: copilotSonnet, agent: { kind: "sub" } };
    expect(pi.handlers.before_provider_request({ payload: anthropicPayload() }, ctx)).toBeUndefined();
    pi.handlers.after_provider_response({ status: 400 }, ctx);
    expect(notices).toEqual([]);
  });
});
