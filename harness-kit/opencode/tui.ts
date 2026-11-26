// harness-kit @VERSION@

import { execFile } from 'node:child_process';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';

const run = promisify(execFile);

export function reminderNotice(reminder: string): string {
  const logbook = /`([^`]+)\/progress\.md`/.exec(reminder)?.[1];
  return logbook
    ? `harness-kit: logbook reminder sent to the model (${logbook})`
    : 'harness-kit: logbook reminder sent to the model';
}

type CompactionEnded = { data: { sessionID: string } };

// The server part of this plugin (index.ts) adds the reminder to the session; this TUI part shows the user
// that it did, with a toast. Both run agent-env compact-reminder, which prints nothing without a progress.md.
export default {
  id: 'harness-kit-tui',
  setup(context: {
    location?: { directory: string };
    data: {
      on(type: 'session.compaction.ended', handler: (event: CompactionEnded) => void): () => void;
      session: { get(sessionID: string): { directory: string } | undefined };
      location: { default(): { directory: string } };
    };
    ui: {
      toast: {
        show(toast: { message: string; variant?: 'info' | 'success' | 'warning' | 'error' }): void;
      };
    };
  }): () => void {
    return context.data.on('session.compaction.ended', (event) => {
      void (async () => {
        try {
          const sessionID = event.data.sessionID;
          const directory =
            context.data.session.get(sessionID)?.directory ??
            context.location?.directory ??
            context.data.location.default().directory;
          const { stdout } = await run(
            join(process.env.HOME ?? homedir(), '.local/bin/agent-env'),
            ['compact-reminder'],
            {
              cwd: directory,
              env: {
                ...process.env,
                AGENT_HARNESS: 'opencode',
                OPENCODE_SESSION_ID: sessionID,
              },
            },
          );
          const reminder = stdout.trim();
          if (reminder)
            context.ui.toast.show({
              message: reminderNotice(reminder),
              variant: 'info',
            });
        } catch (error) {
          console.error('harness-kit: compaction notice failed:', error);
        }
      })();
    });
  },
};
