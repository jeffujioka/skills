// harness-kit @VERSION@

import { execFile } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);

const SKILLS_SCRIPT = /\/skills\/[^/\s]+\/scripts\//;

export function isSkillsCommand(command: string): boolean {
  return command.includes("agent-env") || SKILLS_SCRIPT.test(command);
}

export function rewriteToolCall(event: {
  toolName: string;
  input: Record<string, unknown>;
}): { input: Record<string, unknown> } | undefined {
  const { command } = event.input;
  if (event.toolName !== "bash" || typeof command !== "string" || !isSkillsCommand(command)) {
    return undefined;
  }
  return { input: { ...event.input, command: `export AGENT_HARNESS=omp; ${command}` } };
}

export function compactReminderEnv(
  base: Record<string, string | undefined>,
  sessionId: string,
  sessionFile: string | undefined,
): Record<string, string> {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(base)) {
    if (value !== undefined) env[key] = value;
  }
  env.AGENT_HARNESS = "omp";
  env.PI_SESSION_ID = sessionId;
  env.PI_SESSION_FILE = sessionFile ?? "";
  return env;
}

export function reminderContext(stdout: string): string | undefined {
  const reminder = stdout.trim();
  return reminder === "" ? undefined : reminder;
}

export function reminderNotice(reminder: string): string {
  const logbook = /`([^`]+)\/progress\.md`/.exec(reminder)?.[1];
  return logbook ? `harness-kit: logbook reminder sent to the model (${logbook})` : "harness-kit: logbook reminder sent to the model";
}

// Copilot serves Claude 1h cache entries, but omp's catalog marks every Copilot Claude model
// supportsLongCacheRetention: false, so omp sends 5m markers (references/omp.md).
const CACHE_OPT_OUT = "HARNESS_KIT_COPILOT_CACHE";
// 400 and 422 are how a server refuses an unknown request field.
const REJECTED = new Set([400, 422]);

type ModelRef = { provider?: string; id?: string };

export function wantsLongCache(
  ctx: { model?: ModelRef; agent?: { kind: string } },
  env: Record<string, string | undefined>,
): boolean {
  return (
    ctx.agent?.kind === "main" &&
    ctx.model?.provider === "github-copilot" &&
    ctx.model.id?.startsWith("claude") === true &&
    env[CACHE_OPT_OUT] !== "5m"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

// Sets ttl "1h" on every ephemeral cache marker in the payload and returns how many it changed.
export function setLongCache(node: unknown): number {
  if (Array.isArray(node)) return node.reduce<number>((sum, item) => sum + setLongCache(item), 0);
  if (!isRecord(node)) return 0;
  let count = 0;
  const marker = node.cache_control;
  if (isRecord(marker) && marker.type === "ephemeral") {
    marker.ttl = "1h";
    count++;
  }
  for (const value of Object.values(node)) count += setLongCache(value);
  return count;
}

export function longCacheRejected(status: number, sentLongCache: boolean): boolean {
  return sentLongCache && REJECTED.has(status);
}

type SessionContext = {
  cwd: string;
  hasUI: boolean;
  ui: { notify(message: string, type?: "info" | "warning" | "error"): void };
  sessionManager: { getSessionId(): string; getSessionFile(): string | undefined };
};

type ProviderContext = {
  hasUI: boolean;
  ui: SessionContext["ui"];
  model?: ModelRef;
  agent?: { kind: string };
};

export default function harnessKit(pi: {
  on(
    event: "tool_call",
    handler: (event: {
      toolName: string;
      input: Record<string, unknown>;
    }) => { input: Record<string, unknown> } | undefined,
  ): void;
  on(event: "session_compact", handler: (event: unknown, ctx: SessionContext) => Promise<void>): void;
  on(event: "before_provider_request", handler: (event: { payload: unknown }, ctx: ProviderContext) => unknown): void;
  on(event: "after_provider_response", handler: (event: { status: number }, ctx: ProviderContext) => void): void;
  sendMessage(
    message: { customType: string; content: string; display: boolean },
    options: { deliverAs: "steer" },
  ): void;
}): void {
  pi.on("tool_call", (event) => rewriteToolCall(event));
  // Sent a 1h marker on the last request; a refusal turns the 1h cache off for this session.
  let sentLongCache = false;
  let refused = false;
  pi.on("before_provider_request", (event, ctx) => {
    sentLongCache = false;
    if (refused || !wantsLongCache(ctx, process.env)) return undefined;
    sentLongCache = setLongCache(event.payload) > 0;
    return event.payload;
  });
  pi.on("after_provider_response", (event, ctx) => {
    if (longCacheRejected(event.status, sentLongCache)) {
      refused = true;
      if (ctx.hasUI) ctx.ui.notify("harness-kit: Copilot refused the 1h cache; back to 5m for this session", "warning");
    }
    sentLongCache = false;
  });
  // session.compacting is not the route: its context lines only feed a summarizer (references/omp.md).
  pi.on("session_compact", async (_event, ctx) => {
    try {
      const { stdout } = await run(join(process.env.HOME ?? homedir(), ".local/bin/agent-env"), ["compact-reminder"], {
        cwd: ctx.cwd,
        env: compactReminderEnv(process.env, ctx.sessionManager.getSessionId(), ctx.sessionManager.getSessionFile()),
      });
      const reminder = reminderContext(stdout);
      if (reminder) {
        pi.sendMessage({ customType: "harness-kit-reminder", content: reminder, display: false }, { deliverAs: "steer" });
        if (ctx.hasUI) ctx.ui.notify(reminderNotice(reminder), "info");
      }
    } catch (error) {
      console.error("harness-kit: compaction reminder failed:", error);
    }
  });
}
