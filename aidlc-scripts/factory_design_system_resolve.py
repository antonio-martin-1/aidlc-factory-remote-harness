#!/usr/bin/env python3
"""factory_design_system_resolve.py — Lazy-load design system files.

Injects only the design system files that match requested component names.
Keeps context lean — no full-system blast.

Subcommands:
  resolve   Given component names, output the matching design.md + anatomy.md
            files and the global token files.
  list      List all available primitives in the design system.
  trim      Enforce memory cap: max 3 examples per component.

Usage:
    python3 aidlc-scripts/factory_design_system_resolve.py resolve Button Input
    python3 aidlc-scripts/factory_design_system_resolve.py list
    python3 aidlc-scripts/factory_design_system_resolve.py trim
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
MAX_EXAMPLES_PER_COMPONENT = 3


# ── Path helpers ──────────────────────────────────────────────────────────────

def _ds_root(repo_root: Path) -> Path:
    return repo_root / DESIGN_SYSTEM_DIR


def _primitives_dir(repo_root: Path) -> Path:
    return _ds_root(repo_root) / "primitives"


def _tokens_dir(repo_root: Path) -> Path:
    return _ds_root(repo_root) / "tokens"


def _examples_dir(repo_root: Path) -> Path:
    return _ds_root(repo_root) / "examples"


def _patterns_dir(repo_root: Path) -> Path:
    return _ds_root(repo_root) / "patterns"


def _anti_patterns_dir(repo_root: Path) -> Path:
    return _ds_root(repo_root) / "anti-patterns"


# ── Available primitives ──────────────────────────────────────────────────────

def list_primitives(repo_root: Path, as_json: bool = False) -> list[dict] | str:
    """List all available primitives with their file stats."""
    primitives = _primitives_dir(repo_root)
    results: list[dict] = []

    if not primitives.exists():
        return [] if as_json else "No design system primitives found."

    for p_dir in sorted(primitives.iterdir()):
        if not p_dir.is_dir():
            continue
        name = p_dir.name
        has_design = (p_dir / "design.md").exists()
        has_anatomy = (p_dir / "anatomy.md").exists()
        has_dodont = (p_dir / "do-dont.md").exists()
        has_ref = (p_dir / f"{name}.tsx").exists()
        example_count = len(list(p_dir.rglob("examples/*.md")))

        results.append({
            "name": name,
            "design": has_design,
            "anatomy": has_anatomy,
            "do_dont": has_dodont,
            "reference": has_ref,
            "examples": example_count,
        })

    if as_json:
        return results

    if not results:
        return "No design system primitives found."

    lines = ["Available primitives:"]
    for r in results:
        tags = []
        if r["design"]:
            tags.append("design")
        if r["anatomy"]:
            tags.append("anatomy")
        if r["reference"]:
            tags.append("ref")
        lines.append(f"  {r['name']:12s} [{', '.join(tags)}]  {r['examples']} example(s)")
    return "\n".join(lines)


# ── Resolve ───────────────────────────────────────────────────────────────────

def resolve(repo_root: Path, component_names: list[str],
            include_patterns: bool = False,
            include_anti_patterns: bool = False) -> dict:
    """Return a dict with paths to design system files matching the request.

    Always includes global token files + INDEX.md.
    For each component: design.md, anatomy.md, do-dont.md (if exists).
    """
    result: dict[str, list[str]] = {
        "tokens": [],
        "primitives": {},
        "patterns": [],
        "anti_patterns": [],
        "index": [],
    }

    ds = _ds_root(repo_root)
    if not ds.exists():
        return result

    # INDEX.md
    index_path = ds / "INDEX.md"
    if index_path.exists():
        result["index"].append(str(index_path))

    # Global tokens
    tokens = _tokens_dir(repo_root)
    if tokens.exists():
        for f in sorted(tokens.iterdir()):
            if f.suffix == ".md":
                result["tokens"].append(str(f))

    # Per-component files
    primitives = _primitives_dir(repo_root)
    for name in component_names:
        comp_dir = primitives / name
        if not comp_dir.is_dir():
            continue

        comp_files: list[str] = []

        for fname in ("design.md", "anatomy.md", "do-dont.md"):
            fp = comp_dir / fname
            if fp.exists():
                comp_files.append(str(fp))

        # Reference implementation if exists
        ref = comp_dir / f"{name}.tsx"
        if ref.exists():
            comp_files.append(str(ref))

        # Examples (capped at MAX_EXAMPLES_PER_COMPONENT)
        examples_dir = comp_dir / "examples"
        if examples_dir.exists():
            examples = sorted(examples_dir.glob("*.md"))
            for ex in examples[:MAX_EXAMPLES_PER_COMPONENT]:
                comp_files.append(str(ex))

        if comp_files:
            result["primitives"][name] = comp_files

    # Optional: load patterns
    if include_patterns:
        patterns = _patterns_dir(repo_root)
        if patterns.exists():
            for f in sorted(patterns.iterdir()):
                if f.suffix == ".md":
                    result["patterns"].append(str(f))

    # Optional: load anti-patterns (including live/ subdirectory)
    if include_anti_patterns:
        anti = _anti_patterns_dir(repo_root)
        if anti.exists():
            for f in sorted(anti.iterdir()):
                if f.suffix == ".md":
                    result["anti_patterns"].append(str(f))
            # Also load live/ antipatterns
            live_dir = anti / "live"
            if live_dir.exists():
                for f in sorted(live_dir.iterdir()):
                    if f.suffix == ".md":
                        result["anti_patterns"].append(str(f))

    return result


# ── Trim examples (memory cap) ────────────────────────────────────────────────

def trim_examples(repo_root: Path, dry_run: bool = False) -> list[str]:
    """Enforce MAX_EXAMPLES_PER_COMPONENT per component examples directory.

    Keeps the newest N examples, removes oldest.
    Called by ship-agent after each approval.
    """
    logs: list[str] = []
    primitives = _primitives_dir(repo_root)
    if not primitives.exists():
        return ["No primitives directory to trim."]

    for p_dir in sorted(primitives.iterdir()):
        if not p_dir.is_dir():
            continue
        examples_dir = p_dir / "examples"
        if not examples_dir.exists():
            continue

        examples = sorted(examples_dir.glob("approved-*.md"))
        if len(examples) <= MAX_EXAMPLES_PER_COMPONENT:
            continue

        to_remove = examples[:-MAX_EXAMPLES_PER_COMPONENT]
        for old in to_remove:
            if dry_run:
                logs.append(f"[DRY-RUN] Would remove {old}")
            else:
                old.unlink()
                logs.append(f"Removed {old.name} (exceeded cap of {MAX_EXAMPLES_PER_COMPONENT})")

    return logs if logs else ["All primitives within example cap."]


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lazy-load design system files for AIDLC code generation.",
    )
    parser.add_argument(
        "--repo-root", type=str, default=str(REPO_ROOT_DEFAULT),
        help="Repository root path (default: parent of this script)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON (for machine consumption)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # resolve
    resolve_parser = subparsers.add_parser("resolve", help="Resolve files for components")
    resolve_parser.add_argument("components", nargs="+", help="Component names")
    resolve_parser.add_argument("--with-patterns", action="store_true",
                                help="Include all patterns/ files")
    resolve_parser.add_argument("--with-anti-patterns", action="store_true",
                                help="Include all anti-patterns/ files")

    # list
    subparsers.add_parser("list", help="List available primitives")

    # trim
    trim_parser = subparsers.add_parser("trim", help="Enforce example cap per component")
    trim_parser.add_argument("--dry-run", action="store_true", help="Preview without deleting")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.command == "resolve":
        result = resolve(
            repo_root, args.components,
            include_patterns=args.with_patterns,
            include_anti_patterns=args.with_anti_patterns,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Design system resolved for: {', '.join(args.components)}")
            if result["tokens"]:
                print(f"\n  Tokens ({len(result['tokens'])} files):")
                for t in result["tokens"]:
                    print(f"    {t}")
            if result["primitives"]:
                print(f"\n  Primitives ({len(result['primitives'])}):")
                for name, files in result["primitives"].items():
                    print(f"    {name}:")
                    for f in files:
                        print(f"      {f}")
            if result["patterns"]:
                print(f"\n  Patterns ({len(result['patterns'])} files):")
                for p in result["patterns"]:
                    print(f"    {p}")

    elif args.command == "list":
        if args.json:
            data = list_primitives(repo_root, as_json=True)
            print(json.dumps(data, indent=2))
        else:
            print(list_primitives(repo_root))

    elif args.command == "trim":
        logs = trim_examples(repo_root, dry_run=args.dry_run)
        for line in logs:
            print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
