**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-design-pass` — Design Pass

PRIORITY: P2

**Phase**: Inception — Design Pass (Phase 0.2)  
**Predecessor**: `/factory-product-pass` (product-pass must be complete)  
**Successor**: `/factory-arch-pass <run-id>`

Produces the **user-facing design** from the product model: UX flows (with information architecture), UI component inventory, and design-system mapping. Design Pass is intentionally scoped to UX/UI only — it does **NOT** decide endpoints, data models, service interfaces, or technical component dependencies. Those are Architecture Pass concerns (the next pass), which validates this design before committing technical decisions.

Until this phase is complete, `/factory-arch-pass` is blocked.

**Output artifacts:**
- `aidlc-docs/inception/design-pass/<run-id>-design-questions.md` (Pass 1)
- `aidlc-docs/inception/design-pass/<run-id>-ux-flows.md` (flows + information architecture)
- `aidlc-docs/inception/design-pass/<run-id>-ui-component-inventory.md` (presentational components, if UI)
- `aidlc-docs/inception/design-pass/<run-id>-design-system-mapping.md` (tokens / primitives, if UI)
- `aidlc-docs/inception/design-pass/<run-id>-application-design.md` (consolidated UX design + story → screen traceability)

> **Out of scope (moved to Architecture Pass):** technical component map (`component-map.md`), service interfaces / endpoints / event contracts / data models (`service-interfaces.md`). Do NOT emit these here.

---

## Step 1 — Validate run + prerequisites + brownfield probe

```bash
<aidlc-python> aidlc-scripts/stage_gate.py check <run-id> product-pass
```
Exit 1 → **HALT**: `Product Pass not complete. Run /factory-product-pass <run-id> first.`

Read manifest. Refuse if `completed_stages` does not contain `product-pass`.

**Brownfield probe** — read `project_profile`:

```bash
<aidlc-python> aidlc-scripts/factory_run.py get <run-id> --field project_profile
```

- `project_profile.has_legacy == true` OR `completed_stages` contains `reverse-engineer` → `design_mode: delta` (design delta on top of existing UI/structure)
- Otherwise → `design_mode: full` (design from scratch)

If `design_mode: delta`, locate existing UI baseline (if present):
- `aidlc-docs/inception/reverse-engineering/<run-id>-component-inventory.md` — existing components
- `aidlc-docs/inception/reverse-engineering/<run-id>-architecture.md` — existing structure

If RE artifacts missing despite `design_mode: delta` → log `[DesignPass] No RE component inventory found — delta mode will infer baseline from product stories` and continue.

Emit: `[DesignPass] Mode: <full|delta>`

Update manifest:
```bash
<aidlc-python> aidlc-scripts/factory_run.py set <run-id> \
    --field current_stage=design-pass \
    --field design_mode=<full|delta>
```

## Step 2 — Resolve skill paths

Skills needed: `design-pass`, `design-system-composer` (conditional on ui:true), `using-agent-skills`.

Log `[Skill] MISSING: <name>` if absent.

## Step 3 — Context snapshot injection

```bash
<aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth standard --format compact \
    --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
```

Depth: `standard` — design needs the product model (vision, personas, stories). It runs before architecture, so there are no arch artifacts to read.

## Step 4 — State update

Update `aidlc-docs/aidlc-state.md`:
- `Current Stage: INCEPTION - Design Pass (in progress)`
- Add stage progress entry: `[ ] Design Pass — started <ISO date>`

Emit audit block:
Write `.aidlc-orchestrator/runs/<run-id>/tmp/design-pass-start-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[Orchestrator] Design Pass started (UX/UI design from product model)`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt orchestrator_note --stage design-pass --phase INCEPTION --label "DESIGN PASS PHASE START" --field summary="design-pass start" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/design-pass-start-bullets.txt
```

## Step 5 — Design system probe

Read `manifest.project_profile.ui`.

If `ui: true`:
- Check `manifest.project_profile.design_system_path`.
- Run design system composer probe per `design-pass/SKILL.md` Step 2.
- Emit `[DesignPass] Design system probe: <result>`.

If `ui: false`:
- Emit `[DesignPass] Non-UI project — design system probe skipped`.
- Skip UX flows, UI component inventory, and design-system mapping artifacts; produce only `application-design.md` (a lightweight functional design from the product model — still no endpoints/data models).

## Step 6 — Design Pass skill execution (two-pass, inline)

Execute `.agents/custom-skills/design-pass/SKILL.md` inline, which delegates to `stage/application-designer.md` with UX/UI overrides.

Ensure output directory exists:
```bash
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id> --extra aidlc-docs/inception/design-pass
```

**skills_required**: `[design-pass, design-system-composer (if ui), unslop (if ui), impeccable (if ui), using-agent-skills]`

**predecessor_artifacts** (always):
- `aidlc-docs/inception/requirements/<run-id>-requirements.md`
- `aidlc-docs/inception/product-pass/<run-id>-product-vision.md`
- `aidlc-docs/inception/user-stories/<run-id>-stories.md`
- `aidlc-docs/inception/user-stories/<run-id>-personas.md`

**predecessor_artifacts** (delta mode only — include if present):
- `aidlc-docs/inception/reverse-engineering/<run-id>-component-inventory.md`
- `aidlc-docs/inception/reverse-engineering/<run-id>-architecture.md`

**Inject `design_mode` into the skill input**: the skill reads this field and switches behaviour:
- `full` → build complete UX/UI design from scratch
- `delta` → load existing UI baseline, produce delta (new + modified + deprecated screens/components only)

**Two-pass**:
- **Pass 1**: application-designer emits **design questions reinforced for UX/UI** (empty `[Answer]:` tags) → **SURFACE `design-questions.md` path to user** → user answers **in-place in that same file** → wait. **Single-file**: do NOT create a separate `*answered*` copy; Pass 2 re-invokes on the same file once its `[Answer]:` tags are filled.
  - Questions MUST cover: target users & devices, key user journeys & entry points, navigation/information architecture, screen inventory, interaction patterns, states (empty/loading/error/success), accessibility expectations, content/tone, responsive behaviour, and (if design system present) which primitives/tokens to reuse.
  - When `ui: true`, questions MUST also cover visual direction: surface mode (`Persuade`, `Operate`, `Read`, or `Experience`), character (two or three concrete words — `clean`, `modern`, `sleek`, `minimal`, and `premium` are not allowed), world, moments, signature, and accent (a hex that replaces `color.brand.primary`, or `fallback`).
  - Questions MUST NOT ask about endpoints, data models, storage, or tech stack — those belong to Architecture Pass.
- **Pass 2** (after answers): emit ux-flows (with IA), ui-component-inventory (if ui), design-system-mapping (if ui), design-direction (if ui), application-design. `design-direction.md` carries Product, Character, World, Moments, Signature, surface mode, and accent status. Empty Character, World, or Moments → `needs_human`.

The `needs_human` gate from application-designer is the inter-pass boundary — surface it using the Structured Approval Format, then re-invoke on user response.

## Step 7 — Approval gate (structured contract)

1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.design-pass.input.yaml`:
   ```yaml
   stage: design-pass
   run_id: <run-id>
   title: "Design Pass — Approval Gate"
   units:
     - label: "UX Flows"
       tasks:
         - id: "UXFLOWS"
           description: "UX flows + information architecture (navigation, screen inventory, journeys)"
           status: complete
     - label: "UI Components"
       tasks:
         - id: "UICOMPONENTS"
           description: "UI component inventory (presentational) + design-system mapping"
           status: complete
     - label: "Application (UX) Design"
       tasks:
         - id: "DESIGN"
           description: "Consolidated UX design with story → screen traceability"
           status: complete
   artifacts:
     - path: "aidlc-docs/inception/design-pass/<run-id>-ux-flows.md"
       kind: doc
       description: "UX flows with information architecture"
     - path: "aidlc-docs/inception/design-pass/<run-id>-ui-component-inventory.md"
       kind: doc
       description: "Presentational UI component inventory"
     - path: "aidlc-docs/inception/design-pass/<run-id>-design-system-mapping.md"
       kind: doc
       description: "Design system / token mapping"
     - path: "aidlc-docs/inception/design-pass/<run-id>-design-direction.md"
       kind: doc
       description: "Visual direction the code generator must paint from"
     - path: "aidlc-docs/inception/design-pass/<run-id>-application-design.md"
       kind: doc
       description: "Consolidated UX design with story → screen traceability"
   skill_compliance:
     - skill: "design-pass"
       status: PASS
     - skill: "design-system-composer"
       status: "PASS | N/A"
     - skill: "unslop"
       status: "PASS | N/A"
     - skill: "impeccable"
       status: "PASS | N/A"
   resolution:
     options: [approve, request_changes, cancel]
     note_prompt: "Describe what changes are needed"
   next_command:
     command: "/factory-arch-pass <run-id>"
     description: "Architecture Pass — validates product + design, then defines tech architecture (final inception gate)"
   context: "<N> UX flows, <N> UI components, <N> stories traced to screens"
   ```
2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.
3. **Surface** using the Structured Approval Format. **Explicitly ask for approval.**

- **Approve / LGTM / Continue** → proceed to Step 8.
- **Request changes** → re-run design-pass Pass 2 with revision context.
- **Cancel** → mark run as cancelled, stop.

## Step 8 — State update + auto-commit

**On EXPLICIT user approval only:**

1. Update state:
   - `Current Stage: INCEPTION - Design Pass (complete) — awaiting /factory-arch-pass`
   - `Stage Progress`: mark `[x] Design Pass — <ISO date>`

2. Update manifest:
   ```bash
   <aidlc-python> aidlc-scripts/factory_run.py set <run-id> \
       --field current_stage=arch-pass \
       --append completed_stages=design-pass
   ```

3. Emit completion audit block:
   Write `.aidlc-orchestrator/runs/<run-id>/tmp/design-pass-complete-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

   - `[Orchestrator] Design Pass complete (mode: <full|delta>): <N> UX flows, <N> UI components, <N> stories traced to screens`

   ```text
   <aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt orchestrator_note --stage design-pass --phase INCEPTION --label "DESIGN PASS PHASE COMPLETE" --field summary="design-pass complete" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/design-pass-complete-bullets.txt
   ```

4. Commit:
   ```bash
   git add -A && git commit -m "docs(design-pass): complete UX/UI design pass for <run-id>"
   ```

5. **Record** `approval.output.yaml` with decision, timestamp, commit_sha.

**If the user did not approve, do NOT run this step. Do NOT commit.**

Present completion:
```
Design Pass complete: <run-id>

  ux-flows:               aidlc-docs/inception/design-pass/<run-id>-ux-flows.md
  ui-component-inventory: aidlc-docs/inception/design-pass/<run-id>-ui-component-inventory.md  [if UI]
  design-system-mapping:  aidlc-docs/inception/design-pass/<run-id>-design-system-mapping.md  [if UI]
  application-design:     aidlc-docs/inception/design-pass/<run-id>-application-design.md

Next command: /factory-arch-pass <run-id>
```

Do NOT auto-execute `/factory-arch-pass`.

---

## Hard rules

- Stage gate enforced — halt if product-pass not complete.
- Design Pass is UX/UI only — NEVER emit endpoints, data models, service interfaces, or a technical component map. Those are Architecture Pass artifacts.
- story → screen/component traceability must be 100% before approval gate opens.
- Design system composer runs when `ui: true` — never skip silently.
- Approval gate pauses; never auto-approve.
- Do NOT proceed to `/factory-arch-pass` without explicit user approval.
- Design Pass is NOT the final inception gate — `inception_complete` is set by Architecture Pass, the last pass.
- Both passes (questions → artifacts) must complete before approval gate opens.
