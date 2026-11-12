# UI Compiler

PRIORITY: P2

The LLM generates **intent** using primitives and semantic tokens.
The "compiler" is the process the LLM follows — not a separate software component.
Snap pre-processing (`factory_design_system_snap.py`) cleans the input;
drift detection (`factory_drift_detect.py`) verifies the output.

Transforms semantic UI intent into token-compliant code. Runs as a
post-processing step in code-generator's TDD loop, applied after each
Green step.

---

## §1 The model generates intent, the compiler generates code

The LLM should never write arbitrary CSS or Tailwind arbitrary values.
Instead, the LLM writes **intent** using primitives and semantic tokens:

```
Intent (LLM writes)                  → Compiler → Token-compliant code

<Button variant="primary" size="md"> → <button class="btn btn--primary btn--md">
<Stack gap="lg">                     → <div class="stack stack--gap-lg">
<Box padding="md" radius="sm">       → <div class="box box--pad-md box--rad-sm">
<Text variant="h2">                  → <h2 class="text text--h2">
```

---

## §2 Compilation steps

Applied automatically by code-generator after each Green step:

### Step 1: Primitive resolution

Scan generated JSX/TSX for recognized primitives:
- `<Button>`, `<Stack>`, `<Inline>`, `<Box>`, `<Input>`, `<Text>`, `<Surface>`, `<Icon>`

Each primitive maps to a canonical HTML/CSS output defined in its `anatomy.md`.

### Step 2: Token resolution

For each prop that accepts a token value:
1. Look up the token value in the loaded `tokens/*.md` files
2. If the value matches a known token → use the token's CSS value
3. If the value is NOT a known token → run nearest-neighbor snap
4. If no reasonable snap exists → log deviation, use closest token

### Step 3: Style output

When a CSS-in-JS or utility framework is used:

| Framework | Output format |
|-----------|--------------|
| None (plain CSS) | Generate CSS class per anatomy.md with token values inlined |
| Tailwind | Use standard Tailwind classes (`p-3` for 12px, `rounded-sm` for 3px, etc.) |
| Styled Components | Generate styled component with token values |
| CSS Modules | Generate `.module.css` with token values |

When no framework is detected: compile to inline styles with token values
(not ideal, but ensures consistency).

---

## §3 Intent-first vs component-library mode

If the project already has a component library (MUI, Chakra, Ant, shadcn):

```
The compiler maps:
  <Button variant="primary" size="md" label="Save" />
    → <MuiButton variant="contained" size="medium">Save</MuiButton>
```

The mapping is read from `project-profile.md` → `tech_stack[]` and resolved
per-framework. When the framework is unknown, use the generic primitive output.

---

## §4 What the compiler does NOT do

- Does NOT change component logic or state management
- Does NOT modify tests
- Does NOT modify `data-testid` attributes
- Does NOT change component props structure (only visual token values)

---

## §5 Input Snapping — Figma Pre-processing

When data comes from Figma, `factory_design_system_snap.py` runs
**BEFORE** the LLM sees the data. This ensures Claude never receives chaotic
values (13.4px, colors without variables, absolute coordinates).

### Pipeline

```
Figma JSON raw
    ↓
factory_design_system_snap.py snap-file --input figma.json
    ↓
Clean JSON (tokens only, no raw values)
    ↓
LLM composes with primitives
    ↓
ui-constraint-validator (post-processing)
```

### What the snap does

| Raw Figma value | Resulting token | Method |
|----------------|------------------|--------|
| `padding: 13.4px` | `spacing.md` (12px) | Nearest-neighbor with Euclidean distance |
| `border-radius: 4.2px` | `radius.sm` (3px) | Nearest-neighbor, ±2px tolerance |
| `font-size: 15px` | `font-size.body` (14px) | Nearest-neighbor in set {12,14,16,20,24,32,40} |
| `color: #3c83f6` | `color.brand.primary` | Hex → known token map |
| `itemSpacing: 7` | `spacing.sm` (8px) | Spacing snap |

### When it runs

- Whenever `project_profile.ui == true` AND Figma data is present in the input
- Injected by `project-profile.md` as a step before the code-generator
- The script reports how many corrections it made — if >10, it suggests "Archaeologist" mode

---

## §6 Input Snapping — Google Stitch

Google Stitch generates UI designs as HTML/CSS from text prompts. Its
style values (padding, radius, colors, sizes) must be mapped to the
design system's canonical tokens before the LLM uses them for code generation.

### Pipeline

```
Stitch export HTML / CSS / DESIGN.md
    ↓
factory_stitch_snap.py snap-file --input stitch/export.html
    ↓
Clean JSON (tokens only, no raw values) + corrected HTML
    ↓
LLM composes with primitives
    ↓
ui-constraint-validator (post-processing)
```

### What the snap does

| Raw Stitch value | Resulting token | Method |
|-----------------|------------------|--------|
| `padding: 13px` | `spacing.md` (12px) | Nearest-neighbor |
| `border-radius: 5px` | `radius.sm` (3px) | Nearest-neighbor, ±2px tolerance |
| `font-size: 15px` | `font-size.body` (14px) | Nearest-neighbor in set {12,14,16,20,24,32,40} |
| `color: #3c83f6` | `color.brand.primary` | Hex → known token map |
| `gap: 7px` | `spacing.sm` (8px) | Spacing snap |

### Stitch DESIGN.md Import

Stitch 2.0 can export a `DESIGN.md` that defines the project's visual tokens.
The snap imports these tokens into `design-system/tokens/stitch-*.md`:

```
DESIGN.md token definitions
    ↓
factory_stitch_snap.py snap-design --input stitch/DESIGN.md
    ↓
design-system/tokens/stitch-spacing.md
design-system/tokens/stitch-radius.md
design-system/tokens/stitch-typography.md
design-system/tokens/stitch-color.md
```

These imported tokens coexist with the native tokens — the resolver loads them
alongside the other files in `tokens/`.

### When it runs

- Whenever `project_profile.ui == true` AND `has_stitch_data == true`
- Injected by `project-profile.md` as a step before the code-generator
- If `stitch/DESIGN.md` exists, it is automatically imported to tokens
- More than 10 corrections triggers `stitch_archaeologist_mode`
