# Design System Index

Catalog of approved UI primitives, tokens, and composition patterns.
The factory selects from this index — it does not invent new primitives.

---

## Primitives

| Primitive | Description | When to use | When NOT to use |
|-----------|-------------|-------------|-----------------|
| `Button` | Action trigger, clickable | Forms, dialogs, toolbars, any primary action | Navigation links (use `<a>`), non-action text |
| `Stack` | Vertical layout container | arranging children top-to-bottom with consistent gap | Horizontal layouts (use `Inline`), grid layouts |
| `Inline` | Horizontal layout container | Arranging children left-to-right with consistent gap | Vertical layouts (use `Stack`), wrapping lists |
| `Box` | Generic surface with padding + radius | Cards, panels, containers, any styled wrapper | Plain divs without styling (use raw `<div>`) |
| `Input` | Text input field | Forms, search, data entry | Read-only display (use `Text`), multi-line (use `<textarea>`) |
| `Text` | Typography element | Paragraphs, labels, headings, captions | Interactive text (use `Button` or `<a>`) |
| `Surface` | Themed background container | Page sections, modals, sidebars, banners | Inline elements (use `Text`) |
| `Icon` | SVG icon wrapper | Buttons, inputs, empty states, alerts | Decorative images (use `<img>`) |

---

## Patterns (compositions)

| Pattern | Primitives used | When |
|---------|----------------|------|
| `form-layout` | Stack + Input + Button + Text | Data entry forms |
| `data-table` | Surface + Text + Inline + Box | Tabular data display |
| `navigation` | Inline + Button + Icon | Toolbars, nav bars |
| `modal-dialog` | Surface + Stack + Button + Text | Overlay dialogs |
| `settings-page` | Stack + Surface + Input + Text | Configuration UIs |
| `card-grid` | Grid + Surface + Box + Text | Card layouts |

---

## Token categories

| Category | File | Quick ref |
|----------|------|-----------|
| Spacing | `tokens/spacing.md` | 4, 8, 12, 16, 24, 32 |
| Typography | `tokens/typography.md` | 12/14/16/20/24/32px |
| Radius | `tokens/radius.md` | sm=3, md=6, lg=12 |
| Color | `tokens/color.md` | brand/neutral/danger/success |
| Elevation | `tokens/elevation.md` | 0-4 shadow levels |

---

## Anti-patterns (what NOT to do)

See `anti-patterns/`. Quick list:
- `broken-spacing` — arbitrary padding/margin values outside token set
- `inconsistent-radius` — mixing different radii on similar elements
- `overflowing-content` — fixed heights without overflow handling
- `no-hierarchy` — same font-size for heading and body
- `giant-forms` — single-column forms > 8 fields without grouping

---

## Design sources

Graphical design data is **snapped** to token-compliant primitives before the composer uses it.

| Source | Detection | Snap adapter | Archaeologist |
|--------|-----------|-------------|---------------|
| Figma | `figma/` dir or `*.figma.json` | `harness_adapters/source/figma.py` | >10 errs → extract text+inputs only, rebuild from `patterns/` |
| Stitch | `stitch/` dir / `.stitch-project.json` / `*.stitch.json` | `harness_adapters/source/stitch.py` | Same fallback as Figma |

| Aspect | Figma | Stitch |
|--------|-------|--------|
| Input | Manual exports (JSON nodes) | AI-generated HTML/CSS from prompts |
| Token import | N/A (snapped inline) | `tokens/stitch-*.md` from DESIGN.md |
| MCP server | `figma-mcp` (npm) + Remote MCP | `@_davideast/stitch-mcp` (npm) |

---

## Lifecycle

| Phase | Command | Effect |
|-------|---------|--------|
| Bootstrap | `factory_token_bridge.py bootstrap` | Write default tokens + `tokens.css` (greenfield) |
| Init | `factory_ds_bootstrap.py init` | Full DS: tokens + INDEX.md + patterns + primitives |
| Brownfield extract | `factory_design_system_extract_brownfield.py extract` | Extract tokens from existing CSS/MUI/Tailwind |
| Snap | `harness_adapters/source/{figma,stitch}.py` | Convert raw design to token-compliant output |
| Prepare | `factory_token_bridge.py prepare` | Generate `tokens.css` + `token-prompt.md` + Tailwind config |
| Resolve | `factory_design_system_resolve.py resolve <types>` | Lazy-load only needed primitive docs |
| Update index | `factory_design_system_learn.py update-index` | Refresh usage stats after approval |

---

## Companion skills

| Skill | Role |
|-------|------|
| `design-system-composer` | Compose from INDEX.md primitives; Figma archaeologist; Stitch DESIGN.md import |
| `ui-constraint-validator` | Post-generation token compliance scanner + autocorrect |
| `frontend-ui-engineering` | Generic frontend patterns (responsive, state, component arch) |

---

## Contribution rules

| Who | Can do | Requires |
|-----|--------|----------|
| Any contributor | Add primitives | `design.md` + `anatomy.md` + `do-dont.md` (≥3 DON'T) + token-only values |
| Pipeline PR | Modify tokens | Update all `design.md` files referencing changed tokens |
| ship-agent only | Approve examples | Human approval in visual feedback loop |

---

## Usage stats (auto-updated by ship-agent)

| Primitive | Approved examples | Times used |
|-----------|------------------|------------|
| Button | 0 | 0 |
| Stack | 0 | 0 |
| Inline | 0 | 0 |
| Box | 0 | 0 |
| Input | 0 | 0 |
| Text | 0 | 0 |
| Surface | 0 | 0 |
| Icon | 0 | 0 |
