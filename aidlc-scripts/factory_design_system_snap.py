#!/usr/bin/env python3
"""factory_design_system_snap.py — Input Snapping for Figma data.

⚠️ DEPRECATED — Use `FigmaAdapter` from `harness_adapters/source/figma.py` instead.
   Example:
     python3 aidlc-scripts/harness_adapters/source/figma.py --input <file> --output <file>
   This script is kept for backwards compatibility and will be removed in v0.4.0.


Pre-processing layer that snaps raw Figma values to canonical design tokens
BEFORE the LLM ever sees them. Figma proposes intent; this script enforces
the local design system as law.

Subcommands:
  snap      Read raw Figma JSON (node attributes), output token-snapped JSON
  snap-file Read a Figma JSON file, output snapped version

Usage:
    python3 aidlc-scripts/factory_design_system_snap.py snap \
        --spacing 4,8,12,16,24,32 \
        --radius 0,3,6,12,9999 \
        --font-sizes 12,14,16,20,24,32,40 \
        --colors '{"#2563EB":"color.brand.primary","#EF4444":"color.semantic.danger"}' \
        --json '{"padding":"13.4px","borderRadius":"4.2px","fontSize":"15px"}'

    python3 aidlc-scripts/factory_design_system_snap.py snap-file \
        --input figma-node.json --output snapped.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
REPO_ROOT_DEFAULT = _SCRIPT_DIR.parent
DESIGN_SYSTEM_DIR = "design-system"

# ── Nearest-neighbor helpers ─────────────────────────────────────────────────

def _nearest(value: float, candidates: list[int]) -> int:
    """Return the nearest integer in `candidates` to `value`."""
    return min(candidates, key=lambda c: abs(c - value))


def _parse_px(raw: str | float | int) -> float:
    """Parse a pixel value from string (e.g. '13.4px', '16', 13.4)."""
    if isinstance(raw, (int, float)):
        return float(raw)
    m = re.search(r"([-+]?\d*\.?\d+)", str(raw))
    if m:
        return float(m.group(1))
    return 0.0


# ── Color matcher ────────────────────────────────────────────────────────────

def _normalize_hex(hex_str: str) -> str:
    """Normalize a hex color to lowercase 6-char form."""
    h = hex_str.strip().lower().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return f"#{h}"


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
    """Convert a hex color string to (R, G, B)."""
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
    """Euclidean distance between two RGB colors."""
    return sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5


_COLOR_DISTANCE_THRESHOLD = 60.0


def _snap_color(raw: str, color_map: dict[str, str]) -> tuple[str, str | None]:
    """Snap a raw hex color to the nearest known token.

    Returns (token_value, raw_input) if matched, (raw, None) if no match.
    Uses exact match first, then Euclidean distance in RGB space.
    """
    normalized = _normalize_hex(raw)

    # 1. Exact match
    for known_hex, token in color_map.items():
        if _normalize_hex(known_hex) == normalized:
            return token, raw

    # 2. RGB proximity match
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


# ── Snapping engine ──────────────────────────────────────────────────────────

def snap_value(key: str, raw_value: str | float | int,
               spacing: list[int], radius: list[int],
               font_sizes: list[int],
               color_map: dict[str, str]) -> dict:
    """Snap a single key-value pair to canonical tokens.

    Returns {key, raw, snapped, token_category, was_corrected}.
    """
    result = {
        "key": key,
        "raw": str(raw_value),
        "snapped": str(raw_value),
        "token_category": None,
        "was_corrected": False,
    }

    key_lower = key.lower()

    # Detect category from key name
    is_spacing = any(k in key_lower for k in ("padding", "margin", "gap", "inset", "itemspacing", "spacing"))
    is_radius = any(k in key_lower for k in ("radius", "rounded", "corner"))
    is_font_size = any(k in key_lower for k in ("font-size", "fontsize", "font_size"))
    is_color = any(k in key_lower for k in ("color", "background", "fill", "stroke", "border-color", "background-color"))

    try:
        px = _parse_px(raw_value)
    except (ValueError, TypeError):
        px = 0.0

    if is_spacing and spacing:
        snapped = _nearest(px, spacing)
        if abs(snapped - px) > 0.01:
            result["snapped"] = f"{snapped}px"
            result["token_category"] = f"spacing.{_spacing_name(snapped, spacing)}"
            result["was_corrected"] = True
        else:
            result["snapped"] = f"{px:.0f}px" if px == int(px) else f"{px}px"
            result["token_category"] = f"spacing.{_spacing_name(int(px), spacing)}"

    elif is_radius and radius:
        snapped = _nearest(px, radius)
        if abs(snapped - px) > 0.01:
            result["snapped"] = _radius_str(snapped)
            result["token_category"] = f"radius.{_radius_name(snapped, radius)}"
            result["was_corrected"] = True
        else:
            result["snapped"] = _radius_str(int(px))
            result["token_category"] = f"radius.{_radius_name(int(px), radius)}"

    elif is_font_size and font_sizes:
        snapped = _nearest(px, font_sizes)
        if abs(snapped - px) > 0.01:
            result["snapped"] = f"{snapped}px"
            result["token_category"] = f"font-size.{_font_name(snapped, font_sizes)}"
            result["was_corrected"] = True
        else:
            result["snapped"] = f"{px:.0f}px"
            result["token_category"] = f"font-size.{_font_name(int(px), font_sizes)}"

    elif is_color and color_map:
        snapped_token, raw_used = _snap_color(str(raw_value), color_map)
        if snapped_token != str(raw_value):
            result["snapped"] = snapped_token
            result["token_category"] = "color"
            result["was_corrected"] = True

    return result


def _spacing_name(value: int, candidates: list[int]) -> str:
    mapping = {4: "xs", 8: "sm", 12: "md", 16: "lg", 24: "xl", 32: "xxl"}
    return mapping.get(value, f"_{value}px")


def _radius_name(value: int, candidates: list[int]) -> str:
    mapping = {0: "none", 3: "sm", 6: "md", 12: "lg", 9999: "full"}
    return mapping.get(value, f"_{value}px")


def _radius_str(value: int) -> str:
    return "9999px" if value >= 9999 else f"{value}px"


def _font_name(value: int, candidates: list[int]) -> str:
    mapping = {12: "caption", 14: "body", 16: "body-large", 20: "h4",
               24: "h3", 32: "h2", 40: "h1"}
    return mapping.get(value, f"_{value}px")


# ── Process a full Figma node ────────────────────────────────────────────────

def snap_figma_node(node: dict, spacing: list[int], radius: list[int],
                    font_sizes: list[int], color_map: dict[str, str]) -> dict:
    """Snap all visual properties in a Figma node dict.

    Recursively processes nested `children[]`.
    Returns a new dict with snapped values and a corrections log.
    """
    result = dict(node)  # shallow copy
    corrections: list[dict] = []

    # Style properties to check
    style_keys = [
        "paddingLeft", "paddingRight", "paddingTop", "paddingBottom",
        "padding", "itemSpacing", "gap",
        "marginLeft", "marginRight", "marginTop", "marginBottom",
        "cornerRadius", "borderRadius", "cornerSmoothing",
        "fontSize", "letterSpacing",
        "fills", "strokes", "background", "backgroundColor",
        "color", "borderColor", "strokeColor", "fillColor",
        "effects",
    ]

    for key in style_keys:
        if key not in node:
            continue
        entry = snap_value(key, node[key], spacing, radius, font_sizes, color_map)
        if entry["was_corrected"]:
            result[key] = entry["snapped"]
            corrections.append(entry)

    # Recurse into children
    if "children" in node and isinstance(node["children"], list):
        result["children"] = []
        for child in node["children"]:
            child_result, child_corrections = snap_figma_node(
                child, spacing, radius, font_sizes, color_map
            )
            result["children"].append(child_result)
            corrections.extend(child_corrections)

    return result, corrections


# ── CLI ───────────────────────────────────────────────────────────────────────

def _load_color_map(path: str | None, repo_root: Path) -> dict[str, str]:
    """Load color map from the design system token file or from a JSON argument."""
    if path:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # Try to auto-load from design-system
    color_file = repo_root / DESIGN_SYSTEM_DIR / "tokens" / "color.md"
    if color_file.exists():
        text = color_file.read_text(encoding="utf-8")
        color_map: dict[str, str] = {}
        for line in text.splitlines():
            # Match: | `color.token` | #HEX | description |
            m = re.match(r"\|\s*`([^`]+)`\s*\|\s*(#[0-9A-Fa-f]{3,8})\s*\|", line)
            if m:
                color_map[m.group(2)] = m.group(1)
        return color_map
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Snap raw Figma values to canonical design tokens.",
    )
    parser.add_argument("--repo-root", type=str, default=str(REPO_ROOT_DEFAULT),
                        help="Repository root path")
    parser.add_argument("--spacing", type=str, default="4,8,12,16,24,32",
                        help="Comma-separated spacing values")
    parser.add_argument("--radius", type=str, default="0,3,6,12,9999",
                        help="Comma-separated radius values")
    parser.add_argument("--font-sizes", type=str, default="12,14,16,20,24,32,40",
                        help="Comma-separated font sizes")
    parser.add_argument("--color-map", type=str, default=None,
                        help="JSON file mapping hex values to token names")
    parser.add_argument("--color-map-json", type=str, default=None,
                        help="Inline JSON color map")

    subparsers = parser.add_subparsers(dest="command", required=True)

    snap_parser = subparsers.add_parser("snap", help="Snap a single JSON object")
    snap_parser.add_argument("--json", type=str, required=True,
                             help="Inline JSON with Figma node attributes")

    snap_file_parser = subparsers.add_parser("snap-file", help="Snap a Figma JSON file")
    snap_file_parser.add_argument("--input", type=str, required=True,
                                  help="Input Figma JSON file path")
    snap_file_parser.add_argument("--output", type=str, default=None,
                                  help="Output snapped JSON file path (default: stdout)")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    spacing = [int(x.strip()) for x in args.spacing.split(",")]
    radius = [int(x.strip()) for x in args.radius.split(",")]
    font_sizes = [int(x.strip()) for x in args.font_sizes.split(",")]

    # Load color map
    color_map: dict[str, str] = {}
    if args.color_map_json:
        color_map = json.loads(args.color_map_json)
    elif args.color_map:
        with open(args.color_map, encoding="utf-8") as f:
            color_map = json.loads(f)
    else:
        color_map = _load_color_map(None, repo_root)

    if args.command == "snap":
        try:
            node = json.loads(args.json)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
            return 1

        snapped_node, corrections = snap_figma_node(
            node, spacing, radius, font_sizes, color_map
        )

        output = {
            "snapped": snapped_node,
            "corrections": corrections,
            "correction_count": len(corrections),
        }
        print(json.dumps(output, indent=2))

    elif args.command == "snap-file":
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
            return 1

        try:
            node = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in {input_path}: {e}", file=sys.stderr)
            return 1

        # Handle both single node and array of nodes
        if isinstance(node, list):
            snapped_list = []
            all_corrections = []
            for n in node:
                snapped_n, corrections_n = snap_figma_node(
                    n, spacing, radius, font_sizes, color_map
                )
                snapped_list.append(snapped_n)
                all_corrections.extend(corrections_n)
            output = {
                "snapped": snapped_list,
                "corrections": all_corrections,
                "correction_count": len(all_corrections),
            }
        else:
            snapped_node, corrections = snap_figma_node(
                node, spacing, radius, font_sizes, color_map
            )
            output = {
                "snapped": snapped_node,
                "corrections": corrections,
                "correction_count": len(corrections),
            }

        output_json = json.dumps(output, indent=2)

        if args.output:
            Path(args.output).write_text(output_json, encoding="utf-8")
            print(f"Snapped -> {args.output} ({len(output['corrections'])} corrections)")
        else:
            print(output_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
