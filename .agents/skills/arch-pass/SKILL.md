---
name: arch-pass
description: Architecture definition orchestrator for the Architecture Pass phase of AIDLC Inception. Validates the product + design models, then produces ADRs, tech-stack decisions, technical component map, and service interfaces. Two-pass with a human validation gate. Wraps ai-architecture-cookbook. Runs LAST in Inception, between /factory-design-pass and /factory-plan — the final Inception gate.
stages: [arch-pass-agent]
---

**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# Architecture Pass Skill

Orchestrates the Architecture Pass phase: validates the product vision + design, then translates them into concrete architectural decisions, ADRs, a validated tech stack, a technical component map, and service interfaces. Architecture runs **last** in Inception so it can reconcile WHAT (product) with the user-facing HOW (design) before committing technical decisions. This phase is the **final Inception gate** and sets `inception_complete=true`.

## Why this skill exists

Without a dedicated architecture phase placed AFTER product and design, tech-stack and pattern decisions get made implicitly during code generation — often inconsistently, and often contradicting the agreed UX. Architecture Pass makes these decisions explicit, documented, and reversible, and validates them against both prior passes before a single line of code is written.

## Two-pass with human validation gate

This stage is **two-pass**:

- **Pass 1** — validate product + design coherence and emit clarifying questions (`arch-questions.md`) → `status: needs_human`. The human validates findings and answers before any technical artifact is generated.
- **Pass 2** — after the human answers, generate the architecture artifacts.

Never generate Pass 2 artifacts without the Pass 1 human validation.

## Execution modes

This skill operates in one of two modes set by the orchestrator via `arch_mode` in the stage input:

| Mode | When | Behaviour |
|------|------|-----------|
| `greenfield` | New codebase, no prior tech stack | Define tech stack from scratch; ADRs capture initial decisions |
| `brownfield` | Existing codebase (RE artifacts present OR `has_legacy: true`) | Audit existing stack; ADRs capture evolution decisions (why we change / keep X) |

Read `arch_mode` from the input handoff before executing any step. Emit: `[ArchPass] Mode: <greenfield|brownfield>`.

---

## Process (mandatory order)

### Step 1 — Validate prerequisites

Check that product-pass AND design-pass are complete:
```bash
<aidlc-python> aidlc-scripts/stage_gate.py check <run-id> design-pass
<aidlc-python> aidlc-scripts/stage_gate.py check <run-id> product-pass
```
If not complete → HALT with: `[ArchPass] BLOCKED — product-pass and design-pass must complete before arch-pass`.

Read predecessor artifacts (always — product model):
- `aidlc-docs/inception/requirements/<run-id>-requirements.md`
- `aidlc-docs/inception/product-pass/<run-id>-product-vision.md`
- `aidlc-docs/inception/user-stories/<run-id>-personas.md`
- `aidlc-docs/inception/user-stories/<run-id>-stories.md`

Read predecessor artifacts (always — design model, to validate against):
- `aidlc-docs/inception/design-pass/<run-id>-ux-flows.md`
- `aidlc-docs/inception/design-pass/<run-id>-ui-component-inventory.md` (if present / UI project)
- `aidlc-docs/inception/design-pass/<run-id>-design-system-mapping.md` (if present / UI project)
- `aidlc-docs/inception/design-pass/<run-id>-application-design.md`

Read predecessor artifacts (brownfield only — if present):
- `aidlc-docs/inception/reverse-engineering/<run-id>-architecture.md`
- `aidlc-docs/inception/reverse-engineering/<run-id>-tech-stack.md`
- `aidlc-docs/inception/reverse-engineering/<run-id>-component-inventory.md`

Quote ≥1 line from each RE artifact read in `audit_entries[]`: `[ArchPass] RE read: <path> L<n>: "<quote>"`. If no RE artifacts → emit `[ArchPass] No RE artifacts — operating in greenfield mode`.

### Step 2 — Pass 1: Validate product + design, emit clarifying questions

Cross-check the product model against the design:
- Every story has a screen/flow in the design (re-verify the design's traceability).
- No UX flow implies a capability the product vision explicitly excludes.
- The design's "Open questions for Architecture Pass" section is collected.

Produce `aidlc-docs/inception/arch-pass/<run-id>-arch-questions.md`:

```markdown
# Architecture — Validation & Clarifying Questions — <run-id>

## Validation findings
| # | Type (gap / ambiguity / contradiction) | Between | Description | Suggested resolution |
|---|----------------------------------------|---------|-------------|----------------------|

## Clarifying questions (answer before architecture is generated)
<MCQ per question-format-guide — cover: tech-stack constraints, integration points,
 non-functional requirements (scale, latency, availability), compliance, data ownership/residency,
 and any design decision that forces an architectural trade-off>

## Design open questions carried forward
<from application-design.md "Open questions for Architecture Pass">
```

Set `status: needs_human`. **SURFACE the path to the user.** Wait for answers.

If no gaps and no open questions exist, still emit `arch-questions.md` with an explicit "No blocking questions — confirm to proceed" item so the human validates before Pass 2.

---

### Step 3 — Pass 2: Load ai-architecture-cookbook

(Executed only after the human answers Pass 1.)

Load `.agents/custom-skills/ai-architecture-cookbook/SKILL.md`.

Detect MCP availability per the cookbook Step 0 protocol.

Call `recommend_pattern_nl` with the product vision + design summary:
```
text: "<product goal> — <key UX flows> — <tech signals from requirements>"
format: "human"
include_trace: true
```

If `mode: "discovery"` → follow the cookbook's discovery flow (Step 3 of that skill).

Emit: `[ArchPass] Cookbook: <N> patterns recommended for domains: [<list>]`.

### Step 4 — Tech stack decision matrix

**Mode: greenfield** — define each layer choosing the best technology.

**Mode: brownfield** — for each layer, read the existing tech from RE artifacts and classify:

| Status | Meaning |
|--------|---------|
| `KEEP` | Existing tech stays — no change |
| `EVOLVE` | Existing tech upgraded/extended |
| `REPLACE` | Existing tech replaced — ADR required |
| `ADD` | New layer not previously present |

Produce `aidlc-docs/inception/arch-pass/<run-id>-tech-stack.md`:

```markdown
# Tech Stack — <run-id>

## Mode: <greenfield | brownfield>

## Decision Matrix

| Layer | Technology | Status [brownfield: KEEP/EVOLVE/REPLACE/ADD] | Rationale | Alternatives considered | Cookbook standard |
|-------|-----------|----------------------------------------------|-----------|------------------------|------------------|
| Frontend | | | | | |
| Backend | | | | | |
| Data | | | | | |
| Infrastructure | | | | | |
| Auth | | | | | |
| Observability | | | | | |

## Constraints honored
<list from requirements.md + arch-questions answers that constrain tech choices>

## Brownfield constraints [brownfield only]
<existing tech that CANNOT be changed (cost, contracts, team expertise)>
```

For each row, call `get_decision_tree` for the relevant cookbook domain.
Budget: ≤4 `get_decision_tree` calls for this step.

### Step 5 — ADR production

**Mode: greenfield** — ADR for each major decision with ≥2 alternatives.

**Mode: brownfield** — ADR required for every `REPLACE` or `EVOLVE` decision. `KEEP` decisions do NOT require an ADR unless a significant risk was identified. `ADD` decisions require an ADR only if ≥2 alternatives were considered.

Minimum ADRs:
- Greenfield: ≥3
- Brownfield: ≥1 per `REPLACE`, ≥1 per `EVOLVE` (capped at 6 max)

Produce ADRs in `aidlc-docs/inception/arch-pass/<run-id>-adrs.md`:

```markdown
## ADR-<N>: <decision title>

**Status**: Accepted  
**Date**: <ISO date>  
**Type**: <initial-decision | evolution | deprecation>  [brownfield: always one of these]
**Cookbook reference**: <standard-id or "N/A">

### Context
<why this decision was needed>
[brownfield: include "existing implementation" section describing what was there before]

### Decision
<what was decided>

### Consequences
- **Positive**: <benefits>
- **Negative**: <trade-offs accepted>
- **Risks**: <risks to monitor>
[brownfield: add **Migration impact**: <what needs to change in existing code>]

### Alternatives rejected
| Alternative | Reason for rejection |
|------------|---------------------|
```

### Step 6 — Architecture summary

Produce `aidlc-docs/inception/arch-pass/<run-id>-architecture-decisions.md`:

```markdown
# Architecture Decisions Summary — <run-id>

## Chosen patterns
<from cookbook recommendations — name each pattern + standard ID>

## Cross-cutting concerns
| Concern | Approach | ADR reference |
|---------|---------|---------------|
| Authentication | | |
| Authorization | | |
| Error handling | | |
| Logging & tracing | | |
| Data validation | | |
| Security | | |

## Scale assumptions
<inferred from personas + requirements + arch-questions answers — concurrent users, data volume>

## Compliance flags
<from requirements — GDPR, HIPAA, PCI-DSS, etc.>
```

### Step 7 — Technical component map

Produce `aidlc-docs/inception/arch-pass/<run-id>-component-map.md` — the **technical** component map (this moved here from Design Pass):

**Mode: greenfield** — build the complete inventory from scratch:

```markdown
# Component Map — <run-id>  [Mode: greenfield]

## Component Inventory
| Component | Type (service/module/library) | Owns | Depends on | Interface contract |
|-----------|-------------------------------|------|------------|--------------------|

## Dependency graph (ASCII)
<follow .aidlc-orchestrator/runtime/common/ascii-diagram-standards.md — NO circular dependencies>

## Boundary rules
<what each component does NOT do — as important as what it does>

## Design alignment
<map each technical component to the UI screens/flows it serves (from design-pass ux-flows + ui-component-inventory)>
```

**Mode: brownfield** — load the existing component baseline from the RE component inventory; every existing component MUST be classified, and the graph combines existing + delta:

```markdown
# Component Map — <run-id>  [Mode: brownfield]

## Existing components (from RE inventory)
| Component | Type | Status (UNCHANGED/MODIFIED/DEPRECATED) | Notes |
|-----------|------|----------------------------------------|-------|

## Delta components
| Component | Type | Change (NEW/MODIFIED/DEPRECATED) | Owns | Depends on | Interface contract | What changed |
|-----------|------|----------------------------------|------|------------|--------------------|--------------|

## Full dependency graph (ASCII) — existing + delta
<mark new (+), modified (~), deprecated (-); NO circular dependencies>

## Boundary rules
<what each component does NOT do>

## Design alignment
<map each technical component to the UI screens/flows it serves>
```

Every existing component from the RE inventory must be classified (UNCHANGED/MODIFIED/DEPRECATED) — an unclassified existing component → HALT. Every MODIFIED/DEPRECATED entry must say what changed / what replaces it. Each REPLACE ADR should map to a corresponding DEPRECATED + NEW component pair.

Detect circular dependencies with DFS before emitting (both modes). Any cycle → `status: needs_human`.

### Step 8 — Service interfaces

Produce `aidlc-docs/inception/arch-pass/<run-id>-service-interfaces.md` (this moved here from Design Pass):

```markdown
# Service Interfaces — <run-id>

## API contracts (summary)
| Endpoint / Method | Input | Output | Auth | Error codes |
|------------------|-------|--------|------|-------------|

## Event contracts (if event-driven)
| Event | Producer | Consumer | Schema |
|-------|---------|----------|--------|

## Data models (key entities)
| Entity | Fields | Validation rules | Storage layer |
|--------|--------|-----------------|---------------|
```

### Step 9 — Phase gate validation

| Check | Greenfield | Brownfield |
|-------|-----------|-----------|
| arch-questions human-validated | Pass 1 answered before Pass 2 | Same |
| Tech stack doc exists | All 6 layers filled | All 6 layers filled + Status column |
| ADRs produced | ≥3 | ≥1 per REPLACE, ≥1 per EVOLVE |
| Architecture summary exists | Patterns cited with standard IDs | Same + migration impact section |
| Component map exists | ≥2 components, acyclic dependency graph | Baseline + delta, acyclic |
| Service interfaces exist | ≥1 API or event contract | ≥1 new or modified contract |
| All stories covered | Every story served by ≥1 component | Same |
| Cookbook consulted | ≥1 `[ArchPass] Cookbook` audit entry | Same |
| RE artifacts quoted (brownfield) | N/A | ≥1 `[ArchPass] RE read` audit entry |

### Step 10 — Skill compliance

```yaml
- skill: arch-pass
  status: PASS
  evidence: "mode: <greenfield|brownfield>; questions validated; tech-stack: <N> layers; ADRs: <N> (<N> replace, <N> evolve); components: <N>; interfaces: <N>; patterns: <list>"
- skill: ai-architecture-cookbook
  status: PASS
  evidence: "recommend_pattern_nl called; <N> patterns; <N> get_decision_tree calls"
```

## Verification (objective gates)

| Check | Verification |
|-------|-------------|
| Pass 1 human-validated | arch-questions.md exists and was answered before Pass 2 |
| ADRs present | ≥3 in adrs.md |
| Tech stack filled | 6 layers, no empty cells |
| Component map acyclic | No cycle in component-map.md dependency graph |
| Service interfaces present | service-interfaces.md non-empty |
| Cookbook cited | Every pattern has a standard ID or explicit "N/A" |
| No fabricated standards | All cited IDs come from cookbook tool responses |

## Red Flags

- Product/design contradiction found but not surfaced in arch-questions.md → HALT; surface before Pass 2
- Cookbook returns conflicting patterns for same domain → `status: needs_human`; list conflict
- Requirements imply compliance (GDPR/HIPAA/PCI) but no compliance ADR exists → HALT; generate compliance ADR first
- Tech stack has no auth layer and product has user-facing flows → `status: needs_human`
- Circular dependency in component map → `status: needs_human`; flag the cycle
- A design screen/flow has no backing component or interface → `status: needs_human`; design coverage gap
- **Brownfield**: REPLACE decision with no migration impact in ADR → HALT; add migration impact before exiting
- **Brownfield**: >50% of layers are REPLACE → `status: needs_human`; high migration risk, flag explicitly
- **Brownfield**: Existing tech referenced in RE artifacts not mentioned in tech-stack matrix → HALT; all existing layers must appear
