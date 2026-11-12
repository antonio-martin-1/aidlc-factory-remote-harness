**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# In-stage progress trace

PRIORITY: P2

A subagent that stops before `stage-close` leaves no output handoff. The next
spawn would reload skills, context, and prior work. The progress YAML is the
cursor that prevents that. It is run state under `.aidlc-orchestrator/runs/`
and stays gitignored with the rest of the run.

One live file per stage, or per unit when the handoff has `unit_name`:

```text
.aidlc-orchestrator/runs/<run-id>/progress/<stage>.yaml
.aidlc-orchestrator/runs/<run-id>/progress/<stage>.<unit>.yaml
```

The cursor sits at the top. `log` keeps only the last 5 beats. Each beat
carries `at`, stamped by the script. `attempt_started_at` and `attempts[]`
record every spawn. `task_seconds` keeps the closed intervals so the log cap
does not drop task time.

## Orchestrator

On every spawn, full and inline, `spawn-loop.md` step 0 runs `begin` once and
merges the JSON into the input handoff as `continuation`. Validate the handoff
after that merge.

When `continuation.mode` is `resume`, shrink the context snapshot to depth
`minimal` and replace `context_snapshot.markdown` with:

```text
Resume in progress; follow continuation.resume_from.
```

`--fresh` is only for an explicit discard. Replay archives every live cursor
for each rolled-back stage before spawning again:

```text
<aidlc-python> aidlc-scripts/factory_progress.py archive --run-id <run-id> --stage <stage>
```

`/factory-resume` lists cursors and offers **Resume at cursor** beside the
existing fresh and trust options. See `cmd-factory-resume.md`.

## Stage agent

Read `continuation` before any other work.

`mode: resume`:

- Read `continuation.progress_path`.
- Start at `resume_from.next_action`. If that action is empty, no beat was saved: start the stage normally.
- Treat `resume_from.completed_task_ids` as done.
- Record each `resume_from.skills_satisfied` entry as already applied, using its `evidence`. Do not open those `SKILL.md` files again.
- Leave `do_not_redo` untouched.
- Read only the files the open task still needs.

`mode: fresh`:

- Run the stage's normal start.
- After the skill batch, upsert `phase: skills_loaded` and list each applied skill with `--skill name=evidence`.

After every completed step — skill batch, plan, checkbox, QA row, or the moment before a long generation — rewrite the YAML in the same turn:

```text
<aidlc-python> aidlc-scripts/factory_progress.py upsert --run-id <run-id> --stage <stage-id> [--unit <unit>] --phase <phase> --next-action "<exact next action>" [--task-id <id>] [--mark-done] [--skill name=evidence] [--artifact <path>] [--decision "<one line>"] [--skip "<what the next spawn must leave alone>"]
```

`--phase task_done` adds `--task-id` to `done`. Use `--mark-done` to record a finished task with any other phase.

If token pressure is about to stop the stage, upsert before returning:

```text
<aidlc-python> aidlc-scripts/factory_progress.py upsert --run-id <run-id> --stage <stage-id> [--unit <unit>] --phase suspending --status suspending --next-action "<exact next action>"
```

Phases: `skills_loaded`, `plan_written`, `task_started`, `task_done`, `suspending`, `beat`.

Write `--status complete` only after the output handoff for this stage is on disk. The progress file does not close the stage. `stage-close` still owns the manifest — and when called with `--unit`, it also marks the live progress cursor terminal (`complete`/`failed`/`blocked`) and updates `manifest.units[].status`. Construction must `begin --unit` **before** spawn so `started_at` is trustworthy.

## Timings

Durations are derived from the stamps. Do not pass a duration to `upsert`.

A task's time is the gap from its beat's `at` to the next beat. The open task
of the current attempt runs until now. Time from `attempt_started_at` to the
first beat is overhead. When the next spawn calls `begin`, the previous
attempt closes at its last beat, so the gap while tokens were recharged stays
out of the sum.

```text
<aidlc-python> aidlc-scripts/factory_progress.py timings --run-id <run-id>
```

The report rolls up task, attempt, stage, and phase (INCEPTION, CONSTRUCTION,
OPERATIONS). `wall` is the first start to the latest end. `sum` adds the
attempts, so overlapping units stay visible. Approval wait stays in
`factory_run.py status --latency`.

Host token counts land on the attempt when `stage-close` receives `--tokens`,
`--tokens-in`, or `--tokens-out`. Pass `--unit` when the cursor is per unit.
`timings` sums those counts on the attempt, the unit, the stage, and the phase.
A task line stays time-only. An attempt with no recorded count stays blank,
including one that is still open. Do not pass a token count to `upsert`. When
only input and output are present, the stored total is their sum.
