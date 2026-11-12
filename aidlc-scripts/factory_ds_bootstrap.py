#!/usr/bin/env python3
"""factory_ds_bootstrap.py — Bootstrap or import a design system.

Subcommands:
  init      Create design-system/ from scratch with sensible defaults.
  import    Import an external design system and rebuild our representation.

Usage:
    python3 aidlc-scripts/factory_ds_bootstrap.py init
    python3 aidlc-scripts/factory_ds_bootstrap.py init --force --dry-run
    python3 aidlc-scripts/factory_ds_bootstrap.py import --source material.json
    python3 aidlc-scripts/factory_ds_bootstrap.py import --source stitch/DESIGN.md --format stitch
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).parent
REPO_ROOT_DEFAULT = _SCRIPT_DIR.parent
DS_DIR = "design-system"

# ── Default token content ─────────────────────────────────────────────────

SPACING_MD = """# Spacing Tokens

Allowed spacing values for padding, margin, and gap.
Any value not in this set MUST be snapped to the nearest canonical value.

## Scale

| Token | Pixels | Used for |
|-------|--------|----------|
| `spacing.xs` | 4 | Compact UI, icon spacing, nested padding |
| `spacing.sm` | 8 | Tight layouts, button padding, inline gaps |
| `spacing.md` | 12 | Standard padding, card content, form fields |
| `spacing.lg` | 16 | Section spacing, modal padding, list gaps |
| `spacing.xl` | 24 | Page sections, card groups, form sections |
| `spacing.xxl` | 32 | Page margins, hero areas, major sections |

## Snap rules

| If value is | Snap to |
|-------------|---------|
| 0-6 | 4 (xs) |
| 7-10 | 8 (sm) |
| 11-14 | 12 (md) |
| 15-20 | 16 (lg) |
| 21-28 | 24 (xl) |
| 29+ | 32 (xxl) |
"""

RADIUS_MD = """# Radius Tokens

Allowed border-radius values.

## Scale

| Token | Pixels | Used for |
|-------|--------|----------|
| `radius.none` | 0 | No rounding, sharp edges |
| `radius.sm` | 3 | Buttons, inputs, small elements |
| `radius.md` | 6 | Cards, modals, larger containers |
| `radius.lg` | 12 | Dialogs, sheets, prominent surfaces |
| `radius.full` | 9999 | Pills, badges, circular elements |

## Snap rules

| Found value | Snap to |
|-------------|---------|
| 0-1px | 0 (`radius.none`) |
| 2-4px | 3px (`radius.sm`) |
| 5-9px | 6px (`radius.md`) |
| 10-16px | 12px (`radius.lg`) |
| 17+px | 9999px (`radius.full`) |
"""

TYPOGRAPHY_MD = """# Typography Tokens

Allowed font sizes, weights, and line heights.

## Font sizes

| Token | Pixels | Used for |
|-------|--------|----------|
| `font-size.caption` | 12 | Labels, captions, helper text |
| `font-size.body` | 14 | Body text, paragraphs |
| `font-size.body-large` | 16 | Larger body text, descriptions |
| `font-size.h4` | 20 | Section headings |
| `font-size.h3` | 24 | Page subheadings |
| `font-size.h2` | 32 | Major headings |
| `font-size.h1` | 40 | Page titles, hero text |

## Font weights

| Token | Value | Used for |
|-------|-------|----------|
| `font-weight.regular` | 400 | Body text |
| `font-weight.medium` | 500 | Emphasized text |
| `font-weight.semibold` | 600 | Subheadings |
| `font-weight.bold` | 700 | Headings |

## Line heights

| Token | Value | Used for |
|-------|-------|----------|
| `line-height.tight` | 1.2 | Headings |
| `line-height.normal` | 1.5 | Body text |
| `line-height.relaxed` | 1.75 | Long-form reading |

## Snap rules

| Found size | Snap to |
|------------|---------|
| 11-13px | 12px (`font-size.caption`) |
| 13-15px | 14px (`font-size.body`) |
| 15-18px | 16px (`font-size.body-large`) |
| 19-22px | 20px (`font-size.h4`) |
| 23-28px | 24px (`font-size.h3`) |
| 29-36px | 32px (`font-size.h2`) |
| 37+px | 40px (`font-size.h1`) |
"""

COLOR_MD = """# Color Tokens

Semantic color tokens. Always reference these — never use raw hex values.

## Brand

| Token | Hex | Used for |
|-------|-----|----------|
| `color.brand.primary` | #2563EB | Primary buttons, links, active states |
| `color.brand.primary-hover` | #1D4ED8 | Primary button hover |
| `color.brand.secondary` | #6366F1 | Secondary accents |
| `color.brand.secondary-hover` | #4F46E5 | Secondary accent hover |

## Neutral

| Token | Hex | Used for |
|-------|-----|----------|
| `color.neutral.bg` | #FFFFFF | Page backgrounds, surfaces |
| `color.neutral.surface` | #F9FAFB | Card/panel backgrounds |
| `color.neutral.border` | #E5E7EB | Borders, dividers |
| `color.neutral.text-primary` | #111827 | Primary text, headings |
| `color.neutral.text-secondary` | #6B7280 | Secondary text, labels |
| `color.neutral.text-disabled` | #9CA3AF | Disabled text |
| `color.neutral.icon` | #6B7280 | UI icons |

## Semantic

| Token | Hex | Used for |
|-------|-----|----------|
| `color.semantic.success` | #10B981 | Success states, positive feedback |
| `color.semantic.warning` | #F59E0B | Warning states, caution |
| `color.semantic.danger` | #EF4444 | Errors, destructive actions |
| `color.semantic.info` | #3B82F6 | Informational states |
| `color.semantic.danger-bg` | #FEF2F2 | Error background, alert surfaces |
| `color.semantic.success-bg` | #F0FDF4 | Success background |

## Overlay

| Token | Value | Used for |
|-------|-------|----------|
| `color.overlay.dark` | rgba(0,0,0,0.5) | Modal backdrops |
| `color.overlay.light` | rgba(0,0,0,0.08) | Hover states, focus rings |

## Snap rules

| If raw hex matches | Replace with |
|--------------------|--------------|
| #1D4ED8, #1E40AF, any blue-700+ | `color.brand.primary` |
| #EF4444, #DC2626, #B91C1C | `color.semantic.danger` or `color.semantic.danger-bg` |
| #10B981, #059669, #047857 | `color.semantic.success` |
| #F59E0B, #D97706 | `color.semantic.warning` |
| #111827, #1F2937, #374151 | `color.neutral.text-primary` |
| #6B7280, #9CA3AF | `color.neutral.text-secondary` |
"""

ELEVATION_MD = """# Elevation Tokens

Allowed shadow and z-index values.

## Shadow scale

| Token | Value | Used for |
|-------|-------|----------|
| `elevation.none` | none | Flat surfaces |
| `elevation.sm` | `0 1px 2px rgba(0,0,0,0.05)` | Cards, subtle elevation |
| `elevation.md` | `0 4px 6px -1px rgba(0,0,0,0.1)` | Dropdowns, popovers |
| `elevation.lg` | `0 10px 15px -3px rgba(0,0,0,0.1)` | Modals, dialogs |
| `elevation.xl` | `0 20px 25px -5px rgba(0,0,0,0.15)` | Top-level overlays, toasts |

## Z-index scale

| Token | Value | Used for |
|-------|-------|----------|
| `z.base` | 1 | Sticky elements |
| `z.dropdown` | 10 | Dropdowns, popovers |
| `z.sticky` | 50 | Sticky headers |
| `z.modal` | 100 | Modal backdrops |
| `z.modal-content` | 110 | Modal content |
| `z.toast` | 200 | Toasts, notifications |

## Snap rules

| If shadow resembles | Snap to |
|--------------------|---------|
| 0-2px blur, any color | `elevation.sm` |
| 3-6px blur, any color | `elevation.md` |
| 7-15px blur, any color | `elevation.lg` |
| 16+ px blur, any color | `elevation.xl` |
"""

INDEX_MD = """# Design System Index

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
| Figma | `figma/` dir or `*.figma.json` | `harness_adapters/source/figma.py` | >10 errs → extract text+inputs only |
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
"""

PATTERNS: dict[str, str] = {
    "form-layout.md": """# Pattern: Form Layout

Composition of Stack + Input + Button + Text for data entry forms.

## Structure

```
Stack (gap="lg")
  ├── Text (variant="h3")          -- Form title
  ├── Stack (gap="md")             -- Fields group
  │   ├── Input (label="Field 1")
  │   ├── Input (label="Field 2")
  │   └── ...
  ├── Inline (gap="sm")            -- Actions row
  │   ├── Button (variant="primary", label="Submit")
  │   └── Button (variant="ghost", label="Cancel")
```

## Rules
- Max 8 fields per form section (split into sections beyond that)
- Use `gap="md"` between fields, `gap="lg"` between sections
- Submit button right-aligned, Cancel left of Submit
""",
    "navigation.md": """# Pattern: Navigation

Composition of Inline + Button + Icon for toolbars and nav bars.

## Structure

```
Inline (gap="sm", align="center")
  ├── Icon (name="logo")           -- Brand
  ├── Button (variant="ghost", label="Item 1")
  ├── Button (variant="ghost", label="Item 2")
  ├── Spacer                       -- Push to right
  └── Button (variant="primary", label="Action")
```

## Rules
- Max 5 primary nav items (overflow into a menu)
- Active item uses `variant="secondary"` or underline
- Logo always leftmost
""",
    "modal-dialog.md": """# Pattern: Modal Dialog

Composition of Surface + Stack + Button + Text for overlay dialogs.

## Structure

```
Surface (radius="lg", elevation="xl")
  ├── Stack (gap="md", padding="lg")
  │   ├── Inline (gap="sm")        -- Header
  │   │   ├── Text (variant="h3")  -- Title
  │   │   └── Button (variant="ghost", icon="close")
  │   ├── Text (variant="body")    -- Content area
  │   └── Inline (gap="sm")        -- Footer
  │       ├── Button (variant="primary", label="Confirm")
  │       └── Button (variant="ghost", label="Cancel")
```

## Rules
- Surface gets `radius="lg"` (12px) + `elevation.xl`
- Backdrop uses `color.overlay.dark`
- Focus trap inside modal
- Close on Escape key + backdrop click
""",
}


def _write(repo_root: Path, rel_path: str, content: str,
           dry_run: bool, force: bool, log: list[str]) -> bool:
    """Write a file. Returns True if written, False if skipped."""
    path = repo_root / rel_path
    if path.exists() and not force:
        log.append(f"  SKIP {rel_path} (exists, use --force to overwrite)")
        return False
    if dry_run:
        log.append(f"  [DRY-RUN] Would write {rel_path}")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    log.append(f"  WRITE {rel_path}")
    return True


# ── Init ─────────────────────────────────────────────────────────────────

TOKEN_FILES = {
    "design-system/tokens/spacing.md": SPACING_MD,
    "design-system/tokens/radius.md": RADIUS_MD,
    "design-system/tokens/typography.md": TYPOGRAPHY_MD,
    "design-system/tokens/color.md": COLOR_MD,
    "design-system/tokens/elevation.md": ELEVATION_MD,
}

PATTERN_FILES = {f"design-system/patterns/{k}": v for k, v in PATTERNS.items()}


def cmd_init(repo_root: Path, force: bool, dry_run: bool) -> int:
    log: list[str] = []
    log.append(f"[Bootstrap] Initializing design system at {repo_root / DS_DIR}")

    # 1. Token files
    log.append("  Tokens:")
    written = 0
    for rel, content in TOKEN_FILES.items():
        if _write(repo_root, rel, content, dry_run, force, log):
            written += 1

    # 2. INDEX.md
    log.append("  Index:")
    _write(repo_root, "design-system/INDEX.md", INDEX_MD, dry_run, force, log)

    # 3. Patterns
    log.append("  Patterns:")
    for rel, content in PATTERN_FILES.items():
        _write(repo_root, rel, content, dry_run, force, log)

    # 4. Anti-patterns placeholder (link to existing)
    log.append("  Anti-patterns:")
    _write(repo_root, "design-system/anti-patterns/.gitkeep",
           "", dry_run, force, log)

    for line in log:
        print(line)

    # 5. Generate primitives via factory_primitive_gen.py
    DEFAULT_PRIMITIVES = ["Button", "Stack", "Input", "Text", "Box", "Icon", "Inline", "Surface"]

    ds_primitives = repo_root / DS_DIR / "primitives"
    if not dry_run:
        ds_primitives.mkdir(parents=True, exist_ok=True)
        for p in DEFAULT_PRIMITIVES:
            (ds_primitives / p).mkdir(exist_ok=True)
        print(f"\n[Bootstrap] Primitive stubs: {', '.join(DEFAULT_PRIMITIVES)}")

        prim_gen = _SCRIPT_DIR / "factory_primitive_gen.py"
        if prim_gen.exists():
            print(f"[Bootstrap] Generating primitive documentation...")
            result = subprocess.run(
                [sys.executable, str(prim_gen), "--ds-path", str(ds_primitives),
                 "generate", "--all-missing", "--force"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    print(f"  {line}")
            else:
                print(f"  WARN: primitive gen failed: {result.stderr.strip()}")
        else:
            print(f"  WARN: factory_primitive_gen.py not found at {prim_gen}")
    else:
        ds_primitives = repo_root / DS_DIR / "primitives"
        print(f"\n  [DRY-RUN] Would run: factory_primitive_gen.py --ds-path {ds_primitives} generate --all-missing")

    print(f"\n[Bootstrap] Done. {written} token files written.")
    return 0


# ── Import ───────────────────────────────────────────────────────────────

def _detect_format(source_path: Path) -> str:
    ext = source_path.suffix.lower()
    if ext == ".json":
        return "json"
    if ext == ".md":
        return "stitch"
    return "json"


def _parse_json_tokens(data: dict) -> dict[str, Any]:
    """Parse tokens from a JSON object. Expects keys: spacing, radius, etc."""
    tokens: dict[str, Any] = {}

    raw_spacing = data.get("spacing", {})
    if isinstance(raw_spacing, dict):
        tokens["spacing"] = {k: int(v) for k, v in raw_spacing.items()}
    elif isinstance(raw_spacing, list):
        names = ["xs", "sm", "md", "lg", "xl", "xxl"]
        tokens["spacing"] = {
            names[i] if i < len(names) else f"v{i}": int(v)
            for i, v in enumerate(raw_spacing)
        }

    raw_radius = data.get("radius", {})
    if isinstance(raw_radius, dict):
        tokens["radius"] = {k: int(v) for k, v in raw_radius.items()}
    elif isinstance(raw_radius, list):
        names = ["none", "sm", "md", "lg", "full"]
        tokens["radius"] = {
            names[i] if i < len(names) else f"v{i}": int(v)
            for i, v in enumerate(raw_radius)
        }

    raw_typography = data.get("typography", data.get("fontSizes", {}))
    if isinstance(raw_typography, dict):
        tokens["typography"] = {}
        for k, v in raw_typography.items():
            if isinstance(v, dict):
                tokens["typography"][k] = v
            else:
                tokens["typography"][k] = {"size": int(v)}

    raw_color = data.get("color", data.get("colors", {}))
    if isinstance(raw_color, dict):
        tokens["color"] = {k: str(v) for k, v in raw_color.items()}

    raw_elevation = data.get("elevation", data.get("shadows", {}))
    if isinstance(raw_elevation, dict):
        tokens["elevation"] = {}
        for k, v in raw_elevation.items():
            if isinstance(v, dict):
                tokens["elevation"][k] = v
            else:
                tokens["elevation"][k] = {"shadow": str(v), "zIndex": 1}

    return tokens


def _parse_material_tokens(data: dict) -> dict[str, Any]:
    """Parse Material Design token schema to our format."""
    tokens: dict[str, Any] = {}

    md_spacing = data.get("spacing", [4, 8, 12, 16, 24, 32, 40, 48])
    md_names = ["xs", "sm", "md", "lg", "xl", "xxl", "xxxl", "xxxxl"]
    tokens["spacing"] = {
        md_names[i] if i < len(md_names) else f"v{i}": int(v)
        for i, v in enumerate(md_spacing[:8])
    }

    md_radius = data.get("shape", {}).get("borderRadius", {})
    if isinstance(md_radius, dict):
        tokens["radius"] = {k: int(v) for k, v in md_radius.items()}
    else:
        tokens["radius"] = {"none": 0, "sm": 4, "md": 8, "lg": 16, "full": 9999}

    md_typescale = data.get("typescale", {})
    tokens["typography"] = {}
    for k, v in md_typescale.items():
        size = v.get("fontSize", 16) if isinstance(v, dict) else 16
        tokens["typography"][k] = {"size": int(size)}

    md_color = data.get("color", data.get("colors", {}))
    if isinstance(md_color, dict):
        tokens["color"] = {}
        for k, v in md_color.items():
            if isinstance(v, str) and v.startswith("#"):
                tokens["color"][k] = v

    return tokens


def _parse_stitch_designmd(content: str) -> dict[str, Any]:
    """Parse Stitch DESIGN.md format. Lines like | `token` | `value` | ... |"""
    tokens: dict[str, Any] = {
        "spacing": {}, "radius": {}, "typography": {}, "color": {}
    }
    for line in content.splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*`?([^`|\n]+)`?\s*\|", line)
        if not m:
            continue
        key = m.group(1).strip()
        val = m.group(2).strip().lstrip("`").rstrip("`")
        kl = key.lower()
        if any(k in kl for k in ("padding", "margin", "gap", "spacing")):
            tokens["spacing"][key] = _parse_val(val)
        elif any(k in kl for k in ("radius", "rounded", "corner")):
            tokens["radius"][key] = _parse_val(val)
        elif any(k in kl for k in ("font", "size", "typography", "type")):
            tokens["typography"][key] = {"size": _parse_val(val)}
        elif any(k in kl for k in ("color", "fill", "stroke", "background")):
            tokens["color"][key] = val
    return {k: v for k, v in tokens.items() if v}


def _parse_val(raw: str) -> int:
    m = re.search(r"(\d+)", raw)
    return int(m.group(1)) if m else 0


def _tokens_to_md(tokens: dict[str, Any]) -> dict[str, str]:
    """Convert parsed tokens back to markdown files."""
    files: dict[str, str] = {}

    if "spacing" in tokens and tokens["spacing"]:
        lines = ["# Spacing Tokens", "", "| Token | Pixels |", "|-------|--------|"]
        for name, val in tokens["spacing"].items():
            lines.append(f"| `spacing.{name}` | {val} |")
        lines.append("")
        files["design-system/tokens/spacing.md"] = "\n".join(lines) + "\n"

    if "radius" in tokens and tokens["radius"]:
        lines = ["# Radius Tokens", "", "| Token | Pixels |", "|-------|--------|"]
        for name, val in tokens["radius"].items():
            lines.append(f"| `radius.{name}` | {val} |")
        lines.append("")
        files["design-system/tokens/radius.md"] = "\n".join(lines) + "\n"

    if "typography" in tokens and tokens["typography"]:
        lines = ["# Typography Tokens", "", "| Token | Pixels |", "|-------|--------|"]
        for name, val in tokens["typography"].items():
            size = val.get("size", 16) if isinstance(val, dict) else val
            lines.append(f"| `{name}` | {size} |")
        lines.append("")
        files["design-system/tokens/typography.md"] = "\n".join(lines) + "\n"

    if "color" in tokens and tokens["color"]:
        lines = ["# Color Tokens", "", "| Token | Hex |", "|-------|-----|"]
        for name, val in tokens["color"].items():
            lines.append(f"| `{name}` | {val} |")
        lines.append("")
        files["design-system/tokens/color.md"] = "\n".join(lines) + "\n"

    if "elevation" in tokens and tokens["elevation"]:
        lines = ["# Elevation Tokens", "", "| Token | Value |", "|-------|-------|"]
        for name, val in tokens["elevation"].items():
            shadow = val.get("shadow", "none") if isinstance(val, dict) else str(val)
            lines.append(f"| `elevation.{name}` | {shadow} |")
        lines.append("")
        files["design-system/tokens/elevation.md"] = "\n".join(lines) + "\n"

    return files


def cmd_import(repo_root: Path, source: str, fmt: str | None,
               force: bool, dry_run: bool) -> int:
    source_path = Path(source)
    if not source_path.exists():
        print(f"ERROR: Source file not found: {source_path}", file=sys.stderr)
        return 1

    fmt = fmt or _detect_format(source_path)
    log: list[str] = []
    log.append(f"[Bootstrap] Importing design system from {source_path} (format: {fmt})")

    tokens: dict[str, Any] = {}

    if fmt == "json":
        data = json.loads(source_path.read_text(encoding="utf-8"))
        tokens = _parse_json_tokens(data)
    elif fmt == "material":
        data = json.loads(source_path.read_text(encoding="utf-8"))
        tokens = _parse_material_tokens(data)
    elif fmt == "stitch":
        content = source_path.read_text(encoding="utf-8")
        tokens = _parse_stitch_designmd(content)
    else:
        print(f"ERROR: Unknown format '{fmt}'. Use: json, material, stitch", file=sys.stderr)
        return 1

    if not tokens:
        print("ERROR: No tokens could be parsed from source", file=sys.stderr)
        return 1

    token_files = _tokens_to_md(tokens)
    for rel_path, content in token_files.items():
        _write(repo_root, rel_path, content, dry_run, force, log)

    # Regenerate INDEX.md with imported token values
    log.append("  Index:")
    imported_index = _build_imported_index(tokens, repo_root=repo_root)
    _write(repo_root, "design-system/INDEX.md", imported_index, dry_run, force, log)

    # Regenerate primitives
    ds_primitives = repo_root / DS_DIR / "primitives"
    if not dry_run:
        ds_primitives.mkdir(parents=True, exist_ok=True)
        prim_gen = _SCRIPT_DIR / "factory_primitive_gen.py"
        if prim_gen.exists():
            print(f"\n[Bootstrap] Regenerating primitives for imported tokens...")
            result = subprocess.run(
                [sys.executable, str(prim_gen), "--ds-path", str(ds_primitives),
                 "generate", "--all-missing", "--force"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    print(f"  {line}")
            else:
                print(f"  WARN: primitive gen failed: {result.stderr.strip()}")
    else:
        print(f"\n  [DRY-RUN] Would run: factory_primitive_gen.py --ds-path {ds_primitives} generate --all-missing")

    for line in log:
        print(line)

    print(f"\n[Bootstrap] Imported {len(token_files)} token files from {fmt}.")
    return 0


def _extract_primitive_description(design_md: Path) -> str:
    """Extract the first sentence from a primitive's design.md as description."""
    try:
        text = design_md.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", "-", "|", ">", "---")):
                # Take first ~80 chars as description
                desc = stripped.rstrip(".").strip()[:80]
                return desc + ("." if desc else "")
    except OSError:
        pass
    return "Auto-imported."


def _build_imported_index(tokens: dict[str, Any],
                          repo_root: Path | None = None) -> str:
    ds_dir = repo_root / DS_DIR if repo_root else None
    lines = ["# Design System Index", "",
             "Catalog of approved UI primitives, tokens, and composition patterns.",
             "Auto-generated from imported design system.", "",
             "---", "", "## Primitives", "",
             "| Primitive | Description | When to use | When NOT to use |",
             "|-----------|-------------|-------------|-----------------|"]

    # Read primitives from disk if available, otherwise use hardcoded defaults
    primitives_found = False
    if ds_dir:
        prim_dir = ds_dir / "primitives"
        if prim_dir.exists():
            prim_mds = sorted(prim_dir.glob("*/design.md"))
            for pm in prim_mds:
                name = pm.parent.name
                desc = _extract_primitive_description(pm)
                lines.append(f"| `{name}` | {desc} | Auto-imported | See `design.md` |")
                primitives_found = True

    if not primitives_found:
        lines.extend([
            "| `Button` | Action trigger, clickable | Forms, dialogs, toolbars | Navigation links, non-action text |",
            "| `Stack` | Vertical layout container | Arranging children top-to-bottom | Horizontal layouts (use `Inline`) |",
            "| `Inline` | Horizontal layout container | Arranging children left-to-right | Vertical layouts (use `Stack`) |",
            "| `Box` | Generic surface with padding + radius | Cards, panels, containers | Plain divs without styling |",
            "| `Input` | Text input field | Forms, search, data entry | Read-only display (use `Text`) |",
            "| `Text` | Typography element | Paragraphs, labels, headings | Interactive text |",
            "| `Surface` | Themed background container | Page sections, modals | Inline elements (use `Text`) |",
            "| `Icon` | SVG icon wrapper | Buttons, inputs, empty states | Decorative images |",
        ])

    # Read patterns from disk if available
    patterns_lines = []
    if ds_dir:
        pat_dir = ds_dir / "patterns"
        if pat_dir.exists():
            pat_mds = sorted(pat_dir.glob("*.md"))
            if pat_mds:
                patterns_lines.append("", "---", "", "## Patterns (compositions)", "",
                                      "| Pattern | Primitives used | When |",
                                      "|---------|----------------|------|")
                for pm in pat_mds:
                    name = pm.stem
                    content = pm.read_text(encoding="utf-8", errors="replace")
                    # Extract first table row with primitives info
                    for line in content.splitlines():
                        if line.startswith("|") and "`" in line:
                            patterns_lines.append(line)
                            break

    lines.extend(["", "---", "", "## Token categories", "",
                  "| Category | Values |",
                  "|----------|--------|"])

    if "spacing" in tokens:
        vals = ", ".join(str(v) for v in tokens["spacing"].values())
        lines.append(f"| Spacing | {vals} |")
    if "radius" in tokens:
        lines.append(f"| Radius | {len(tokens['radius'])} levels |")
    if "typography" in tokens:
        lines.append(f"| Typography | {len(tokens['typography'])} sizes |")
    if "color" in tokens:
        lines.append(f"| Color | {len(tokens['color'])} tokens |")
    if "elevation" in tokens:
        lines.append(f"| Elevation | {len(tokens['elevation'])} levels |")

    # Append patterns section if we found any
    if patterns_lines:
        lines.extend(patterns_lines)

    lines.extend(["", "---", "", "## Anti-patterns", "",
                  "See `anti-patterns/` for known bad patterns to avoid."])

    lines.extend(["", "---", "", "## Design sources", "",
                  "| Source | Detection | Snap adapter |",
                  "|--------|-----------|-------------|",
                  "| Figma | `figma/` dir or `*.figma.json` | `harness_adapters/source/figma.py` |",
                  "| Stitch | `stitch/` dir / `.stitch-project.json` / `*.stitch.json` | `harness_adapters/source/stitch.py` |",
                  "", "| Aspect | Figma | Stitch |",
                  "|--------|-------|--------|",
                  "| Input | Manual exports (JSON nodes) | AI-generated HTML/CSS from prompts |",
                  "| Token import | N/A (snapped inline) | `tokens/stitch-*.md` from DESIGN.md |",
                  "| MCP server | `figma-mcp` (npm) + Remote MCP | `@_davideast/stitch-mcp` (npm) |"])

    lines.extend(["", "---", "", "## Lifecycle", "",
                  "| Phase | Command |",
                  "|-------|---------|",
                  "| Bootstrap | `factory_token_bridge.py bootstrap` |",
                  "| Init | `factory_ds_bootstrap.py init` |",
                  "| Snap | `harness_adapters/source/{figma,stitch}.py` |",
                  "| Prepare | `factory_token_bridge.py prepare` |",
                  "| Resolve | `factory_design_system_resolve.py resolve <types>` |",
                  "| Update index | `factory_design_system_learn.py update-index` |"])

    lines.extend(["", "---", "", "## Companion skills", "",
                  "| Skill | Role |",
                  "|-------|------|",
                  "| `design-system-composer` | Compose from INDEX.md primitives; Figma archaeologist; Stitch DESIGN.md import |",
                  "| `ui-constraint-validator` | Post-generation token compliance scanner + autocorrect |",
                  "| `frontend-ui-engineering` | Generic frontend patterns (responsive, state, component arch) |"])

    lines.extend(["", "---", "", "## Contribution rules", "",
                  "| Who | Can do | Requires |",
                  "|-----|--------|----------|",
                  "| Any contributor | Add primitives | `design.md` + `anatomy.md` + `do-dont.md` (≥3 DON'T) + token-only values |",
                  "| Pipeline PR | Modify tokens | Update all `design.md` files referencing changed tokens |",
                  "| ship-agent only | Approve examples | Human approval in visual feedback loop |"])
    return "\n".join(lines) + "\n"


# ── CLI ─────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap or import a design system.",
    )
    parser.add_argument("--repo-root", type=str, default=str(REPO_ROOT_DEFAULT),
                        help="Repository root path")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing")

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create DS from scratch")

    import_parser = subparsers.add_parser("import", help="Import external DS")
    import_parser.add_argument("--source", type=str, required=True,
                               help="Source file path")
    import_parser.add_argument("--format", type=str, default=None,
                               choices=["json", "material", "stitch"],
                               help="Source format (auto-detected if omitted)")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.command == "init":
        return cmd_init(repo_root, force=args.force, dry_run=args.dry_run)
    elif args.command == "import":
        return cmd_import(repo_root, source=args.source, fmt=args.format,
                          force=args.force, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
