**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell and follow its workspace-local run state rules.

# `/factory-product` — Product Harness

PRIORITY: P2

Produces product artifacts only. Pipeline: workspace-scout → requirements-analyst → story-writer → workflow-planner → **stop**. No complexity routing, no code-gen, no build, no review.

**Output artifacts:**
- `aidlc-docs/inception/requirements/<run-id>-requirements.md`
- `aidlc-docs/inception/user-stories/<run-id>-personas.md`
- `aidlc-docs/inception/user-stories/<run-id>-stories.md`
- `aidlc-docs/inception/plans/<run-id>-execution-plan.md`

---

## Step 1 — Init run dir + audit.md

```
run_id = YYYY-MM-DDTHH-MM-SSZ-<slug>   # UTC; slug = first 3-4 words, hyphenated
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id>
```

Ensure `aidlc-docs/` exists:
```bash
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id>
```
`aidlc-docs/audit.md` is auto-created by `stage-open` in `spawn-loop.md` step 0.

Create `manifest.yaml`:
```yaml
run_id: <run-id>
started_at: <ISO>
user_request: <verbatim>
harness: product
current_stage: workspace-scout
completed_stages: []
skipped_stages: [complexity-routing, unit-decomposer, build-test, reviewer-pool, ship]
```

## Step 2 — Resolve skill paths

Find each SKILL.md: `.agents/custom-skills/<name>/SKILL.md` → `.agents/skills/<name>/SKILL.md` → `~/.agents/skills/<name>/SKILL.md`. Store in `manifest.skill_paths`. Log `[Skill] MISSING: <name>` if absent.

Skills needed: `using-agent-skills`, `idea-refine`, `spec-driven-development`, `requirements-intelligence`.

## Step 3 — Workspace Scout (inline)

Execute `stage/workspace-scout.md` inline per [post-execution loop](spawn-loop.md).

- **skills_required**: `[using-agent-skills]`
- **predecessor_artifacts**: none
- **approval gate**: none — auto-proceeds on `status: complete`
- **state on success**: `Current Stage: PRODUCT - Workspace Detection (complete)`; manifest `current_stage: requirements-analyst`

## Step 3.5 — Classify `project_profile`

Set `project_profile.ui/api/has_legacy` via `factory_run.py set --field` based on workspace-scout output + user_request.

Skip reverse-engineer routing — product harness does not run RE. Log `[Skipped] reverse-engineer: product harness`.

## Step 4 — Requirements Analyst (two-pass, inline) + approval

Execute `stage/requirements-analyst.md` inline per [post-execution loop](spawn-loop.md).

**Two-pass**: Pass 1 emits questions → **SURFACE the questions file path** (from `questions_artifact_path`) to the user → user responds → Pass 2.

After Pass 2, surface the requirements artifact path (e.g. `aidlc-docs/inception/requirements/<run-id>-requirements.md`) and **explicitly ask the user for approval**. Do NOT proceed without an explicit approval signal.

**Approval gate (structured contract) — requirements:**
1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.requirements.input.yaml`:
   ```yaml
   stage: requirements-analyst
   run_id: <run-id>
   title: "Requirements Analysis — Approval"
   units:
     - label: "Requirements Document"
       tasks:
         - id: "REQ"
           description: "Complete requirements analysis"
           status: complete
   artifacts:
     - path: "aidlc-docs/inception/requirements/<run-id>-requirements.md"
       kind: doc
       description: "Requirements specification"
   resolution:
     options: [approve, request_changes, cancel]
     note_prompt: "Describe what changes are needed"
   next_command:
     command: "/factory-product <run-id>"
     description: "Continue to story writing"
   context: "<requirements summary + key decisions>"
   ```
2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.
3. **Surface** using the Structured Approval Format.

- **Approve / LGTM / Continue** → proceed to Step 5.
- **Request changes** → re-run requirements-analyst Pass 2 with revision context.
- **Cancel** → mark run as cancelled, stop.

- **skills_required**: `[using-agent-skills, idea-refine, spec-driven-development, requirements-intelligence]`
- **predecessor_artifacts**: workspace-scout output; copy `workspace_state` block
- **depth_override**: none — analyst determines depth normally
- **state on Pass 2 success**:
  1. `Current Stage: PRODUCT - Requirements Analysis (complete)`
  2. `Stage Progress`: mark `[x] Requirements Analysis — <ISO date>`

## Step 5 — Story Writer (always, two-pass, inline) + approval

**Always run** — not gated on scope or complexity (product harness always needs personas + stories).

Execute `stage/story-writer.md` inline per [post-execution loop](spawn-loop.md).

**Two-pass**: Pass 1 emits questions → **SURFACE the questions file path** (from `questions_artifact_path`) to the user → user responds → Pass 2.

After Pass 2, surface the personas and stories artifact paths and **explicitly ask the user for approval**. Do NOT proceed without an explicit approval signal.

**Approval gate (structured contract) — stories:**
1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.stories.input.yaml`:
   ```yaml
   stage: story-writer
   run_id: <run-id>
   title: "Story Writing — Approval"
   units:
     - label: "Personas & Stories"
       tasks:
         - id: "STORY"
           description: "User personas and stories"
           status: complete
   artifacts:
     - path: "aidlc-docs/inception/user-stories/<run-id>-personas.md"
       kind: doc
       description: "User personas"
     - path: "aidlc-docs/inception/user-stories/<run-id>-stories.md"
       kind: doc
       description: "User stories"
   resolution:
     options: [approve, request_changes, cancel]
     note_prompt: "Describe what changes are needed"
   next_command:
     command: "/factory-product <run-id>"
     description: "Continue to workflow planning"
   context: "<personas count> personas, <stories count> stories"
   ```
2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.
3. **Surface** using the Structured Approval Format.

- **Approve / LGTM / Continue** → proceed to Step 6.
- **Request changes** → re-run story-writer Pass 2 with revision context.
- **Cancel** → mark run as cancelled, stop.

- **skills_required**: `[using-agent-skills, spec-driven-development]`
- **predecessor_artifacts**: requirements-analyst Pass 2 output
- **state on Pass 2 success**: `Current Stage: PRODUCT - Story Writing (complete)`; manifest `current_stage: workflow-planner`

## Step 6 — Workflow Planner (inline, opus, minimal depth)

Execute `stage/workflow-planner.md` inline per [post-execution loop](spawn-loop.md).

- **model**: opus
- **skills_required**: `[using-agent-skills, planning-and-task-breakdown]`
- **predecessor_artifacts**: requirements + stories (both Pass 2 outputs)
- **depth_override**: `minimal` — product harness; plan is for discovery, not construction
- **units**: planner may emit units but unit-decomposer does NOT run
- **approval gate (structured contract)**: surface the plan file using the approval handoff:
  1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.product.input.yaml`:
     ```yaml
     stage: workflow-planner
     run_id: <run-id>
     title: "Product Discovery — Execution Plan Approval"
     units:
       - label: "Execution Plan"
         tasks:
           - id: "PLAN"
             description: "Product discovery execution plan"
             status: complete
     artifacts:
       - path: "aidlc-docs/inception/plans/<run-id>-execution-plan.md"
         kind: plan
         description: "Execution plan for product discovery"
     resolution:
       options: [approve, request_changes, cancel]
       note_prompt: "Describe what changes are needed"
     next_command:
       command: "(none — product harness complete)"
       description: "Product discovery complete. Start new run with /factory-spec for construction."
     context: "<plan summary + key decisions>"
     ```
  2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.
  3. **Surface** using the Structured Approval Format. **Explicitly ask the user for approval**. Do NOT proceed without an explicit approval signal. Log answer to audit. Re-run planner if user requests changes.
- **state on approval**: `Current Stage: PRODUCT - Execution Plan (complete)`; manifest `current_stage: complete`

## Step 7 — Auto-commit + completion

**On EXPLICIT user approval only:**
```bash
git add -A && git commit -m "docs(product-harness): complete product discovery for <run-id>"
```

**If the user did not approve, do NOT run this step. Do NOT commit.**

2. **Record** `approval.output.yaml` with decision, timestamp, and commit_sha. Validate against `.aidlc-orchestrator/contracts/approval.output.v1.json`.

Surface to user (MUST substitute actual run_id for every `<run-id>` below — do NOT output the literal text `<run-id>`):
```
run_id:           <run-id>
harness:          product

Artifacts:
  requirements:   aidlc-docs/inception/requirements/<run-id>-requirements.md
  personas:       aidlc-docs/inception/user-stories/<run-id>-personas.md
  stories:        aidlc-docs/inception/user-stories/<run-id>-stories.md
  execution-plan: aidlc-docs/inception/plans/<run-id>-execution-plan.md

Skill compliance: <table>
```

**Do NOT offer `/factory-build`** — product harness terminates here. If user wants to proceed to construction, they start a new run with `/factory-spec`.

---

## Hard rules

- Validate every input AND output. No exceptions.
- Sequential only — no parallel Task() calls.
- audit.md is append-only, orchestrator-owned.
- story-writer ALWAYS runs in product harness — no scope/complexity gate.
- workflow-planner depth is always `minimal` in product harness.
- No complexity routing — `factory_complexity.py` is NOT called.
- No unit-decomposer, no build, no review, no ship.
- Approval gates pause; never auto-approve.
