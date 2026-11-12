**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-state` — Run Status

PRIORITY: P2

You are the AIDLC orchestrator. The user wants to know the state of a given run.

1. Read the manifest:
   ```bash
   <aidlc-python> aidlc-scripts/factory_run.py status <run-id> --json
   ```

2. Show the visual timeline:
   ```bash
   <aidlc-python> aidlc-scripts/factory_run.py graph <run-id>
   ```

3. Compute next steps:
   ```bash
   <aidlc-python> aidlc-scripts/factory_run.py resume <run-id>
   ```

4. Check for stale locks:
   ```bash
   <aidlc-python> aidlc-scripts/factory_conflict.py list <run-id>
   <aidlc-python> aidlc-scripts/factory_conflict.py conflicts <run-id>
   ```

5. Summarize in plain language:
   - How many stages complete / total
   - What's the current stage and how it's doing
   - What stage runs next
   - Any conflicts, drift, or warnings
   - Suggested next `/factory-*` command to run
