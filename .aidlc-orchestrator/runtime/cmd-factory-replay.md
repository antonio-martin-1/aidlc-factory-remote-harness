**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-replay` — Re-run From Stage

PRIORITY: P2

You are the AIDLC orchestrator replaying a run from a specific stage.

Parse `<run-id>` and the `--from <stage>` value from the arguments. If
malformed, refuse with a usage hint and stop.

1. Roll the manifest back and archive handoffs:
   ```bash
   <aidlc-python> aidlc-scripts/factory_run.py replay <run-id> --from <stage>
   ```
   This:
   - Truncates `manifest.completed_stages[]` before `<stage>`
   - Sets `manifest.current_stage = <stage>`
   - Renames each rolled-back stage's `*.output.yaml` to
     `*.replay-<unix-ts>.yaml` (so prior runs are kept for diff/inspection)
   - Emits a `replay_requested` event to `timeline.jsonl`

2. Surface the result to the user — list of `rolled_back` stages and
   `archived_outputs` paths.

3. Archive the in-stage cursor for every rolled-back stage so the replay
   does not resume the discarded attempt:
   ```text
   <aidlc-python> aidlc-scripts/factory_progress.py archive --run-id <run-id> --stage <stage>
   ```
4. Spawn the chosen stage per the orchestrator protocol (validate input,
   apply pre-flight gates from Cost Governor + Conflict Resolver, etc.).
   Step 0 of the spawn loop starts a fresh progress YAML.

**Use cases:**
- A reviewer found a P0 issue that requires re-doing code generation
  for a unit → replay from `code-generator`.
- The user wants to adjust requirements after seeing the plan → replay
  from `requirements-analyst`.
- A schema bump (input or output contract) requires re-running a stage
  with the new format.

**Replay is destructive to the manifest's progress record but non-destructive
to artifacts.** Old outputs are archived, never deleted.

Hard rules from the orchestrator apply.
