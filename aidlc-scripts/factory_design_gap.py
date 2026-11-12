#!/usr/bin/env python3
"""factory_design_gap.py — Construction design artifact gate (shared + per-unit).

Shared construction design docs are run-scoped and written once. Per-unit work
only requires the code-generation plan. This checker replaces the old
"rewrite five design docs on every unit" DesignGap ritual.

Usage
-----
    factory_design_gap.py check <run-id> --unit <unit-name> [--repo-root .]
    factory_design_gap.py check-shared <run-id> [--repo-root .]
    factory_design_gap.py list-shared <run-id> [--repo-root .]

Exit codes
----------
    0  all required artifacts present
    1  missing artifacts (paths listed on stderr as JSON)
    2  usage / IO error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from skill_utils import _log
except ImportError:
    def _log(level: str, msg: str, **kwargs) -> None:
        stream = sys.stderr if level in ("ERROR", "WARNING") else sys.stdout
        print(f"[{level}] {msg}", file=stream)


SHARED_DESIGN_SUFFIXES = (
    "business-logic-model.md",
    "domain-entities.md",
    "nfr-requirements.md",
    "nfr-design-patterns.md",
    "infrastructure-design.md",
)


def _die(msg: str, code: int = 2) -> None:
    _log("ERROR", msg)
    sys.exit(code)


def shared_design_paths(repo_root: Path, run_id: str) -> list[Path]:
    design = repo_root / "aidlc-docs" / "construction" / "design"
    return [design / f"{run_id}-{suffix}" for suffix in SHARED_DESIGN_SUFFIXES]


def unit_plan_path(repo_root: Path, run_id: str, unit: str) -> Path:
    return (
        repo_root
        / "aidlc-docs"
        / "construction"
        / "plans"
        / f"{run_id}-{unit}-code-generation-plan.md"
    )


def missing_paths(paths: list[Path]) -> list[str]:
    return [str(p.as_posix()) for p in paths if not p.is_file()]


def cmd_list_shared(args: argparse.Namespace) -> None:
    root = Path(args.repo_root).resolve()
    paths = shared_design_paths(root, args.run_id)
    print(json.dumps({"run_id": args.run_id, "shared_design": [str(p.as_posix()) for p in paths]}, indent=2))


def cmd_check_shared(args: argparse.Namespace) -> None:
    root = Path(args.repo_root).resolve()
    missing = missing_paths(shared_design_paths(root, args.run_id))
    payload = {
        "run_id": args.run_id,
        "ok": not missing,
        "missing": missing,
        "scope": "shared",
    }
    print(json.dumps(payload, indent=2))
    if missing:
        _log("ERROR", f"[DesignGap] shared construction design missing: {', '.join(missing)}")
        sys.exit(1)


def cmd_check(args: argparse.Namespace) -> None:
    root = Path(args.repo_root).resolve()
    unit = args.unit
    if not unit:
        _die("--unit is required for check")
    required = shared_design_paths(root, args.run_id) + [unit_plan_path(root, args.run_id, unit)]
    missing = missing_paths(required)
    payload = {
        "run_id": args.run_id,
        "unit": unit,
        "ok": not missing,
        "missing": missing,
        "scope": "unit+shared",
        "note": (
            "Shared design docs are run-scoped (written once). "
            "Per-unit requirement is the code-generation plan only."
        ),
    }
    print(json.dumps(payload, indent=2))
    if missing:
        _log(
            "ERROR",
            f"[DesignGap] Unit {unit}: construction artifacts missing: {', '.join(missing)}",
        )
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="factory_design_gap.py",
        description="Check Construction shared design + per-unit plan artifacts.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def _add_root(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--repo-root",
            default=".",
            help="Project root (default: cwd)",
        )

    p_check = sub.add_parser("check", help="shared design + unit plan")
    p_check.add_argument("run_id")
    p_check.add_argument("--unit", required=True)
    _add_root(p_check)
    p_check.set_defaults(func=cmd_check)

    p_shared = sub.add_parser("check-shared", help="shared design docs only")
    p_shared.add_argument("run_id")
    _add_root(p_shared)
    p_shared.set_defaults(func=cmd_check_shared)

    p_list = sub.add_parser("list-shared", help="print shared design paths")
    p_list.add_argument("run_id")
    _add_root(p_list)
    p_list.set_defaults(func=cmd_list_shared)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
