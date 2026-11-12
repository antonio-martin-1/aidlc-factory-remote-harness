**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# /factory-context — Context Snapshot

PRIORITY: P2

## Goal

Build a contextual snapshot from the run's traceability files and present it to the user. This helps humans (and agents) quickly understand:
- What stage the project is in
- What decisions have been made recently
- What items are still open
- What skills are active

## Procedure

1. Parse the run-id from the arguments. If a second argument is present, treat it as `--depth`.

2. Generate the context snapshot:
   ```bash
   <aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth <depth> --format compact
   ```
   - Depth `auto` (default): Automatically selects based on completed stage count.
     - 0-2 stages → `minimal` (~200 tokens)
     - 3-5 stages → `standard` (~800 tokens)
     - 6+ stages → `comprehensive` (~2000 tokens)
   - Depth `minimal`: Current stage + last 3 audit entries.
   - Depth `standard`: Full state + last 10 audit entries + stage timing.
   - Depth `comprehensive`: Everything + handoff summaries.
   - Format `compact`: Dense YAML-like format (saves ~40% tokens vs Markdown).

3. If the script fails (e.g., run not found), surface the error and suggest `<aidlc-python> aidlc-scripts/factory_run.py list` to see available runs.

4. Present the output in a clean format:
   - Show the current stage and phase prominently
   - List recent decisions with timestamps
   - Highlight any open items or pending approvals
   - Mention the next recommended command
   - Show token count and cache status (if cached)

5. (Optional) Append an orchestrator note to the audit trail:
   Write `.aidlc-orchestrator/runs/<run-id>/tmp/orchestrator-orchestrator_note-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

   - `[Orchestrator] Context generated for run <run-id>`

   ```text
   <aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt orchestrator_note --phase <current-phase> --label "Context Snapshot Viewed" --field summary="User viewed context snapshot at depth <depth>" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/orchestrator-orchestrator_note-bullets.txt
   ```
