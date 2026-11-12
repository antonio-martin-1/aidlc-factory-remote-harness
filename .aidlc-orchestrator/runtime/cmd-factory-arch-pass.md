**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-arch-pass` — Architecture Pass

PRIORITY: P2

**Phase**: Inception — Architecture Pass (Phase 0.3 — **FINAL INCEPTION GATE**)  
**Predecessor**: `/factory-design-pass` (product-pass AND design-pass must be complete)  
**Successor**: `/factory-plan <run-id>` (Context Pass)

Validates the product model + design, then produces the technical architecture: ADRs, tech stack, technical component map, and service interfaces. Architecture runs **last** in Inception so it can reconcile WHAT (product) and the user-facing HOW (design) before committing technical decisions.

This is a **two-pass** stage: Pass 1 emits architecture clarifying questions and validation findings for human approval; Pass 2 generates the artifacts. This is the **last Inception gate** — until all three passes (product, design, arch) are complete, `/factory-plan` and `/factory-build` are blocked.

**Output artifacts:**
- `aidlc-docs/inception/arch-pass/<run-id>-arch-questions.md` (Pass 1 — clarifying questions + validation findings)
- `aidlc-docs/inception/arch-pass/<run-id>-tech-stack.md`
- `aidlc-docs/inception/arch-pass/<run-id>-adrs.md`
- `aidlc-docs/inception/arch-pass/<run-id>-architecture-decisions.md`
- `aidlc-docs/inception/arch-pass/<run-id>-component-map.md` (technical component map — moved here from Design Pass)
- `aidlc-docs/inception/arch-pass/<run-id>-service-interfaces.md` (endpoints, event contracts, data models — moved here from Design Pass)

---

## Step 1 — Validate run + prerequisites + brownfield detection

```bash
<aidlc-python> aidlc-scripts/stage_gate.py check <run-id> design-pass
```
Exit 1 → **HALT**: `Design Pass not complete. Run /factory-design-pass <run-id> first.`

Also verify product-pass complete (defensive — design-pass already requires it):
```bash
<aidlc-python> aidlc-scripts/stage_gate.py check <run-id> product-pass
```
Exit 1 → **HALT**: `Product Pass not complete. Run /factory-product-pass <run-id> first.`

Read manifest. Refuse if `completed_stages` does not contain both `product-pass` and `design-pass`.

**Brownfield detection** — read manifest fields and set `arch_mode`:

```bash
<aidlc-python> aidlc-scripts/factory_run.py get <run-id> --field project_profile
```

- `project_profile.has_legacy == true` OR `completed_stages` contains `reverse-engineer` → `arch_mode: brownfield`
- Otherwise → `arch_mode: greenfield`

Store in manifest:
```bash
<aidlc-python> aidlc-scripts/factory_run.py set <run-id> \
    --field current_stage=arch-pass \
    --field arch_mode=<greenfield|brownfield>
```

Emit: `[ArchPass] Mode: <greenfield|brownfield>`

**If brownfield**: locate RE artifacts — check for:
- `aidlc-docs/inception/reverse-engineering/<run-id>-architecture.md`
- `aidlc-docs/inception/reverse-engineering/<run-id>-tech-stack.md`
- `aidlc-docs/inception/reverse-engineering/<run-id>-component-inventory.md`

If any RE artifact is missing but `arch_mode: brownfield` → log `[ArchPass] RE artifact missing: <path> — will infer from codebase` and continue (non-blocking).

## Step 2 — Resolve skill paths

Skills needed: `arch-pass`, `ai-architecture-cookbook`, `using-agent-skills`.

Log `[Skill] MISSING: <name>` if absent.

## Step 3 — Context snapshot injection

```bash
<aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth comprehensive --format compact \
    --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
```

Depth: `comprehensive` — architecture is the last inception stage; it needs the full product model AND the design artifacts to validate against.

## Step 4 — State update

Update `aidlc-docs/aidlc-state.md`:
- `Current Stage: INCEPTION - Architecture Pass (in progress)`
- Add stage progress entry: `[ ] Architecture Pass — started <ISO date>`

Emit audit block:
Write `.aidlc-orchestrator/runs/<run-id>/tmp/arch-pass-start-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[Orchestrator] Architecture Pass started (validates product + design, two-pass)`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt orchestrator_note --stage arch-pass --phase INCEPTION --label "ARCH PASS PHASE START" --field summary="arch-pass start" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/arch-pass-start-bullets.txt
```

## Step 5 — Architecture Pass skill execution (two-pass, inline)

Execute `.agents/custom-skills/arch-pass/SKILL.md` inline.

Ensure output directory exists:
```bash
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id> --extra aidlc-docs/inception/arch-pass
```

**skills_required**: `[arch-pass, ai-architecture-cookbook, using-agent-skills]`

**predecessor_artifacts** (always — product model):
- `aidlc-docs/inception/requirements/<run-id>-requirements.md`
- `aidlc-docs/inception/product-pass/<run-id>-product-vision.md`
- `aidlc-docs/inception/user-stories/<run-id>-stories.md`
- `aidlc-docs/inception/user-stories/<run-id>-personas.md`

**predecessor_artifacts** (always — design model, to validate against):
- `aidlc-docs/inception/design-pass/<run-id>-ux-flows.md`
- `aidlc-docs/inception/design-pass/<run-id>-ui-component-inventory.md` (if present / UI project)
- `aidlc-docs/inception/design-pass/<run-id>-design-system-mapping.md` (if present / UI project)
- `aidlc-docs/inception/design-pass/<run-id>-application-design.md`

**predecessor_artifacts** (brownfield only — include if present):
- `aidlc-docs/inception/reverse-engineering/<run-id>-architecture.md`
- `aidlc-docs/inception/reverse-engineering/<run-id>-tech-stack.md`
- `aidlc-docs/inception/reverse-engineering/<run-id>-component-inventory.md`

**Inject `arch_mode` into the skill input**: the skill reads this field and switches behaviour:
- `greenfield` → define tech stack from scratch
- `brownfield` → audit existing tech stack, produce evolution ADRs

**depth**: `comprehensive`

**Cookbook call budget for this stage**: ≤6 total calls (recommend_pattern_nl + get_decision_tree × 4 + get_checklist × 1).

**Two-pass**:

- **Pass 1 — Validation + clarifying questions**: the arch-pass-agent reads the product model AND the design artifacts, validates coherence between them, and emits:
  - `aidlc-docs/inception/arch-pass/<run-id>-arch-questions.md` containing:
    - **Validation findings**: gaps, ambiguities, or contradictions between product stories and the design (e.g. a story with no screen, a UX flow implying a capability the product vision excludes).
    - **Clarifying questions** (MCQ per question-format-guide): tech-stack constraints, integration points, non-functional requirements (scale, latency, compliance), data ownership, and any design decision that forces an architectural trade-off.
  - Set `status: needs_human`. **SURFACE `arch-questions.md` path to user** → the human validates findings and answers **in-place in that same file** → wait. **Single-file**: do NOT create a separate `*answered*` copy; Pass 2 re-invokes on the same `arch-questions.md` once its `[Answer]:` tags are filled.
  - If NO gaps and NO open questions are found, the agent MAY still emit `arch-questions.md` with an explicit "No blocking questions — confirm to proceed" item, so the human always validates before technical artifacts are generated.

- **Pass 2 — Architecture artifacts** (after the human answers): the skill orchestrates:
  1. Cookbook MCP detection + `recommend_pattern_nl` call.
  2. Tech stack decision matrix via `get_decision_tree` (≤4 calls) → `tech-stack.md`.
  3. ≥3 ADRs → `adrs.md`.
  4. Architecture decisions summary → `architecture-decisions.md`.
  5. **Technical component map** (dependency graph, boundary rules, interface contracts) → `component-map.md`.
  6. **Service interfaces** (endpoints, event contracts, data models) → `service-interfaces.md`.

The `needs_human` gate from Pass 1 is the inter-pass boundary — surface it, then re-invoke the agent on the user's response.

## Step 6 — Inception completion gate

After Pass 2, before the approval gate, run the inception completeness check:

```
Inception Phase Completeness:
  [x] Workspace Detection   (factory-spec)
  [x] Requirements Analysis (factory-spec)
  [x] Product Pass          (factory-product-pass)
  [x] Design Pass           (factory-design-pass)
  [x] Architecture Pass     (factory-arch-pass — current, FINAL gate)
  [ ] Context Pass          (factory-plan — next)
```

Surface this checklist to the user as part of the approval surface.

## Step 7 — Approval gate (structured contract)

1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.arch-pass.input.yaml`:
   ```yaml
   stage: arch-pass
   run_id: <run-id>
   title: "Architecture Pass — Approval Gate (Final Inception Gate)"
   units:
     - label: "Tech Stack & ADRs"
       tasks:
         - id: "TECH"
           description: "Tech stack decision matrix (≥6 layers)"
           status: complete
         - id: "ADRS"
           description: "Architecture decision records (≥3)"
           status: complete
     - label: "Component Map & Interfaces"
       tasks:
         - id: "COMPONENTS"
           description: "Technical component map (dependency graph + boundary rules)"
           status: complete
         - id: "INTERFACES"
           description: "Service interfaces (endpoints, events, data models)"
           status: complete
     - label: "Architecture Summary"
       tasks:
         - id: "ARCH"
           description: "Architecture decisions summary with pattern references"
           status: complete
   artifacts:
     - path: "aidlc-docs/inception/arch-pass/<run-id>-tech-stack.md"
       kind: doc
       description: "Tech stack with rationale and cookbook standard IDs"
     - path: "aidlc-docs/inception/arch-pass/<run-id>-adrs.md"
       kind: doc
       description: "Architectural decision records"
     - path: "aidlc-docs/inception/arch-pass/<run-id>-architecture-decisions.md"
       kind: doc
       description: "Architecture summary with cross-cutting concerns"
     - path: "aidlc-docs/inception/arch-pass/<run-id>-component-map.md"
       kind: doc
       description: "Technical component map with dependency graph"
     - path: "aidlc-docs/inception/arch-pass/<run-id>-service-interfaces.md"
       kind: doc
       description: "Service interfaces, event contracts, and data models"
   skill_compliance:
     - skill: "arch-pass"
       status: PASS
     - skill: "ai-architecture-cookbook"
       status: PASS
   resolution:
     options: [approve, request_changes, cancel]
     note_prompt: "Describe what changes are needed"
   next_command:
     command: "/factory-plan <run-id>"
     description: "Context Pass — workflow planning and unit decomposition"
   context: "mode: <greenfield|brownfield> — <N> patterns, <N> ADRs, <N> components, <N> interfaces; all inception gates complete"
   ```
2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.
3. **Surface** using the Structured Approval Format with the Inception Completeness checklist. **Explicitly ask for approval.**

- **Approve / LGTM / Continue** → proceed to Step 8.
- **Request changes** → re-run arch-pass-agent Pass 2 with revision context (cite specific ADR, component, or tech decision to change).
- **Cancel** → mark run as cancelled, stop.

## Step 8 — State update + auto-commit

**On EXPLICIT user approval only:**

1. Update state:
   - `Current Stage: INCEPTION - Architecture Pass (complete) — Inception complete, awaiting /factory-plan`
   - `Stage Progress`: mark `[x] Architecture Pass — <ISO date>`
   - Add Inception summary block to `aidlc-state.md`:
     ```
     ## Inception Summary
     Completed: <ISO date>
     Passes:    Product ✓  |  Design ✓  |  Architecture ✓
     Ready for: /factory-plan (Context Pass) → /factory-build (Construction)
     ```

2. Update manifest:
   ```bash
   <aidlc-python> aidlc-scripts/factory_run.py set <run-id> \
       --field current_stage=workflow-planner \
       --append completed_stages=arch-pass \
       --field inception_complete=true
   ```

3. Emit completion audit block:
   Write `.aidlc-orchestrator/runs/<run-id>/tmp/arch-pass-complete-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

   - `[Orchestrator] Architecture Pass complete (mode: <greenfield|brownfield>). Inception phase fully complete. <N> ADRs, tech stack defined, <N> components, <N> interfaces, patterns: [<list>]`

   ```text
   <aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt orchestrator_note --stage arch-pass --phase INCEPTION --label "ARCH PASS PHASE COMPLETE" --field summary="arch-pass complete" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/arch-pass-complete-bullets.txt
   ```

4. Commit:
   ```bash
   git add -A && git commit -m "docs(arch-pass): complete architecture pass and inception phase for <run-id>"
   ```

5. **Record** `approval.output.yaml` with decision, timestamp, commit_sha.

**If the user did not approve, do NOT run this step. Do NOT commit.**

Present completion:
```
Architecture Pass complete: <run-id>

  tech-stack:         aidlc-docs/inception/arch-pass/<run-id>-tech-stack.md
  adrs:               aidlc-docs/inception/arch-pass/<run-id>-adrs.md
  arch-summary:       aidlc-docs/inception/arch-pass/<run-id>-architecture-decisions.md
  component-map:      aidlc-docs/inception/arch-pass/<run-id>-component-map.md
  service-interfaces: aidlc-docs/inception/arch-pass/<run-id>-service-interfaces.md

  Patterns adopted: <list from cookbook>
  ADRs produced: <N>

  ✅ Inception Phase COMPLETE
     Product Pass ✓ | Design Pass ✓ | Architecture Pass ✓

Next command: /factory-plan <run-id>
```

Do NOT auto-execute `/factory-plan`.

---

## Hard rules

- Stage gate enforced — halt if product-pass OR design-pass not complete.
- Architecture Pass validates the product model AND the design — surface any contradiction in `arch-questions.md` before generating artifacts.
- Pass 1 (clarifying questions / validation) MUST be human-approved before Pass 2 generates artifacts. Never skip the human validation gate.
- ai-architecture-cookbook MUST be consulted (MCP or logged-skip). Never fabricate pattern recommendations.
- ≥3 ADRs required before approval gate opens.
- Technical component map + service interfaces are produced HERE (not in Design Pass).
- Approval gate pauses; never auto-approve.
- Do NOT proceed to `/factory-plan` without explicit user approval.
- `inception_complete=true` MUST be set in manifest before exiting — `/factory-plan` reads this flag.
