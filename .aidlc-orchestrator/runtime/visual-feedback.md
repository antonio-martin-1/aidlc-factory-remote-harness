# Visual Feedback Loop

PRIORITY: P3

Screenshot-based reinforcement that converges UI output toward what humans
actually approve. Run by `ship-agent` (FULL mode) or `build-test-agent`
(FAST mode) when Playwright/Chrome is available.

> **See also**: `factory_drift_detect.py` — the current drift detection tool.
> Provides `diff-structural` (always available) and `diff-visual` (Playwright-optional)
> modes, plus snapshot capture and baseline management.

---

## §1 Capture

After codegen and human approval:

1. Start a headless browser (Playwright or Chrome DevTools Protocol)
2. Navigate to the generated page/component
3. Capture screenshot → `design-system/screenshots/<component>/approved-<run-id>.png`
4. Extract JSX structure → map to primitives used
5. Extract CSS computed values → map to tokens

---

## §2 Drift detection

Compare the captured screenshot against the baseline in
`design-system/screenshots/<component>/` (if one exists):

| Check | Method |
|-------|--------|
| Spacing drift | Measure padding/margin of all elements, compare to tokens |
| Radius drift | Measure border-radius of all elements, compare to tokens |
| Color drift | Sample pixel colors at key positions, compare to tokens |
| Alignment drift | Measure element positions relative to parent |
| Size drift | Compare element dimensions to design.md constraints |

Drift is NOT a blocker — it's logged to `audit_entries[]` for awareness.
The system learns from drift over time.

---

## §3 Knowledge reinforcement

### On human approval

```
1. Extract JSX → token map → spacing map
2. Save as design-system/examples/<component>/approved-<run-id>.md
3. Run factory_design_system_resolve.py trim (enforce cap of 3)
4. Update INDEX.md usage count
5. Emit emitted_knowledge[] entry kind: pattern
```

### On human rejection

```
1. Capture rejection reason from user feedback
2. Save as design-system/anti-patterns/live/<issue-slug>.md
3. Include: what was generated, what was expected, what was wrong
4. Emit emitted_knowledge[] entry kind: antipattern
5. Linked to the component that failed
```

---

## §4 Example file format (approved)

```markdown
# Approved: Button/Primary variant

Run: 2026-05-21T10-30-00Z-auth
Component: Button
Variant: primary, size=md
Primitives used: Button, Inline, Text

## Token map
- Button: padding-x=spacing.lg(16px), padding-y=spacing.sm(8px)
- Button: border-radius=radius.sm(3px)
- Button: font-size=font-size.body(14px)
- Button: background=color.brand.primary(#2563EB)
- Inline: gap=spacing.sm(8px)

## Deviations corrected
None — fully compliant.

## Screenshot
screenshots/Button/approved-2026-05-21T10-30-00Z-auth.png
```

---

## §5 Prerequisites

The feedback loop is **optional** — it only runs when:

1. Playwright is installed (`npx playwright --version` succeeds)
   OR Chrome DevTools Protocol is available
2. The generated code includes at least one renderable page/component
3. `design_system_path` is set

If any prerequisite is missing: skip with a log entry, no block.
