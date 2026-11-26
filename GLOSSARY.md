# Skills

Personal agent skills, shared across coding harnesses.

## Language

**Harness**:
A coding-agent program that runs a session, such as opencode, claude, or omp.
_Avoid_: Agent kind, tool, CLI

**Current harness**:
The harness running the current session.

**Target harness**:
The harness started in the new Herdr location. Defaults to the current harness.

**Handoff document**:
A file summarising a session so a fresh session can continue the work.
_Avoid_: Summary, context dump

**Target remote**:
The remote a push or review request goes to. Its host decides which skill applies.
_Avoid_: Origin (when another remote is meant), upstream

### Harness kit

**Root session**:
The top-level session a subagent descends from. A top-level session is its own root.
_Avoid_: Parent session (when the top level is meant), main session

**Consumer skill**:
A skill that reads the harness and session through harness-kit's `agent-env`: logbook, captain-away and hc-handoff.

**Logbook folder**:
The folder holding one root session's `progress.md`, `decisions.md` and `needs-you.md`, keyed by the project folder and the root session.

**Skills script**:
A shell command whose text contains `agent-env` or a path segment `/skills/<name>/scripts/`. On omp only these get `AGENT_HARNESS`.

**Pinned agent**:
A subagent started for one task on the model and effort the user named.
_Avoid_: Model agent, tagged agent, preset agent, hired agent

### Skill engineering

**Standard**:
One of the three files a skill is checked against: rules, model notes or guardrails.
_Avoid_: Guideline, spec, policy

**Finding**:
One problem in a skill: its location, the standard it breaks, and the fix.
_Avoid_: Miss, issue, violation

**Severity**:
The tier of a finding, set by its source. Must fix: a broken FAIL-level rule, or a triggered guardrail that is absent. Should fix: a broken WARN-level rule, or a manual rule or model note the skill breaks.
_Avoid_: Priority, level

**Suggestion**:
An improvement with no standard to cite, or an extra file, script or section worth adding that a run did not build. Never the fix for a finding.
_Avoid_: Next step, recommendation

**Scenario**:
One request in a skill's evals, with the behaviors a run must show.
_Avoid_: Eval, test case

**Run**:
One execution of a scenario by a fresh agent in its own scratch directory.
_Avoid_: Trial, attempt

**Required behavior**:
A behavior that must pass on every run of its scenario, because one slip harms people or data.
_Avoid_: Hard check, must-pass

**Expected behavior**:
A behavior that counts toward a scenario's pass threshold.
_Avoid_: Assertion, check

**Judge**:
The model that grades a run's transcript against its scenario's behaviors.
_Avoid_: Grader, evaluator

### README crafting

**Direction**:
One complete creative proposal for a README: name, tagline, pitch, tone, palette, fonts, hero idea, page outline and sketch.
_Avoid_: Option, concept, theme

**Board**:
The local browser page that shows the directions side by side and records the user's pick in `choice.json`.
_Avoid_: Gallery, picker, dashboard
