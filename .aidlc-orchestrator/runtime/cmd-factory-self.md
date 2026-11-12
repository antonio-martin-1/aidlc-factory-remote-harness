**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-self` — Self-Hosting Mode

PRIORITY: P2

Run the orchestrator on its **own codebase**. Treats `aidlc-scripts/`, the
agentic tool's agents directory, and `tests/` as the workspace being developed.

## Workspace scope

Limited to these directories:
- `aidlc-scripts/` — factory Python scripts
- `<tool-agents-dir>/` — stage subagent definitions (`.claude/agents/`, `.cursor/agents/`, `.github/agents/`, etc. — whichever is installed)
- `.aidlc-orchestrator/contracts/` — handoff schemas
- `.agents/skills/` — factory command skills
- `tests/` — test suite

## Self-hosting rules

1. **Design units** map to individual scripts or agent files. For example:
   - "Add --stale flag to factory_conflict.py" → 1 design unit
   - "Add version-locking to factory_validate.py and factory_run.py" → 2 design units

2. **Validation** uses the existing test suite:
   ```bash
   <aidlc-python> -m pytest tests/ --tb=short
   ```

3. **Review** focuses on test coverage and backward compatibility.

4. **The commit** includes the update to `docs/TROUBLESHOOTING.md` if the change
   introduces a new failure mode.

5. **No ship stage** — self-hosting runs skip ship-agent. The changelog entry
   is written directly.

Proceed with the standard `/factory-spec` flow (triage → stages → review → commit)
applying the scope constraints above.
