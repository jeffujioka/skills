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
