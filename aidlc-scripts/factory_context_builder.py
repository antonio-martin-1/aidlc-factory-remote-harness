#!/usr/bin/env python3
"""factory_context_builder.py — Build contextual snapshots from AIDLC traceability files.

Reads audit.md, aidlc-state.md, manifest.yaml, timeline.jsonl, and handoffs
 to produce a condensed context summary that can be injected into stage prompts.

Key features:
- Precise token counting (tiktoken when available, adaptive fallback)
- Intelligent caching with checksum-based invalidation
- Compact YAML output format (saves ~40% tokens vs Markdown)
- Auto depth adjustment for short runs
- Cost tracking metrics

Usage
    python3 aidlc-scripts/factory_context_builder.py <run-id> [--depth minimal|standard|comprehensive] [--output path] [--format markdown|yaml|json|compact]

    --depth minimal       → 200 tokens max. Current stage + last 3 audit entries.
    --depth standard      → 800 tokens max. Full state + last 10 audit entries + stage timing.
    --depth comprehensive → 2000 tokens max. Everything + handoff summaries.
    --depth auto          → Auto-select based on completed stage count (default).

    --format compact      → Dense YAML-like format (saves ~40% tokens vs Markdown).

Output
    Compact YAML (default) with structured sections:
    - project: slug, version, profile
    - state: stage, phase, completed/skipped/failed
    - decisions: last N events from audit.md
    - timeline: per-stage events
    - open: incomplete units, pending approvals
    - skills: resolved paths
    - handoffs: recent output statuses (comprehensive)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print(f"missing dependency: {sys.executable} -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)

try:
    from skill_utils import _log
except ImportError:
    def _log(level: str, msg: str, **kwargs) -> None:
        import sys as _sys
        stream = _sys.stderr if level in ("ERROR", "WARNING") else _sys.stdout
        print(f"[{level}] {msg}", file=stream)

# ---------------------------------------------------------------------------
# Optional tiktoken for precise token counting
# ---------------------------------------------------------------------------
try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
    _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    _TIKTOKEN_ENCODER = None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(os.environ.get("AIDLC_ROOT", Path(__file__).resolve().parents[1]))
RUNS_ROOT = REPO_ROOT / ".aidlc-orchestrator" / "runs"
AIDLC_DOCS = REPO_ROOT / "aidlc-docs"
SCRIPTS_VERSION = REPO_ROOT / "aidlc-scripts" / "VERSION"

# ---------------------------------------------------------------------------
# Depth budgets (token estimates) — these are MAXIMUMS, not targets
# ---------------------------------------------------------------------------
DEPTH_BUDGETS = {
    "minimal": 200,
    "standard": 800,
    "comprehensive": 2000,
}

# Auto-depth mapping by completed stage count
AUTO_DEPTH_MAP = {
    (0, 2): "minimal",       # 0-2 completed stages
    (3, 5): "standard",       # 3-5 completed stages
    (6, float("inf")): "comprehensive",  # 6+ stages
}

# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Accurate token count. Uses tiktoken when available, falls back to
    adaptive heuristic based on UTF-8 byte length (more accurate than
    naive char count).
    """
    if _TIKTOKEN_AVAILABLE and _TIKTOKEN_ENCODER is not None:
        try:
            return len(_TIKTOKEN_ENCODER.encode(text))
        except Exception:
            pass
    # Fallback: adaptive heuristic based on UTF-8 byte length
    # English text: ~4 chars/token. Mixed languages: ~3 chars/token.
    # Code: ~3.5 chars/token. We use a conservative 3.5 to avoid overshooting.
    byte_len = len(text.encode("utf-8"))
    return max(1, byte_len // 3)


def _truncate_text(text: str, max_tokens: int) -> str:
    """Truncate text to fit within token budget. Binary search for precision."""
    if _estimate_tokens(text) <= max_tokens:
        return text
    # Binary search to find the exact cut point
    lo, hi = 0, len(text)
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if _estimate_tokens(text[:mid]) <= max_tokens:
            lo = mid
        else:
            hi = mid
    return text[:lo] + "\n... [truncated]"

# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

def _cache_path(run_id: str) -> Path:
    return RUNS_ROOT / run_id / "context-snapshot-cache.json"


def _file_checksums(run_id: str) -> dict[str, str]:
    """Compute MD5 checksums of all traceability files for a run."""
    files = {
        "manifest": _manifest_path(run_id),
        "timeline": _timeline_path(run_id),
        "audit": AIDLC_DOCS / "audit.md",
        "state": AIDLC_DOCS / "aidlc-state.md",
    }
    checksums = {}
    for key, path in files.items():
        if path.exists():
            h = hashlib.md5()
            h.update(path.read_bytes())
            checksums[key] = h.hexdigest()
        else:
            checksums[key] = "missing"
    return checksums


def _load_cached(run_id: str, depth: str, checksums: dict) -> dict | None:
    """Return cached snapshot if all checksums match."""
    cache_path = _cache_path(run_id)
    if not cache_path.exists():
        return None
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        # Check if depth matches
        if cache.get("depth") != depth:
            return None
        # Check if all file checksums match
        cached_checksums = cache.get("checksums", {})
        for key, val in checksums.items():
            if cached_checksums.get(key) != val:
                return None
        # Check if cache is not too old (max 1 hour)
        cache_ts = cache.get("cached_at", "")
        try:
            dt = datetime.fromisoformat(cache_ts.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - dt).total_seconds()
            if age > 3600:
                return None
        except (ValueError, TypeError):
            return None
        return cache
    except (json.JSONDecodeError, Exception):
        return None


def _save_cached(run_id: str, depth: str, checksums: dict, result: dict) -> None:
    """Save snapshot to cache with checksums."""
    cache_path = _cache_path(run_id)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_data = {
        "depth": depth,
        "checksums": checksums,
        "cached_at": _now_iso(),
        "result": result,
    }
    cache_path.write_text(json.dumps(cache_data, indent=2, default=str), encoding="utf-8")

# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _format_timestamp(ts: str) -> str:
    """Format ISO timestamp to human-readable short form."""
    if not ts or ts == "unknown":
        return "unknown"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, TypeError):
        return ts

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _run_dir(run_id: str) -> Path:
    return RUNS_ROOT / run_id


def _manifest_path(run_id: str) -> Path:
    return RUNS_ROOT / run_id / "manifest.yaml"


def _timeline_path(run_id: str) -> Path:
    return RUNS_ROOT / run_id / "timeline.jsonl"


def _load_manifest(run_id: str) -> dict:
    p = _manifest_path(run_id)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _load_timeline(run_id: str) -> list[dict]:
    p = _timeline_path(run_id)
    if not p.exists():
        return []
    events = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _load_audit_md() -> list[dict]:
    """Parse audit.md into structured blocks.
    
    Returns list of dicts: {ts, phase, label, bullets}
    """
    p = AIDLC_DOCS / "audit.md"
    if not p.exists():
        return []
    
    text = p.read_text(encoding="utf-8")
    blocks = []
    
    # Split by ## headers
    parts = re.split(r'\n##\s+', text)
    for part in parts[1:]:  # Skip preamble
        lines = part.strip().splitlines()
        if not lines:
            continue
        
        # Parse header: "<ts> <PHASE> - <LABEL>"
        header = lines[0]
        match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)\s+([A-Z]+)\s+-\s+(.+)', header)
        if not match:
            continue
        
        ts, phase, label = match.groups()
        bullets = []
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('- '):
                bullets.append(line[2:])
        
        blocks.append({
            "ts": ts,
            "phase": phase,
            "label": label,
            "bullets": bullets,
        })
    
    return blocks


def _load_state_md() -> dict:
    """Parse aidlc-state.md into structured data."""
    p = AIDLC_DOCS / "aidlc-state.md"
    if not p.exists():
        return {}
    
    text = p.read_text(encoding="utf-8")
    data = {
        "project_name": "",
        "project_type": "",
        "current_stage": "",
        "phase": "",
        "stage_progress": [],
        "extensions": [],
    }
    
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- **Project Name**:"):
            data["project_name"] = line.split(":", 1)[1].strip()
        elif line.startswith("- **Project Type**:"):
            data["project_type"] = line.split(":", 1)[1].strip()
        elif line.startswith("- **Current Stage**:"):
            data["current_stage"] = line.split(":", 1)[1].strip()
        elif line.startswith("- **Lifecycle Phase**:"):
            data["phase"] = line.split(":", 1)[1].strip()
        elif line.startswith("| ") and "Extension" in line:
            pass  # Header row
        elif line.startswith("| ") and line.count("|") >= 3:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4 and parts[1] and parts[1] != "Extension":
                data["extensions"].append({
                    "name": parts[1],
                    "enabled": parts[2],
                    "decided_at": parts[3],
                })
        elif line.startswith("- [x]") or line.startswith("- [ ]"):
            checked = line.startswith("- [x]")
            desc = line[5:].strip()
            data["stage_progress"].append({
                "done": checked,
                "description": desc,
            })
    
    return data

# ---------------------------------------------------------------------------
# Compact YAML builders
# ---------------------------------------------------------------------------

def _build_project_context(manifest: dict) -> dict:
    """Build compact project context dict."""
    profile = manifest.get("project_profile", {})
    version = manifest.get("orchestrator_version", "unknown")
    if version == "unknown" and SCRIPTS_VERSION.exists():
        version = SCRIPTS_VERSION.read_text(encoding="utf-8").strip()
    
    ctx = {
        "slug": manifest.get("project_slug", "unknown"),
        "version": version,
        "started": _format_timestamp(manifest.get("started_at", "")),
        "profile": {
            "ui": profile.get("ui", False),
            "api": profile.get("api", False),
            "legacy": profile.get("has_legacy", False),
            "framework": profile.get("framework", "none"),
        },
    }

    # Include design system info when available
    ds_path = profile.get("design_system_path", "")
    if ds_path:
        ctx["design_system"] = {
            "path": ds_path,
            "has_stitch_data": profile.get("has_stitch_data", False),
            "has_figma_data": profile.get("has_figma_data", False),
        }

    return ctx


def _build_current_state(state: dict, manifest: dict) -> dict:
    """Build compact current state dict."""
    current_stage = state.get("current_stage") or manifest.get("current_stage", "unknown")
    return {
        "stage": current_stage,
        "phase": state.get("phase", "unknown"),
        "type": state.get("project_type", manifest.get("project_type", "unknown")),
        "completed": manifest.get("completed_stages", []),
        "skipped": manifest.get("skipped_stages", []),
        "failed": len(manifest.get("failed_stages", [])),
    }


def _build_recent_decisions(audit_blocks: list[dict], max_entries: int = 10) -> list[dict]:
    """Build compact recent decisions list."""
    decisions = [b for b in audit_blocks if "decision" in b["label"].lower() or "approved" in b["label"].lower()]
    recent = decisions[-max_entries:] if len(decisions) > max_entries else decisions
    return [
        {
            "ts": b["ts"],
            "phase": b["phase"],
            "label": b["label"],
            "bullets": b["bullets"],
        }
        for b in recent
    ]


def _build_stage_timeline(timeline: list[dict], max_events: int = 5) -> dict:
    """Build compact stage timeline dict."""
    stage_events: dict[str, list[dict]] = {}
    for evt in timeline:
        stage = evt.get("stage", "orchestrator")
        if stage not in stage_events:
            stage_events[stage] = []
        stage_events[stage].append(evt)
    
    result = {}
    for stage, evts in stage_events.items():
        result[stage] = [
            {
                "ts": e.get("ts", "unknown"),
                "evt": e.get("evt", "unknown"),
            }
            for e in evts[-max_events:]
        ]
    return result


def _build_open_items(manifest: dict, timeline: list[dict]) -> dict:
    """Build compact open items dict."""
    units = manifest.get("units", [])
    incomplete = [u for u in units if isinstance(u, dict) and not u.get("complete", False)]
    pending = [e for e in timeline if e.get("evt") == "needs_human"]
    
    return {
        "incomplete_units": len(incomplete),
        "pending_approvals": len(pending),
        "items": [
            *[f"unit:{u.get('name', 'unknown')}:pending" for u in incomplete],
            *[f"approval:{d.get('stage', 'unknown')}" for d in pending],
        ],
    }


def _build_skills(manifest: dict) -> list[str]:
    """Build compact skills list."""
    return list(manifest.get("skill_paths", {}).keys())


def _build_handoff_summary(run_id: str, max_handoffs: int = 10) -> list[dict]:
    """Build compact handoff summary list."""
    handoffs_dir = _run_dir(run_id) / "handoffs"
    if not handoffs_dir.exists():
        return []
    
    outputs = sorted(handoffs_dir.glob("*.output.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)
    result = []
    for handoff in outputs[:max_handoffs]:
        try:
            content = yaml.safe_load(handoff.read_text(encoding="utf-8")) or {}
            result.append({
                "name": handoff.name,
                "status": content.get("status", "unknown"),
                "stage": content.get("stage", "unknown"),
            })
        except Exception:
            result.append({
                "name": handoff.name,
                "status": "unreadable",
                "stage": "unknown",
            })
    return result

# ---------------------------------------------------------------------------
# Compact format rendering
# ---------------------------------------------------------------------------

def _render_compact(data: dict) -> str:
    """Render compact YAML-like format. Saves ~40% tokens vs Markdown."""
    lines = []
    
    def _emit(key: str, value: Any, indent: int = 0) -> None:
        prefix = "  " * indent
        if isinstance(value, dict):
            if not value:
                lines.append(f"{prefix}{key}: {{}}")
                return
            lines.append(f"{prefix}{key}:")
            for k, v in sorted(value.items()) if key != "profile" else value.items():
                _emit(k, v, indent + 1)
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
                return
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    # Inline dicts in lists
                    parts = []
                    for k, v in item.items():
                        if isinstance(v, (dict, list)):
                            parts.append(f"{k}:<complex>")
                        else:
                            parts.append(f"{k}={v}")
                    lines.append(f"{prefix}  - {', '.join(parts)}")
                elif isinstance(item, str):
                    lines.append(f"{prefix}  - {item}")
                else:
                    lines.append(f"{prefix}  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{prefix}{key}: {value}")
        elif isinstance(value, float):
            lines.append(f"{prefix}{key}: {value:.1f}")
        elif value is None:
            lines.append(f"{prefix}{key}: null")
        else:
            # String - escape if needed
            val = str(value)
            if any(c in val for c in [":", "#", "{", "}", "[", "]"]):
                val = f'"{val}"'
            lines.append(f"{prefix}{key}: {val}")
    
    for key, value in data.items():
        _emit(key, value)
    
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Main build function
# ---------------------------------------------------------------------------

def build_context(run_id: str, depth: str = "auto", format: str = "compact") -> dict:
    """Build the full context snapshot for a run.
    
    Args:
        run_id: The run identifier
        depth: "minimal", "standard", "comprehensive", or "auto"
        format: "markdown", "yaml", "json", or "compact"
    
    Returns:
        Dict with: run_id, depth, generated_at, tokens, format, context
    """
    manifest = _load_manifest(run_id)
    timeline = _load_timeline(run_id)
    audit_blocks = _load_audit_md()
    state = _load_state_md()
    
    # Auto depth selection
    if depth == "auto":
        completed_count = len(manifest.get("completed_stages", []))
        for (min_stages, max_stages), selected_depth in AUTO_DEPTH_MAP.items():
            if min_stages <= completed_count <= max_stages:
                depth = selected_depth
                break
        else:
            depth = "standard"
    
    budget = DEPTH_BUDGETS.get(depth, 800)
    
    # Check cache
    checksums = _file_checksums(run_id)
    cached = _load_cached(run_id, depth, checksums)
    if cached is not None:
        result = cached["result"]
        result["cached"] = True
        result["cache_age"] = _format_timestamp(cached["cached_at"])
        return result
    
    # Build data structure
    project = _build_project_context(manifest)
    current = _build_current_state(state, manifest)
    
    data = {
        "project": project,
        "state": current,
    }
    
    # Depth-dependent sections
    if depth == "minimal":
        data["decisions"] = _build_recent_decisions(audit_blocks, max_entries=3)
    
    elif depth == "standard":
        data["decisions"] = _build_recent_decisions(audit_blocks, max_entries=10)
        data["timeline"] = _build_stage_timeline(timeline, max_events=5)
        data["open"] = _build_open_items(manifest, timeline)
    
    elif depth == "comprehensive":
        data["decisions"] = _build_recent_decisions(audit_blocks, max_entries=20)
        data["timeline"] = _build_stage_timeline(timeline, max_events=10)
        data["open"] = _build_open_items(manifest, timeline)
        data["skills"] = _build_skills(manifest)
        data["handoffs"] = _build_handoff_summary(run_id, max_handoffs=10)
    
    # Render based on format
    if format == "compact":
        rendered = _render_compact(data)
    elif format == "markdown":
        # Build markdown from compact data
        rendered = _render_markdown(data)
    elif format in ("yaml", "json"):
        # Keep structured, will be dumped later
        rendered = None
    else:
        rendered = _render_compact(data)
    
    # Calculate metrics
    token_count = _estimate_tokens(rendered or json.dumps(data, indent=2))
    savings_estimate = token_count  # Baseline: full files would be much larger
    
    result = {
        "run_id": run_id,
        "depth": depth,
        "generated_at": _now_iso(),
        "tokens": token_count,
        "format": format,
        "cached": False,
        "savings_estimate": savings_estimate,
        "data": data,
    }
    
    if rendered is not None:
        result["context"] = rendered
    
    # Save to cache
    _save_cached(run_id, depth, checksums, result)
    
    return result


def _render_markdown(data: dict) -> str:
    """Render markdown from compact data structure."""
    lines = []
    lines.append(f"# AIDLC Context: {data['project']['slug']} ({data['state']['stage']})")
    lines.append(f"_depth={data.get('depth', 'unknown')}, tokens={data.get('tokens', 'unknown')}_")
    lines.append("")
    
    # Project
    p = data["project"]
    lines.append(f"**Project**: {p['slug']} v{p['version']}")
    lines.append(f"**Profile**: UI={p['profile']['ui']}, API={p['profile']['api']}, Legacy={p['profile']['legacy']}, Framework={p['profile']['framework']}")
    lines.append("")
    
    # State
    s = data["state"]
    lines.append(f"**Stage**: {s['stage']} | **Phase**: {s['phase']} | **Type**: {s['type']}")
    if s['completed']:
        lines.append(f"**Completed**: {', '.join(s['completed'])}")
    if s['skipped']:
        lines.append(f"**Skipped**: {', '.join(s['skipped'])}")
    if s['failed']:
        lines.append(f"**Failed**: {s['failed']}")
    lines.append("")
    
    # Decisions
    if "decisions" in data:
        lines.append("**Recent Decisions**:")
        for d in data["decisions"]:
            lines.append(f"- {d['ts']} [{d['phase']}] {d['label']}")
        lines.append("")
    
    # Timeline
    if "timeline" in data:
        lines.append("**Stage Timeline**:")
        for stage, evts in data["timeline"].items():
            lines.append(f"- {stage}: {len(evts)} events")
        lines.append("")
    
    # Open items
    if "open" in data:
        o = data["open"]
        if o["items"]:
            lines.append(f"**Open**: {o['incomplete_units']} units, {o['pending_approvals']} approvals")
        lines.append("")
    
    # Skills
    if "skills" in data:
        lines.append(f"**Skills**: {', '.join(data['skills'])}")
        lines.append("")
    
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description="Build AIDLC contextual snapshot from traceability files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s 2026-05-08-healthz-endpoint
    %(prog)s 2026-05-08-healthz-endpoint --depth comprehensive --format compact
    %(prog)s 2026-05-08-healthz-endpoint --depth auto --output context.yaml --format yaml
    %(prog)s 2026-05-08-healthz-endpoint --format json | jq .tokens
        """
    )
    p.add_argument("run_id", help="Run identifier")
    p.add_argument("--depth", choices=["minimal", "standard", "comprehensive", "auto"], default="auto",
                   help="Context depth (default: auto — selects based on completed stage count)")
    p.add_argument("--output", "-o", help="Output file path (default: stdout)")
    p.add_argument("--format", choices=["markdown", "yaml", "json", "compact"], default="compact",
                   help="Output format (default: compact YAML-like)")
    p.add_argument("--no-cache", action="store_true",
                   help="Bypass cache and force regeneration")
    
    args = p.parse_args()
    
    result = build_context(args.run_id, args.depth, args.format)
    
    if args.no_cache:
        # Regenerate ignoring cache
        cache_path = _cache_path(args.run_id)
        if cache_path.exists():
            cache_path.unlink()
        result = build_context(args.run_id, args.depth, args.format)
    
    # Format output
    if args.format == "json":
        output = json.dumps(result, indent=2, default=str)
    elif args.format == "yaml":
        output = yaml.safe_dump(result, default_flow_style=False, sort_keys=False)
    elif args.format == "markdown":
        output = result.get("context", "")
    else:  # compact
        output = result.get("context", "")
    
    # Print metrics
    metrics = f"# Context: {result['run_id']} | depth={result['depth']} | tokens={result['tokens']} | cached={result['cached']}"
    if result.get("cache_age"):
        metrics += f" (cached_at={result['cache_age']})"
    
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(output, encoding="utf-8")
        print(f"{metrics}")
        print(f"Written to {args.output}")
    else:
        print(metrics)
        print("")
        print(output)


if __name__ == "__main__":
    main()
