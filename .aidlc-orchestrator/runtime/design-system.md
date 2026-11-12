# Design System — Orchestrator Integration

PRIORITY: P2

Reference doc for how the design system integrates with the AIDLC pipeline.

---

## §1 Directory layout

```
design-system/
  INDEX.md                    — Catalog of all primitives (auto-updated)
  tokens/                     — Global design tokens
    spacing.md, typography.md, radius.md, color.md, elevation.md
  primitives/<Component>/     — One dir per primitive
    design.md                 — Purpose, constraints, sizes, when-not-to-use
    anatomy.md                — Expected children, props, layout structure
    do-dont.md                — BAD vs GOOD examples
    <Component>.tsx           — Canonical reference implementation (optional)
    examples/                 — Approved usage examples (capped at 3)
  patterns/                   — Composition recipes (optional, on-demand)
  anti-patterns/              — Known bad patterns (optional, on-demand)
  screenshots/                — Visual baselines (optional, future)
```

---

## §2 How the pipeline loads the design system

Only the `code-generator` and reviewer stages interact with the design system.

### Load flow

```
project_profile.ui == true
  → project-profile.md sets design_system_path
  → code-generator input includes design_system_path
  → code-generator (design-system-composer skill + frontend-ui-engineering skill):
      1. Extracts needed component types from ui_intent[]
      2. Calls factory_design_system_resolve.py resolve <types>
      3. Loads ONLY returned files into context
      4. Never loads full directory
      5. Reads design-direction.md, applies unslop's nine passes, then impeccable detect
      6. A token-valid screen without that craft pass is not done
```

### When `design_system_path` is absent

If `design_system_path` is null or the directory doesn't exist:
- Log `[DesignSystem] NOT FOUND — UI will be generated without token enforcement`
- The `design-system-composer` falls back to inline token defaults; `frontend-ui-engineering` still runs with generic patterns:
  - Common sense spacing (4/8/12/16/24/32)
  - Common sense radius (3/6/12)
  - Standard font sizes (12/14/16/20/24/32)
  - No autocorrection, no constraint validation

---

## §3 Versioning

The design system is versioned by git — no separate version file.
Changes to `design-system/` are committed like any other source file.

When the design system changes:
- Old `examples/` remain valid (they're captured from real approvals)
- But snap rules may change (if tokens change, old examples may mismatch)
- The `trim` command handles cleanup

---

## §4 Contribution rules

Who can add primitives:
- Any contributor with a `design.md` + `anatomy.md`
- Must include `do-dont.md` with at least 3 DON'T examples
- Must reference only tokens from `tokens/` (no new values)
- Must have a reference implementation (`Component.tsx`) or be marked as `composition-only`

Who can modify tokens:
- Requires pipeline change (PR with contract updates)
- Token changes affect ALL primitives — must update all `design.md` files that reference changed tokens

Who can approve to `examples/`:
- Only the `ship-agent` via the visual feedback loop
- Human approval required before any example is saved

---

## §5 Google Stitch Integration

Google Stitch is a supported design source alongside Figma. Stitch generates
UI designs and frontend code from text prompts via Gemini 2.5 Pro. Its output
(HTML/CSS) is snapped to design system tokens before the LLM processes it.

### Detection

The pipeline detects Stitch data via:
- `stitch/` directory at repo root
- `.stitch-project.json` (created by Stitch MCP workspace persistence)
- `*.stitch.json` files anywhere in the workspace

### Pipeline integration

```
Stitch export (HTML / CSS / DESIGN.md)
    ↓
factory_stitch_snap.py snap-file --input stitch/export.html
    ↓
Token-snapped output → code-generator input (stitch_snapped_path)
    ↓
Design-system-composer skill (§8 Stitch integration)
    ↓
ui-constraint-validator (post-processing)
```

### DESIGN.md import

Stitch 2.0's DESIGN.md defines a project's visual design system. When present,
our pipeline imports these tokens into `design-system/tokens/stitch-*.md` via
`factory_stitch_snap.py snap-design`. These imported tokens are loaded alongside
native tokens by `factory_design_system_resolve.py`.

### MCP server

The pipeline can optionally use the Stitch MCP server
(`@_davideast/stitch-mcp`) to fetch designs programmatically:
- `get_screen_code` — fetch HTML code for a Stitch screen
- `get_screen_image` — fetch screenshot
- `build_site` — build full site from Stitch project
- `extract_design_context` — extract design tokens from screens

The MCP server is registered in the project's `.mcp.json` (or per-tool config)
and managed via `factory_stitch_mcp.py doctor|config`.

### When to use vs Figma

| Aspect | Figma | Stitch |
|--------|-------|--------|
| Input type | Manual design exports | AI-generated designs from prompts |
| Data format | Figma JSON nodes (coordinates, fills) | HTML/CSS, DESIGN.md |
| Snap target | `factory_design_system_snap.py` | `factory_stitch_snap.py` |
| Best for | Existing designs, pixel-perfect specs | Rapid ideation, prompt-to-UI |
| Archaeologist mode | Shared (same §7 fallback) | Shared (same §7 fallback) |
