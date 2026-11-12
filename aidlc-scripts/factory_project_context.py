#!/usr/bin/env python3
"""
Project Memory Adapter for AI Architecture Cookbook.

Reads project state from aidlc-docs/ and Engram entries to build
a structured context object for the Cookbook MCP tools.

Usage:
    python factory_project_context.py [--repo-root <path>]

Output:
    JSON object with context fields for recommend_pattern / recommend_workflow
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def find_aidlc_docs(repo_root: Path) -> Path | None:
    """Locate aidlc-docs/ in the repo root or any subdirectory."""
    candidates = [
        repo_root / "aidlc-docs",
        repo_root / "docs" / "aidlc-docs",
        repo_root / ".aidlc-docs",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return None


def read_tech_stack(repo_root: Path) -> list[dict]:
    """Read tech stack from workspace-scout output or lockfiles."""
    tech_stack: list[dict] = []

    # Check workspace-scout artifact
    scout_paths = [
        repo_root / "aidlc-docs" / "inception" / "workspace-scout-output.json",
        repo_root / "aidlc-docs" / "inception" / "inception-output.json",
    ]
    for sp in scout_paths:
        if sp.exists():
            try:
                data = json.loads(sp.read_text(encoding="utf-8"))
                raw_ts = data.get("tech_stack", data.get("project_profile", {}).get("tech_stack", []))
                if raw_ts:
                    tech_stack = raw_ts
                    break
            except (json.JSONDecodeError, KeyError):
                continue

    # Fallback: parse lockfiles
    if not tech_stack:
        lockfile_parsers = [
            (repo_root / "package.json", _parse_package_json),
            (repo_root / "Cargo.toml", _parse_cargo_toml),
            (repo_root / "pyproject.toml", _parse_pyproject_toml),
            (repo_root / "go.mod", _parse_go_mod),
        ]
        for path, parser in lockfile_parsers:
            if path.exists():
                try:
                    result = parser(path)
                    tech_stack.extend(result)
                except Exception:
                    continue

    return tech_stack


def _parse_package_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    tech = []
    layer_map: dict[str, str] = {
        "react": "frontend", "vue": "frontend", "angular": "frontend",
        "next": "frontend", "nuxt": "frontend",
        "express": "backend", "fastify": "backend", "koa": "backend",
        "prisma": "database", "typeorm": "database", "drizzle": "database",
        "redis": "cache", "ioredis": "cache",
        "bull": "queue", "bullmq": "queue",
    }
    for pkg, ver in deps.items():
        for key, layer in layer_map.items():
            if key in pkg.lower():
                tech.append({"layer": layer, "name": pkg, "version": str(ver).lstrip("^~")})
                break
    return tech


def _parse_cargo_toml(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    tech = []
    for match in re.finditer(r'^(\w[\w-]*)\s*=\s*\{?\s*version\s*=\s*"([^"]+)"', text, re.MULTILINE):
        name, ver = match.group(1), match.group(2)
        layer = "backend"
        if any(k in name for k in ("sqlx", "diesel", "sea-orm")):
            layer = "database"
        elif any(k in name for k in ("redis", "moka")):
            layer = "cache"
        tech.append({"layer": layer, "name": name, "version": ver})
    return tech


def _parse_pyproject_toml(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    tech = []
    layer_map: dict[str, str] = {
        "django": "backend", "flask": "backend", "fastapi": "backend",
        "sqlalchemy": "database", "psycopg": "database",
        "redis": "cache", "celery": "queue",
        "tensorflow": "ai", "torch": "ai", "transformers": "ai",
        "langchain": "ai", "llama-index": "ai",
    }
    for match in re.finditer(r'^(\w[\w-]*)\s*=\s*"?([^"\n]+)"?', text, re.MULTILINE):
        name = match.group(1).lower()
        ver = match.group(2)
        for key, layer in layer_map.items():
            if key in name:
                tech.append({"layer": layer, "name": name, "version": ver})
                break
    return tech


def _parse_go_mod(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    tech = []
    layer_map: dict[str, str] = {
        "chi": "backend", "gin": "backend", "echo": "backend",
        "gorm": "database", "sqlx": "database", "ent": "database",
        "redis": "cache",
    }
    for match in re.finditer(r'^(\S+)\s+v(\S+)', text, re.MULTILINE):
        pkg = match.group(1).lower()
        ver = match.group(2)
        for key, layer in layer_map.items():
            if key in pkg:
                tech.append({"layer": layer, "name": pkg.split("/")[-1], "version": ver})
                break
    return tech


def read_previous_decisions(repo_root: Path) -> list[dict]:
    """Read previous architecture decisions from aidlc-docs/."""
    decisions: list[dict] = []
    aidlc_docs = find_aidlc_docs(repo_root)
    if not aidlc_docs:
        return decisions

    # Check for ADRs or architecture decisions
    adr_dir = aidlc_docs / "inception" / "adrs"
    if adr_dir.is_dir():
        for adr_file in sorted(adr_dir.glob("*.md")):
            text = adr_file.read_text(encoding="utf-8")
            title_match = re.search(r'^#\s+(.+)', text)
            status_match = re.search(r'^Status:\s*(.+)', text, re.MULTILINE)
            if title_match:
                decisions.append({
                    "source": str(adr_file.name),
                    "title": title_match.group(1).strip(),
                    "status": status_match.group(1).strip() if status_match else "unknown",
                })

    # Check for execution plan decisions
    plan_path = aidlc_docs / "inception" / "execution-plan.md"
    if plan_path.exists():
        text = plan_path.read_text(encoding="utf-8")
        arch_matches = re.findall(
            r'(?:Architecture|Pattern|Decision):\s*([^\n]+)', text, re.IGNORECASE
        )
        for m in arch_matches:
            decisions.append({"source": "execution-plan", "note": m.strip()})

    return decisions


def read_project_scale(repo_root: Path) -> str | None:
    """Infer project scale from aidlc-docs audit entries."""
    aidlc_docs = find_aidlc_docs(repo_root)
    if not aidlc_docs:
        return None
    audit = aidlc_docs / "audit.md"
    if not audit.exists():
        return None
    text = audit.read_text(encoding="utf-8")
    if re.search(r'\benterprise\b', text, re.IGNORECASE):
        return "enterprise"
    if re.search(r'\b(scale|massive|large)\b', text, re.IGNORECASE):
        return "enterprise"
    return None


def read_compliance_requirements(repo_root: Path) -> list[str]:
    """Read compliance requirements from requirements doc."""
    aidlc_docs = find_aidlc_docs(repo_root)
    if not aidlc_docs:
        return []
    req_path = aidlc_docs / "inception" / "requirements.md"
    if not req_path.exists():
        return []
    text = req_path.read_text(encoding="utf-8").lower()
    compliance: list[str] = []
    if "gdpr" in text or "hipaa" in text:
        compliance.append("gdpr")
    if "pci" in text or "pci-dss" in text:
        compliance.append("pci-dss")
    if "sox" in text:
        compliance.append("sox")
    if "ccpa" in text:
        compliance.append("ccpa")
    return compliance


def build_context(repo_root: Path) -> dict:
    """Build a complete context object for Cookbook MCP tools."""
    tech_stack = read_tech_stack(repo_root)
    decisions = read_previous_decisions(repo_root)
    scale = read_project_scale(repo_root)
    compliance = read_compliance_requirements(repo_root)

    context: dict = {}

    if tech_stack:
        context["techStack"] = tech_stack

    if scale:
        context["scale"] = scale

    if compliance:
        context["compliance"] = compliance

    if decisions:
        context["previous_decisions"] = decisions

    # Infer client types from tech stack
    layers = {t.get("layer") for t in tech_stack}
    if "frontend" in layers:
        context.setdefault("client_types", [])
        if isinstance(context["client_types"], list):
            context["client_types"].append("web")
    if "mobile" in layers:
        context.setdefault("client_types", [])
        if isinstance(context["client_types"], list):
            context["client_types"].append("mobile")

    # Infer needs_login from decisions or stack
    if any("auth" in str(d).lower() for d in decisions):
        context["needs_login"] = True

    return {
        "project": repo_root.name,
        "context": context,
        "tech_stack": tech_stack,
        "previous_decisions": decisions,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build project context for Cookbook MCP")
    parser.add_argument("--repo-root", type=str, default=".",
                        help="Path to the project repository root")
    parser.add_argument("--format", choices=["json", "compact"], default="json",
                        help="Output format")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    result = build_context(repo_root)

    if args.format == "compact":
        ctx = result["context"]
        # Only output the context object for direct use
        print(json.dumps(ctx, indent=2))
    else:
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
