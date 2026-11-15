// harness-kit @VERSION@

import { execFile } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);

type CompactionEnded = { data: { sessionID: string } };

export default {
  id: "harness-kit",
  async setup(ctx: {
    shell: {
      hook(
        name: "create.before",
        handler: (event: { env: Record<string, string | undefined> }) => void,
      ): unknown;
    };
    event: {
      subscribe(options: { types: ["session.compaction.ended"] }): AsyncIterable<CompactionEnded>;
    };
    session: {
      get(input: { sessionID: string }): Promise<{ directory: string }>;
      instructions: {
        entry: {
          put(input: { sessionID: string; key: string; value: string }): Promise<unknown>;
        };
      };
    };
  }): Promise<void> {
    ctx.shell.hook("create.before", (event) => {
      event.env.AGENT_HARNESS = "opencode";
    });
    // Not awaited: setup must return while the subscription stays open.
    (async () => {
      for await (const event of ctx.event.subscribe({ types: ["session.compaction.ended"] })) {
        try {
          const sessionID = event.data.sessionID;
          const { directory } = await ctx.session.get({ sessionID });
          const { stdout } = await run(join(process.env.HOME ?? homedir(), ".local/bin/agent-env"), ["compact-reminder"], {
            cwd: directory,
            env: { ...process.env, AGENT_HARNESS: "opencode", OPENCODE_SESSION_ID: sessionID },
          });
          const value = stdout.trim();
          if (value) {
            await ctx.session.instructions.entry.put({ sessionID, key: "harness-kit-compact-reminder", value });
          }
        } catch (error) {
          // One failed event must not end the subscription.
          console.error("harness-kit: compaction reminder failed:", error);
        }
      }
    })().catch((error) => console.error("harness-kit: compaction subscription failed:", error));
  },
};
