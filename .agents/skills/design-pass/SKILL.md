---
name: design-pass
description: User-facing design orchestrator for the Design Pass phase of AIDLC Inception. Produces UX flows (with information architecture), UI component inventory, and design-system mapping from the product model. Wraps design-system-composer and application-designer into a phase gate. Runs between /factory-product-pass and /factory-arch-pass.
stages: [design-pass-agent]
---

**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# Design Pass Skill

Orchestrates the Design Pass phase: translates the product model (vision + personas + stories) into a concrete **user-facing design** — UX flows, information architecture, presentational UI components, and design-system integration. Design Pass runs **before** Architecture Pass so that the architecture can be validated against an agreed user experience.

## Scope boundary (critical)

Design Pass is **UX/UI only**. It decides how the product looks and how the user moves through it. It does **NOT** decide:

- ❌ endpoints / API contracts / event contracts
- ❌ data models / storage / schemas
- ❌ technical component map (service dependencies, interface contracts)
- ❌ tech stack / infrastructure

All of those are **Architecture Pass** artifacts (the next pass). If a design question forces a technical decision, record it as an open question for Architecture Pass — do NOT resolve it here.

## Why this skill exists

Product Pass decides WHAT to build and WHY. Design Pass decides the user-facing HOW — navigation, screens, interactions, states — grounded in the stories. Without it, architecture and construction guess at the user experience, producing UIs that don't match the product intent.

## Execution modes

This skill operates in one of two modes set by the orchestrator via `design_mode` in the stage input:

| Mode | When | Behaviour |
|------|------|-----------|
| `full` | Greenfield project | Build complete UX/UI design from scratch |
| `delta` | Brownfield project (existing UI from RE) | Load existing UI baseline → map unchanged screens/components → produce delta (new, modified, deprecated only) |

Read `design_mode` from the input handoff before executing any step. Emit: `[DesignPass] Mode: <full|delta>`.

---

## Process (mandatory order)

### Step 1 — Validate prerequisites

Check that product-pass is complete:
```bash
<aidlc-python> aidlc-scripts/stage_gate.py check <run-id> product-pass
```
If not complete → HALT with: `[DesignPass] BLOCKED — product-pass must complete before design-pass`.

Read predecessor artifacts (always — the product model):
- `aidlc-docs/inception/requirements/<run-id>-requirements.md`
- `aidlc-docs/inception/product-pass/<run-id>-product-vision.md`
- `aidlc-docs/inception/user-stories/<run-id>-stories.md`
- `aidlc-docs/inception/user-stories/<run-id>-personas.md`

Read predecessor artifacts (delta mode only — if present):
- `aidlc-docs/inception/reverse-engineering/<run-id>-component-inventory.md` → existing UI baseline
- `aidlc-docs/inception/reverse-engineering/<run-id>-architecture.md` → existing structure

**Mode: delta** — if RE component inventory present, parse the UI/presentational components into a baseline list. Emit: `[DesignPass] Baseline: <N> existing UI components loaded from RE inventory`. If absent → emit `[DesignPass] Delta mode but no RE inventory — inferring baseline from product stories` and derive baseline from the stories.

> Architecture artifacts do NOT exist yet at this stage (Architecture Pass runs after Design Pass). Do not attempt to read `aidlc-docs/inception/arch-pass/`.

### Step 2 — Design system probe (conditional)

If `manifest.project_profile.ui == true`:

1. Load `.agents/custom-skills/design-system-composer/SKILL.md`.
2. Check for design system at `design-system/INDEX.md`.
   - Exists → load it; emit `[DesignPass] Design system loaded: <N> primitives`.
   - Missing → emit `[DesignPass] No design system — UI composition will use generic primitives`.
3. Check for Figma/Stitch data via `manifest.project_profile.design_system_path`.
4. Load `.agents/custom-skills/unslop/SKILL.md` (Direction section only) and the `impeccable` skill (Modes section only). Do not edit UI. Do not run impeccable `init`, `document`, or `live`. Do not write `PRODUCT.md` or `DESIGN.md`. Do not render a story video. If impeccable is not installed, log `[Skill] MISSING: impeccable` and still write the direction using the four mode names below.

If `manifest.project_profile.ui == false` → skip design system; emit `[DesignPass] Non-UI project — design system probe skipped`. Produce only a lightweight `application-design.md` (functional UX description from stories) and skip ux-flows/ui-component-inventory/design-system-mapping/design-direction.

### Step 3 — User-facing design (two-pass, inline)

Execute `stage/application-designer.md` inline per the post-execution loop with these UX/UI overrides:

- **Predecessor artifacts**: product vision + personas + stories.
- **context_snapshot**: inject with `--depth standard`.
- **Skills required**: `[design-pass, design-system-composer (if ui), unslop (if ui), impeccable (if ui), using-agent-skills]`.

**Pass 1** — emit UX/UI design questions:
- Questions MUST cover: target users & devices, key user journeys & entry points, navigation & information architecture, screen inventory, interaction patterns, component states (empty / loading / error / success), accessibility expectations, content & tone, responsive behaviour, and (if a design system is present) which primitives/tokens to reuse.
- When `ui == true`, questions MUST also cover the visual direction Construction will paint from: surface mode (`Persuade`, `Operate`, `Read`, or `Experience`), character (two or three concrete words — `clean`, `modern`, `sleek`, `minimal`, and `premium` are not allowed), world (the material or place), moments (one or two places color is allowed), signature (one product-specific detail), and accent (a hex that replaces `color.brand.primary`, or `fallback` to keep the design-system token).
- Questions MUST NOT ask about endpoints, data models, storage, or tech stack — defer those to Architecture Pass.
- Output: `aidlc-docs/inception/design-pass/<run-id>-design-questions.md` with empty `[Answer]:` tags.
- Surface file path to user → user answers **in-place in that same file** → wait. **Single-file**: do NOT create a separate `*answered*` copy; Pass 2 keys off the same file once its `[Answer]:` tags are filled.

**Pass 2** — after user answers, produce:

#### 3a. UX Flows (with Information Architecture)
`aidlc-docs/inception/design-pass/<run-id>-ux-flows.md`:

```markdown
# UX Flows — <run-id>  [Mode: <full|delta>]

## Information Architecture
### Navigation map / sitemap (ASCII)
<screen hierarchy and how the user navigates between screens — follow ascii-diagram-standards.md>

### Screen inventory
| Screen | Purpose | Reached from | Primary persona |
|--------|---------|--------------|-----------------|

## Flow inventory
| Flow | Persona | Entry point | Steps | Exit state |
|------|---------|-------------|-------|------------|

## Critical paths
<3-5 most important user journeys, step by step>

## States & error treatment
<key empty/loading/error/success states and their UX treatment per screen>
```

**Delta mode**: mark screens/flows as NEW `(+)`, MODIFIED `(~)`, DEPRECATED `(-)`; every existing screen must be classified.

#### 3b. UI Component Inventory (if ui == true)
`aidlc-docs/inception/design-pass/<run-id>-ui-component-inventory.md` — **presentational components only**:

```markdown
# UI Component Inventory — <run-id>  [Mode: <full|delta>]

## Presentational components
| Component | Type (page/section/widget/control) | Used on screens | Design-system primitive | States |
|-----------|------------------------------------|-----------------|-------------------------|--------|

## Visual hierarchy (ASCII)
<screen → section → component nesting — NOT service dependencies>
```

> This is a **presentational** inventory (screens, sections, widgets, controls). Do NOT list services, depends-on relationships, or interface contracts — those belong to the technical component map in Architecture Pass.

#### 3c. Design System Mapping (if ui == true)
`aidlc-docs/inception/design-pass/<run-id>-design-system-mapping.md`:

```markdown
# Design System Mapping — <run-id>

## Component → primitive mapping
| UI component | design-system primitive | Tokens used | Gap (new primitive needed?) |
|--------------|-------------------------|-------------|-----------------------------|

## Token gaps
<values needed that are outside current tokens — flag with [DSTokenGap], do NOT mutate tokens without human approval>
```

If no design system exists, document the intended primitives/tokens to be created and emit `[DesignPass] No design system — documented intended primitives`.

#### 3d. Design direction (if ui == true)
`aidlc-docs/inception/design-pass/<run-id>-design-direction.md` — the brief code generation must follow. Write it from the answered questions. Do not invent a palette when the accent answer is empty or `fallback`.

```markdown
# Design Direction — <run-id>

## Direction
- Product:
- Character:
- World:
- Moments:
- Signature:

## Surface mode
<Persuade | Operate | Read | Experience>

## Accent
- Token: color.brand.primary
- Value: <#hex or the current design-system hex>
- Status: approved | fallback

## Bans
- No hue gradients on surfaces, gradient text, glows, emoji icons, "New" badges, uppercase tracked labels, or pulsing decoration.
- Chrome stays quiet. Color lives in Moments only.

## Construction rule
Code generation loads unslop and applies its nine passes inside these tokens. The impeccable detector must be clean of the bans above before a UI unit closes. Story video, live, bolder, and overdrive stay out of the pipeline unless the user asks.
```

Empty Character, World, or Moments → `status: needs_human`. Do not proceed to Architecture Pass on an empty direction.

**Delta mode**: when the existing UI has a real brand (a chosen color or typeface that is not a purple-to-blue gradient, glow, or sparkle), keep it. Set Accent status to `approved` with that brand hex. Derive Character and World from the product, not from a trend.

If `ui == false` → skip; emit `[DesignPass] Design direction skipped — non-UI project`.

#### 3e. Application (UX) Design Consolidation
`aidlc-docs/inception/design-pass/<run-id>-application-design.md`:

```markdown
# Application (UX) Design — <run-id>

## Design intent
<how this design realizes the product vision and serves each persona>

## Design decisions
| Decision | Rationale | Trade-off |
|----------|-----------|-----------|

## Open questions for Architecture Pass
<any design choice that implies a technical/architectural decision — hand off, do NOT resolve here>

## Construction (UX) readiness checklist
- [ ] All stories map to ≥1 screen
- [ ] All screens have defined states (empty/loading/error/success)
- [ ] Navigation / information architecture defined
- [ ] Design system primitives identified (if UI)
- [ ] Design direction written (if UI): character, world, moments, signature, accent status
- [ ] Accessibility expectations captured
```

### Step 4 — Story → screen traceability

For each user story in `stories.md`, identify which screen(s)/flow(s) deliver it.
Emit a traceability matrix appended to `application-design.md`:

```markdown
## Story → Screen Traceability
| Story ID | Story title | Screen(s) / Flow(s) | UI component(s) |
|----------|------------|---------------------|-----------------|
```

All stories must map to ≥1 screen/flow. Unmapped stories → HALT; assign before proceeding.

### Step 5 — Phase gate validation

| Check | Full mode | Delta mode |
|-------|-----------|-----------|
| UX flows exist | ≥1 critical path + IA/navigation map | Baseline + delta flows, full navigation map |
| UI component inventory (if UI) | ≥1 presentational component | Baseline + delta components |
| All stories traced | 100% → screen coverage | 100% → screen coverage (including UNCHANGED) |
| Application design exists | UX readiness checklist complete | Checklist + migration impact section |
| Design system mapping (if UI) | Component → primitive mapping present | Mapping for new/modified components |
| Design direction (if UI) | Product, Character, World, Moments, Signature, surface mode, accent status | Same; existing real brand kept |
| RE artifacts quoted (delta) | N/A | ≥1 `[DesignPass] Baseline` audit entry |
| No architecture leakage | No endpoints/data-models/service-map present | Same |

### Step 6 — Skill compliance

```yaml
- skill: design-pass
  status: PASS
  evidence: "mode: <full|delta>; UX flows: <N>; UI components: <N> (<N> new/<N> modified/<N> unchanged); stories traced: <N>/<total>"
- skill: design-system-composer
  status: "PASS | N/A"
  evidence: "<N> primitives loaded | non-UI project"
- skill: unslop
  status: "PASS | N/A"
  evidence: "design-direction.md written | non-UI project"
- skill: impeccable
  status: "PASS | N/A"
  evidence: "surface mode <mode> | MISSING — mode chosen without the skill"
```

## Verification (objective gates)

| Check | Verification |
|-------|-------------|
| No unmapped stories | Traceability matrix rows == stories count |
| Navigation map present | ASCII IA diagram in ux-flows.md |
| No architecture leakage | No service-interfaces.md / technical component-map.md emitted |
| UX readiness checklist | All items `[x]` or explicitly deferred with reason |

## Red Flags

- Story maps to 0 screens → HALT; must resolve before phase exit
- >30% stories map to a single "catch-all" screen → `status: needs_human`; likely missing decomposition
- Design specifies endpoints, data models, or service dependencies → STOP; strip them and hand off to Architecture Pass as an open question
- **Delta mode**: existing UI component from RE inventory not classified (UNCHANGED/MODIFIED/DEPRECATED) → HALT
- **Delta mode**: MODIFIED screen/component has no description of what changed → HALT
