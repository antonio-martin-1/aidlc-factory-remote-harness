#!/usr/bin/env python3
"""Validate a YAML or JSON document against a JSON Schema.

Usage:
    python3 aidlc-scripts/factory_validate.py <schema.json> <doc.yaml|doc.json>
    python3 aidlc-scripts/factory_validate.py --check-cookbook

Exit codes:
    0  document is valid (or cookbook is healthy)
    1  document is invalid (details on stderr)
    2  usage error or missing dependency
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    from skill_utils import _log
except ImportError:
    def _log(level: str, msg: str, **kwargs) -> None:
        """Fallback _log if skill_utils is not available."""
        stream = sys.stderr if level in ("ERROR", "WARNING") else sys.stdout
        print(f"[{level}] {msg}", file=stream)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_AIDLC_ROOT = Path(os.environ["AIDLC_ROOT"]) if "AIDLC_ROOT" in os.environ else _REPO_ROOT


def _die(msg: str, code: int = 2) -> None:
    _log("ERROR", msg)
    sys.exit(code)


ORCHESTRATOR_VERSION = "0.2.0"
EXPECTED_SCHEMA_VERSION = 1


def _strict_check(doc: dict, doc_path: Path, schema_id: str = "") -> list[str]:
    """Content-level validation beyond JSON Schema."""
    issues: list[str] = []
    status = doc.get("status")
    artifacts = doc.get("artifacts", []) or []
    findings = doc.get("findings", []) or []
    knowledge = doc.get("emitted_knowledge", []) or []

    # status: complete requires at least 1 artifact with a non-empty path
    if status == "complete":
        valid_paths = [a for a in artifacts if isinstance(a, dict) and a.get("path")]
        if not valid_paths:
            issues.append("status=complete but no artifact with a non-empty `path`")

    # code-generator: any non-FAST_PATH sub_stage MUST produce a plan artifact on disk.
    # Without this check, agents can claim sub_stage=generated without writing the plan,
    # and downstream stages silently fail. See TOKEN-OPTIMIZATION-PLAN.md #6.
    if schema_id.startswith("code-generator.output"):
        sub_stage = doc.get("sub_stage")
        fast_path = bool(doc.get("fast_path"))
        if sub_stage in {"plan", "generated"} and not fast_path:
            plan_artifacts = [
                a for a in artifacts
                if isinstance(a, dict) and a.get("kind") == "plan" and a.get("path")
            ]
            if not plan_artifacts:
                issues.append(
                    f"sub_stage={sub_stage} (non-fast_path) but no artifact with kind=plan — "
                    "the construction plan file is mandatory whenever fast_path is not set; "
                    "merged_plan_generate removes the approval gate, not the plan file"
                )
            else:
                for art in plan_artifacts:
                    art_path = Path(art["path"])
                    candidates = [art_path] if art_path.is_absolute() else [
                        Path.cwd() / art_path,
                        _AIDLC_ROOT / art_path,
                    ]
                    resolved = next((c for c in candidates if c.exists()), None)
                    if not resolved:
                        issues.append(
                            f"plan artifact declared at {art['path']} but file does not exist on disk"
                        )
                    elif sub_stage == "generated":
                        # Plan content: scan for remaining unchecked checkboxes.
                        # This catches the silent-skip failure where an agent claims
                        # "generated" / "complete" but left tasks unchecked.
                        # Only at sub_stage=generated: at sub_stage=plan the plan is
                        # awaiting the human approval gate, so every box is unchecked
                        # by design (see code-generator.agent.md, standard path).
                        text = resolved.read_text(encoding="utf-8", errors="replace")
                        unchecked = [ln.strip() for ln in text.splitlines() if "- [ ]" in ln]
                        if unchecked:
                            preview = "; ".join(u[:80] for u in unchecked[:5])
                            if len(unchecked) > 5:
                                preview += f" ... (and {len(unchecked) - 5} more)"
                            issues.append(
                                f"plan file '{art['path']}' has {len(unchecked)} unchecked "
                                f"checkbox(es): {preview}"
                            )

        # Shared construction design must exist once per run at generated —
        # existence only (reuse is OK; rewrite is not required).
        if sub_stage == "generated" and not fast_path:
            run_id = doc.get("run_id") or ""
            if run_id:
                scripts_dir = str(Path(__file__).resolve().parent)
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)
                from factory_design_gap import missing_paths, shared_design_paths

                missing_shared: list[str] | None = None
                for root in (_AIDLC_ROOT, Path.cwd()):
                    miss = missing_paths(shared_design_paths(root, run_id))
                    if not miss:
                        missing_shared = []
                        break
                    missing_shared = miss
                if missing_shared:
                    issues.append(
                        "sub_stage=generated but shared construction design missing: "
                        + ", ".join(missing_shared)
                        + " (write-once / reuse — do not rewrite per unit)"
                    )

    # tests_added > 0 requires at least 1 test file in artifacts
    tests_added = doc.get("tests_added", 0)
    if isinstance(tests_added, int) and tests_added > 0:
        has_test_artifact = False
        for a in artifacts:
            path = a.get("path", "") if isinstance(a, dict) else ""
            stem = Path(path).stem
            name = Path(path).name
            if (
                    any(p in ("test", "tests", "__tests__", "spec", "e2e", "cypress") for p in Path(path).parts)
                    or stem.startswith("test_")
                    or stem.endswith("_test")
                    or stem.endswith("_spec")
                    or ".test." in name
                    or ".spec." in name
                    or name == "conftest.py"
                ):
                    has_test_artifact = True
                    break
        if not has_test_artifact:
            issues.append(f"tests_added={tests_added} but no test file found in artifacts")

    # findings with severity P0/P1 should have a recommendation
    for f in findings:
        sev = f.get("severity")
        if sev in ("P0", "P1") and not f.get("recommendation"):
            loc = f.get("file", "?")
            issues.append(f"finding [{sev}] {loc} has no `recommendation`")

    # emitted_knowledge body must be non-empty
    for i, k in enumerate(knowledge):
        if not k.get("body"):
            issues.append(f"emitted_knowledge[{i}].body is empty")

    return issues


def _check_cookbook_health(project_root: Path) -> tuple[str, list[str]]:
    """Check the health of the AI Architecture Cookbook integration.

    The MCP server runs via npx (@ai-architecture-cookbook/mcp-server) and is
    configured in the project's MCP config files (.mcp.json etc.). All standards
    data is bundled inside the npm package — no local YAML copy needed.

    Returns (status, details[]) where status is 'healthy', 'degraded', or 'unhealthy'.
    """
    import json

    status = "unhealthy"
    details: list[str] = []

    # Check MCP config entry exists (npx-based)
    mcp_configured = False
    for mcp_file, key_name in [
        (project_root / ".mcp.json", "mcpServers"),
        (project_root / ".cursor" / "mcp.json", "mcpServers"),
        (project_root / "opencode.json", "mcp"),
        (project_root / ".vscode" / "mcp.json", "servers"),
    ]:
        if mcp_file.exists():
            try:
                cfg = json.loads(mcp_file.read_text(encoding="utf-8"))
                servers = cfg.get(key_name, {})
                if "ai-architecture-cookbook" in servers:
                    mcp_configured = True
                    details.append(f"MCP server: npx @ai-architecture-cookbook/mcp-server (configured in {mcp_file.name})")
                    break
            except (json.JSONDecodeError, OSError):
                continue

    if mcp_configured:
        status = "healthy"
    else:
        status = "unhealthy"
        details.append("Cookbook MCP not configured in any config file.")
        details.append("Re-run: python aidlc-scripts/install_aidlc.py --with-architecture-cookbook")

    # Check schemas exist
    schemas_dir = _REPO_ROOT / ".aidlc-orchestrator" / "contracts" / "cookbook"
    if schemas_dir.exists():
        schema_files = list(schemas_dir.glob("*.json"))
        if schema_files:
            details.append(f"Validation schemas: {len(schema_files)} found ({', '.join(f.name for f in schema_files)})")
        else:
            details.append("Validation schemas: none found")

    # Try a quick MCP server probe if configured (via npx)
    if mcp_configured:
        ok, version_str = _probe_node()
        if not ok:
            details.append(f"MCP probe skipped: Node.js not found ({version_str})")
        else:
            try:
                result = subprocess.run(
                    ["node", "-e", "process.exit(0)"],
                    capture_output=True, timeout=10,
                )
                if result.returncode == 0:
                    details.append("Node.js: available (MCP server ready)")
                else:
                    details.append("Node.js: found but non-zero exit")
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
                details.append(f"MCP probe: failed ({e})")

    return status, details


def _probe_node() -> tuple[bool, str]:
    """Probe Node.js availability. Returns (ok, version_string)."""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, "not found"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False, "not found"


def main() -> None:
    p = argparse.ArgumentParser(description="Validate a document against a JSON Schema")
    p.add_argument("schema", nargs="?", help="path to JSON Schema file")
    p.add_argument("document", nargs="?", help="path to YAML or JSON document")
    p.add_argument("--strict", action="store_true",
                   help="enable content-level checks beyond schema validation")
    p.add_argument("--check-cookbook", action="store_true",
                   help="check AI Architecture Cookbook integration health")
    args = p.parse_args()

    # Cookbook health check mode
    if args.check_cookbook:
        status, details = _check_cookbook_health(_AIDLC_ROOT)
        print(f"AI Architecture Cookbook: {status.upper()}")
        for detail in details:
            print(f"  {detail}")
        if status == "healthy":
            sys.exit(0)
        elif status == "degraded":
            _log("WARNING", "Cookbook is DEGRADED — inline YAML fallback mode.")
            sys.exit(0)  # Degraded is non-blocking
        else:
            _log("ERROR", "Cookbook is UNHEALTHY — re-run installer.")
            sys.exit(1)

    if not args.schema or not args.document:
        p.error("schema and document arguments are required (or use --check-cookbook)")

    schema_path = Path(args.schema)
    doc_path = Path(args.document)

    if not schema_path.exists():
        _die(f"schema not found: {schema_path}")
    if not doc_path.exists():
        _die(f"document not found: {doc_path}")

    try:
        from jsonschema import Draft7Validator
    except ImportError:
        _die(f"missing dependency: {sys.executable} -m pip install jsonschema")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    suffix = doc_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError:
            _die(f"missing dependency: {sys.executable} -m pip install pyyaml")
        doc = yaml.safe_load(doc_path.read_text(encoding="utf-8"))
    elif suffix == ".json":
        doc = json.loads(doc_path.read_text(encoding="utf-8"))
    else:
        _die(f"unsupported document extension: {suffix} (expected .yaml/.yml/.json)")

    # Version check: schema $id should indicate expected schema version.
    # Fall back to file name when $id is empty (common in simple schemas).
    schema_id = schema.get("$id", "") or schema_path.name
    schema_ver = schema.get("schema_version")
    if schema_ver is not None and schema_ver != EXPECTED_SCHEMA_VERSION:
        _log("WARNING", f"VERSION MISMATCH schema_version={schema_ver}, expected {EXPECTED_SCHEMA_VERSION} (orchestrator v{ORCHESTRATOR_VERSION})")

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))

    if errors:
        _log("ERROR", f"INVALID {doc_path} ({len(errors)} schema error(s)):")
        for err in errors:
            loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
            _log("ERROR", f"  - {loc}: {err.message}")
        sys.exit(1)

    if args.strict:
        strict_issues = _strict_check(doc, doc_path, schema_id=schema_id)
        if strict_issues:
            _log("ERROR", f"STRICT FAIL {doc_path} ({len(strict_issues)} content issue(s)):")
            for issue in strict_issues:
                _log("ERROR", f"  - {issue}")
            sys.exit(1)

    print(f"OK {doc_path} matches {schema_path.name}")
    sys.exit(0)


if __name__ == "__main__":
    main()
