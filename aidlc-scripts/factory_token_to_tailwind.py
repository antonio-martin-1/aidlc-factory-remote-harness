#!/usr/bin/env python3
"""factory_token_to_tailwind.py — Generate Tailwind config from design tokens.

Reads design-system/tokens/*.md and produces a tailwind.config.js with
theme.extend values mapped from the canonical token set.

Usage:
    python3 aidlc-scripts/factory_token_to_tailwind.py generate
    python3 aidlc-scripts/factory_token_to_tailwind.py generate --output tailwind.config.js
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


_SCRIPT_DIR = Path(__file__).parent
REPO_ROOT_DEFAULT = _SCRIPT_DIR.parent
TOKENS_DIR = "design-system/tokens"


# ── Token parsers (shared logic with factory_token_to_css.py) ──────────────

def _parse_spacing(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`spacing\.(\w+)`\s*\|\s*(\d+)", line)
        if m:
            result[m.group(1)] = m.group(2)
    return result


def _parse_radius(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`radius\.(\w+)`\s*\|\s*(\d+)", line)
        if m:
            val = int(m.group(2))
            result[m.group(1)] = "9999px" if val >= 9999 else f"{val}px"
    return result


def _parse_typography(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`font-size\.([a-z][a-z0-9-]*)`\s*\|\s*(\d+)", line)
        if m:
            result[m.group(1)] = m.group(2)
    return result


def _parse_color(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`([a-z.]+)`\s*\|\s*(#[0-9A-Fa-f]{3,8}|rgba?\([^)]+\))\s*\|", line)
        if m:
            key = m.group(1)
            if key.startswith("color."):
                key = key[6:]
            result[key] = m.group(2).lower()
    return result


_PARSERS: dict[str, tuple[str, Any, str]] = {
    "spacing": ("Spacing", _parse_spacing, "spacing"),
    "radius": ("Border Radius", _parse_radius, "borderRadius"),
    "typography": ("Font Sizes", _parse_typography, "fontSize"),
    "color": ("Colors", _parse_color, "colors"),
}


# ── Tailwind Config JS generation ─────────────────────────────────────────

def _tw_value(category: str, key: str, value: str) -> str:
    if category == "spacing":
        return value
    elif category == "radius":
        return value
    elif category == "typography":
        return f"{value}px"
    elif category == "color":
        return value
    return value


def _tw_key(category: str, key: str) -> str:
    if category == "color":
        return key.replace(".", "-")
    return key


def generate_tailwind_config(repo_root: Path, esm: bool = False) -> str:
    tokens_dir = repo_root / TOKENS_DIR
    if not tokens_dir.exists():
        return "// No design-system/tokens/ directory found\nmodule.exports = { theme: { extend: {} } };\n"

    extend: dict[str, Any] = {}

    for category, (_, parser, tw_key) in _PARSERS.items():
        path = tokens_dir / f"{category}.md"
        if not path.exists():
            continue
        tokens = parser(path)
        if not tokens:
            continue

        if tw_key == "spacing":
            extend["spacing"] = {}
            for key, val in tokens.items():
                extend["spacing"][_tw_key(category, key)] = int(val)
        elif tw_key == "borderRadius":
            extend["borderRadius"] = {}
            for key, val in tokens.items():
                extend["borderRadius"][_tw_key(category, key)] = val
        elif tw_key == "fontSize":
            extend["fontSize"] = {}
            for key, val in tokens.items():
                extend["fontSize"][_tw_key(category, key)] = f"{val}px"
        elif tw_key == "colors":
            extend["colors"] = {}
            for key, val in tokens.items():
                extend["colors"][_tw_key(category, key)] = val

    indent = "  "
    lines = [
        "// Design System Tokens — auto-generated",
        "// Run: factory_token_to_tailwind.py generate",
    ]
    if esm:
        lines.append("")
        lines.append("/** @type {import('tailwindcss').Config} */")
        lines.append("const config = {")
        lines.append(f'{indent}content: ["./src/**/{{js,ts,jsx,tsx,html}}"],')
    else:
        lines.append("")
        lines.append("/** @type {import('tailwindcss').Config} */")
        lines.append("module.exports = {")
        lines.append(f'{indent}content: ["./src/**/{{js,ts,jsx,tsx,html}}"],')

    lines.append(f"{indent}theme: {{")
    lines.append(f"{indent}{indent}extend: {{")

    for tw_key, values in extend.items():
        if not values:
            continue
        lines.append(f"{indent}{indent}{indent}{tw_key}: {{")
        for k, v in values.items():
            val_str = json.dumps(v) if isinstance(v, str) else str(v)
            lines.append(f"{indent}{indent}{indent}{indent}'{k}': {val_str},")
        lines.append(f"{indent}{indent}{indent}}},")

    lines.append(f"{indent}{indent}}}, // end extend")
    lines.append(f"{indent}}}, // end theme")
    lines.append("};")

    if esm:
        lines.append("")
        lines.append("export default config;")
    else:
        lines.append("")
        lines.append("module.exports = config;")

    return "\n".join(lines)


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Tailwind config from design tokens.",
    )
    parser.add_argument("--repo-root", type=str, default=str(REPO_ROOT_DEFAULT),
                        help="Repository root path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_p = subparsers.add_parser("generate", help="Generate tailwind.config.js")
    gen_p.add_argument("--output", type=str, default=None,
                       help="Output JS file (default: stdout)")
    gen_p.add_argument("--esm", action="store_true",
                       help="Generate ES module export (default: CommonJS)")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.command == "generate":
        config = generate_tailwind_config(repo_root, esm=args.esm)
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(config, encoding="utf-8")
            print(f"Wrote {out} ({len(config)} bytes)")
        else:
            print(config)

    return 0


if __name__ == "__main__":
    sys.exit(main())
