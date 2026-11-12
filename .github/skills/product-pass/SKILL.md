---
name: product-pass
description: Product discovery orchestrator for the Product Pass phase of AIDLC Inception. Produces product vision, personas, and user stories. Wraps requirements-intelligence and story-writing guidance into a single phase gate. Runs between /factory-spec and /factory-design-pass.
stages: [product-pass-agent]
---

**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# Product Pass Skill

Orchestrates the Product Pass phase: transforms requirements into a validated product vision, personas, and user stories. This skill is the single entry point for the product discovery phase.

## Why this skill exists

Requirements analysis (`/factory-spec`) captures WHAT users need at a functional level. Product Pass goes one level higher: WHO are the users, WHAT is the product vision, HOW do stories map to business value. Without this, architecture and design operate without a validated product model.

## Process (mandatory order)

### Step 1 — Validate prerequisites

Check that requirements-analyst is complete:
```bash
<aidlc-python> aidlc-scripts/stage_gate.py check <run-id> requirements-analyst
```
If not complete → HALT with: `[ProductPass] BLOCKED — requirements-analyst must complete before product-pass`.

### Step 2 — Product Vision synthesis

Read the requirements doc at `aidlc-docs/inception/requirements/<run-id>-requirements.md`.

Produce `aidlc-docs/inception/product-pass/<run-id>-product-vision.md` with:

```markdown
# Product Vision — <run-id>

## Problem Statement
<one paragraph — what problem does this solve, for whom>

## Product Goal
<measurable outcome — what does success look like in 6 months>

## Success Metrics
| Metric | Target | Measurement method |
|--------|--------|-------------------|

## Out of Scope
<explicit list of what this product does NOT do>

## Assumptions & Dependencies
<list — each assumption that could invalidate the product vision>
```

Emit: `[ProductPass] Product vision synthesised from requirements`.

### Step 3 — Load requirements-intelligence (plan-stage variant)

Load `.agents/custom-skills/requirements-intelligence/SKILL.md`.

Run the **plan-stage pre-mortem variant** on the product vision (not the requirements doc):
- Fire only `pre-mortem.md` on the product vision document.
- Generate ≤3 product risk questions targeting business/strategic failure modes.
- Append to `aidlc-docs/inception/product-pass/<run-id>-product-questions.md`.

Emit: `[ProductPass] pre-mortem fired on product vision — <N> risk questions generated`.

### Step 4 — Persona + story generation

Execute the story-writer stage per its agent instructions with these overrides:
- **Scope**: always run (no complexity gate in Product Pass).
- **Predecessor artifact**: product-vision.md + requirements.md (both).
- **Output paths** (standard story-writer paths):
  - `aidlc-docs/inception/user-stories/<run-id>-personas.md`
  - `aidlc-docs/inception/user-stories/<run-id>-stories.md`
  - `aidlc-docs/inception/user-stories/<run-id>-user-stories-assessment.md`

INVEST gate applies. All 6 criteria enforced.

### Step 5 — Phase gate validation

Before surfacing for approval, verify:

| Check | Command |
|-------|---------|
| Product vision exists | file present + non-empty |
| Risk questions exist | `product-questions.md` ≥ 1 question |
| Personas exist | `personas.md` ≥ 1 persona |
| Stories exist | `stories.md` ≥ 3 stories, all INVEST-compliant |

If any check fails → `status: blocked`. List failures verbatim.

### Step 6 — Skill compliance

`skill_compliance[]` MUST include:

```yaml
- skill: product-pass
  status: PASS
  evidence: "product-vision.md synthesised; pre-mortem: <N> risks; personas: <N>; stories: <N>; INVEST: all pass"
- skill: requirements-intelligence
  status: PASS
  evidence: "plan-stage pre-mortem variant; <N> risk questions"
```

## Verification (objective gates)

| Check | Verification |
|-------|-------------|
| Product vision present | File at expected path, non-empty |
| Pre-mortem executed | ≥1 `[ProductPass] pre-mortem` audit entry |
| INVEST compliant | Assessment doc lists all 6 columns passing |
| No chat questions | Zero `?` in chat reply outside artifact paths |

## Red Flags

- Product vision contradicts requirements → `status: needs_human`; list conflicts
- ≥5 INVEST failures → HALT; rewrite stories before proceeding
- Pre-mortem identifies unmitigated fatal risk → `status: needs_human`; surface risk explicitly
