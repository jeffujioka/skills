import { afterEach, beforeEach, expect, test } from "bun:test";
import { Database } from "bun:sqlite";
import { chmodSync, copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import plugin from "../../harness-kit/opencode/server.ts";

type ShellEvent = { command: string; env: Record<string, string | undefined> };
type Put = { sessionID: string; key: string; value: string };

const compactionEnded = {
  id: "evt_1",
  created: 1794693323262,
  type: "session.compaction.ended",
  durable: { aggregateID: "ses_a", seq: 9, version: 1 },
  location: { directory: "" },
  data: { sessionID: "ses_a", reason: "auto", text: "summary", cost: 0, tokens: {} },
};

function peer(directory: string, events: unknown[] = []) {
  const hooks: Record<string, (event: ShellEvent) => void> = {};
  const puts: Put[] = [];
  const subscriptions: unknown[] = [];
  const { promise: allHandled, resolve: handled } = Promise.withResolvers<void>();
  return {
    hooks,
    puts,
    subscriptions,
    allHandled,
    shell: {
      hook(name: string, handler: (event: ShellEvent) => void) {
        hooks[name] = handler;
      },
    },
    event: {
      subscribe(options: unknown) {
        subscriptions.push(options);
        return (async function* () {
          for (const event of events) yield event;
          // The plugin asks for the next event only after it handled the last one.
          handled();
          await Promise.withResolvers<never>().promise;
        })();
      },
    },
    session: {
      async get({ sessionID }: { sessionID: string }) {
        return { id: sessionID, directory };
      },
      instructions: {
        entry: {
          async put(entry: Put) {
            puts.push(entry);
          },
        },
      },
    },
  };
}

let tmp: string;
let home: string;
let project: string;
const realHome = process.env.HOME;

beforeEach(() => {
  tmp = mkdtempSync("/tmp/harness-kit-opencode-");
  home = join(tmp, "home");
  project = join(tmp, "project");
  mkdirSync(join(home, ".local/bin"), { recursive: true });
  mkdirSync(project);
  const agentEnv = join(home, ".local/bin/agent-env");
  copyFileSync(join(import.meta.dir, "../../harness-kit/bin/agent-env"), agentEnv);
  chmodSync(agentEnv, 0o755);
  mkdirSync(join(home, ".local/share/opencode"), { recursive: true });
  const db = new Database(join(home, ".local/share/opencode/opencode.db"));
  db.run("create table session_v2(id text primary key, parent_id text)");
  db.run("insert into session_v2(id, parent_id) values ('ses_a', null)");
  db.close();
  process.env.HOME = home;
});

afterEach(() => {
  process.env.HOME = realHome;
  rmSync(tmp, { recursive: true, force: true });
});

test("sets AGENT_HARNESS on shell create", async () => {
  const ctx = peer(project);
  await plugin.setup(ctx);
  const event: ShellEvent = { command: "agent-env", env: { AGENT_HARNESS: "omp", PI_SESSION_ID: "s9" } };
  ctx.hooks["create.before"](event);
  expect(event.env.AGENT_HARNESS).toBe("opencode");
  expect(event.env.PI_SESSION_ID).toBe("s9");
});

test("exports one plugin", async () => {
  // Imported here to check the module's whole export list.
  const mod = await import("../../harness-kit/opencode/server.ts");
  expect(mod.default.id).toBe("harness-kit");
  expect(Object.keys(mod)).toEqual(["default"]);
});

test("puts the reminder after compaction", async () => {
  const logbook = join(home, ".local/state/agents/logbooks", project.replaceAll("/", "-"), "ses_a");
  mkdirSync(logbook, { recursive: true });
  writeFileSync(join(logbook, "progress.md"), "# Progress\n");
  const ctx = peer(project, [compactionEnded]);
  await plugin.setup(ctx);
  await ctx.allHandled;
  expect(ctx.subscriptions).toEqual([{ types: ["session.compaction.ended"] }]);
  expect(ctx.puts).toHaveLength(1);
  expect(ctx.puts[0].sessionID).toBe("ses_a");
  expect(ctx.puts[0].key).toBe("harness-kit-compact-reminder");
  expect(ctx.puts[0].value).toStartWith("Context was compacted.");
  expect(ctx.puts[0].value).toContain(`${logbook}/progress.md`);
  expect(ctx.puts[0].value).not.toEndWith("\n");
});

test("puts nothing without a logbook", async () => {
  const ctx = peer(project, [compactionEnded]);
  await plugin.setup(ctx);
  await ctx.allHandled;
  expect(ctx.subscriptions).toHaveLength(1);
  expect(ctx.puts).toEqual([]);
});

test("keeps reminding after a failed event", async () => {
  const logbook = join(home, ".local/state/agents/logbooks", project.replaceAll("/", "-"), "ses_a");
  mkdirSync(logbook, { recursive: true });
  writeFileSync(join(logbook, "progress.md"), "# Progress\n");
  const missing = { ...compactionEnded, data: { ...compactionEnded.data, sessionID: "ses_missing" } };
  const ctx = peer(project, [missing, compactionEnded]);
  await plugin.setup(ctx);
  await ctx.allHandled;
  expect(ctx.puts.map((put) => put.sessionID)).toEqual(["ses_a"]);
});

test("setup returns before any event", async () => {
  const ctx = peer(project);
  await plugin.setup(ctx);
  expect(ctx.subscriptions).toHaveLength(1);
  expect(ctx.puts).toEqual([]);
});

test("logs a failed subscription", async () => {
  const ctx = peer(project);
  ctx.event.subscribe = () => {
    throw new Error("closed");
  };
  const { promise: logged, resolve: log } = Promise.withResolvers<unknown[]>();
  const realError = console.error;
  console.error = (...args: unknown[]) => log(args);
  try {
    await plugin.setup(ctx);
    expect(String((await logged)[1])).toContain("closed");
  } finally {
    console.error = realError;
  }
});
