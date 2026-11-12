**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-plan` — Context Pass (Phase 1)

PRIORITY: P2

Inception phase, post-requirements. Produces the execution plan and (optional) decomposes into units. Depending on whether extended inception passes were run, this command operates in **extended** or **legacy** mode.

**1. Validate stage prerequisites (MANDATORY):**

   Read `manifest.yaml`. Refuse if missing or run not past `requirements-analyst`.
   If `<run-id>` manifest is missing → refuse: "run not found — start with `/factory-spec` first".

   **Determine plan mode** from `manifest.completed_stages[]`:

   ```
   IF completed_stages contains ANY of [product-pass, arch-pass, design-pass]:
     → EXTENDED MODE (Context Pass only — story-writer + application-designer already done)
   ELSE:
     → LEGACY MODE (inline story-writer + application-designer + workflow-planner)
   ```

   **Extended mode — inception completeness gate**: all three passes MUST be complete:
   ```bash
   <aidlc-python> aidlc-scripts/stage_gate.py check <run-id> product-pass
   <aidlc-python> aidlc-scripts/stage_gate.py check <run-id> design-pass
   <aidlc-python> aidlc-scripts/stage_gate.py check <run-id> arch-pass
   ```

   If ANY pass missing → **HALT**:
   ```
   ⛔ Inception passes incomplete. Construction-ready planning requires all three:
      product-pass:  <complete ✓ | pending ✗>
      design-pass:   <complete ✓ | pending ✗>
      arch-pass:     <complete ✓ | pending ✗>

   Complete missing passes first (in order):
      /factory-product-pass <run-id>
      /factory-design-pass  <run-id>
      /factory-arch-pass    <run-id>
   ```

   If all three complete → log `[Plan] Extended mode — story-writer and application-designer already complete via inception passes. Running Context Pass only.` and skip Steps 2 and 3 (go directly to Step 4 — Workflow Planner).

   **Legacy mode** — no passes detected: log `[Plan] Legacy mode — running full inline inception: story-writer + application-designer + workflow-planner.` and continue to Step 2.

   ```bash
   <aidlc-python> aidlc-scripts/stage_gate.py check <run-id> workflow-planner
   ```
   Exit 0 → continue. Exit 1 → **HALT**. Do NOT proceed.

2. **Story Writer (legacy mode only)** — SKIP entirely in extended mode (already done in `/factory-product-pass`).

   In legacy mode, skip when ANY of:
   - `manifest.skip_stages[]` contains `story-writer` (set by ComplexityGov)
   - `requirements-analyst` output's `request_classification.scope` ∉ `{Multiple Components, System-wide, Cross-system}`
   - The user request does not involve user-facing flows

   When skipping, follow complexity-gate skip enforcement. Otherwise execute `stage/story-writer.md` inline per the [post-execution loop](spawn-loop.md).
   Predecessor: requirements-analyst output.

   **Context Injection**: Before spawning, generate the context snapshot:
   ```bash
   <aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth auto --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
   ```
   **Depth**: `auto` — with 2 completed stages, resolves to `standard` (~800 tokens). Inject under `context_snapshot:`.

   > **Cookbook**: The story-writer loads `ai-architecture-cookbook` (`search_standards`) to align stories with architecture standards. Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present.

3. **Application Designer (legacy mode only)** — SKIP entirely in extended mode (already done in `/factory-design-pass`).

   In legacy mode, skip ONLY when ALL of:
   - `manifest.skip_stages[]` contains `application-designer`
   - The request scope is single-component AND involves no new interfaces/components
   - `manifest.project_profile.design_system_path` is empty or absent (no design system)

   **NEVER skip when a design system exists** (`design_system_path` is set). The designer bridges UI primitives → application architecture.

   When skipping, log `[Skip] application-designer` to audit with reason.

   Otherwise execute `stage/application-designer.md` inline per the [post-execution loop](spawn-loop.md).

   > **Two-pass**: Pass 1 → questions → `needs_human` → wait → Pass 2 → 5 design artifacts.

   **Context Injection**:
   ```bash
   <aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth auto --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
   ```
   **Depth**: `auto` — resolves to `standard` or `comprehensive`. Inject under `context_snapshot:`.

   Predecessors: requirements + (if present) stories + (if brownfield) reverse engineering.

4. **Workflow Planner (always — Context Pass)** — `model: opus`. Required. Execute `stage/workflow-planner.md` inline per the [post-execution loop](spawn-loop.md).

   > **Output location (enforce):** the execution plan MUST be written to `aidlc-docs/inception/plans/<run-id>-execution-plan.md`. The `plans/` folder is the construction entry point. Do NOT let the stage create a folder named after the phase (e.g. `aidlc-docs/inception/workflow-planning/`). After the stage returns, verify the file exists at `aidlc-docs/inception/plans/` — if it landed elsewhere, move it there before the approval gate.

   **Extended mode predecessors** (richer context from inception passes):
   - `aidlc-docs/inception/requirements/<run-id>-requirements.md`
   - `aidlc-docs/inception/product-pass/<run-id>-product-vision.md`
   - `aidlc-docs/inception/user-stories/<run-id>-stories.md`
   - `aidlc-docs/inception/user-stories/<run-id>-personas.md`
   - `aidlc-docs/inception/design-pass/<run-id>-ux-flows.md`
   - `aidlc-docs/inception/design-pass/<run-id>-application-design.md`
   - `aidlc-docs/inception/arch-pass/<run-id>-tech-stack.md`
   - `aidlc-docs/inception/arch-pass/<run-id>-adrs.md`
   - `aidlc-docs/inception/arch-pass/<run-id>-architecture-decisions.md`
   - `aidlc-docs/inception/arch-pass/<run-id>-component-map.md`
   - `aidlc-docs/inception/arch-pass/<run-id>-service-interfaces.md`

   **Legacy mode predecessors**:
   - requirements + (if produced) stories + (if produced) application-design artifacts

   The planner emits `status: needs_human` after producing the plan; on user response, call `emit_audit_block` per [`audit-block.protocol.md` § workflow-planner gate](../contracts/audit-block.protocol.md).

   **Context Injection**:
   ```bash
   <aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth auto --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
   ```
   **Depth**: `auto` — typically resolves to `standard` or `comprehensive`. Inject under `context_snapshot:`.

   > **Cookbook**: The workflow-planner loads `ai-architecture-cookbook` (`recommend_workflow(mode: 'audit')`). Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present and inject `techStack`, `scale`, `compliance`, `previous_decisions` into the call.

4.5. **Pre-mortem visibility check (defensive guard)** — run after Workflow Planner output is received:
   - Locate the `skill_compliance[]` row for `requirements-intelligence` in `workflow-planner.output.yaml`.
     If MISSING → append `[PlanPreMortem] missing — workflow-planner contract violation: no requirements-intelligence row in skill_compliance` to `audit_entries[]` and continue (do NOT halt).
   - Locate any `audit_entries[]` bullet starting with `[PlanPreMortem]`.
     If the `skill_compliance[]` row is present but no `[PlanPreMortem]` bullet exists → append `[PlanPreMortem] orphan compliance row — workflow-planner emitted skill_compliance without matching audit_entry` to `audit_entries[]` and continue.
   - These guards exist because the workflow-planner contract requires DUAL emission (compliance row + matching audit bullet); the orchestrator must log any violation so it appears in `audit.md` instead of being silently swallowed.

5. **Unit Decomposer (conditional)** — skip ONLY when ANY of these TWO conditions holds (no others):
   - `manifest.skip_stages[]` contains `unit-decomposer` (set by ComplexityGov)
   - The approved plan enumerates < 2 units AND requirements do not call out distinct services/components

   **MUST-RUN rule (do NOT rationalize a skip):** if the approved plan enumerates **≥ 2 units** OR the requirements call out **distinct services/components**, you MUST execute the unit-decomposer. These are the ONLY two skip conditions — do NOT invent others. In particular, **the presence of inline tasks in the execution plan is NOT a reason to skip**: the plan's inline task tree does NOT substitute for the per-unit specs the unit-decomposer writes to `aidlc-docs/inception/units/`. Skipping a multi-unit decomposition leaves Construction without per-unit specs and breaks layer-parallel build.

   When skipping due to ComplexityGov, follow complexity-gate skip enforcement. When skipping due to <2 units, log `[Plan] unit-decomposer skipped — single-unit plan (no distinct services)` to `audit_entries[]`.

   **Honest skip reporting (mandatory):** whenever the unit-decomposer is skipped (either condition), the approval handoff's `Unit Decomposition` → `DECOMP` task MUST carry `status: skipped` — NOT `complete`. Marking a skipped stage as `complete` is a contract violation. Pair it with the matching `[Plan] unit-decomposer skipped — <reason>` audit entry so the skip is traceable in `audit.md`.
   Otherwise execute `stage/unit-decomposer.md` inline per the [post-execution loop](spawn-loop.md). Ensure the output directory exists first: `<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id> --extra aidlc-docs/inception/units aidlc-docs/inception/plans`.

   **Context Injection**:
   ```bash
   <aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth auto --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
   ```
   **Depth**: `auto` — resolves to `standard` or `comprehensive`. Inject under `context_snapshot:`.

   > **Cookbook**: The unit-decomposer loads `ai-architecture-cookbook` (`get_decision_tree`) to ensure decomposed units carry architecture-standard context. Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present.

6. **Approval gate (structured contract)** — before presenting, build the approval handoff:

   1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.input.yaml`:
      ```yaml
      stage: workflow-planner
      run_id: <run-id>
      title: "Execution Plan — Approval Gate"
      plan_mode: "<extended|legacy>"
      units:
        - label: "Execution Plan"
          tasks:
            - id: "PLAN"
              description: "Complete workflow plan with task breakdown and acceptance criteria"
              status: complete
        - label: "Unit Decomposition"
          tasks:
            - id: "DECOMP"
              description: "Per-unit specs with dependency matrix"
              status: <complete if unit-decomposer ran | skipped if it was skipped>
      artifacts:
        - path: "aidlc-docs/inception/plans/<run-id>-execution-plan.md"
          kind: plan
          description: "Execution plan with task breakdown"
      skill_compliance:
        - skill: "requirements-intelligence"
          status: "<PASS|N/A|MISSING>"
          evidence: "Pre-mortem: <result>"
        - skill: "planning-and-task-breakdown"
          status: PASS
      resolution:
        options: [approve, request_changes, cancel]
        note_prompt: "Describe what changes are needed"
      next_command:
        command: "/factory-build <run-id>"
        description: "Generate code and run tests"
      context: "<plan_mode> | <pre-mortem line + skill compliance summary>"
      ```
      Include optional artifacts (stories, personas, design artifacts) if they were produced.

   2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.

   3. **Present** using the Structured Approval Format. Never omit the `Pre-mortem:` line.

   **Explicitly ask the user for approval.** Do NOT proceed without an explicit approval signal.

   Wait for user response:
   - **Approve / LGTM / Continue** → proceed to Step 7 (auto-commit + suggest next command).
   - **Request changes** → re-run the relevant stage (workflow-planner or unit-decomposer) with revision context. Do NOT auto-commit until user approves.
   - **Cancel** → mark run as cancelled, stop.

7. **Auto-commit + present next**

   **On EXPLICIT user approval only:**
   ```bash
   git add -A && git commit -m "docs(workflow-planning): complete context pass for <run-id>"
   ```
   Update state.

   **Record** `approval.output.yaml` with decision, timestamp, and commit_sha. Validate against `.aidlc-orchestrator/contracts/approval.output.v1.json`.

   **If the user did not approve, do NOT run this step. Do NOT commit.**

   Present completion with the **literal next command** (substitute the actual run_id, never output `<run-id>` as placeholder text):
   ```
   Context Pass complete: <run-id>  [mode: <extended|legacy>]

   Next command: /factory-build <run-id>
   ```
   Do NOT auto-execute `/factory-build`.

> **Framework skills** are synced at `/factory-build` Pre-Build Step 0, not here.
> Plan stages use `.agents/custom-skills/` process skills only.

---

## Hard rules

- **Extended mode**: story-writer and application-designer MUST NOT run — their work is already in inception pass artifacts.
- **Legacy mode**: story-writer and application-designer run as before — complexity governor skip rules apply.
- workflow-planner always runs regardless of mode.
- Hard rules from the orchestrator apply.
