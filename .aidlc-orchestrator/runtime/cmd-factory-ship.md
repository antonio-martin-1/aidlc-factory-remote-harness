**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-ship` — Phase 1 ship

PRIORITY: P2

Final stage. Execute `stage/ship-agent.md` inline per the
[post-execution loop](spawn-loop.md).

**1. Validate stage prerequisites (MANDATORY):**
   ```bash
   <aidlc-python> aidlc-scripts/stage_gate.py check <run-id> ship-agent
   ```
   Exit 0 → continue. Exit 1 → **HALT**. Do NOT proceed.

   Also read `manifest.yaml`. Refuse if review hasn't completed with user approval.

1.5. **State update + audit (MANDATORY — do NOT skip):**

```bash
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id> --extra aidlc-docs/operations/adrs
```

Update `aidlc-docs/aidlc-state.md`:
- `Current Stage: SHIP (in progress)`
- Add: `- [ ] Ship — started <ISO date>`

Emit audit block:
Write `.aidlc-orchestrator/runs/<run-id>/tmp/ship-agent-start-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[Orchestrator] Ship phase started`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt orchestrator_note --stage ship-agent --phase OPERATIONS --label "SHIP AGENT PHASE START" --field summary="ship-agent start" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/ship-agent-start-bullets.txt
```

2. **ship-agent** — spawn with `predecessor_artifacts` = all prior outputs +
   the merged review report. Pass `manifest.project_profile` so the agent
   knows whether to load `deprecation-and-migration*` (when `has_legacy: true`).

3. Validate output. Expected fields include `version_proposal` and `adr_count`.

4. If `status: needs_human` (because the version bump or release plan needs
   user OK): surface, wait, log answer.

> **Framework skills** are available here if `/factory-build` ran first (stored in
> `manifest.skill_paths_resolved`). Ship agent inherits this list from the manifest.

Stage-specific knobs:
- **skills_required**: `[shipping-and-launch, git-workflow-and-versioning, ci-cd-and-automation, documentation-and-adrs]`. Add `deprecation-and-migration` if `manifest.project_profile.has_legacy == true`.
- **Design system**: if `manifest.project_profile.ui == true` AND `manifest.project_profile.design_system_path` is set, inject `design_system_path` into ship-agent input so UI example capture and INDEX.md update-index run.
- **Output artifacts**: `RELEASE_NOTES.md`, `aidlc-docs/operations/adrs/`, CI/CD files, updated `CHANGELOG.md`, (conditional) updated `design-system/INDEX.md` usage stats.

## Approval gate (structured contract)

After ship-agent completes, build the approval handoff:

1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.ship.input.yaml`:
   ```yaml
   stage: ship-agent
   run_id: <run-id>
   title: "Release — Ship Approval"
   units:
     - label: "Release Artifacts"
       tasks:
         - id: "REL"
           description: "Release notes, ADRs, CHANGELOG, CI/CD"
           status: complete
   artifacts:
     - path: "RELEASE_NOTES.md"
       kind: doc
       description: "Release notes summary"
     - path: "aidlc-docs/operations/adrs/"
       kind: adr
       description: "Architecture Decision Records"
     - path: "CHANGELOG.md"
       kind: changelog
       description: "Updated changelog"
   skill_compliance:
     - skill: "shipping-and-launch"
       status: PASS
     - skill: "git-workflow-and-versioning"
       status: PASS
   resolution:
     options: [approve, request_changes, cancel]
     note_prompt: "Describe what changes are needed"
   next_command:
     command: "(none — final stage)"
     description: "Pipeline complete. No further commands."
   context: "<version proposal + key changes summary>"
   ```

2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.

3. **Surface** the artifacts using the Structured Approval Format. **Explicitly ask the user for approval.** Do NOT proceed without an explicit approval signal.

Wait for user response:
- **Approve / LGTM / Continue** → proceed to auto-commit + present completion.
- **Request changes** → re-run ship-agent with revision context.
- **Cancel** → mark run as cancelled, stop.

## Auto-commit + present completion

**On EXPLICIT user approval only:**
```bash
git add -A && git commit -m "docs(ship): release prep complete"
```

**If the user did not approve, do NOT run this step. Do NOT commit.**

2. **Record** `approval.output.yaml` with decision, timestamp, and commit_sha. Validate against `.aidlc-orchestrator/contracts/approval.output.v1.json`.

Update `aidlc-docs/aidlc-state.md`:
- `Current Stage: OPERATIONS` (or `CONSTRUCTION - Complete` if user opts not to deploy)
- Mark: `[x] Ship — <ISO date>`

Emit audit block:
Write `.aidlc-orchestrator/runs/<run-id>/tmp/ship-agent-complete-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[Orchestrator] Ship complete — version: <version_proposal>, ADRs: <N>, CHANGELOG updated`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt orchestrator_note --stage ship-agent --phase OPERATIONS --label "SHIP AGENT PHASE COMPLETE" --field summary="ship-agent complete" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/ship-agent-complete-bullets.txt
```

Present completion + summary of all stages:
```
Run complete: <run-id>

Artifacts:
  RELEASE_NOTES.md
  ADRs: <N> created
  CHANGELOG.md updated
  CI/CD: <files>

Full pipeline complete. The full audit trail is in aidlc-docs/audit.md.
```

The run is complete. No further commands to suggest (this is the final stage).
Remind the user to manually push tags and remote branches after reviewing the commits.

**Safety rule**: This stage does NOT push tags or remote branches. The user pushes manually after reviewing the commits.

---

## Hard rules

- Hard rules from the orchestrator apply.
- **This agent does NOT push tags or remote branches.** User pushes manually.
