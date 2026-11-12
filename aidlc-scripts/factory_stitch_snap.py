#!/usr/bin/env python3
"""factory_stitch_snap.py — Snap Google Stitch HTML/CSS output to design tokens.

⚠️ DEPRECATED — Use `StitchAdapter` from `harness_adapters/source/stitch.py` instead.
   Example:
     python3 aidlc-scripts/harness_adapters/source/stitch.py --input <file> --output <file>
   This script is kept for backwards compatibility and will be removed in v0.4.0.


Pre-processing layer that snaps raw style values from Stitch-generated
HTML/CSS to canonical design tokens BEFORE the LLM uses them for code
generation. Stitch proposes intent; this script enforces the local design
system as law.

Subcommands:
  snap-html    Parse HTML with inline styles, snap values to tokens
  snap-design  Parse Stitch DESIGN.md token definitions → our token format
  snap-file    Read an HTML/CSS/DESIGN.md file, output token-snapped version

Usage:
    python3 aidlc-scripts/factory_stitch_snap.py snap-html \
        --html '<div style="padding:13px;border-radius:5px">...</div>'

    python3 aidlc-scripts/factory_stitch_snap.py snap-design \
        --input stitch/DESIGN.md --output design-system/tokens/

    python3 aidlc-scripts/factory_stitch_snap.py snap-file \
        --input stitch/export.html --output stitch/snapped.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
REPO_ROOT_DEFAULT = _SCRIPT_DIR.parent
DESIGN_SYSTEM_DIR = "design-system"


# ── Nearest-neighbor helpers ─────────────────────────────────────────────────

def _nearest(value: float, candidates: list[int]) -> int:
    return min(candidates, key=lambda c: abs(c - value))


def _parse_px(raw: str | float | int) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    m = re.search(r"([-+]?\d*\.?\d+)", str(raw))
    if m:
        return float(m.group(1))
    return 0.0


# ── Color matcher (shared logic with factory_design_system_snap.py) ────────────

def _normalize_hex(hex_str: str) -> str:
    h = hex_str.strip().lower().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return f"#{h}"


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
    h = hex_str.strip().lower().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return None


def _color_distance(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
    return sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5


_COLOR_DISTANCE_THRESHOLD = 60.0


def _snap_color(raw: str, color_map: dict[str, str]) -> tuple[str, str | None]:
    normalized = _normalize_hex(raw)
    for known_hex, token in color_map.items():
        if _normalize_hex(known_hex) == normalized:
            return token, raw
    raw_rgb = _hex_to_rgb(normalized)
    if raw_rgb:
        best_dist = float("inf")
        best_token = None
        for known_hex, token in color_map.items():
            known_rgb = _hex_to_rgb(known_hex)
            if known_rgb:
                dist = _color_distance(raw_rgb, known_rgb)
                if dist < best_dist:
                    best_dist = dist
                    best_token = token
        if best_token and best_dist < _COLOR_DISTANCE_THRESHOLD:
            return best_token, raw
    return raw, None


# ── Token mapping (mirrors factory_design_system_snap.py) ──────────────────────

def _spacing_name(value: int) -> str:
    mapping = {4: "xs", 8: "sm", 12: "md", 16: "lg", 24: "xl", 32: "xxl"}
    return mapping.get(value, f"_{value}px")


def _radius_name(value: int) -> str:
    mapping = {0: "none", 3: "sm", 6: "md", 12: "lg", 9999: "full"}
    return mapping.get(value, f"_{value}px")


def _radius_str(value: int) -> str:
    return "9999px" if value >= 9999 else f"{value}px"


def _font_name(value: int) -> str:
    mapping = {12: "caption", 14: "body", 16: "body-large",
               20: "h4", 24: "h3", 32: "h2", 40: "h1"}
    return mapping.get(value, f"_{value}px")


# ── Snapping engine ───────────────────────────────────────────────────────────

def _load_color_map(repo_root: Path) -> dict[str, str]:
    color_file = repo_root / DESIGN_SYSTEM_DIR / "tokens" / "color.md"
    if not color_file.exists():
        return {}
    color_map: dict[str, str] = {}
    for line in color_file.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*(#[0-9A-Fa-f]{3,8})\s*\|", line)
        if m:
            color_map[m.group(2)] = m.group(1)
    return color_map


def _snap_declaration(key: str, raw_value: str,
                      spacing: list[int], radius: list[int],
                      font_sizes: list[int],
                      color_map: dict[str, str]) -> dict:
    """Snap a single CSS declaration to canonical tokens.

    Returns {property, raw, snapped, token_category, was_corrected}.
    """
    result = {
        "property": key,
        "raw": raw_value,
        "snapped": raw_value,
        "token_category": None,
        "was_corrected": False,
    }

    key_lower = key.lower()
    is_spacing = any(k in key_lower for k in ("padding", "margin", "gap", "inset"))
    is_radius = any(k in key_lower for k in ("radius", "rounded", "corner"))
    is_font_size = any(k in key_lower for k in ("font-size", "fontsize", "font_size"))
    is_color = any(k in key_lower for k in ("color", "background", "fill", "stroke",
                                              "border-color", "background-color"))

    try:
        px = _parse_px(raw_value)
    except (ValueError, TypeError):
        px = 0.0

    if is_spacing and spacing:
        snapped = _nearest(px, spacing)
        token_name = _spacing_name(snapped)
        result["snapped"] = f"{snapped}px"
        result["token_category"] = f"spacing.{token_name}"
        if abs(snapped - px) > 0.01:
            result["was_corrected"] = True

    elif is_radius and radius:
        snapped = _nearest(px, radius)
        token_name = _radius_name(snapped)
        result["snapped"] = _radius_str(snapped)
        result["token_category"] = f"radius.{token_name}"
        if abs(snapped - px) > 0.01:
            result["was_corrected"] = True

    elif is_font_size and font_sizes:
        snapped = _nearest(px, font_sizes)
        token_name = _font_name(snapped)
        result["snapped"] = f"{snapped}px"
        result["token_category"] = f"font-size.{token_name}"
        if abs(snapped - px) > 0.01:
            result["was_corrected"] = True

    elif is_color and color_map:
        snapped_token, _ = _snap_color(raw_value.strip(), color_map)
        if snapped_token != raw_value.strip():
            result["snapped"] = snapped_token
            result["token_category"] = "color"
            result["was_corrected"] = True

    return result


# ── Parse inline styles from HTML ─────────────────────────────────────────────

_INLINE_STYLE_RE = re.compile(r'style="([^"]*)"')


def _parse_inline_styles(html: str) -> list[dict]:
    """Extract all CSS declaration blocks from inline styles in HTML."""
    declarations: list[dict] = []
    for match in _INLINE_STYLE_RE.finditer(html):
        style_block = match.group(1)
        for decl in style_block.split(";"):
            decl = decl.strip()
            if not decl:
                continue
            if ":" not in decl:
                continue
            key, val = decl.split(":", 1)
            declarations.append({"property": key.strip(), "value": val.strip()})
    return declarations


def snap_html(html: str, spacing: list[int], radius: list[int],
              font_sizes: list[int], color_map: dict[str, str]) -> dict:
    """Snap all inline style values in HTML to canonical tokens.

    Returns dict with snapped HTML and corrections log.
    """
    corrections: list[dict] = []

    def _replace_style(m: re.Match) -> str:
        style_block = m.group(1)
        new_decls: list[str] = []
        for decl in style_block.split(";"):
            decl = decl.strip()
            if not decl:
                continue
            if ":" not in decl:
                new_decls.append(decl)
                continue
            key, val = decl.split(":", 1)
            key = key.strip()
            val = val.strip()
            snapped = _snap_declaration(key, val, spacing, radius, font_sizes, color_map)
            if snapped["was_corrected"]:
                corrections.append(snapped)
            new_decls.append(f"{key}: {snapped['snapped']}")
        return f'style="{"; ".join(new_decls)}"'

    snapped_html = _INLINE_STYLE_RE.sub(_replace_style, html)

    return {
        "original_html": html,
        "snapped_html": snapped_html,
        "corrections": corrections,
        "correction_count": len(corrections),
    }


# ── Parse Stitch DESIGN.md ────────────────────────────────────────────────────

_DESIGN_MD_TOKEN_RE = re.compile(
    r"\|\s*`([^`]+)`\s*\|\s*`?([^`|\n]+)`?\s*\|"
)


def snap_designmd(content: str, repo_root: Path) -> dict:
    """Parse Stitch DESIGN.md and map tokens to our design system format.

    Stitch DESIGN.md defines the design system used in a Stitch project.
    This function extracts token definitions and maps them to our local
    design system tokens.

    Returns a dict with mapped tokens and any unmapped values.
    """
    from datetime import datetime, timezone

    mapped: dict[str, list[dict]] = {
        "spacing": [],
        "radius": [],
        "typography": [],
        "color": [],
    }
    unmapped: list[dict] = []

    for line in content.splitlines():
        m = _DESIGN_MD_TOKEN_RE.search(line)
        if not m:
            continue
        token_name = m.group(1).strip()
        token_value = m.group(2).strip()

        # Try to categorize the token
        key_lower = token_name.lower()
        if any(k in key_lower for k in ("padding", "margin", "gap", "spacing")):
            mapped["spacing"].append({"token": token_name, "value": token_value})
        elif any(k in key_lower for k in ("radius", "rounded", "corner")):
            mapped["radius"].append({"token": token_name, "value": token_value})
        elif any(k in key_lower for k in ("font", "size", "typography", "type")):
            mapped["typography"].append({"token": token_name, "value": token_value})
        elif any(k in key_lower for k in ("color", "fill", "stroke", "background")):
            mapped["color"].append({"token": token_name, "value": token_value})
        else:
            unmapped.append({"token": token_name, "value": token_value})

    # Try to write out mapped tokens to our format
    output_dir = repo_root / DESIGN_SYSTEM_DIR / "tokens"
    written: list[str] = []

    def _write_stitch_tokens(category: str, entries: list[dict],
                               file_name: str, template: str) -> None:
        if not entries:
            return
        out_path = output_dir / file_name
        lines: list[str] = [
            f"# Stitch-imported tokens ({category})",
            f"# Imported from Stitch DESIGN.md at "
            f"{datetime.now(timezone.utc).isoformat()}",
            "",
            template,
            "",
        ]
        for e in entries:
            lines.append(f"| `{e['token']}` | `{e['value']}` | Stitch import |")
        lines.append("")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        written.append(str(out_path))

    _write_stitch_tokens(
        "spacing", mapped["spacing"], "stitch-spacing.md",
        "| Token | Value | Source |\n|-------|-------|--------|",
    )
    _write_stitch_tokens(
        "radius", mapped["radius"], "stitch-radius.md",
        "| Token | Value | Source |\n|-------|-------|--------|",
    )
    _write_stitch_tokens(
        "typography", mapped["typography"], "stitch-typography.md",
        "| Token | Value | Source |\n|-------|-------|--------|",
    )
    _write_stitch_tokens(
        "color", mapped["color"], "stitch-color.md",
        "| Token | Value | Source |\n|-------|-------|--------|",
    )

    return {
        "mapped": {k: v for k, v in mapped.items() if v},
        "unmapped": unmapped,
        "written_files": written,
        "token_count": sum(len(v) for v in mapped.values()),
    }


# ── File-based snapping ───────────────────────────────────────────────────────

def snap_file(input_path: Path, repo_root: Path,
              spacing: list[int], radius: list[int],
              font_sizes: list[int], color_map: dict[str, str]) -> dict:
    """Snap a file (HTML, CSS, or DESIGN.md) to canonical tokens.

    Detects file type by extension:
      - .html, .htm → parse inline styles
      - .md → parse as Stitch DESIGN.md
      - .css → parse CSS declarations (basic)
    """
    content = input_path.read_text(encoding="utf-8")
    ext = input_path.suffix.lower()

    if ext in (".html", ".htm"):
        return snap_html(content, spacing, radius, font_sizes, color_map)
    elif ext == ".md":
        return snap_designmd(content, repo_root)
    elif ext == ".css":
        return _snap_css(content, spacing, radius, font_sizes, color_map)
    else:
        # Fallback: try HTML detection
        if "<html" in content[:500] or "<div" in content[:500]:
            return snap_html(content, spacing, radius, font_sizes, color_map)
        return snap_designmd(content, repo_root)


# ── CSS snapping (basic) ──────────────────────────────────────────────────────

_CSS_DECL_RE = re.compile(r"([a-z-]+)\s*:\s*([^;{}]+)")


def _snap_css(css: str, spacing: list[int], radius: list[int],
              font_sizes: list[int], color_map: dict[str, str]) -> dict:
    """Snap CSS declaration values to canonical tokens."""
    corrections: list[dict] = []

    def _replace_decl(m: re.Match) -> str:
        key = m.group(1).strip()
        val = m.group(2).strip()
        snapped = _snap_declaration(key, val, spacing, radius, font_sizes, color_map)
        if snapped["was_corrected"]:
            corrections.append(snapped)
        return f"{key}: {snapped['snapped']}"

    snapped_css = _CSS_DECL_RE.sub(_replace_decl, css)

    return {
        "original_css": css,
        "snapped_css": snapped_css,
        "corrections": corrections,
        "correction_count": len(corrections),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Snap raw Google Stitch HTML/CSS output to canonical design tokens.",
    )
    parser.add_argument("--repo-root", type=str, default=str(REPO_ROOT_DEFAULT),
                        help="Repository root path")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without making changes")
    parser.add_argument("--spacing", type=str, default="4,8,12,16,24,32",
                        help="Comma-separated spacing values")
    parser.add_argument("--radius", type=str, default="0,3,6,12,9999",
                        help="Comma-separated radius values")
    parser.add_argument("--font-sizes", type=str, default="12,14,16,20,24,32,40",
                        help="Comma-separated font sizes")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # snap-html
    html_parser = subparsers.add_parser("snap-html", help="Snap inline styles in HTML")
    html_parser.add_argument("--html", type=str, required=True,
                             help="HTML string with inline styles")

    # snap-design
    design_parser = subparsers.add_parser("snap-design", help="Snap Stitch DESIGN.md")
    design_parser.add_argument("--input", type=str, required=True,
                               help="Path to DESIGN.md file")

    # snap-file
    file_parser = subparsers.add_parser("snap-file", help="Snap an HTML/CSS/DESIGN.md file")
    file_parser.add_argument("--input", type=str, required=True,
                             help="Input file path")
    file_parser.add_argument("--output", type=str, default=None,
                             help="Output file path (default: stdout)")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    spacing = [int(x.strip()) for x in args.spacing.split(",")]
    radius = [int(x.strip()) for x in args.radius.split(",")]
    font_sizes = [int(x.strip()) for x in args.font_sizes.split(",")]
    color_map = _load_color_map(repo_root)

    if args.command == "snap-html":
        result = snap_html(args.html, spacing, radius, font_sizes, color_map)
        print(json.dumps(result, indent=2))

    elif args.command == "snap-design":
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"ERROR: File not found: {input_path}", file=sys.stderr)
            return 1
        content = input_path.read_text(encoding="utf-8")
        result = snap_designmd(content, repo_root)
        if args.dry_run:
            result["dry_run"] = True
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result, indent=2))

    elif args.command == "snap-file":
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"ERROR: File not found: {input_path}", file=sys.stderr)
            return 1
        result = snap_file(input_path, repo_root, spacing, radius, font_sizes, color_map)
        output_json = json.dumps(result, indent=2)
        if args.output:
            Path(args.output).write_text(output_json, encoding="utf-8")
            print(f"Snapped -> {args.output} ({result.get('correction_count', 0)} corrections)")
        else:
            print(output_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
