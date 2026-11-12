**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-resume` — Resume Interrupted Run

PRIORITY: P3

Picks up an interrupted run from its last checkpoint.

1. Read run state:
   ```bash
   <aidlc-python> aidlc-scripts/factory_run.py resume <run-id>
   ```
   This emits a JSON report with `completed_stages`, `current_stage`,
   `next_stage_suggestion`, `partial_outputs[]`, `reconcile`, and
   `version_warning` (if scripts version differs from manifest version).
   It also appends a `resume_requested` event to `timeline.jsonl`.

2. List in-stage cursors:
   ```text
   <aidlc-python> aidlc-scripts/factory_progress.py list --run-id <run-id>
   ```
3. If a cursor for `next_stage_suggestion` has status `in_progress` or
   `suspending`, surface it before spawning:
   - **Resume at cursor** — spawn that stage without `--fresh`. The agent
     reads the progress YAML and continues at `cursor.next_action`.
   - **Re-spawn fresh** — archive that stage's cursors, then spawn from scratch:
     ```text
     <aidlc-python> aidlc-scripts/factory_progress.py archive --run-id <run-id> --stage <stage>
     ```
   - **Trust and complete** — only when `partial_outputs[]` is non-empty.
     Accept those outputs as-is and proceed to `next_stage_suggestion`.
4. If no such cursor exists and `partial_outputs[]` is non-empty, surface the
   two original options:
   - **Trust and complete** — accept partial outputs as-is; proceeds to
     `next_stage_suggestion`.
   - **Re-spawn fresh** — discard partial outputs for the interrupted stage
     (re-queues it; re-spawns from scratch).
5. If no cursor exists and `partial_outputs[]` is empty, proceed directly to
   `next_stage_suggestion`.
6. Log `[RunManager] Resumed run <run-id> from stage <s>` to audit.

Hard rules from the orchestrator apply.
