---
name: design-system-composer
description: Design-system-driven UI composition (V2). Never invents primitives — selects from INDEX.md. Composes from Stack, Inline, Box, Button, Input, Text, Surface, Icon. Enforces CSS Custom Properties from tokens.css. Companion to frontend-ui-engineering (generic frontend patterns).
---

**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# Design System Composer

## Overview

You do NOT generate UI from scratch. You compose from approved primitives
listed in the design system INDEX.md. The design system is the single source
of truth for all visual output.

**Companion to `frontend-ui-engineering`**: That skill provides generic frontend
patterns (component architecture, responsive design, state management). This skill
provides design-system-specific composition: primitive selection, token enforcement,
and Figma resilience.

**Lazy loading**: You only load design system files for the components you need.
Use `input.token_bridge_artifacts[]` to get the `tokens.css` (CSS Custom Properties)
and `token-prompt.md` (usage guidelines). For primitive-specific files (design.md,
anatomy.md, do-dont.md), load them directly from `design-system/primitives/<name>/`
or call `factory_design_system_resolve.py resolve <components>` as fallback.

---

## Step 1: Determine needed component types

Read the input handoff. Extract which UI elements are needed from:
- `input.ui_intent[]` (if present) — explicit list of primitives
- The user request and functional design artifacts

Collect unique component types (e.g. `Button`, `Input`, `Stack`).

---

## Step 2: Load design system files (lazy)

Load the Token Bridge artifacts first:

1. **Read `input.token_bridge_artifacts[]`** — find the artifact with `type: "css"`
   and load the `tokens.css` file. This gives you the canonical CSS Custom Properties:
   `--spacing-*`, `--radius-*`, `--typography-*`, `--color-*`, `--elevation-*`.

2. **Load `token-prompt.md`** — from the artifact with `type: "prompt"`. This tells you
   how to use the tokens in code (e.g., `var(--spacing-md)` instead of `padding: 12px`).

3. **Load primitive specs** — for each component type needed, load files directly:
   ```
   design-system/primitives/<name>/design.md
   design-system/primitives/<name>/anatomy.md
   design-system/primitives/<name>/do-dont.md
   ```
   (Fallback: `<aidlc-python> aidlc-scripts/factory_design_system_resolve.py resolve <types>`)

Do NOT load primitives you don't need. Do NOT bulk-load.
Do NOT load `.tsx` reference implementations — the LLM generates framework-specific code.

---

## Step 3: Compose (never invent)

For each UI element needed:

1. **Check INDEX.md** — does a matching primitive exist?
   - YES → use it with token-compliant props
   - NO → check patterns/ for a composition recipe (call `resolve` with `--with-patterns`)
   - STILL NO → compose from existing primitives only

2. **Mapping rules**:
   - Any `<div>` with padding → `Box`
   - Any vertical group → `Stack`
   - Any horizontal group → `Inline`
   - Any button-like element → `Button` (never raw `<button>` unless token-compliant)
   - Any input → `Input` (never raw `<input>`)
   - Any text → `Text` (never raw `<p>`, `<span>`, `<h1>` directly)
   - Any themed container → `Surface`

3. **Resolve all visual properties through CSS Custom Properties**:
   - `padding`, `margin`, `gap` → `var(--spacing-*)` token
   - `border-radius` → `var(--radius-*)` token
   - `font-size` → `var(--typography-*)` token
   - `color`, `background-color` → `var(--color-*)` token
   - `box-shadow` → `var(--elevation-*)` token (where applicable)

4. **Never hardcode raw values**. Never use Tailwind arbitrary values
   (`px-[13px]`, `rounded-[5px]`, `gap-[7px]`).

---

## Step 4: Accessibility (mandatory)

| Requirement | Check |
|-------------|-------|
| `data-testid` | Every interactive element (Button, Input, link) |
| Focus ring | Every interactive element |
| `aria-label` | Icon-only buttons, inputs without visible labels |
| `aria-invalid` | Inputs in error state |
| `aria-describedby` | Inputs with error messages |
| Keyboard support | Enter/Space for buttons, Tab for inputs |
| Color contrast | Text meets WCAG 2.1 AA (4.5:1 normal, 3:1 large) |

---

## Step 5: Ban Figma Absolute Geometry

When data comes from Figma (directly or indirectly), apply these rules:

```
STRICT RULES:
- NEVER use position: absolute, top, left, right, bottom based on Figma coordinates
- ONLY EXCEPTION: tooltips, modals, popovers (intentionally floating elements)
- Instead of coordinates: reconstruct the visual flow with Stack (vertical) and Inline (horizontal)
- Ignore the designer's layer grouping — use reading order (top→bottom, left→right)
- If Figma does not use Auto Layout: treat each element as part of a sequential flow, not an absolute canvas
```

**Rationale**: Figma without Auto Layout produces floating XY coordinates.
Replicating them destroys responsiveness. Stack/Inline rebuild the correct flow.

---

## Step 6: Component Triage by Similarity

When Figma does not use official component instances, apply this algorithm:

```
TRIAGE ALGORITHM (preference order):
1. Is it an official instance?
   → The Figma node refers to a known component ID
   → Use the equivalent primitive without question

2. Does it behave like something known? (Heuristics)
   → Single-line text + contrasted background + small dimensions (< 60px height)
     → TREAT AS: Button (ignore raw vector)
   → Visible border + padding + vertical children
     → TREAT AS: Stack
   → Visible border + padding + horizontal children
     → TREAT AS: Inline
   → Input type + label + border
     → TREAT AS: Input (use anatomy.md, ignore raw Figma)
   → Long text + no background + no border
     → TREAT AS: Text (with appropriate variant)

3. Nothing matches?
   → Compose from existing primitives, ignore all custom styles
   → Use patterns/ as layout blueprint

4. DESTROY CUSTOM STYLES:
   → If the node uses CSS that does not exist in INDEX.md (e.g. border-radius: 7, padding: 11)
   → Force the nearest primitive with its correct tokens
   → Do NOT preserve the designer's "artistic" values if they are not in the token set
```

---

## Step 7: "Archaeologist" Mode (Fallback for Chaotic Figma)

If the Figma data is a tangle of layers with no recognizable structure:

```
WHEN TO ACTIVATE:
- Auto Layout absent in all nodes
- Overlapping coordinates (elements at the same XY)
- No recognizable component instances
- More than 50% of values need correction

PROTOCOL:
1. EXTRACT ONLY:
   - Visible text from each node
   - Required inputs (placeholders, types)
   - Reading order (ascending Y, then ascending X)

2. IGNORE COMPLETELY:
   - Absolute positions (top, left)
   - Container dimensions (width, height)
   - Specific colors
   - Paddings, margins, gaps
   - Borders, corner radii
   - Shadows, effects

3. GENERATE FROM SCRATCH using design-system/patterns/:
   - Select the pattern that best fits the extracted content
   - The pattern dictates the layout, not Figma
   - All visual values come from tokens/

4. PRIORITY: functionality over visual fidelity
   - Text and inputs are correct
   - Layout may differ from original Figma
   - The designer fixes the Figma, not the other way around
```

**This turns Figma into an "idea sketch" — the local system builds the real UI.**

---

## Step 8: Google Stitch Integration

When data comes from Google Stitch (directly or indirectly), apply these
additional rules:

```
STITCH RULES:
1. Stitch generates HTML/CSS as output — do NOT use Stitch's generated HTML
   directly. Extract the INTENT (layout, hierarchy, content) and
   rebuild with local primitives.

2. Value snapping: Stitch may generate raw styles (padding: 13px,
   border-radius: 5px). Run the StitchAdapter V2 to correct them:
   ```bash
   <aidlc-python> aidlc-scripts/harness_adapters/source/stitch.py --input stitch/export.html --output stitch/snapped.json
   ```

3. DESIGN.md: If Stitch exported a DESIGN.md, load the imported tokens
   from design-system/tokens/stitch-*.md as additional valid tokens.
   These tokens coexist with native ones — use the nearest token.

4. Do not trust Stitch code: Stitch generated HTML may use
   arbitrary classnames, non-semantic nested divs, and inline styles.
   Rebuild from scratch using the visual hierarchy as reference.

5. Intent priority over code:
   - Stitch TEXT and CONTENT is correct (reflects what the user asked for)
   - Stitch LAYOUT is a suggestion (rebuild with Stack/Inline)
   - Stitch CSS is suspect (always pass through snap + composer)
```

**Rationale**: Stitch is excellent for rapid ideation, but its technical output
does not follow our conventions for primitives, tokens, or accessibility. We
take the visual intent and discard the generated code.

---

## Step 9: Stitch DESIGN.md Import

When the pipeline detects a `stitch/DESIGN.md` (Stitch 2.0 design system
definition), load the imported tokens:

```
IMPORTED TOKENS:
- design-system/tokens/stitch-spacing.md    → Stitch spacing tokens
- design-system/tokens/stitch-radius.md     → Stitch radius tokens
- design-system/tokens/stitch-typography.md → Stitch typography tokens
- design-system/tokens/stitch-color.md      → Stitch color tokens

RULES:
1. Imported tokens are COMPLEMENTARY to native ones
2. If an imported token duplicates a native one (same value), use the native
3. If an imported token introduces a NEW value, it is available for use
4. NEVER use raw values from DESIGN.md without snapping (may be floats)
5. Prefer native tokens over imported ones when there is a conflict
```

**This allows Stitch projects to bring their visual identity without
compromising the local design system's consistency.**

---

## Verification (mandatory — BLOCKING if fails)

After code generation for each slice:

1. **Primitive audit**: Scan generated files for HTML elements that should be
   primitives (raw `<div>`, `<button>`, `<input>`, `<p>`, `<h1-6>` with styling).
   If found → flag as deviation.

2. **Token audit**: Search for hardcoded spacing, radius, font-size, color, shadow.
   If found → log each as a deviation in `ui_compliance[]`.

3. **data-testid audit**: Grep for all interactive elements, confirm each has
   `data-testid`. If missing → flag.

4. **Autocorrect**: Run `ui-constraint-validator` skill on all generated UI files.
   **Precondition:** `tokens.css` (from `token_bridge_artifacts`) must be present
   and non-empty. If missing, fall back to `design-system/tokens/tokens.css`.
   If still missing, the validator emits `status: blocked` — do NOT proceed
   with codegen until tokens are resolved. See
   `ui-constraint-validator/SKILL.md` § 2d for the hard-fail rule.

5. **Craft**: Run `unslop` on the generated screen, nine passes in order, against
   `aidlc-docs/inception/design-pass/<run-id>-design-direction.md`. If Accent
   status is `approved`, that hex is `color.brand.primary` for this run and is
   written into the token files before the passes. Components keep using the
   token. Then run `npx impeccable detect` when the CLI is available and fix
   the bans listed in the direction file. Do not run impeccable live, bolder,
   or overdrive. Do not build the unslop story video. A screen that only passes
   the token audit is not done.

6. **Log deviations**: Add to output `ui_compliance[]`:
   ```json
   {
     "element": "button.save-btn",
     "primitive_used": "Button",
     "token_compliance": true,
     "deviations_corrected": [
       { "property": "border-radius", "found": "4px", "corrected_to": "radius.sm (3px)" }
     ]
   }
   ```

---

## Common Rationalizations (REJECT these)

| Rationalization | Why it's rejected |
|----------------|-------------------|
| "This padding is slightly different, it's fine" | Every deviation breaks systemic consistency |
| "I'll use a raw div here, it's just a wrapper" | Use Box or Stack — that's what they're for |
| "The token doesn't have 13px, but 13px looks better" | The token set is the source of truth |
| "I'll add data-testid later" | It's a generation requirement, not optional |
| "This inline style is temporary" | There is no temporary — code lives forever |

---

## Red Flags

- More than 3 token deviations in a single slice → `status: needs_human`
- Any interactive element missing `data-testid` → `status: blocked`
- Raw HTML elements replacing primitives (e.g. raw `<button>` when `Button` exists) → flag
- Arbitrary Tailwind values (`px-[...]`, `rounded-[...]`) → autocorrect, flag if repeated
