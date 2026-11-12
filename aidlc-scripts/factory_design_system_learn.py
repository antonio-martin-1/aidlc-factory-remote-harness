#!/usr/bin/env python3
"""factory_design_system_learn.py — Learn from approved/rejected UI output.

Saves approved examples and rejected antipatterns into the design system.
Enforces memory caps to prevent unbounded growth.

Subcommands:
  approve   Save an approved UI component as an example, trim to cap, update INDEX
  reject    Save a rejected UI component as a live antipattern
  update-index  Rebuild INDEX.md usage counts from examples directory

Usage:
    python3 aidlc-scripts/factory_design_system_learn.py approve \\
        --component Button --code '<Button variant=\"primary\">...</Button>' \\
        --source src/components/SaveButton.tsx --run-id <run-id>

    python3 aidlc-scripts/factory_design_system_learn.py reject \\
        --component Button --reason 'Missing loading state' \\
        --source src/components/SaveButton.tsx --run-id <run-id>

    python3 aidlc-scripts/factory_design_system_learn.py update-index
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
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


def _examples_dir(repo_root: Path) -> Path:
    return _ds_root(repo_root) / "examples"


def _anti_patterns_dir(repo_root: Path) -> Path:
    return _ds_root(repo_root) / "anti-patterns"


# ── Approve ───────────────────────────────────────────────────────────────────

def approve(repo_root: Path, component: str, code: str,
            source: str, run_id: str) -> dict:
    """Save an approved UI component example and trim to cap.

    Returns a dict with the saved example path and logs.
    """
    primitives = _primitives_dir(repo_root)
    component_dir = primitives / component
    component_dir.mkdir(parents=True, exist_ok=True)

    examples_dir = component_dir / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"approved-{run_id}-{timestamp}.md"
    filepath = examples_dir / filename

    # Extract token measurements from the code
    tokens = _extract_tokens(code)

    content = (
        f"# Approved Example: {component}\n\n"
        f"- **Source**: `{source}`\n"
        f"- **Run ID**: `{run_id}`\n"
        f"- **Approved**: {timestamp}\n\n"
        f"## Code\n"
        f"```tsx\n{code}\n```\n\n"
        f"## Token Measurements\n"
        f"{json.dumps(tokens, indent=2)}\n"
    )

    filepath.write_text(content, encoding="utf-8")

    # Trim to cap
    logs = _trim_primitive_examples(examples_dir)

    logs.insert(0, f"Saved approved {component} example -> {filepath}")

    return {"path": str(filepath), "logs": logs}


def _extract_tokens(code: str) -> dict:
    """Extract spacing, radius, typography, color tokens from TSX code."""
    tokens = {
        "spacing": set(),
        "radius": set(),
        "typography": set(),
        "color": set(),
        "primitives": set(),
    }

    # Detect primitives used
    primitive_pattern = re.compile(
        r'<(Button|Stack|Inline|Box|Surface|Text|Input|Icon)\b'
    )
    tokens["primitives"] = sorted(set(primitive_pattern.findall(code)))

    # Detect semantic props like padding="md", gap="lg", radius="sm"
    prop_pattern = re.compile(
        r'(padding|gap|margin|radius|spacing)=["\']([a-zA-Z]+)["\']'
    )
    for match in prop_pattern.finditer(code):
        prop, val = match.groups()
        if prop in ("padding", "gap", "margin", "spacing"):
            tokens["spacing"].add(val)
        elif prop == "radius":
            tokens["radius"].add(val)

    # Detect typography via variant/size props
    variant_pattern = re.compile(
        r'(variant|size)=["\']([a-zA-Z-]+)["\']'
    )
    for match in variant_pattern.finditer(code):
        tokens["typography"].add(match.group(2))

    # Detect color tokens in color/bg props
    color_pattern = re.compile(
        r'(color|bg|background)=["\']([a-zA-Z.]+)["\']'
    )
    for match in color_pattern.finditer(code):
        tokens["color"].add(match.group(2))

    return {
        k: sorted(v) if isinstance(v, set) else v
        for k, v in tokens.items()
    }


def _trim_primitive_examples(examples_dir: Path) -> list[str]:
    """Keep newest MAX_EXAMPLES_PER_COMPONENT, remove oldest."""
    logs: list[str] = []
    examples = sorted(examples_dir.glob("approved-*.md"))
    if len(examples) <= MAX_EXAMPLES_PER_COMPONENT:
        return logs

    to_remove = examples[:-MAX_EXAMPLES_PER_COMPONENT]
    for old in to_remove:
        old.unlink()
        logs.append(f"  Trimmed {old.name} (exceeded cap of {MAX_EXAMPLES_PER_COMPONENT})")
    return logs


# ── Reject ────────────────────────────────────────────────────────────────────

def reject(repo_root: Path, component: str, reason: str,
           source: str, run_id: str) -> dict:
    """Save a rejected UI as a live antipattern."""
    anti = _anti_patterns_dir(repo_root)
    live_dir = anti / "live"
    live_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(reason)[:40]
    filename = f"{component}-{slug}-{timestamp}.md"
    filepath = live_dir / filename

    content = (
        f"# Antipattern: {component}\n\n"
        f"- **Component**: {component}\n"
        f"- **Source**: `{source}`\n"
        f"- **Run ID**: `{run_id}`\n"
        f"- **Rejected**: {timestamp}\n"
        f"- **Reason**: {reason}\n\n"
        f"## What went wrong\n"
        f"{reason}\n\n"
        f"## Prevention\n"
        f"On next generation of `{component}`, check for this rejection reason "
        f"before finalizing output.\n"
    )

    filepath.write_text(content, encoding="utf-8")

    return {"path": str(filepath), "logs": [f"Saved antipattern -> {filepath}"]}


def _slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9-]', '-', text.lower().strip())


# ── Update INDEX.md ──────────────────────────────────────────────────────────

def update_index(repo_root: Path) -> list[str]:
    """Rebuild usage counts in INDEX.md from examples directory."""
    primitives = _primitives_dir(repo_root)
    index_path = _ds_root(repo_root) / "INDEX.md"
    logs: list[str] = []

    if not index_path.exists():
        return ["INDEX.md not found — skip"]

    usage: dict[str, int] = {}
    for p_dir in sorted(primitives.iterdir()):
        if not p_dir.is_dir():
            continue
        examples_dir = p_dir / "examples"
        if examples_dir.exists():
            count = len(list(examples_dir.glob("approved-*.md")))
            if count > 0:
                usage[p_dir.name] = count

    if not usage:
        return ["No approved examples to update INDEX.md"]

    # Read INDEX, find or append usage section
    content = index_path.read_text(encoding="utf-8")
    usage_lines = ["\n## Usage Count\n\n| Primitive | Approved Examples |\n|-----------|-----------------|\n"]
    for name in sorted(usage):
        usage_lines.append(f"| `{name}` | {usage[name]} |\n")

    # Replace existing usage section or append
    usage_block = "".join(usage_lines)
    if "## Usage Count" in content:
        content = re.sub(
            r"## Usage Count\n\n\| Primitive.*(?:\n\|.*)*",
            usage_block.strip(),
            content,
        )
    else:
        content += "\n" + usage_block

    index_path.write_text(content, encoding="utf-8")
    logs.append(f"Updated INDEX.md with {len(usage)} usage counts")
    return logs


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Learn from approved/rejected UI output.",
    )
    parser.add_argument("--repo-root", type=str, default=str(REPO_ROOT_DEFAULT),
                        help="Repository root path")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # approve
    approve_parser = subparsers.add_parser("approve", help="Save an approved UI example")
    approve_parser.add_argument("--component", type=str, required=True,
                                help="Primitive component name")
    approve_parser.add_argument("--code", type=str, required=True,
                                help="TSX/JSX code of the approved output")
    approve_parser.add_argument("--source", type=str, required=True,
                                help="Source file path")
    approve_parser.add_argument("--run-id", type=str, required=True,
                                help="AIDLC run identifier")

    # reject
    reject_parser = subparsers.add_parser("reject", help="Save a rejected UI antipattern")
    reject_parser.add_argument("--component", type=str, required=True,
                               help="Primitive component name")
    reject_parser.add_argument("--reason", type=str, required=True,
                               help="Rejection reason")
    reject_parser.add_argument("--source", type=str, required=True,
                               help="Source file path")
    reject_parser.add_argument("--run-id", type=str, required=True,
                               help="AIDLC run identifier")

    # trim
    subparsers.add_parser("trim", help="Enforce memory cap across all primitives")

    # update-index
    subparsers.add_parser("update-index", help="Rebuild INDEX.md usage counts")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.command == "approve":
        result = approve(repo_root, args.component, args.code,
                         args.source, args.run_id)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for line in result["logs"]:
                print(line)

    elif args.command == "reject":
        result = reject(repo_root, args.component, args.reason,
                        args.source, args.run_id)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for line in result["logs"]:
                print(line)

    elif args.command == "trim":
        primitives = _primitives_dir(repo_root)
        logs: list[str] = []
        for p_dir in sorted(primitives.iterdir()):
            if not p_dir.is_dir():
                continue
            examples_dir = p_dir / "examples"
            if examples_dir.exists():
                logs += _trim_primitive_examples(examples_dir)
        if not logs:
            logs.append("All primitives within cap — nothing to trim")
        for line in logs:
            print(line)

    elif args.command == "update-index":
        logs = update_index(repo_root)
        for line in logs:
            print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
