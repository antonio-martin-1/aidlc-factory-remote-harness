---
name: ui-constraint-validator
description: Design token constraint enforcer V2. Validates generated UI against CSS Custom Properties. No hardcoded values — every visual property references a var() from tokens.css.
---

**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# UI Constraint Validator V2

## Overview

Post-generation validation that scans generated UI code and ensures every
visual property references a CSS Custom Property from the token set.
Unlike V1, this version:

- Validates against the actual `design-system/tokens/tokens.css` file (not hardcoded values)
- Works for any framework (the LLM generates framework-specific syntax)
- Snaps unknown values to the nearest CSS var automatically

---

## Step 1: Load the token set

Read the generated `tokens.css` file. Extract all CSS Custom Property names:
```bash
<aidlc-python> aidlc-scripts/factory_token_to_css.py inspect
```

The canonical CSS var prefixes are:
```
--spacing-*     → padding, margin, gap
--radius-*      → border-radius
--typography-*  → font-size
--color-*       → color, background, border-color
```

---

## Step 2: Scan generated files

For each generated UI file (`.tsx`, `.jsx`, `.html`, `.css`, `.dart`):

### 2a. Spacing validator

Search for:
- Inline `padding: <value>` with raw px values
- `margin: <value>`, `gap: <value>` with raw px
- Tailwind arbitrary values: `p-[<num>]`, `gap-[<num>]`
- Flutter `EdgeInsets.all(<num>)` where `<num>` doesn't match a token

❌ BAD: `padding: 13px` → ✅ GOOD: `padding: var(--spacing-md)`

### 2b. Radius validator

Search for `border-radius` with raw px values.

Snap rules (from tokens.css):

| Found | Snap to |
|-------|---------|
| 0-1px | `var(--radius-none)` |
| 2-4px | `var(--radius-sm)` |
| 5-9px | `var(--radius-md)` |
| 10-16px | `var(--radius-lg)` |
| 17+px | `var(--radius-full)` |

### 2c. Color validator

Search for raw hex values (`#2563EB`, `#F9FAFB`, etc.).

Build the snap table from the project's `design-system/tokens/color.md`.
Every raw hex should be replaced with `var(--color-*)`.

❌ BAD: `color: #2563EB` → ✅ GOOD: `color: var(--color-brand-primary)`

### 2d. Elevation validator

Search for `box-shadow` with raw values. Replace with elevation tokens
where applicable.

---

## Step 3: Apply corrections

For each deviation found:
1. Replace the raw value with the nearest `var(--*)` reference
2. Log to `ui_compliance[].deviations_corrected[]`

---

## Step 4: Gate

| Condition | Action |
|-----------|--------|
| 0 deviations | ✅ PASS |
| 1-3 deviations | ✅ PASS — autocorrected |
| >3 deviations per slice | 🛑 BLOCK — `status: needs_human` |

---

## Verification checklist

- [ ] No raw `padding: <N>px` — all use `var(--spacing-*)`
- [ ] No raw `border-radius: <N>px` — all use `var(--radius-*)`
- [ ] No raw hex colors — all use `var(--color-*)`
- [ ] No arbitrary Tailwind values (`p-[...]`)
- [ ] All corrections logged to `ui_compliance[]`
