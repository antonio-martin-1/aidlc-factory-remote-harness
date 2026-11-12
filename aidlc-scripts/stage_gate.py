#!/usr/bin/env python3
"""stage_gate.py — Stage Gate Enforcement for AIDLC Orchestrator.

Validates that prerequisite stages are completed before allowing a stage to run.
This prevents agents from skipping mandatory stages.

Usage:
    python3 aidlc-scripts/stage_gate.py check <run-id> <stage>
        Exit 0 if stage can run (all prerequisites completed).
        Exit 1 if stage CANNOT run (missing prerequisites).
        Exit 2 if run not found or other error.

    python3 aidlc-scripts/stage_gate.py list <run-id>
        List all stages and their completion status.

    python3 aidlc-scripts/stage_gate.py next <run-id>
        Show the next stage that should run.

Stage prerequisites (MUST match core-workflow.md):
    workspace-scout:          (none — first stage)
    requirements-analyst:     workspace-scout
    reverse-engineer:         workspace-scout  (brownfield only)
    product-pass:             requirements-analyst
    design-pass:              product-pass
    arch-pass:                product-pass, design-pass
    story-writer:             requirements-analyst  (legacy mode only)
    application-designer:     requirements-analyst  (legacy mode only)
    workflow-planner:         requirements-analyst
    unit-decomposer:          workflow-planner
    code-generator:           workflow-planner  (or unit-decomposer if present)
    build-test-agent:         code-generator
    reviewer-*:               code-generator
    ship-agent:               reviewer-*
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = REPO_ROOT / ".aidlc-orchestrator" / "runs"

# Stage dependency graph — MUST stay in sync with core-workflow.md
STAGE_ORDER = [
    "workspace-scout",
    "requirements-analyst",
    "reverse-engineer",
    "product-pass",
    "design-pass",
    "arch-pass",
    "story-writer",
    "application-designer",
    "workflow-planner",
    "unit-decomposer",
    "code-generator",
    "build-test-agent",
    "reviewer-code",
    "reviewer-security",
    "reviewer-performance",
    "reviewer-simplifier",
    "ship-agent",
]

STAGE_PREREQUISITES: dict[str, list[str]] = {
    "workspace-scout": [],
    "requirements-analyst": ["workspace-scout"],
    "reverse-engineer": ["workspace-scout"],  # brownfield only
    "product-pass": ["requirements-analyst"],
    "design-pass": ["product-pass"],
    "arch-pass": ["product-pass", "design-pass"],
    "story-writer": ["requirements-analyst"],  # legacy mode only
    "application-designer": ["requirements-analyst"],  # legacy mode only
    "workflow-planner": ["requirements-analyst"],
    "unit-decomposer": ["workflow-planner"],
    "code-generator": ["workflow-planner"],  # unit-decomposer is optional
    "build-test-agent": ["code-generator"],
    "reviewer-code": ["code-generator"],
    "reviewer-security": ["code-generator"],
    "reviewer-performance": ["code-generator"],
    "reviewer-simplifier": ["code-generator"],
    "ship-agent": ["reviewer-code"],  # at least one reviewer required
}


def load_manifest(run_id: str) -> dict:
    manifest_path = RUNS_ROOT / run_id / "manifest.yaml"
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}


def check_stage(run_id: str, stage: str) -> int:
    """Check if stage can run. Returns exit code (0=ok, 1=blocked, 2=error)."""
    manifest = load_manifest(run_id)
    completed = set(manifest.get("completed_stages", []))
    
    if stage not in STAGE_PREREQUISITES:
        print(f"ERROR: unknown stage: {stage}", file=sys.stderr)
        return 2
    
    prerequisites = STAGE_PREREQUISITES[stage]
    # Special case: ship-agent needs at least one reviewer
    if stage == "ship-agent":
        reviewer_stages = ["reviewer-code", "reviewer-security", "reviewer-performance", "reviewer-simplifier"]
        has_reviewer = any(r in completed for r in reviewer_stages)
        if not has_reviewer:
            print(f"BLOCKED: stage '{stage}' cannot run. Missing: at least one reviewer stage")
            print(f"Completed stages: {sorted(completed)}")
            print(f"Required: any of {reviewer_stages}")
            return 1
        print(f"OK: stage '{stage}' can run. At least one reviewer completed.")
        return 0
    
    missing = [p for p in prerequisites if p not in completed]
    
    if missing:
        print(f"BLOCKED: stage '{stage}' cannot run. Missing prerequisites: {missing}")
        print(f"Completed stages: {sorted(completed)}")
        print(f"Required stages: {prerequisites}")
        
        # Provide helpful context
        if stage == "code-generator" and "workflow-planner" not in completed:
            print("\nNOTE: workflow-planner must complete before code-generator.")
            print("Run: /factory-plan <run-id> to complete workflow planning.")
        elif stage == "workflow-planner" and "requirements-analyst" not in completed:
            print("\nNOTE: requirements-analyst must complete before workflow-planner.")
            print("The user must answer questions and approve requirements first.")
        
        return 1
    
    print(f"OK: stage '{stage}' can run. All prerequisites completed: {prerequisites}")
    return 0


def list_stages(run_id: str) -> int:
    """List all stages and their completion status."""
    manifest = load_manifest(run_id)
    completed = set(manifest.get("completed_stages", []))
    current_stage = manifest.get("current_stage", "unknown")
    
    print(f"Run: {run_id}")
    print(f"Current stage: {current_stage}")
    print(f"Completed stages: {sorted(completed)}")
    print()
    print("Stage completion status:")
    print("-" * 50)
    
    for stage in STAGE_ORDER:
        status = "✅ COMPLETED" if stage in completed else "⬜ PENDING"
        prerequisites = STAGE_PREREQUISITES.get(stage, [])
        prereq_status = "✅" if all(p in completed for p in prerequisites) else "❌"
        print(f"{status} {stage:<25} (prerequisites: {prereq_status})")
    
    return 0


def next_stage(run_id: str) -> int:
    """Show the next stage that should run."""
    manifest = load_manifest(run_id)
    completed = set(manifest.get("completed_stages", []))
    current_stage = manifest.get("current_stage", "unknown")
    
    print(f"Run: {run_id}")
    print(f"Current stage: {current_stage}")
    print(f"Completed stages: {sorted(completed)}")
    print()
    
    # Find all stages that can run (prerequisites met, not completed)
    available = []
    for stage in STAGE_ORDER:
        if stage in completed:
            continue
        prerequisites = STAGE_PREREQUISITES.get(stage, [])
        if all(p in completed for p in prerequisites):
            available.append(stage)
    
    if not available:
        print("All stages completed!")
        return 0
    
    # Prioritize: show mandatory stages first, then conditional
    mandatory = ["workspace-scout", "requirements-analyst", "product-pass", "design-pass",
                 "arch-pass", "workflow-planner", "code-generator", "build-test-agent",
                 "ship-agent"]
    prioritized = [s for s in available if s in mandatory] + [s for s in available if s not in mandatory]
    
    print(f"Available stages to run:")
    for stage in prioritized:
        cmd = f"/factory-{stage.replace('_', '-')} {run_id}"
        marker = " (MANDATORY)" if stage in mandatory else " (conditional)"
        print(f"  - {stage}{marker}")
        print(f"    Command: {cmd}")
    
    # Highlight the first mandatory stage
    first_mandatory = next((s for s in prioritized if s in mandatory), None)
    if first_mandatory:
        print(f"\nRecommended next stage: {first_mandatory}")
    else:
        print(f"\nNext stage: {prioritized[0]}")
    
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage Gate Enforcement — validates stage prerequisites"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    check_parser = subparsers.add_parser("check", help="Check if stage can run")
    check_parser.add_argument("run_id", help="Run ID")
    check_parser.add_argument("stage", help="Stage name to check")
    
    list_parser = subparsers.add_parser("list", help="List all stages")
    list_parser.add_argument("run_id", help="Run ID")
    
    next_parser = subparsers.add_parser("next", help="Show next stage")
    next_parser.add_argument("run_id", help="Run ID")
    
    args = parser.parse_args()
    
    if args.command == "check":
        return check_stage(args.run_id, args.stage)
    elif args.command == "list":
        return list_stages(args.run_id)
    elif args.command == "next":
        return next_stage(args.run_id)
    
    return 2


if __name__ == "__main__":
    sys.exit(main())
