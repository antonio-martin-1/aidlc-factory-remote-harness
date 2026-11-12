#!/usr/bin/env python3
"""factory_primitive_gen.py -- Generate primitive documentation from templates.

Subcommands:
  generate    Create design.md, anatomy.md, do-dont.md, examples/ for a primitive.
  list        List all primitives and their completeness status.
  template    Show the template that would be used for a given primitive+style.

Usage:
    python3 aidlc-scripts/factory_primitive_gen.py generate Stack
    python3 aidlc-scripts/factory_primitive_gen.py generate Input --style flutter
    python3 aidlc-scripts/factory_primitive_gen.py generate --all-missing
    python3 aidlc-scripts/factory_primitive_gen.py list
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_DS_PRIMITIVES_DEFAULT = Path(__file__).resolve().parent.parent / "design-system" / "primitives"
DS_PRIMITIVES = _DS_PRIMITIVES_DEFAULT

REQUIRED_FILES = {"design.md", "anatomy.md", "do-dont.md"}
OPTIONAL_DIRS = {"examples"}


# -- Template registry -----------------------------------------------------

def _t(primitive: str, style: str) -> dict[str, str]:
    """Return {filename: content} for a primitive+style combo."""
    p = primitive.lower()
    gen = _generator(p, style)
    return {
        "design.md": gen("design"),
        "anatomy.md": gen("anatomy"),
        "do-dont.md": gen("dodont"),
    }


def _generator(p: str, style: str):
    """Factory: returns a function that generates template content."""

    def _get(mode: str) -> str:
        if mode == "design":
            return _design_template(p, style)
        elif mode == "anatomy":
            return _anatomy_template(p, style)
        elif mode == "dodont":
            return _dodont_template(p, style)
        return ""

    return _get


# -- Design templates per primitive ----------------------------------------

_PRIMITIVE_META: dict[str, dict[str, Any]] = {
    "stack": {
        "title": "Stack",
        "description": "Vertical layout container. Arranges children top-to-bottom with consistent gap.",
        "category": "layout",
        "variants": [],
        "sizes": [],
        "props": [
            ("gap", "spacing token", "spacing.md", "Vertical gap between children"),
            ("align", "'start' | 'center' | 'end' | 'stretch'", "stretch", "Cross-axis alignment"),
            ("padding", "spacing token", "--", "Inner padding"),
            ("radius", "radius token", "--", "Container border radius"),
        ],
        "constraints": [
            ("Display", "flex, flex-direction: column"),
            ("Gap", "One of spacing.xs through spacing.xxl (never arbitrary)"),
            ("Width", "Defaults to 100% of parent"),
            ("Children", "Accepts multiple children, stacks vertically"),
        ],
        "no_when": [
            "Horizontal layouts -> use Inline",
            "Grid layouts -> use CSS Grid",
            "Single child -> just render the child directly",
        ],
    },
    "inline": {
        "title": "Inline",
        "description": "Horizontal layout container. Arranges children left-to-right with consistent gap and optional wrapping.",
        "category": "layout",
        "variants": [],
        "sizes": [],
        "props": [
            ("gap", "spacing token", "spacing.sm", "Horizontal gap between children"),
            ("align", "'start' | 'center' | 'end' | 'stretch'", "center", "Cross-axis alignment"),
            ("wrap", "boolean", "false", "Allow wrapping to next line"),
            ("padding", "spacing token", "--", "Inner padding"),
        ],
        "constraints": [
            ("Display", "flex, flex-direction: row"),
            ("Gap", "One of spacing.xs through spacing.xxl"),
            ("Wrap", "When true, children wrap to next line on overflow"),
            ("Width", "Defaults to auto (fits content)"),
        ],
        "no_when": [
            "Vertical layouts -> use Stack",
            "Single child -> no layout wrapper needed",
        ],
    },
    "box": {
        "title": "Box",
        "description": "Generic container with optional padding, border, and background. Lowest-level layout primitive.",
        "category": "layout",
        "variants": [],
        "sizes": [],
        "props": [
            ("padding", "spacing token", "--", "Inner padding"),
            ("radius", "radius token", "radius.none", "Border radius"),
            ("background", "color token", "--", "Background color"),
            ("border", "color token", "--", "Border color"),
            ("elevation", "elevation token", "--", "Box shadow elevation"),
        ],
        "constraints": [
            ("Display", "block by default"),
            ("Padding", "Must use spacing tokens, never raw px"),
            ("Background", "Must use color tokens from neutral or semantic"),
        ],
        "no_when": [
            "Children need vertical layout -> use Stack",
            "Children need horizontal layout -> use Inline",
        ],
    },
    "surface": {
        "title": "Surface",
        "description": "Elevated container for cards, dialogs, and dropdowns. Includes background, border, and shadow.",
        "category": "layout",
        "variants": [
            ("elevated", "Default card with shadow", "bg=color.neutral.surface, elevation=sm"),
            ("outlined", "Subtle border instead of shadow", "bg=color.neutral.surface, border=color.neutral.border"),
            ("filled", "Filled background, no border or shadow", "bg=color.neutral.bg, no border"),
        ],
        "sizes": [],
        "props": [
            ("variant", "'elevated' | 'outlined' | 'filled'", "elevated", "Surface style"),
            ("padding", "spacing token", "spacing.lg", "Inner padding"),
            ("radius", "radius token", "radius.lg", "Border radius"),
        ],
        "constraints": [
            ("Background", "Must use color.neutral.surface or color.neutral.bg"),
            ("Elevation", "Only elevated variant uses elevation tokens"),
            ("Radius", "Surface radius should be larger than component radius"),
        ],
        "no_when": [
            "Non-elevated grouping -> use Box",
            "Interactive container -> use Card pattern",
        ],
    },
    "input": {
        "title": "Input",
        "description": "Text input field for user data entry. Supports text, email, password, and number types.",
        "category": "form",
        "variants": [
            ("outlined", "Default variant with border", "border=color.neutral.border, bg=white"),
            ("filled", "Filled background, no border border", "bg=color.neutral.surface, no visible border"),
        ],
        "sizes": [
            ("sm", "28px", "font-size.caption", "spacing.sm"),
            ("md", "36px", "font-size.body", "spacing.md"),
            ("lg", "44px", "font-size.body", "spacing.lg"),
        ],
        "props": [
            ("variant", "'outlined' | 'filled'", "outlined", "Input style"),
            ("size", "'sm' | 'md' | 'lg'", "md", "Input height"),
            ("placeholder", "string", "--", "Placeholder text"),
            ("value", "string", "--", "Controlled value"),
            ("type", "'text' | 'email' | 'password' | 'number'", "text", "HTML input type"),
            ("error", "string", "--", "Error message shown below input"),
            ("disabled", "boolean", "false", "Disabled state"),
            ("readOnly", "boolean", "false", "Read-only state"),
        ],
        "constraints": [
            ("Height", "Must match size token (sm=28, md=36, lg=44)"),
            ("Border radius", "radius.sm (3px)"),
            ("Font", "font-size.body (14px) for md/lg, font-size.caption (12px) for sm"),
            ("Padding horizontal", "spacing.md for sm, spacing.lg for md/lg"),
        ],
        "no_when": [
            "Multi-line text -> use Textarea",
            "Select from options -> use Select",
            "File upload -> use FileUpload component",
        ],
    },
    "text": {
        "title": "Text",
        "description": "Typography element for non-interactive text content.",
        "category": "typography",
        "variants": [
            ("h1", "Page titles", "font-size.h1, font-weight.bold"),
            ("h2", "Section headings", "font-size.h2, font-weight.bold"),
            ("h3", "Sub-section headings", "font-size.h3, font-weight.semibold"),
            ("h4", "Card titles", "font-size.h4, font-weight.semibold"),
            ("body", "Body text, paragraphs", "font-size.body, font-weight.regular"),
            ("body-large", "Lead paragraphs", "font-size.body-large, font-weight.regular"),
            ("caption", "Metadata, footnotes", "font-size.caption, font-weight.regular"),
            ("label", "Form labels", "font-size.body, font-weight.medium"),
        ],
        "sizes": [],
        "props": [
            ("variant", "See variants above", "body", "Text style variant"),
            ("color", "color token", "color.neutral.text-primary", "Text color"),
            ("align", "'left' | 'center' | 'right'", "left", "Text alignment"),
            ("as", "element type", "--", "HTML element override (h1, p, span, etc.)"),
        ],
        "constraints": [
            ("Font size", "Must be a font-size token"),
            ("Font weight", "Must be a font-weight token"),
            ("Color", "Must use color.neutral.text-* or color.semantic.* tokens"),
        ],
        "no_when": [
            "Interactive text -> use Button or <a>",
            "Input labels -> use <label> with variant='label'",
            "SVG text -> use <text> SVG element",
        ],
    },
    "icon": {
        "title": "Icon",
        "description": "Single SVG icon renderer. Supports multiple icon sets with consistent sizing and coloring.",
        "category": "media",
        "variants": [],
        "sizes": [
            ("sm", "16px"),
            ("md", "20px"),
            ("lg", "24px"),
            ("xl", "32px"),
        ],
        "props": [
            ("name", "string", "--", "Icon identifier from the icon set"),
            ("size", "'sm' | 'md' | 'lg' | 'xl'", "md", "Icon dimension (square)"),
            ("color", "color token", "currentColor", "Icon fill color"),
            ("set", "'feather' | 'material' | 'custom'", "feather", "Icon set source"),
        ],
        "constraints": [
            ("Size", "Icon is always square (width == height)"),
            ("Color", "Must use color.neutral.icon or color.neutral.text-* tokens"),
            ("Set", "Icon set must be documented in design-system/icons/INDEX.md"),
        ],
        "no_when": [
            "Decorative icon next to text -> use Button icon prop",
            "Custom SVG illustration -> inline SVG directly",
        ],
    },
    "button": {
        "title": "Button",
        "description": "Primary action trigger. Clickable element that initiates an action.",
        "category": "action",
        "variants": [
            ("primary", "Main CTA", "bg=brand.primary, text=white, no border"),
            ("secondary", "Alternative", "bg=transparent, text=brand.primary, border=brand.primary"),
            ("ghost", "Low emphasis", "bg=transparent, text=neutral.text-primary, no border"),
            ("danger", "Destructive", "bg=semantic.danger, text=white, no border"),
            ("icon", "Icon-only", "bg=transparent, text=neutral.icon, no border"),
        ],
        "sizes": [
            ("sm", "28px", "font-size.body", "spacing.md"),
            ("md", "36px", "font-size.body", "spacing.lg"),
            ("lg", "44px", "font-size.body-large", "spacing.lg"),
        ],
        "props": [
            ("variant", "'primary' | 'secondary' | 'ghost' | 'danger' | 'icon'", "primary", "Visual style"),
            ("size", "'sm' | 'md' | 'lg'", "md", "Button size"),
            ("label", "string", "--", "Button text"),
            ("onClick", "() => void", "--", "Click handler"),
            ("disabled", "boolean", "false", "Disabled state"),
            ("icon", "string", "--", "Icon name (prefixes label)"),
            ("loading", "boolean", "false", "Show spinner, disable clicks"),
        ],
        "constraints": [
            ("Height", "sm=28px, md=36px, lg=44px"),
            ("Border radius", "radius.sm (3px)"),
            ("Font size", "font-size.body (14px) for sm/md, font-size.body-large (16px) for lg"),
        ],
        "no_when": [
            "Navigation between pages -> use <a> / Link component",
            "Non-action decorative elements -> use Text or Icon",
            "Multiple primary buttons on one view -> max one primary",
        ],
    },
}


def _name(p: str) -> str:
    return _PRIMITIVE_META.get(p, {}).get("title", p.title())


def _design_template(p: str, style: str) -> str:
    meta = _PRIMITIVE_META.get(p)
    if not meta:
        return f"# {_name(p)}\n\n"

    lines = [f"# {meta['title']}", "", meta["description"], "", "## Constraints", "",
             "| Property | Value |", "|----------|-------|"]
    for prop, val in meta["constraints"]:
        lines.append(f"| {prop} | {val} |")

    if meta.get("variants"):
        lines += ["", "## Variants", "", "| Variant | Purpose | Style |"]
        lines += ["|---------|---------|-------|"]
        for name, purpose, style_desc in meta["variants"]:
            lines.append(f"| `{name}` | {purpose} | {style_desc} |")

    if meta.get("sizes"):
        if p == "button":
            lines += ["", "## Sizes", "", "| Size | Height | Font | Padding X |"]
            lines += ["|------|--------|------|-----------|"]
            for name, height, font, pad_x in meta["sizes"]:
                lines.append(f"| `{name}` | {height} | {font} | {pad_x} |")
        elif p == "input":
            lines += ["", "## Sizes", "", "| Size | Height | Font | Padding X |"]
            lines += ["|------|--------|------|-----------|"]
            for name, height, font, pad_x in meta["sizes"]:
                lines.append(f"| `{name}` | {height} | {font} | {pad_x} |")
        elif p == "icon":
            lines += ["", "## Sizes", "", "| Size | Dimension |", "|------|-----------|"]
            for name, dim in meta["sizes"]:
                lines.append(f"| `{name}` | {dim} |")

    lines += ["", "## Props", "", "| Prop | Type | Default | Description |"]
    lines += ["|------|------|---------|-------------|"]
    for name, ptype, default, desc in meta["props"]:
        lines.append(f"| `{name}` | {ptype} | {default} | {desc} |")

    if meta.get("no_when"):
        lines += ["", "## When NOT to use", ""]
        for item in meta["no_when"]:
            lines.append(f"- {item}")

    if meta.get("variants"):
        lines += ["", "## Interactions", "", "| State | Behavior |", "|-------|----------|",
                  "| Default | Normal variant colors |",
                  "| Hover | BG darkens 10%, cursor: pointer |",
                  "| Active/Pressed | BG darkens 20% |",
                  "| Disabled | Opacity 0.5, cursor: not-allowed |",
                  "| Focus | brand.primary focus ring |"]

    if p in ("button", "input"):
        lines += ["", "## Accessibility", "",
                  "- Must have visible focus ring",
                  "- Must support keyboard activation (Enter/Space)",
                  "- Must have aria-label when icon-only (button)",
                  "- Error messages must be associated via aria-describedby (input)"]

    lines.append("")
    return "\n".join(lines)


def _anatomy_template(p: str, style: str) -> str:
    title = _name(p)
    lines = [f"# {title} -- Anatomy", "", "## Element structure", ""]

    if p == "button":
        lines.extend([
            "```tsx",
            "<button class=\"btn btn-{variant} btn-{size}\">",
            "  {Icon ? <Icon name={iconName} size={iconSize} /> : null}",
            "  {label}",
            "</button>",
            "```",
        ])
    elif p == "stack":
        lines.extend([
            "```tsx",
            "<div class=\"stack\" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap)' }}>",
            "  {children}",
            "</div>",
            "```",
        ])
    elif p == "inline":
        lines.extend([
            "```tsx",
            "<div class=\"inline\" style={{ display: 'flex', flexDirection: 'row', gap: 'var(--gap)', flexWrap: wrap ? 'wrap' : 'nowrap' }}>",
            "  {children}",
            "</div>",
            "```",
        ])
    elif p == "box":
        lines.extend([
            "```tsx",
            "<div class=\"box\" style={{ padding, borderRadius, backgroundColor, boxShadow }}>",
            "  {children}",
            "</div>",
            "```",
        ])
    elif p == "surface":
        lines.extend([
            "```tsx",
            "<div class=\"surface surface--{variant}\">",
            "  {children}",
            "</div>",
            "```",
        ])
    elif p == "input":
        lines.extend([
            "```tsx",
            "<div class=\"input-wrapper\">",
            "  {label ? <label>{label}</label> : null}",
            "  <input class=\"input input--{size}\" type=\"{type}\" placeholder=\"{placeholder}\" />",
            "  {error ? <span class=\"input-error\">{error}</span> : null}",
            "</div>",
            "```",
        ])
    elif p == "text":
        lines.extend([
            "```tsx",
            "<Tag class=\"text text--{variant}\" style={{ color }}>",
            "  {children}",
            "</Tag>",
            "```",
        ])
    elif p == "icon":
        lines.extend([
            "```tsx",
            "<svg class=\"icon icon--{size}\" width={size} height={size} fill={color}>",
            "  <use href={`#icon-{name}`} />",
            "</svg>",
            "```",
        ])

    # Props tables
    meta = _PRIMITIVE_META.get(p, {})
    if meta:
        lines += ["", "## Required props", "", "| Prop | Type | Default | Description |",
                  "|------|------|---------|-------------|"]
        for name, ptype, default, desc in meta["props"][:4]:
            lines.append(f"| `{name}` | {ptype} | {default} | {desc} |")

    lines += ["", "## CSS class structure", ""]
    if p == "button":
        lines.extend([
            "```css",
            ".btn { display: inline-flex; align-items: center; justify-content: center; gap: spacing.sm; }",
            ".btn--primary { background-color: color.brand.primary; color: #FFFFFF; }",
            ".btn--secondary { background: transparent; border: 1px solid color.brand.primary; }",
            "```",
        ])
    elif p == "stack":
        lines.extend([
            "```css",
            ".stack { display: flex; flex-direction: column; width: 100%; }",
            ".stack--align-center { align-items: center; }",
            ".stack--align-end { align-items: flex-end; }",
            "```",
        ])
    elif p == "inline":
        lines.extend([
            "```css",
            ".inline { display: flex; flex-direction: row; align-items: center; }",
            ".inline--wrap { flex-wrap: wrap; }",
            "```",
        ])
    elif p in ("box", "surface"):
        lines.extend([
            "```css",
            f".{p} {{ box-sizing: border-box; }}",
            f".{p}--elevated {{ box-shadow: var(--elevation); }}",
            f".{p}--outlined {{ border: 1px solid color.neutral.border; }}",
            "```",
        ])
    elif p == "input":
        lines.extend([
            "```css",
            ".input { border: 1px solid color.neutral.border; border-radius: radius.sm; }",
            ".input--error { border-color: color.semantic.danger; }",
            ".input:focus { outline: 2px solid color.brand.primary; }",
            "```",
        ])
    elif p == "text":
        lines.extend([
            "```css",
            ".text--h1 { font-size: font-size.h1; font-weight: font-weight.bold; }",
            ".text--body { font-size: font-size.body; font-weight: font-weight.regular; }",
            ".text--caption { font-size: font-size.caption; color: color.neutral.text-secondary; }",
            "```",
        ])
    elif p == "icon":
        lines.extend([
            "```css",
            ".icon { display: inline-block; flex-shrink: 0; }",
            ".icon--sm { width: 16px; height: 16px; }",
            ".icon--md { width: 20px; height: 20px; }",
            "```",
        ])

    lines.append("")
    return "\n".join(lines)


def _dodont_template(p: str, style: str) -> str:
    title = _name(p)
    lines = [f"# {title} -- Do / Don't", "", "## DO [OK]", ""]

    meta = _PRIMITIVE_META.get(p, {})
    category = meta.get("category", "")

    if p == "button":
        lines.extend([
            "### Use primary variant for the main action",
            "",
            "```",
            "[OK] <Button variant=\"primary\" label=\"Save\" />",
            "[X] <Button variant=\"ghost\" label=\"Save\" />",
            "```",
            "",
            "### Use consistent height across related buttons",
            "",
            "```",
            "[OK] Two buttons side-by-side, both same size=\"md\"",
            "[X] <Button size=\"sm\" /> next to <Button size=\"lg\" />",
            "```",
            "",
            "### Use `loading` state for async actions",
            "",
            "```",
            "[OK] <Button variant=\"primary\" label=\"Submit\" loading={isSubmitting} />",
            "[X] Manually disabling without spinner feedback",
            "```",
        ])
    elif p == "stack":
        lines.extend([
            "### Use Stack for vertical form layouts",
            "",
            "```",
            "[OK] <Stack gap=\"lg\"><Input /><Button /></Stack>",
            "[X] Margin-bottom on each child element",
            "```",
            "",
            "### Use consistent gap across the page",
            "",
            "```",
            "[OK] All vertical sections use spacing.lg",
            "[X] Mixing spacing.sm, 13px, 1rem in the same view",
            "```",
        ])
    elif p == "inline":
        lines.extend([
            "### Use Inline for action groups",
            "",
            "```",
            "[OK] <Inline gap=\"sm\"><Button label=\"Save\" /><Button label=\"Cancel\" /></Inline>",
            "[X] Float: left on each button",
            "```",
        ])
    elif p == "input":
        lines.extend([
            "### Always associate labels with inputs",
            "",
            "```",
            "[OK] <label for=\"email\">Email</label><Input id=\"email\" />",
            "[X] Placeholder-only labels that disappear on input",
            "```",
            "",
            "### Show error messages inline",
            "",
            "```",
            "[OK] <Input error=\"Email is required\" /> with aria-describedby",
            "[X] Alert banner at top of form",
            "```",
        ])
    elif p == "text":
        lines.extend([
            "### Use semantic variants, not custom styles",
            "",
            "```",
            "[OK] <Text variant=\"h2\">Section Title</Text>",
            "[X] <Text style={{ fontSize: 22, fontWeight: 600 }}>Title</Text>",
            "```",
        ])
    elif p == "icon":
        lines.extend([
            "### Use consistent icon sizes within a context",
            "",
            "```",
            "[OK] All toolbar icons are size=\"sm\"",
            "[X] Mixing sm, md, and lg icons in the same toolbar",
            "```",
        ])

    lines += ["", "## DON'T [X]", ""]

    if p == "button":
        lines.extend([
            "### Don't stack multiple primary buttons",
            "",
            "```",
            "[OK] Use primary + secondary pair",
            "[X] Two primary buttons competing for attention",
            "```",
            "",
            "### Don't use hardcoded padding",
            "",
            "```",
            "[OK] Uses design tokens",
            "[X] style={{ padding: '7px 14px' }} -> snaps to spacing.sm + spacing.md",
            "```",
        ])
    elif category == "layout":
        lines.extend([
            "### Don't nest layout components unnecessarily",
            "",
            "```",
            "[OK] <Stack gap=\"sm\"><Text /><Text /></Stack>",
            "[X] <Stack><Box><Inline><Text /></Inline></Box></Stack> (excessive nesting)",
            "```",
        ])
    elif p == "input":
        lines.extend([
            "### Don't use raw px values for spacing/padding",
            "",
            "```",
            "[OK] style={{ padding: 'var(--spacing-md)' }}",
            "[X] style={{ padding: '13px' }} -> snaps to spacing.md (12px)",
            "```",
        ])
    elif p == "icon":
        lines.extend([
            "### Don't use color for decorative icons",
            "",
            "```",
            "[OK] <Icon name=\"info\" color={color.neutral.icon} />",
            "[X] <Icon name=\"info\" color=\"#FF0000\" /> -> use semantic.danger",
            "```",
        ])

    lines.append("")
    return "\n".join(lines)


# -- Core logic ------------------------------------------------------------

def _primitive_dir(name: str) -> Path:
    return DS_PRIMITIVES / name


def _completeness(prim_dir: Path) -> dict[str, bool]:
    status: dict[str, bool] = {}
    for f in REQUIRED_FILES:
        status[f] = (prim_dir / f).exists()
    for d in OPTIONAL_DIRS:
        status[d] = (prim_dir / d).exists() and any((prim_dir / d).iterdir())
    return status


def list_primitives() -> list[dict[str, Any]]:
    if not DS_PRIMITIVES.exists():
        return []
    result: list[dict[str, Any]] = []
    for entry in sorted(DS_PRIMITIVES.iterdir()):
        if not entry.is_dir():
            continue
        status = _completeness(entry)
        meta = _PRIMITIVE_META.get(entry.name.lower(), {})
        result.append({
            "name": entry.name,
            "category": meta.get("category", "unknown"),
            "files": status,
            "complete": all(status.get(f, False) for f in REQUIRED_FILES),
        })
    return result


def generate_primitive(
    name: str,
    style: str = "web",
    force: bool = False,
    dry_run: bool = False,
) -> list[str]:
    target = _primitive_dir(name)
    target.mkdir(parents=True, exist_ok=True)

    files = _t(name, style)
    created: list[str] = []

    for filename, content in files.items():
        path = target / filename
        if path.exists() and not force:
            continue
        if dry_run:
            created.append(f"[dry-run] would write: {path}")
        else:
            path.write_text(content, encoding="utf-8")
            created.append(f"Created: {path}")

    examples_dir = target / "examples"
    if not examples_dir.exists() and not dry_run:
        examples_dir.mkdir(parents=True, exist_ok=True)
        created.append(f"Created: {examples_dir}/")

    return created


def generate_all_missing(style: str = "web", force: bool = False, dry_run: bool = False) -> list[str]:
    created: list[str] = []
    for entry in sorted(DS_PRIMITIVES.iterdir()):
        if not entry.is_dir():
            continue
        status = _completeness(entry)
        if all(status.get(f, False) for f in REQUIRED_FILES):
            continue
        created.extend(generate_primitive(entry.name, style=style, force=force, dry_run=dry_run))
    return created


# -- CLI -------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate primitive documentation from templates.",
    )
    parser.add_argument("--ds-path", type=str, default=None,
                        help="Path to primitives directory")

    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_p = subparsers.add_parser("generate", help="Generate primitive files")
    gen_p.add_argument("name", nargs="?", help="Primitive name (e.g. Stack, Input)")
    gen_p.add_argument("--all-missing", action="store_true", help="Generate all incomplete primitives")
    gen_p.add_argument("--style", choices=["web", "flutter"], default="web", help="Target framework style")
    gen_p.add_argument("--force", action="store_true", help="Overwrite existing files")
    gen_p.add_argument("--dry-run", action="store_true", help="Show what would be created")

    list_p = subparsers.add_parser("list", help="List primitives and completeness")
    list_p.add_argument("--json", action="store_true", help="JSON output")

    tmpl_p = subparsers.add_parser("template", help="Show template content")
    tmpl_p.add_argument("name", help="Primitive name")
    tmpl_p.add_argument("--style", choices=["web", "flutter"], default="web")

    args = parser.parse_args()

    if args.ds_path:
        globals()["DS_PRIMITIVES"] = Path(args.ds_path)

    if args.command == "generate":
        if args.all_missing:
            results = generate_all_missing(style=args.style, force=args.force, dry_run=args.dry_run)
        elif args.name:
            results = generate_primitive(args.name, style=args.style, force=args.force, dry_run=args.dry_run)
        else:
            parser.error("provide a primitive name or --all-missing")
        for r in results:
            print(r)
        if not results:
            print("Nothing to generate.")

    elif args.command == "list":
        prims = list_primitives()
        if args.json:
            import json
            print(json.dumps(prims, indent=2))
        else:
            if not prims:
                print("No primitives found.")
                return 0
            print(f"{'Primitive':<12} {'Category':<14} {'design.md':<10} {'anatomy.md':<10} {'do-dont.md':<10} {'examples':<10} Status")
            print("-" * 78)
            for p in prims:
                s = p["files"]
                ok = "OK" if p["complete"] else "MISSING"
                y, n = "Y", "-"
                print(f"{p['name']:<12} {p['category']:<14} {y if s.get('design.md') else n:<10} {y if s.get('anatomy.md') else n:<10} {y if s.get('do-dont.md') else n:<10} {y if s.get('examples') else n:<10} {ok}")

    elif args.command == "template":
        meta = _PRIMITIVE_META.get(args.name.lower())
        if not meta:
            print(f"Unknown primitive: {args.name}")
            return 1
        files = _t(args.name, args.style)
        for fname, content in files.items():
            print(f"=== {fname} ===")
            print(content)
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
