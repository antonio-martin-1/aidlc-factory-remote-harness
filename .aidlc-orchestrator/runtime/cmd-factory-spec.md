**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-spec` — Phase 0 sequence

PRIORITY: P2

For `/factory-spec <description>`. Pass `--tier=small` to force SMALL tier and skip routing.

## Step 1 — Init run dir + budget + audit.md

Generate run-id via the cross-platform Python helper (no shell `date`command):

```bash
   <aidlc-python> aidlc-scripts/factory_run.py generate-run-id --slug "<slug>"
```

Capture stdout as the active `run_id` in orchestration context. A shell variable
only lasts for that shell call: in later calls, pass the captured ID explicitly.
Follow the workspace-local run state rules in
`common/python-runtime.md`; do not write or read an external run-id scratch file.

```
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id>
```
Create `manifest.yaml` with `{run_id, started_at, user_request, current_stage: workspace-scout, completed_stages: []}`.

Ensure `aidlc-docs/` exists:
```bash
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id>
```
`aidlc-docs/audit.md` is auto-created by `stage-open` in `spawn-loop.md` step 0.

## Step 2 — Resolve skill paths (once per run)
Find each required SKILL.md: `.agents/custom-skills/<name>/SKILL.md` → `.agents/skills/<name>/SKILL.md` → `~/.agents/skills/<name>/SKILL.md`. Store in `manifest.skill_paths:`. Log `[Skill] MISSING: <name>` if not found (uses inline fallback).

> **Framework skills** (autoskills-installed) are NOT yet available at spec time —
> they are synced and selected during `/factory-build` Pre-Build Step 0.
> Spec and plan stages use first `.agents/custom-skills/`, then `~/.agents/skills/<name>/SKILL.md`. Log any missing skills to audit.md. process skills only.

## Step 3 — Workspace Scout (inline)

PRIORITY: P2

### Context Injection (Pre-execution)

Before spawning the stage, build and inject the context snapshot:

```bash
<aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth minimal --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
```

**Depth**: `minimal` for workspace-scout (only current stage + last 3 audit entries).

Inject into the workspace-scout input handoff under `context_snapshot:` (or prepend as YAML comment if contract lacks this field). The stage agent MUST read this snapshot before executing its workspace scan.

### Stage execution

Execute `stage/workspace-scout.md` inline (no `Task()`). Follow the
[post-execution loop](spawn-loop.md) for bookkeeping.

**Greenfield shortcut (before workspace-scout):**
Use the file search tool (depth <= 2) for source files and manifests.
Exclude aidlc-scripts, .aidlc-orchestrator, aidlc-docs, .agents, .github,
.venv, node_modules and .git. Treat an empty match set as greenfield.
If no output → workspace is greenfield. Build `workspace-scout.output.yaml` inline (set `project_type: greenfield`, `existing_code: false`, `next_phase: requirements-analysis`, `codegraph_state: {indexed: false}`) and log `[Inline] workspace-scout — greenfield, scanned inline`. Skip spawning workspace-scout. This saves 1 agent spawn.

**MANDATORY after greenfield shortcut** — create `aidlc-state.md` immediately (the workspace-scout agent normally creates this in its Step 4; the inline shortcut bypasses the agent so the orchestrator MUST create it here):
```bash
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id>
```
Create `aidlc-docs/aidlc-state.md` with:
```markdown
# AIDLC State — <run-id>

## Project Information
- **Run ID**: <run-id>
- **Started**: <ISO date>
- **Request**: <user_request>
- **Type**: Greenfield

## Workspace State
- **Project type**: greenfield
- **Existing code**: false

## Current Stage
INCEPTION - Workspace Detection (complete)

## Stage Progress
- [x] Workspace Detection — <ISO date>
- [ ] Requirements Analysis
- [ ] Product Pass
- [ ] Design Pass
- [ ] Architecture Pass
- [ ] Context Pass (Workflow Planning)
- [ ] Construction
- [ ] Review
- [ ] Ship
```

The greenfield shortcut uses the same stage-open/stage-close lifecycle as
a normal inline stage. Write its output handoff with `status: complete`
and the evidence above in `audit_entries[]`; do not emit a second pair.

Pre-execution (steps 0-1): `stage-open`, knowledge query.
Then execute stage instructions directly — write an output handoff for stage-close; no JSON Schema validation.
After execution: lightweight validation (see [`validation.md`](validation.md)),
context compaction (see [`compaction.md`](compaction.md)), `stage-close`,
state document update, halt-check.
**Do NOT commit here.** Commits are deferred to the command-boundary approval gate (Step 6).

Stage-specific knobs:
- **skills_required**: `[using-agent-skills]`
- **predecessor_artifacts**: none (first stage)
- **approval gate**: none — auto-proceeds on `status: complete`
- **state on success**: `Current Stage: INCEPTION - Workspace Detection (complete)`; manifest `current_stage: requirements-analyst`

## Step 3.5 — Classify `project_profile` + design-system bootstrap + reverse-engineer routing

After workspace-scout completes, run the project-profile pipeline:

```bash
<aidlc-python> aidlc-scripts/factory_project_profile.py run <run-id> \
    --workspace-output .aidlc-orchestrator/runs/<run-id>/handoffs/workspace-scout.output.yaml \
    --repo-root .
```

This script:
1. Classifies `project_profile` (ui / api / has_legacy / framework / design_system_path) per [`project-profile.md`](project-profile.md) §A.
2. Bootstraps `design-system/` if `ui: true` and it does not exist.
3. Snaps and imports Figma data if `has_figma_data == true`.
4. Snaps and imports Stitch data if `has_stitch_data == true`.
5. Reverse-engineers tokens from existing CSS/SCSS/styled-components if brownfield + UI + no Figma/Stitch.
6. Persists all fields to the manifest via `factory_run.py set`.

**Reverse-engineer routing** (same as before — decision lives in `project-profile.md` §B):
After the profile pipeline completes, decide whether to run `reverse-engineer` based on brownfield state and artifact presence.

> **Cookbook**: If reverse-engineer runs, its agent loads the `ai-architecture-cookbook` skill (`recommend_pattern` + `query_standard`) to identify architectural patterns in the existing codebase and annotate detected domains with standard IDs, so downstream stages have cookbook context from the start.

## Step 3.6 — Cookbook project context injection

After the project-profile pipeline (and optional reverse-engineer), build the cookbook project context from the detected tech stack and previous architecture decisions:

```bash
<aidlc-python> aidlc-scripts/factory_project_context.py --repo-root . --format compact \
    > .aidlc-orchestrator/runs/<run-id>/cookbook-context.json
```

This script reads lockfiles (package.json, Cargo.toml, pyproject.toml, go.mod) and aidlc-docs/ to extract:
- `techStack[]` — detected technologies per layer (frontend, backend, database, etc.)
- `scale` — inferred from audit.md
- `compliance[]` — extracted from requirements.md (gdpr, hipaa, pci-dss, etc.)
- `previous_decisions[]` — from ADRs and execution plan
- `client_types[]` — inferred from tech stack layers

Store the result path in the manifest:
```bash
<aidlc-python> aidlc-scripts/factory_run.py set <run-id> \
    --field cookbook_context_path=.aidlc-orchestrator/runs/<run-id>/cookbook-context.json
```

Log: `[Cookbook] Project context built and stored at cookbook-context.json`.

Downstream stages (workflow-planner, application-designer, code-generator, reviewers) can read this file and pass its contents as `context` to `recommend_workflow` / `recommend_pattern` / `explain_decision` MCP tools.

Then proceed to Step 4.

## Step 4 — Requirements Analyst (two-pass, inline)

PRIORITY: P2

**Validate stage prerequisites (MANDATORY):**
```bash
<aidlc-python> aidlc-scripts/stage_gate.py check <run-id> requirements-analyst
```
Exit 0 → continue. Exit 1 → **HALT**. Do NOT proceed.

### Context Injection (Pre-execution)

Before spawning the stage, regenerate the context snapshot (depth auto-selects based on completed stage count):

```bash
<aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth auto --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
```

**Depth**: `auto` — with 1 completed stage (workspace-scout), this resolves to `minimal` (~200 tokens). The snapshot includes the workspace-scout decision and project profile.

Inject into the requirements-analyst input handoff under `context_snapshot:`. The agent MUST read this to understand the workspace state before asking questions.

### Stage execution

Execute `stage/requirements-analyst.md` inline (no `Task()`). Follow the
[post-execution loop](spawn-loop.md) for bookkeeping.

**Two-pass**: both passes execute inline. Pass 1 emits the questions → **SURFACE the questions file path** (from `questions_artifact_path`) to the user so they can answer **in-place by filling the `[Answer]:` tags in that same file** (via CLI or by editing it directly) → user responds → Pass 2.

**Single-file convention (do NOT duplicate)**: there is exactly ONE questions file, `<run-id>-requirement-verification-questions.md`. The user answers inside it. Do NOT create, copy to, or expect a separate `*answered*` / `*-answered.md` file — Pass 2 re-invokes requirements-analyst pointing at the SAME file once its `[Answer]:` tags are filled. The agent distinguishes Pass 1 vs Pass 2 by reading the file (empty answer tags → Pass 1; filled → Pass 2).

Pre-execution (steps 0-1): emit `spawn_start`, knowledge query.
Then execute inline. After each pass: lightweight validation, context compaction.
On user answers (between passes): call `emit_audit_block` per [`audit-block.protocol.md` § user_answers_received](../contracts/audit-block.protocol.md).

Stage-specific knobs:
- **skills_required**: `[idea-refine, spec-driven-development, requirements-intelligence, using-agent-skills]`
- **predecessor_artifacts**: workspace-scout's output handoff. Copy its `workspace_state` block into the input.
- **state on Pass 2 success** (three required mutations):
  1. `Current Stage`: `INCEPTION - Requirements Analysis (complete) — awaiting /factory-plan`.
  2. `Stage Progress`: mark `[x] Requirements Analysis — <ISO date>`.
  3. `Extension Configuration` table (upsert per current iteration): parse the in-place answered questions file (`<run-id>-requirement-verification-questions.md`) for `^## Question: (.+) Extension$` headings. Map answer letter → enabled value via the option text: `A → Yes`; `B`/`C` → `Partial` if option text contains "Partial"/"only", else `No`; anything else → `Unknown` (and log warning). Upsert into `## Extension Configuration` table with `Decided At = Current iteration: Requirements Analysis (Answer <letter>) — run_id <run-id>`. Create the table with 3-column shape (`| Extension | Enabled | Decided At |`) if absent. Log `[Orchestrator] Extension Configuration upserted: <ext>=<val>` per row.

## Step 4.5 — Stage-Routing Decisions (once per run, after Pass 2)

Derive concrete pipeline decisions from `request_classification` + `project_profile`. The tier
label is persisted for telemetry; what matters downstream is `fast_path`, `skip_stages[]`,
`reviewer_pool[]`, `merge_codegen_gate`.

1. `factory_complexity.py <run-id> --apply` (on failure default to "run everything": empty skip list, full reviewer pool).
2. Parse JSON output. **If `fast_path == true` (tier=TINY)**: route immediately to
   [`fast-path.md`](fast-path.md) — do NOT proceed to Step 5 or `/factory-plan`. Run terminates
   after fast-path completes or user rejects.
3. `factory_run.py set <run-id> --field complexity_tier=<tier> --field skip_stages='<json>' --field merge_codegen_gate=<bool> --field reviewer_pool='<json>'`. Validate against `shared/complexity-tier.schema.json` (non-blocking warn only). `complexity_tier` is persisted for telemetry but is not the user-facing artifact.
4. `emit_audit_block` with skip list + reviewer pool + one-line rationale per decision.

**Skip enforcement**: for each skipped stage, `emit_audit_block --evt stage_skipped` → append to `manifest.skipped_stages[]` → continue. Do NOT spawn.

**Merged codegen gate**: if `merge_codegen_gate`, set `merged_plan_generate: true` in code-generator input → agent skips plan-approval, outputs `sub_stage: generated`.

## Step 5 — Approval gate (structured contract)

Before presenting to the user, build the approval handoff using the structured contract:

1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.input.yaml`:
   ```yaml
   stage: requirements-analyst
   run_id: <run-id>
   title: "Requirements Analysis — Final Approval"
   units:
     - label: "Requirements Document"
       tasks:
         - id: "REQ"
           description: "Complete requirements analysis with user answers"
           status: complete
   artifacts:
     - path: "aidlc-docs/inception/requirements/<run-id>-requirements.md"
       kind: doc
       description: "Requirements specification document"
     - path: "aidlc-docs/inception/requirements/<run-id>-requirement-verification-questions.md"
       kind: questions
       description: "Answered verification questions (if any)"
   skill_compliance:
     - skill: "using-agent-skills"
       status: PASS
     - skill: "idea-refine"
       status: PASS
     - skill: "spec-driven-development"
       status: PASS
     - skill: "requirements-intelligence"
       status: PASS
   resolution:
     options: [approve, request_changes, cancel]
     note_prompt: "Describe what changes are needed"
   next_command:
     command: "/factory-plan <run-id>"
     description: "Generate execution plan and unit decomposition"
   routing_decisions:
     skip_stages: <list>
     reviewer_pool: <list>
     merge_codegen_gate: <bool>
   context: "<workspace_state one-line summary + key findings>"
   ```

2. **Validate** against the contract:
   ```bash
   <aidlc-python> aidlc-scripts/factory_validate.py \
       .aidlc-orchestrator/contracts/approval.input.v1.json \
       .aidlc-orchestrator/runs/<run-id>/handoffs/approval.input.yaml
   ```
   If validation fails, fix the handoff before presenting. Do NOT skip validation.

3. **Present** the approval gate to the user using the Structured Approval Format from the validated handoff. **Explicitly ask for approval.** Do NOT proceed without an explicit approval signal.

Wait for user response:
- **Approve / LGTM / Continue** → proceed to Step 6 (auto-commit + suggest next command).
- **Request changes** → re-run requirements-analyst Pass 2 with revision context.
- **Cancel** → mark run as cancelled, stop.

## Step 6 — Auto-commit + present next

**On EXPLICIT user approval only:**

1. Run commit:
   ```bash
   git add -A && git commit -m "<type>(<scope>): <description>"
   ```
   per core-workflow.md. Types: `docs` (plans/requirements), `feat` (code), `build` (build/test). Scope = stage in kebab-case. If git fails, log warning and continue.

2. **Record the decision** in `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.output.yaml`:
   ```yaml
   run_id: <run-id>
   stage: requirements-analyst
   decision: approve
   timestamp: <ISO8601>
   commit_triggered: true
   commit_sha: <sha>
   audit_entries:
     - "[Approval] User approved requirements for <run-id>"
   ```
   Validate against `.aidlc-orchestrator/contracts/approval.output.v1.json`.

**If the user did not approve, do NOT run this step. Do NOT commit.**

Then present completion with the **literal next command** (substitute the actual run_id, never output `<run-id>` as placeholder text):
```
Run complete: <run-id>
  requirements: aidlc-docs/inception/requirements/<run-id>-requirements.md
  decisions:    skip_stages=<list>, reviewer_pool=<list>

Inception Extended Flow:
  Step 0.0 ✅  /factory-spec       — Workspace detection + requirements
  Step 0.1     /factory-product-pass <run-id>  — Product vision, personas, stories
  Step 0.2     /factory-design-pass <run-id>  — UX flows, UI components, design-system mapping
  Step 0.3     /factory-arch-pass   <run-id>  — ADRs, tech stack, component map, interfaces

Next command: /factory-product-pass <run-id>
```
Offer `/factory-product-pass <run-id>` (MUST substitute the actual run_id). Do NOT auto-execute. Do NOT offer `/factory-plan` directly — the three inception passes (product, design, arch) must complete first. Do NOT prominently display the abstract `complexity_tier` label — the decisions are the user-visible artifact.

---

## Hard rules

- Validate every input AND every output. No exceptions.
- Never fabricate stage output fields to satisfy schemas.
- Sequential only — no parallel `Task()` calls in Phase 0.
- audit.md is append-only and orchestrator-owned; timestamps come from
  `timeline.jsonl`, not from agent-supplied strings. Agents emit plain bullet
  `audit_entries[]`; orchestrator wraps with `## <ts> ... START/COMPLETE` headers.
- Skill paths missing → log `[Skill] MISSING` and use rule file inline fallback.
- Approval gates pause; never auto-approve (Step 3.5 RE prompt is an approval gate).
