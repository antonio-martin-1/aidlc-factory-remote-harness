**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# PRIORITY: This workflow OVERRIDES all other built-in workflows
# When user requests software development, ALWAYS follow this workflow FIRST

## Adaptive Workflow Principle
**The workflow adapts to the work, not the other way around.**
Assesses: user intent, codebase state, complexity, risk.

## Workspace-local runtime state

Before the first bookkeeping command, follow the workspace-local run state rules
in `.aidlc-orchestrator/runtime/common/python-runtime.md`. Keep the active run ID
in orchestration context and pass it to each command; scratch files belong to
the selected run's directory inside the workspace. Do not introduce external
temporary files or broaden directory permissions for runtime bookkeeping.

## MANDATORY: Auto-Commit on Approval ONLY
**CRITICAL**: Commits fire ONLY after an EXPLICIT user approval signal — never on stage completion alone, never on `status: complete` from an agent.

Approval signals are user messages containing: `approve`, `approved`, `go ahead`, `continue`, `next`, `lgtm`, `ship it`, `proceed`, or equivalent affirmative response to a `needs_human` gate. Silence or ambiguous responses are NOT approval.

When (and only when) an approval signal arrives:
```bash
git add -A && git commit -m "<type>(<scope>): <description>"
```
Types (Angular convention): `build` (build system/deps), `ci` (CI config/scripts), `docs` (documentation), `feat` (new feature), `fix` (bug fix), `perf` (performance), `refactor` (no fix/feat), `style` (formatting), `test` (tests).
Scope: command/stage in kebab-case (e.g. `requirements-analysis`, `workflow-planning`, `auth-unit`). If git fails, log warning and continue.

**Anti-pattern to reject**: committing on `status: complete` from an intermediate stage (e.g. `docs(story-writer): create user stories and personas` fired before the user has reviewed/approved the plan that consumes those stories). The plan-stage approval gate is the commit trigger — story-writer's output rides along inside that commit.

**Multi-stage commands**: `/factory-plan` may run story-writer → application-designer → workflow-planner → unit-decomposer internally. ONE commit fires at command boundary after the user approves the workflow-planner plan, covering everything in the working tree.

---

# INCEPTION PHASE
Purpose: WHAT to build. Stages: Workspace Detection → Reverse Engineering (cond) → Requirements Analysis → Product Pass → Design Pass → Architecture Pass → Workflow Planning (Context Pass) → Units Generation (cond).

**MANDATORY gate**: Product Pass, Design Pass, and Architecture Pass must ALL complete before Workflow Planning (Context Pass) and Construction are allowed.

**Pass ordering rationale**: Product defines WHAT and WHY (vision, personas, stories). Design defines the user-facing HOW (UX flows, information architecture, UI components) grounded in the product model. Architecture comes LAST so it can validate BOTH the product model and the design before committing technical decisions (tech stack, ADRs, service interfaces, technical component map). Architecture is the final Inception gate.

## Workspace Detection (ALWAYS) — `/factory-spec`
Classify workspace → detect greenfield/brownfield → scan tech stack → determine next phase.

## Reverse Engineering (CONDITIONAL — brownfield, no prior artifacts) — `/factory-spec`
Produce architecture docs, component inventory, API docs, tech stack from existing codebase.

## Requirements Analysis (ALWAYS — adaptive depth) — `/factory-spec`
Analyze → ask questions → produce requirements doc → wait for approval.

---

## 🟣 EXTENDED INCEPTION PASSES

The three passes below constitute the product discovery, design, and architecture definition phase. They run sequentially between Requirements Analysis and Workflow Planning in the order **Product → Design → Architecture**. None may be skipped when running the extended inception flow.

## Product Pass (ALWAYS in extended inception) — `/factory-product-pass`
Transform requirements into product model:
- Product vision document (goal, success metrics, out-of-scope)
- User personas (≥1, grounded in user answers)
- INVEST-compliant user stories (≥3, with acceptance criteria)
- Pre-mortem on product vision
Skills: `product-pass`, `requirements-intelligence`

## Design Pass (ALWAYS in extended inception) — `/factory-design-pass`
Define the user-facing design from the product model (NOT architecture — no endpoints, no data models, no tech decisions):
- UX flows with information architecture (navigation map, screen inventory, user journeys)
- UI component inventory (presentational components only — screens, widgets, visual hierarchy)
- Design system mapping (tokens / primitives, if UI)
- Design direction (character, world, moments, signature, accent — if UI)
- Consolidated application (UX) design with story → screen traceability
Reads: product vision + personas + stories. Does NOT read architecture (it runs before it).
Skills: `design-pass`, `design-system-composer` (if UI), `unslop` (if UI), `impeccable` (if UI)

## Architecture Pass (ALWAYS in extended inception — FINAL INCEPTION GATE) — `/factory-arch-pass`
Validate the product + design models, then define the technical architecture. **Two-pass**: emits clarifying architecture questions for human validation first, then generates artifacts:
- Architecture clarifying questions (Pass 1 → `needs_human` human validation gate)
- Tech stack decision matrix (6 layers)
- Architecture Decision Records (≥3 ADRs)
- Architecture summary with cookbook pattern references
- Technical component map (dependency graph, boundary rules, interface contracts)
- Service interfaces (endpoints, event contracts, data models)
Reads: product vision + personas + stories + ALL design-pass artifacts. Validates coherence of both prior passes.
Skills: `arch-pass`, `ai-architecture-cookbook`

---

## Workflow Planning / Context Pass (ALWAYS — after all passes complete) — `/factory-plan`
Plan phases → decompose tasks → produce execution plan → wait for approval.
**Gate**: refuses if product-pass, design-pass, or arch-pass not in `completed_stages[]`.

---

# 🟢 CONSTRUCTION PHASE
Purpose: HOW to build.

## Entry Checkpoint
Before first Construction stage: verify audit.md has all Inception entries, state file is correct.

## Per-unit loop
Plan → Construction Design (`write` once / `skip` thereafter) → Code Generation.
Shared Functional/NFR/Infra design docs are run-scoped; units 2..N hard-skip Sub-stage 2.
Code Gen: plan → implement (TDD thin slices) → self-review → wait for approval.
Build & Test: run build → affected tests (changed_files) → full suite at wave/Construction close → wait for approval.

## MANDATORY: Plan Completion Discipline
**Every task in the construction plan MUST be completed before the unit exits.**
The orchestrator validates this at the `sub_stage: generated` gate via
`factory_validate.py --strict`, which scans the plan file for remaining `[ ]`
checkboxes. Any unchecked item causes the unit to be marked `blocked` and
surfaced to the user. Do NOT proceed to the next unit or stage with incomplete
tasks — the gate will reject the unit. The earlier `sub_stage: plan` gate is
exempt: the plan is presented for approval with every box still unchecked.

---

# 🟡 OPERATIONS PHASE
Placeholder for deployment, monitoring, incident response.

## MANDATORY: State Tracking
- **Current Stage**: Update after EVERY stage completion. Never leave pointing to an earlier stage.
- **Stage Progress**: Mark `[x]` with date same interaction. MUST match audit.md.
- **Plan checkboxes**: Mark `[x]` same interaction as completion.
- Log all user input with ISO8601 in `audit.md`. Timestamps MUST be chronological.

Directory: `aidlc-docs/{inception,construction,operations}/`. App code stays in workspace root.

## MANDATORY: Traceability Contextualization

Every stage input handoff MUST include a `context_snapshot` built from traceability files. This prevents agents from working without awareness of prior decisions.

**Procedure:**
1. Before writing any stage input handoff, run:
   ```bash
   <aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth <depth>
   ```
2. Inject the output into the handoff YAML under `context_snapshot:` (or prepend as a comment block if the contract lacks this field).
3. Regenerate fresh for each stage — do NOT cache across stages.

**Depth mapping:**
- `minimal` (~200 tokens): `workspace-scout` — current stage + last 3 audit entries
- `standard` (~800 tokens): `requirements-analyst`, `story-writer`, `workflow-planner`, `application-designer`, `unit-decomposer`, `reviewer-*`
- `comprehensive` (~2000 tokens): `code-generator`, `build-test-agent`, `ship-agent`

**Manual inspection:**
```
/factory-context <run-id> [--depth minimal|standard|comprehensive]
```

<!-- AIDLC-ORCHESTRATOR-POINTER -->
## AIDLC Orchestrator (multi-agent factory mode)

This project ships with the AIDLC orchestrator. To run the multi-agent factory, use the `/factory-*` slash commands:

- `/factory-onboarding` — guided tour of the orchestrator system
- `/factory-code-tour` — guided human tour of any codebase: architecture, key flows, conventions
- `/factory-help [command]` — quick command reference
- `/factory-state <run-id>` — current stage, next step, budget, timeline
- `/factory-self <task>` — run the orchestrator on its own codebase
- `/factory-spec <feature>` — workspace scout + requirements analysis [Phase 0.0]
- `/factory-product-pass <run-id>` — product vision + personas + stories [Phase 0.1]
- `/factory-design-pass <run-id>` — UX flows + UI components + design-system mapping [Phase 0.2]
- `/factory-arch-pass <run-id>` — ADRs + tech stack + component map + service interfaces [Phase 0.3 — final inception gate, two-pass]
- `/factory-plan <run-id>` — workflow planning + unit decomposition (Context Pass) [requires all inception passes]
- `/factory-build <run-id>` — layer-parallel code generation with locks + AST checks
- `/factory-review <run-id>` — parallel reviewer pool (code, security, performance, simplifier)
- `/factory-ship <run-id>` — release notes, ADRs, CI/CD wiring, CHANGELOG, migration plan
- `/factory-resume <run-id>` — resume interrupted run (or adopt legacy `aidlc-docs/`)
- `/factory-replay <run-id> --from <stage>` — re-run from a specific stage

Roles, contracts, budgets, and parallelism rules: see `<tool-folder>/agents/orchestrator.md` (where `<tool-folder>` is whichever agentic coding tool is installed: `.claude`, `.opencode`, `.codex`, `.github`, or `.cursor`), `.aidlc-orchestrator/contracts/`, and `.aidlc-orchestrator/budgets/default.yaml`.
Design rationale and phase plan: `ORCHESTRATOR-PLAN.md` in the AIDLC source repo.
