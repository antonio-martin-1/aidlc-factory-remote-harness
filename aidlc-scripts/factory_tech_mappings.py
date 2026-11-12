#!/usr/bin/env python3
"""
tech_stack_mappings Generator for AI Architecture Cookbook.

Scans all YAML standards and suggests tech_stack_mappings based on
pattern names, descriptions, use_when, and avoid_when conditions.

Usage:
    python factory_tech_mappings.py [--repo-root <path>] [--dry-run] [--apply]

Output:
    --dry-run: prints suggested mappings per standard (YAML)
    --apply: writes tech_stack_mappings directly into each YAML standard
    default: prints summary of what would be added
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print(
        f"ERROR: PyYAML required by interpreter {sys.executable!r}. Use the launcher from "
        ".aidlc-orchestrator/runtime/common/python-runtime.md with -m pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)


# ── Tech keyword → mapping rules ──────────────────────────────────────────────
# Each entry describes a technology and which pattern patterns it maps to.
# `match_in` specifies where to look (pattern id, name, description, use_when).
# `layer` is the tech layer.
# `priority` determines which mapping wins if multiple match.

TechRule = dict[str, Any]

TECH_RULES: list[TechRule] = [
    # ── Database ORMs ────────────────────────────────────────────────────
    {
        "tech": {"name": "prisma", "layer": "database"},
        "keywords": ["prisma", "typeorm", "drizzle"],
        "match_in": ["id", "name", "description", "use_when"],
        "priority": 10,
        "suggested_patterns": ["repository", "data_access", "generic_repository"],
    },
    {
        "tech": {"name": "sqlx", "layer": "database"},
        "keywords": ["sqlx", "sqlx "],
        "match_in": ["id", "name", "description"],
        "priority": 10,
        "suggested_patterns": ["repository", "data_access", "query_object"],
    },
    {
        "tech": {"name": "django-orm", "layer": "database"},
        "keywords": ["django", "django orm"],
        "match_in": ["id", "name", "description", "use_when"],
        "priority": 10,
        "suggested_patterns": ["repository", "active_record"],
    },
    {
        "tech": {"name": "sqlalchemy", "layer": "database"},
        "keywords": ["sqlalchemy", "sqlalchemy "],
        "match_in": ["id", "name", "description"],
        "priority": 10,
        "suggested_patterns": ["repository", "data_access", "unit_of_work"],
    },
    # ── Caches ───────────────────────────────────────────────────────────
    {
        "tech": {"name": "redis", "layer": "cache"},
        "keywords": ["redis", "cache", "caching", "distributed cache"],
        "match_in": ["id", "name", "description", "use_when"],
        "priority": 5,
        "suggested_patterns": ["cache_aside", "write_through", "cache"],
    },
    {
        "tech": {"name": "memcached", "layer": "cache"},
        "keywords": ["memcached", "memcache"],
        "match_in": ["id", "name", "description"],
        "priority": 5,
        "suggested_patterns": ["cache_aside", "cache"],
    },
    # ── Queues ───────────────────────────────────────────────────────────
    {
        "tech": {"name": "bullmq", "layer": "queue"},
        "keywords": ["bull", "bullmq", "queue", "job", "worker", "task queue"],
        "match_in": ["id", "name", "description", "use_when"],
        "priority": 5,
        "suggested_patterns": ["message_queue", "job_queue", "worker"],
    },
    {
        "tech": {"name": "celery", "layer": "queue"},
        "keywords": ["celery", "celery "],
        "match_in": ["id", "name", "description"],
        "priority": 5,
        "suggested_patterns": ["message_queue", "task_queue", "worker"],
    },
    # ── Frontend ─────────────────────────────────────────────────────────
    {
        "tech": {"name": "react", "layer": "frontend"},
        "keywords": ["react", "react "],
        "match_in": ["id", "name", "description", "use_when"],
        "priority": 5,
        "suggested_patterns": ["component", "hook", "context"],
    },
    {
        "tech": {"name": "vue", "layer": "frontend"},
        "keywords": ["vue", "vue "],
        "match_in": ["id", "name", "description"],
        "priority": 5,
        "suggested_patterns": ["component", "composition"],
    },
    {
        "tech": {"name": "zustand", "layer": "frontend"},
        "keywords": ["zustand"],
        "match_in": ["id", "name", "description", "use_when"],
        "priority": 5,
        "suggested_patterns": ["store", "state", "atomic_state"],
    },
    {
        "tech": {"name": "redux", "layer": "frontend"},
        "keywords": ["redux"],
        "match_in": ["id", "name", "description"],
        "priority": 5,
        "suggested_patterns": ["store", "state", "global_state"],
    },
    # ── Backend Frameworks ───────────────────────────────────────────────
    {
        "tech": {"name": "express", "layer": "backend"},
        "keywords": ["express", "express.js", "node.js"],
        "match_in": ["id", "name", "description", "use_when"],
        "priority": 5,
        "suggested_patterns": ["middleware", "router", "api"],
    },
    {
        "tech": {"name": "fastapi", "layer": "backend"},
        "keywords": ["fastapi", "fast api"],
        "match_in": ["id", "name", "description"],
        "priority": 5,
        "suggested_patterns": ["router", "api", "dependency_injection"],
    },
    {
        "tech": {"name": "django", "layer": "backend"},
        "keywords": ["django"],
        "match_in": ["id", "name", "description"],
        "priority": 5,
        "suggested_patterns": ["mvc", "admin", "middleware"],
    },
    # ── AI / LLM ─────────────────────────────────────────────────────────
    {
        "tech": {"name": "langchain", "layer": "ai"},
        "keywords": ["langchain", "lang chain"],
        "match_in": ["id", "name", "description", "use_when"],
        "priority": 10,
        "suggested_patterns": ["llm", "agent", "chain", "rag"],
    },
    {
        "tech": {"name": "openai", "layer": "ai"},
        "keywords": ["openai", "gpt", "llm", "large language model"],
        "match_in": ["id", "name", "description"],
        "priority": 5,
        "suggested_patterns": ["llm", "completion", "chat"],
    },
    # ── Auth ─────────────────────────────────────────────────────────────
    {
        "tech": {"name": "next-auth", "layer": "backend"},
        "keywords": ["next-auth", "nextauth", "auth.js"],
        "match_in": ["id", "name", "description", "use_when"],
        "priority": 10,
        "suggested_patterns": ["authentication", "oauth", "session"],
    },
    {
        "tech": {"name": "keycloak", "layer": "backend"},
        "keywords": ["keycloak"],
        "match_in": ["id", "name", "description"],
        "priority": 10,
        "suggested_patterns": ["sso", "identity", "oidc", "authorization"],
    },
]


def find_cookbook_root() -> Path:
    """Locate the AI-Architecture-Cookbook repo root."""
    # Try common locations relative to this script
    candidates = [
        Path("..") / "AI-Architecture-Cookbook",
        Path("..") / ".." / "AI-Architecture-Cookbook",
        Path.cwd() / "AI-Architecture-Cookbook",
    ]
    for c in candidates:
        resolved = c.resolve()
        if (resolved / "index.yaml").exists():
            return resolved
    # Search up from cwd
    p = Path.cwd()
    while p.parent != p:
        if (p / "index.yaml").exists():
            return p
        p = p.parent
    raise FileNotFoundError(
        "Could not find AI-Architecture-Cookbook root (no index.yaml found). "
        "Run from the repo root or pass --repo-root."
    )


def list_standards(repo_root: Path) -> list[Path]:
    """Return list of all YAML standard files."""
    return sorted(repo_root.rglob("*.yaml"))


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(data: dict) -> str:
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


def match_tech(entry: dict) -> list[dict]:
    """Match a standard's patterns against tech rules and return suggested mappings."""
    patterns = entry.get("patterns", [])
    if not patterns:
        return []

    suggestions: list[dict] = []

    for rule in TECH_RULES:
        keywords = [k.lower() for k in rule["keywords"]]
        matched_patterns = []

        for p in patterns:
            pid = str(p.get("id", "")).lower()
            pname = str(p.get("name", "")).lower()
            pdesc = str(p.get("description", "")).lower()
            puse = " ".join(str(x).lower() for x in p.get("use_when", []))

            search_text = f"{pid} {pname} {pdesc} {puse}"

            if any(kw in search_text for kw in keywords):
                matched_patterns.append(p["id"])

        if matched_patterns:
            # Pick the best matching pattern (first that matches suggested_patterns)
            best_pattern = None
            for sp in rule.get("suggested_patterns", []):
                for mp in matched_patterns:
                    if sp in mp or mp in sp:
                        best_pattern = mp
                        break
                if best_pattern:
                    break
            if not best_pattern and matched_patterns:
                best_pattern = matched_patterns[0]

            if best_pattern:
                suggestions.append({
                    "tech": rule["tech"],
                    "pattern_id": best_pattern,
                    "implementation_ref": f"#tech-{rule['tech']['name']}-{best_pattern}",
                    "priority": rule["priority"],
                })

    # Deduplicate by tech name + pattern_id
    seen = set()
    unique: list[dict] = []
    for s in suggestions:
        key = (s["tech"]["name"], s["pattern_id"])
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique


def generate_mappings_for_file(path: Path) -> str | None:
    """Generate tech_stack_mappings for a single standard file. Returns None if no changes needed."""
    entry = load_yaml(path)
    if not entry or "meta" not in entry:
        return None

    domain = entry["meta"].get("domain", path.stem)
    existing = entry.get("tech_stack_mappings", [])
    existing_keys = {(m.get("tech", {}).get("name"), m.get("pattern_id")) for m in existing}

    suggestions = match_tech(entry)
    new_mappings = [s for s in suggestions if (s["tech"]["name"], s["pattern_id"]) not in existing_keys]

    if not new_mappings:
        return None

    # Build the tech_stack_mappings block
    result = yaml.dump({"tech_stack_mappings": new_mappings}, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return result


def apply_mappings_to_file(path: Path, dry_run: bool = False) -> bool:
    """Apply generated mappings to a YAML standard file."""
    entry = load_yaml(path)
    if not entry or "meta" not in entry:
        return False

    domain = entry["meta"].get("domain", path.stem)
    existing = entry.get("tech_stack_mappings", [])
    existing_keys = {(m.get("tech", {}).get("name"), m.get("pattern_id")) for m in existing}

    suggestions = match_tech(entry)
    new_mappings = [s for s in suggestions if (s["tech"]["name"], s["pattern_id"]) not in existing_keys]

    if not new_mappings:
        return False

    if dry_run:
        print(f"  [{domain}] Would add {len(new_mappings)} mapping(s):")
        for m in new_mappings:
            print(f"    {m['tech']['name']} ({m['tech']['layer']}) → {m['pattern_id']}")
        return True

    # Read original file to preserve formatting (yaml.dump may change it)
    original = path.read_text(encoding="utf-8")

    # Check if tech_stack_mappings already exists in file
    if "tech_stack_mappings:" in original:
        # Append to existing
        mapping_block = dump_yaml({"tech_stack_mappings": existing + new_mappings})
        # Replace the old tech_stack_mappings block
        import re as re_module
        old_block = dump_yaml({"tech_stack_mappings": existing})
        new_content = original.replace(old_block, mapping_block)
    else:
        # Append at the end
        mapping_block = dump_yaml({"tech_stack_mappings": new_mappings})
        new_content = original.rstrip() + "\n\n" + mapping_block

    path.write_text(new_content, encoding="utf-8")
    print(f"  [{domain}] Added {len(new_mappings)} tech_stack_mapping(s)")
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate tech_stack_mappings for Cookbook standards")
    parser.add_argument("--repo-root", type=str, help="Path to AI-Architecture-Cookbook root")
    parser.add_argument("--dry-run", action="store_true", help="Show suggested mappings without writing")
    parser.add_argument("--apply", action="store_true", help="Write mappings into standard files")
    parser.add_argument("--verbose", action="store_true", help="Show per-file details")
    args = parser.parse_args()

    if args.repo_root:
        repo_root = Path(args.repo_root).resolve()
    else:
        repo_root = find_cookbook_root()

    print(f"Cookbook root: {repo_root}")
    print(f"Total rules: {len(TECH_RULES)}")

    standards = list_standards(repo_root)
    # Filter to only actual standard files (skip index.yaml, base-template.yaml, etc.)
    standard_files = [s for s in standards if s.name != "index.yaml" and s.name != "base-template.yaml" and "_index" not in s.name]

    print(f"Standards scanned: {len(standard_files)}")
    print()

    changed = 0
    total_new = 0

    for sf in standard_files:
        if args.apply:
            domain_meta = load_yaml(sf).get("meta", {})
            domain_name = domain_meta.get("domain", sf.stem)
            if args.verbose:
                print(f"  Scanning {domain_name} ({sf.relative_to(repo_root)})...")
            applied = apply_mappings_to_file(sf, dry_run=False)
            if applied:
                changed += 1
        elif args.dry_run:
            domain_meta = load_yaml(sf).get("meta", {})
            domain_name = domain_meta.get("domain", sf.stem)
            entry = load_yaml(sf)
            suggestions = match_tech(entry)
            if suggestions:
                print(f"\n  [{domain_name}] ({sf.relative_to(repo_root)})")
                for m in suggestions:
                    print(f"    {m['tech']['name']:20s} ({m['tech']['layer']:10s}) -> {m['pattern_id']}")
                    total_new += 1
                changed += 1
        else:
            # Summary mode
            entry = load_yaml(sf)
            domain_meta = entry.get("meta", {})
            domain_name = domain_meta.get("domain", sf.stem)
            existing = entry.get("tech_stack_mappings", [])
            suggestions = match_tech(entry)
            new_count = len(suggestions) - len(existing)
            if new_count > 0:
                print(f"  {domain_name:30s} {len(existing)} existing → {new_count:+d} new")
                total_new += new_count
                changed += 1

    print()
    if args.apply:
        print(f"Applied: {changed} files modified with {total_new} new mappings")
        print("Review each file before committing — the generated mappings are suggestions.")
    elif args.dry_run:
        print(f"Suggested mappings for {changed} standards ({total_new} total mappings)")
        print("Run with --apply to write them.")
    else:
        print(f"{changed} standards have new mappings available ({total_new} total)")
        print("Run with --dry-run to preview, or --apply to write.")


if __name__ == "__main__":
    main()
