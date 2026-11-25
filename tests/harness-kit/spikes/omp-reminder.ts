// Spike (spec D17): after omp compacts, does a hidden custom message carry the reminder?
const SPIKE_REMINDER =
  'Context was compacted. Read `~/.local/state/agents/logbooks/spike/r1/progress.md`, ' +
  '`decisions.md`, `needs-you.md` before anything else; continue from `## Next`.';

export default function (pi) {
  pi.on('session_compact', (event, ctx) => {
    process.stderr.write(
      `omp-reminder ${JSON.stringify({
        eventKeys: Object.keys(event),
        sessionId: ctx.sessionManager.getSessionId(),
        cwd: ctx.cwd,
        sessionFile: ctx.sessionManager.getSessionFile(),
      })}\n`,
    );
    // "nextTurn" waits for a turn that `omp -p` never starts, so the message is lost;
    // "steer" lands in the running turn, or is appended at once when idle.
    pi.sendMessage(
      {
        customType: 'harness-kit-reminder',
        content: SPIKE_REMINDER,
        display: false,
      },
      { deliverAs: 'steer' },
    );
  });
}
