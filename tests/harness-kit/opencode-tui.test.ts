import { Database } from "bun:sqlite";
import { afterEach, beforeEach, expect, test } from "bun:test";
import { chmodSync, copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import plugin, { reminderNotice } from "../../harness-kit/opencode/tui.ts";

type Toast = { message: string; variant?: string };

function context(directory: string, sessionKnown = true) {
  let handler: ((event: { data: { sessionID: string } }) => void) | undefined;
  const toasts: Toast[] = [];
  const { promise: shown, resolve } = Promise.withResolvers<void>();
  return {
    toasts,
    shown,
    emit(sessionID: string) {
      handler?.({ data: { sessionID } });
    },
    ctx: {
      data: {
        on(_type: "session.compaction.ended", h: typeof handler) {
          handler = h;
          return () => {};
        },
        session: { get: (_id: string) => (sessionKnown ? { directory } : undefined) },
        location: { default: () => ({ directory }) },
      },
      ui: {
        toast: {
          show(toast: Toast) {
            toasts.push(toast);
            resolve();
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
  tmp = mkdtempSync("/tmp/harness-kit-opencode-tui-");
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

test("shows a toast naming the logbook after compaction", async () => {
  const logbook = join(home, ".local/state/agents/logbooks", project.replaceAll("/", "-"), "ses_a");
  mkdirSync(logbook, { recursive: true });
  writeFileSync(join(logbook, "progress.md"), "# Progress\n");
  const peer = context(project);
  plugin.setup(peer.ctx);
  peer.emit("ses_a");
  await peer.shown;
  expect(peer.toasts).toEqual([
    { message: `harness-kit: logbook reminder sent to the model (${logbook})`, variant: "info" },
  ]);
});

test("falls back to the default location for an unknown session", async () => {
  const logbook = join(home, ".local/state/agents/logbooks", project.replaceAll("/", "-"), "ses_a");
  mkdirSync(logbook, { recursive: true });
  writeFileSync(join(logbook, "progress.md"), "# Progress\n");
  const peer = context(project, false);
  plugin.setup(peer.ctx);
  peer.emit("ses_a");
  await peer.shown;
  expect(peer.toasts).toHaveLength(1);
});

test("shows nothing without a logbook", async () => {
  const peer = context(project);
  plugin.setup(peer.ctx);
  peer.emit("ses_a");
  await Bun.sleep(1500);
  expect(peer.toasts).toEqual([]);
});

test("names no folder when the reminder has none", () => {
  expect(reminderNotice("Context was compacted.")).toBe("harness-kit: logbook reminder sent to the model");
});
