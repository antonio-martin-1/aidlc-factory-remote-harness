#!/usr/bin/env python3
"""factory_design_system_extract_brownfield.py — Extract design tokens from existing code.

Detects and parses existing design system configurations in a brownfield project:
  - tailwind.config.{js,ts}
  - MUI createTheme() objects
  - Chakra UI theme.ts
  - CSS Custom Properties (:root)
  - CSS files with design tokens

Generates design-system/tokens/*.md files from the detected source.

Usage:
    python3 aidlc-scripts/factory_design_system_extract_brownfield.py detect
    python3 aidlc-scripts/factory_design_system_extract_brownfield.py extract --source tailwind
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


_SCRIPT_DIR = Path(__file__).parent
REPO_ROOT_DEFAULT = _SCRIPT_DIR.parent


# ── Source detection ───────────────────────────────────────────────────────

def detect_sources(repo_root: Path) -> list[dict]:
    """Scan the project for design system configuration files."""
    sources: list[dict] = []
    files_to_check = [
        ("tailwind.config.js", "tailwind", "Tailwind CSS config"),
        ("tailwind.config.ts", "tailwind", "Tailwind CSS config (TypeScript)"),
        ("tailwind.config.mjs", "tailwind", "Tailwind CSS config (ESM)"),
        ("theme.ts", "mui", "MUI theme (createTheme)"),
        ("theme.js", "mui", "MUI theme (createTheme)"),
        ("src/theme.ts", "chakra", "Chakra UI theme"),
        ("src/styles/variables.css", "css_vars", "CSS Custom Properties"),
        ("src/styles/tokens.css", "css_vars", "CSS Custom Properties"),
        ("styles/variables.css", "css_vars", "CSS Custom Properties"),
        ("app/theme.ts", "mui", "MUI theme (Next.js app dir)"),
    ]

    for filepath, source_type, description in files_to_check:
        full_path = repo_root / filepath
        if full_path.exists():
            sources.append({
                "type": source_type,
                "path": str(full_path),
                "description": description,
            })

    # Also scan CSS files for :root with design tokens
    css_dirs = [
        repo_root / "src" / "styles",
        repo_root / "src",
        repo_root / "styles",
    ]
    for css_dir in css_dirs:
        if css_dir.exists():
            for f in sorted(css_dir.glob("**/*.css")):
                content = f.read_text(encoding="utf-8", errors="ignore")
                if ":root" in content and "--" in content:
                    if not any(s["path"] == str(f) for s in sources):
                        sources.append({
                            "type": "css_vars",
                            "path": str(f),
                            "description": f"CSS Custom Properties ({f.name})",
                        })

    return sources


# ── Extractors ─────────────────────────────────────────────────────────────

def extract_tailwind(repo_root: Path, config_path: str | Path) -> dict[str, Any]:
    """Extract tokens from a Tailwind config file."""
    path = Path(config_path)
    content = path.read_text(encoding="utf-8")
    result: dict[str, Any] = {"source": "tailwind", "tokens": {}}

    categories = ["spacing", "colors", "borderRadius", "fontSize"]
    for cat in categories:
        tokens = _extract_tailwind_category(content, cat)
        if tokens:
            result["tokens"][cat] = tokens

    return result


def _extract_tailwind_category(content: str, category: str) -> dict[str, str] | None:
    """Extract a category's key-value pairs from Tailwind config JS.

    Handles nested braces, single-line objects, and both CJS/ESM formats.
    """
    # Find the category block: spacing: { ... }
    pattern = re.compile(
        r'(?:' + re.escape(category) + r')\s*:\s*\{',
        re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        return None

    start = m.end()
    depth = 1
    pos = start
    while pos < len(content) and depth > 0:
        if content[pos] == '{':
            depth += 1
        elif content[pos] == '}':
            depth -= 1
        pos += 1

    block = content[start:pos - 1]
    result: dict[str, str] = {}

    # Regex handles both single-line and multi-line entries
    # Matches: 'xs': '4px'  or  "xs": "4px"  or  xs: '4px'
    entry_re = re.compile(r"['\"]?(\w[\w-]*)['\"]?\s*:\s*['\"]?([^,'\"}\s]+)['\"]?")
    for m2 in entry_re.finditer(block):
        key = m2.group(1)
        val = m2.group(2).strip("'\"")
        if key and val and not val.startswith("{") and not key.startswith("//"):
            result[key] = val

    return result if result else None


def extract_css_vars(repo_root: Path, css_path: str | Path) -> dict[str, Any]:
    """Extract tokens from CSS Custom Properties."""
    path = Path(css_path)
    content = path.read_text(encoding="utf-8")
    result: dict[str, Any] = {"source": "css_vars", "tokens": {}}

    # Find :root block
    root_m = re.search(r":root\s*{([^}]+)}", content, re.DOTALL)
    if not root_m:
        return result

    root_block = root_m.group(1)
    var_pattern = re.compile(r'--([a-zA-Z][\w-]*)\s*:\s*([^;]+)')
    raw_vars: dict[str, str] = {}

    for m in var_pattern.finditer(root_block):
        raw_vars[m.group(1)] = m.group(2).strip()

    result["raw_vars"] = raw_vars

    # Categorize
    for key, val in raw_vars.items():
        if any(k in key for k in ("spacing", "space", "gap", "pad", "margin")):
            result["tokens"].setdefault("spacing", {})[key] = val
        elif any(k in key for k in ("radius", "rounded", "corner")):
            result["tokens"].setdefault("radius", {})[key] = val
        elif any(k in key for k in ("font", "type", "text")):
            result["tokens"].setdefault("typography", {})[key] = val
        elif any(k in key for k in ("color", "bg", "background", "text", "border")):
            result["tokens"].setdefault("color", {})[key] = val
        elif any(k in key for k in ("shadow", "elevation", "z-index")):
            result["tokens"].setdefault("elevation", {})[key] = val

    return result


# ── DSM output generation ─────────────────────────────────────────────────

def _snap_key(raw_key: str) -> str:
    """Convert a CSS var name like --spacing-md or --color-primary to a token key."""
    parts = raw_key.lstrip("-").split("-", 1)
    return "-".join(parts).replace("-", ".") if len(parts) > 1 else parts[0]


def write_tokens_from_extraction(repo_root: Path, extracted: dict[str, Any]) -> list[str]:
    """Write extracted tokens to design-system/tokens/*.md files.

    Returns list of paths written.
    """
    tokens_dir = repo_root / "design-system" / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    category_map = {
        "spacing": "Spacing Tokens (extracted from brownfield)",
        "radius": "Radius Tokens (extracted from brownfield)",
        "typography": "Typography Tokens (extracted from brownfield)",
        "color": "Color Tokens (extracted from brownfield)",
        "elevation": "Elevation Tokens (extracted from brownfield)",
    }

    for category, title in category_map.items():
        tokens = extracted.get("tokens", {}).get(category, {})
        if not tokens:
            continue

        file_path = tokens_dir / f"{category}.md"
        lines = [
            f"# {title}",
            f"# Source: {extracted.get('source', 'unknown')}",
            f"# Extracted at: {__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}",
            "",
            "| Token | Value | Description |",
            "|-------|-------|-------------|",
        ]
        for key, val in tokens.items():
            token_name = f"{category}.{_snap_key(key)}"
            lines.append(f"| `{token_name}` | {val} | Extracted |")

        lines.append("")
        file_path.write_text("\n".join(lines), encoding="utf-8")
        written.append(str(file_path))

    return written


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract design tokens from existing brownfield code.",
    )
    parser.add_argument("--repo-root", type=str, default=str(REPO_ROOT_DEFAULT),
                        help="Repository root path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_p = subparsers.add_parser("detect", help="Detect design system sources")
    detect_p.add_argument("--json", action="store_true", help="JSON output")

    extract_p = subparsers.add_parser("extract", help="Extract tokens from a specific source")
    extract_p.add_argument("--source", required=True, choices=["tailwind", "css_vars", "auto"],
                           help="Source type to extract from")
    extract_p.add_argument("--path", type=str, default=None,
                           help="Specific file path (auto-detected if omitted)")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.command == "detect":
        sources = detect_sources(repo_root)
        if args.json:
            print(json.dumps(sources, indent=2))
        else:
            if not sources:
                print("No design system sources detected.")
                return 0
            print(f"Found {len(sources)} design system source(s):")
            for s in sources:
                print(f"  [{s['type']:10s}] {s['path']}  ({s['description']})")

    elif args.command == "extract":
        if args.source == "auto":
            sources = detect_sources(repo_root)
            if not sources:
                print("No design system sources detected. Run `detect` first.")
                return 1
            source_info = sources[0]
        else:
            if args.path:
                source_info = {"type": args.source, "path": args.path}
            else:
                sources = detect_sources(repo_root)
                matches = [s for s in sources if s["type"] == args.source]
                if not matches:
                    print(f"No {args.source} source detected.")
                    return 1
                source_info = matches[0]

        print(f"Extracting from: [{source_info['type']}] {source_info['path']}")

        if source_info["type"] == "tailwind":
            extracted = extract_tailwind(repo_root, source_info["path"])
        elif source_info["type"] == "css_vars":
            extracted = extract_css_vars(repo_root, source_info["path"])
        else:
            print(f"Unsupported source type: {source_info['type']}")
            return 1

        written = write_tokens_from_extraction(repo_root, extracted)
        if written:
            print(f"\nWrote {len(written)} token file(s):")
            for w in written:
                print(f"  {w}")
        else:
            print("\nNo tokens extracted.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
