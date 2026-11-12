#!/usr/bin/env python3
"""factory_token_to_css.py — Generate CSS Custom Properties from design tokens.

Reads design-system/tokens/*.md and produces a tokens.css file with CSS
Custom Properties. Framework-agnostic — works for any web project.

Subcommands:
  generate    Read tokens and output tokens.css
  inspect     Show what tokens would be generated (JSON)

Usage:
    python3 aidlc-scripts/factory_token_to_css.py generate
    python3 aidlc-scripts/factory_token_to_css.py generate --output design-system/tokens/tokens.css
    python3 aidlc-scripts/factory_token_to_css.py inspect
    python3 aidlc-scripts/factory_token_to_css.py inspect --format css
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


# ── Token parsers ──────────────────────────────────────────────────────────

def _parse_spacing(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`spacing\.(\w+)`\s*\|\s*(\d+)", line)
        if m:
            result[m.group(1)] = f"{m.group(2)}px"
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
            result[m.group(1)] = f"{m.group(2)}px"
    return result


def _parse_color(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`([a-z.]+)`\s*\|\s*(#[0-9A-Fa-f]{3,8}|rgba?\([^)]+\))\s*\|", line)
        if m:
            result[m.group(1)] = m.group(2).lower()
    return result


def _parse_elevation(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`elevation\.(\w+)`\s*\|\s*(\d+)", line)
        if m:
            result[m.group(1)] = f"var(--elevation-{m.group(1)})"
    return result


_PARSERS: dict[str, tuple[str, Any]] = {
    "spacing": ("Spacing — multiples of 4", _parse_spacing),
    "radius": ("Border Radius — 0, 3, 6, 12, 9999", _parse_radius),
    "typography": ("Font Sizes — caption, body, h1-h4", _parse_typography),
    "color": ("Colors — brand, neutral, semantic, overlay", _parse_color),
    "elevation": ("Elevation / Shadows", _parse_elevation),
}


# ── CSS generation ─────────────────────────────────────────────────────────

def _css_var_name(category: str, key: str) -> str:
    prefix = f"{category}."
    if key.startswith(prefix):
        key = key[len(prefix):]
    return f"--{category}-{key}"


def generate_css(repo_root: Path, include_raw_values: bool = False) -> str:
    tokens_dir = repo_root / TOKENS_DIR
    if not tokens_dir.exists():
        return "/* No design-system/tokens/ directory found */\n"

    sections: list[str] = []
    sections.append("/* ═══════════════════════════════════════════════ */")
    sections.append("/*  Design System Tokens — auto-generated          */")
    sections.append("/*  Run: factory_token_to_css.py generate          */")
    sections.append("/* ═══════════════════════════════════════════════ */")
    sections.append("")

    for category, (description, parser) in _PARSERS.items():
        path = tokens_dir / f"{category}.md"
        if not path.exists():
            continue

        tokens = parser(path)
        if not tokens:
            continue

        sections.append(f"/* ── {description} ── */")
        lines: list[str] = []
        for key, value in tokens.items():
            var = _css_var_name(category, key)
            lines.append(f"  {var}: {value};")

        if lines:
            sections.append(":root {")
            sections.extend(lines)
            sections.append("}")
            sections.append("")

            if include_raw_values:
                for key, value in tokens.items():
                    raw_key = _css_var_name(category, f"raw-{key}")
                    raw_value = value.replace("px", "")
                    sections.append(f"  /* {raw_key}: {raw_value} (as number) */")

    return "\n".join(sections)


# ── Inspection ─────────────────────────────────────────────────────────────

def inspect_tokens(repo_root: Path) -> dict[str, Any]:
    tokens_dir = repo_root / TOKENS_DIR
    result: dict[str, Any] = {}
    if not tokens_dir.exists():
        return {"error": f"Not found: {tokens_dir}"}

    for category, (description, parser) in _PARSERS.items():
        path = tokens_dir / f"{category}.md"
        if not path.exists():
            result[category] = {"exists": False, "tokens": []}
            continue
        tokens = parser(path)
        result[category] = {
            "exists": True,
            "description": description,
            "count": len(tokens),
            "tokens": tokens,
        }
    result["_meta"] = {
        "source": str(tokens_dir),
        "categories": sum(1 for v in result.values() if isinstance(v, dict) and v.get("exists")),
    }
    return result


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate CSS Custom Properties from design tokens.",
    )
    parser.add_argument("--repo-root", type=str, default=str(REPO_ROOT_DEFAULT),
                        help="Repository root path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_p = subparsers.add_parser("generate", help="Generate tokens.css")
    gen_p.add_argument("--output", type=str, default=None,
                       help="Output CSS file (default: stdout)")
    gen_p.add_argument("--with-raw", action="store_true",
                       help="Include raw numeric values as comments")

    ins_p = subparsers.add_parser("inspect", help="Inspect available tokens")
    ins_p.add_argument("--format", choices=["json", "css"], default="json",
                       help="Output format")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.command == "generate":
        css = generate_css(repo_root, include_raw_values=args.with_raw)
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(css, encoding="utf-8")
            print(f"Wrote {out} ({len(css)} bytes)")
        else:
            print(css)

    elif args.command == "inspect":
        data = inspect_tokens(repo_root)
        if args.format == "css":
            print(generate_css(repo_root))
        else:
            print(json.dumps(data, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
