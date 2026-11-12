**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-product-pass` — Product Pass

PRIORITY: P2

**Phase**: Inception — Product Pass (Phase 0.1)  
**Predecessor**: `/factory-spec` (requirements-analyst must be complete)  
**Successor**: `/factory-design-pass <run-id>`

Transforms requirements into a validated product model: product vision, user personas, and INVEST-compliant user stories. Until this phase is complete, `/factory-design-pass` is blocked.

**Output artifacts:**
- `aidlc-docs/inception/product-pass/<run-id>-product-vision.md`
- `aidlc-docs/inception/product-pass/<run-id>-product-questions.md`
- `aidlc-docs/inception/user-stories/<run-id>-personas.md`
- `aidlc-docs/inception/user-stories/<run-id>-stories.md`
- `aidlc-docs/inception/user-stories/<run-id>-user-stories-assessment.md`

---

## Step 1 — Validate run + prerequisites

```bash
<aidlc-python> aidlc-scripts/stage_gate.py check <run-id> requirements-analyst
```
Exit 1 → **HALT**: `Requirements analysis not complete. Run /factory-spec <run-id> first.`

Read manifest:
```bash
<aidlc-python> aidlc-scripts/factory_run.py get <run-id>
```
Refuse if missing or if `completed_stages` does not contain `requirements-analyst`.

Update manifest:
```bash
<aidlc-python> aidlc-scripts/factory_run.py set <run-id> --field current_stage=product-pass
```

## Step 2 — Resolve skill paths

Find each SKILL.md: `.agents/custom-skills/<name>/SKILL.md` → `.agents/skills/<name>/SKILL.md` → `~/.agents/skills/<name>/SKILL.md`.

Skills needed: `product-pass`, `requirements-intelligence`, `using-agent-skills`, `spec-driven-development`.

Log `[Skill] MISSING: <name>` if absent (uses inline fallback).

Store resolved paths in `manifest.skill_paths`.

## Step 3 — Context snapshot injection

```bash
<aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth standard --format compact \
    --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
```

## Step 4 — State update

Update `aidlc-docs/aidlc-state.md`:
- `Current Stage: INCEPTION - Product Pass (in progress)`
- Add stage progress entry: `[ ] Product Pass — started <ISO date>`

Emit audit block:
Write `.aidlc-orchestrator/runs/<run-id>/tmp/product-pass-start-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[Orchestrator] Product Pass started`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt orchestrator_note --stage product-pass --phase INCEPTION --label "PRODUCT PASS PHASE START" --field summary="product-pass start" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/product-pass-start-bullets.txt
```

## Step 5 — Product Pass skill execution (inline)

Execute `.agents/custom-skills/product-pass/SKILL.md` inline.

This skill orchestrates:
1. Product vision synthesis from requirements.
2. requirements-intelligence pre-mortem on product vision.
3. story-writer (two-pass) for personas + stories.

**Two-pass for story-writer**:
- Pass 1: emit `aidlc-docs/inception/product-pass/<run-id>-product-questions.md` with empty `[Answer]:` tags → **SURFACE path to user** → user answers **in-place in that same file** → wait. **Single-file**: do NOT create a separate `*answered*` copy; Pass 2 re-invokes on the same file once its `[Answer]:` tags are filled.
- Pass 2 (after user answers): emit personas + stories + INVEST assessment.

Ensure `aidlc-docs/inception/product-pass/` exists:
```bash
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id> --extra aidlc-docs/inception/product-pass
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id> --extra aidlc-docs/inception/user-stories
```

**skills_required**: `[product-pass, requirements-intelligence, spec-driven-development, using-agent-skills]`  
**predecessor_artifacts**: `aidlc-docs/inception/requirements/<run-id>-requirements.md`  
**depth**: `standard`

## Step 6 — Approval gate (structured contract)

After Pass 2 completes, build the approval handoff:

1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.product-pass.input.yaml`:
   ```yaml
   stage: product-pass
   run_id: <run-id>
   title: "Product Pass — Approval Gate"
   units:
     - label: "Product Vision"
       tasks:
         - id: "VISION"
           description: "Product vision document with success metrics"
           status: complete
     - label: "Personas & Stories"
       tasks:
         - id: "PERSONAS"
           description: "User personas (≥1)"
           status: complete
         - id: "STORIES"
           description: "User stories (≥3, INVEST-compliant)"
           status: complete
   artifacts:
     - path: "aidlc-docs/inception/product-pass/<run-id>-product-vision.md"
       kind: doc
       description: "Product vision with success metrics and out-of-scope"
     - path: "aidlc-docs/inception/user-stories/<run-id>-personas.md"
       kind: doc
       description: "User personas"
     - path: "aidlc-docs/inception/user-stories/<run-id>-stories.md"
       kind: doc
       description: "INVEST-compliant user stories"
     - path: "aidlc-docs/inception/user-stories/<run-id>-user-stories-assessment.md"
       kind: doc
       description: "INVEST assessment"
   skill_compliance:
     - skill: "product-pass"
       status: PASS
     - skill: "requirements-intelligence"
       status: PASS
   resolution:
     options: [approve, request_changes, cancel]
     note_prompt: "Describe what changes are needed"
   next_command:
     command: "/factory-design-pass <run-id>"
     description: "Design definition phase (UX flows, UI components)"
   context: "<product goal> — <N> personas, <N> stories"
   ```
2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.
3. **Surface** using the Structured Approval Format. **Explicitly ask for approval.**

- **Approve / LGTM / Continue** → proceed to Step 7.
- **Request changes** → re-run story-writer Pass 2 with revision context.
- **Cancel** → mark run as cancelled, stop.

## Step 7 — State update + auto-commit

**On EXPLICIT user approval only:**

1. Update state:
   - `Current Stage: INCEPTION - Product Pass (complete) — awaiting /factory-design-pass`
   - `Stage Progress`: mark `[x] Product Pass — <ISO date>`

2. Update manifest:
   ```bash
   <aidlc-python> aidlc-scripts/factory_run.py set <run-id> \
       --field current_stage=design-pass \
       --append completed_stages=product-pass
   ```

3. Emit completion audit block:
   Write `.aidlc-orchestrator/runs/<run-id>/tmp/product-pass-complete-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

   - `[Orchestrator] Product Pass complete: <N> personas, <N> stories, product vision validated`

   ```text
   <aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt orchestrator_note --stage product-pass --phase INCEPTION --label "PRODUCT PASS PHASE COMPLETE" --field summary="product-pass complete" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/product-pass-complete-bullets.txt
   ```

4. Commit:
   ```bash
   git add -A && git commit -m "docs(product-pass): complete product discovery for <run-id>"
   ```

5. **Record** `approval.output.yaml` with decision, timestamp, commit_sha.

**If the user did not approve, do NOT run this step. Do NOT commit.**

Present completion:
```
Product Pass complete: <run-id>

  product-vision:  aidlc-docs/inception/product-pass/<run-id>-product-vision.md
  personas:        aidlc-docs/inception/user-stories/<run-id>-personas.md
  stories:         aidlc-docs/inception/user-stories/<run-id>-stories.md
  assessment:      aidlc-docs/inception/user-stories/<run-id>-user-stories-assessment.md

Next command: /factory-design-pass <run-id>
```

Do NOT auto-execute `/factory-design-pass`.

---

## Hard rules

- Stage gate enforced — halt if requirements-analyst not complete.
- story-writer ALWAYS runs in Product Pass — no scope/complexity gate.
- Approval gate pauses; never auto-approve.
- audit.md append-only; orchestrator-owned.
- Do NOT proceed to `/factory-design-pass` without explicit user approval.
- Both passes of story-writer must complete before approval gate opens.
