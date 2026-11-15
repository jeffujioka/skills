# logbook on omp

- omp compacts on its own when the context passes its compaction threshold (`compaction.thresholdTokens` in the omp configuration), and on the user's `/compact`. The logbook never triggers it.
- After a compaction harness-kit's omp hook adds the reminder `agent-env compact-reminder` prints, a line starting `Context was compacted. Read`, to the session right after the compaction summary, only when the logbook folder holds `progress.md`.
