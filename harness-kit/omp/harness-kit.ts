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

type SessionContext = {
  cwd: string;
  hasUI: boolean;
  ui: { notify(message: string, type?: "info" | "warning" | "error"): void };
  sessionManager: { getSessionId(): string; getSessionFile(): string | undefined };
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
  sendMessage(
    message: { customType: string; content: string; display: boolean },
    options: { deliverAs: "steer" },
  ): void;
}): void {
  pi.on("tool_call", (event) => rewriteToolCall(event));
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
