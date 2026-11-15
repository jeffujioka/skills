// Spike (spec D17): does opencode's session.compaction.ended event let a plugin
// put the reminder into the session's instructions?
import { appendFileSync } from "node:fs";
import { join } from "node:path";

const SPIKE_REMINDER =
	"Context was compacted. Read `~/.local/state/agents/logbooks/spike/r1/progress.md`, " +
	"`decisions.md`, `needs-you.md` before anything else; continue from `## Next`.";

export default {
	id: "harness-kit-spike",
	setup(ctx) {
		const log = join(process.cwd(), "spike-events.jsonl");
		const record = (entry) => appendFileSync(log, `${JSON.stringify(entry)}\n`);
		(async () => {
			for await (const event of ctx.event.subscribe({ types: ["session.compaction.ended"] })) {
				const sessionID = event.data.sessionID;
				const session = await ctx.session.get({ sessionID });
				record({ event, session });
				await ctx.session.instructions.entry.put({
					sessionID,
					key: "harness-kit-compact-reminder",
					value: SPIKE_REMINDER,
				});
				record({ put: sessionID });
			}
		})().catch((error) => record({ error: String(error?.stack ?? error) }));
	},
};
