#!/usr/bin/env python3
"""factory_run.py — Run Manager for AIDLC Orchestrator (Phase 6).

Owns the per-run manifest.yaml (state machine source of truth) and the
timeline.jsonl (append-only event log). Provides resume/replay/legacy-adopt
flows so a crashed orchestration run can be picked up at the last completed
stage.

Subcommands
----------
    generate-run-id [--slug <slug>]
        Generate a run-id of the form YYYY-MM-DDTHH-MM-SSZ-<slug> using
        cross-platform Python datetime (not shell date command).

    init <run-id> --user-request <text> [--project-slug <slug>] [--force]
        Initialize manifest.yaml and timeline.jsonl for a new run.

    set <run-id> [--field key=value]...
        Set arbitrary top-level manifest fields. JSON-decoded if possible.

    complete-stage <run-id> <stage> [--next-stage <next>]
        Mark a stage complete in manifest.completed_stages[]; update
        last_checkpoint_at; emit a `stage_complete` event. Idempotent.

    fail-stage <run-id> <stage> [--reason <text>]
        Mark a stage failed. Useful for crash recovery records.

    emit <run-id> --evt <name> [--stage <s>] [--field key=value]...
        Append a single event to timeline.jsonl. Used by the orchestrator
        to record arbitrary lifecycle events (spawn_start, spawn_end,
        cost_govern_skip, etc.).

    stage-open --run-id <run-id> --stage <stage> [--phase <PHASE>] [--unit <unit>]
        Emit spawn_start (with unit when provided), write START audit, set
        manifest.units[].status=in_progress for Construction units, return JSON.

    stage-close --run-id <run-id> --stage <stage> --status <status>
        Read --from-handoff / --bullets-file, write COMPLETE audit, emit
        spawn_end (matched by stage + optional unit + ts-start), update unit
        status, and update completed/failed state. Return one JSON object.

    check-spawns <run-id> [--stage <stage>] [--require-closed]
        List spawn_start events without a matching spawn_end. Exit 1 when
        --require-closed and any remain open (Construction instrumentation gate).

    ensure-dirs --run-id <run-id> [--extra <path> ...]
        Create workspace-local run, handoff, docs and optional directories.

    path-check <path> ... [--type file|dir|any] [--soft]
        Return JSON checks; missing paths exit 1 unless --soft is specified.

    status <run-id> [--json]
        Print the current manifest.

    resume <run-id>
        Compute the next stage to spawn from manifest.completed_stages[].
        Print a JSON object with: completed_count, current_stage,
        next_stage_suggestion, partial_outputs (any stale handoff files).
        Emit a `resume_requested` event.

    replay <run-id> --from <stage>
        Roll the manifest back: truncate completed_stages[] before <stage>;
        archive output handoffs for rolled-back stages with a .replay-<ts>
        suffix; set current_stage = <stage>. Emit a `replay_requested` event.

    tail <run-id> [--follow] [--json]
        Print timeline events. With --follow, polls every 0.5s like `tail -f`.

Atomicity
---------
manifest.yaml writes use write-tmp-then-rename for atomic updates.
timeline.jsonl is append-only with a single line written per call (atomic
for line-sized writes on POSIX local filesystems).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print(f"missing dependency: {sys.executable} -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)

try:
    from skill_utils import _log
except ImportError:
    def _log(level: str, msg: str, **kwargs) -> None:
        """Fallback _log if skill_utils is not available."""
        import sys as _sys
        stream = _sys.stderr if level in ("ERROR", "WARNING") else _sys.stdout
        print(f"[{level}] {msg}", file=stream)


REPO_ROOT = Path(os.environ.get("AIDLC_ROOT", Path(__file__).resolve().parents[1]))
RUNS_ROOT = REPO_ROOT / ".aidlc-orchestrator" / "runs"
AIDLC_DOCS = REPO_ROOT / "aidlc-docs"
SCRIPTS_VERSION = REPO_ROOT / "aidlc-scripts" / "VERSION"

PHASE_ORDER = [
    "workspace-scout",
    "reverse-engineer",
    "requirements-analyst",
    "product-pass",
    "design-pass",
    "arch-pass",
    "story-writer",
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


_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def validate_run_id(run_id: str) -> None:
    if run_id in (".", "..") or not _RUN_ID_RE.match(run_id):
        _die(f"invalid run_id: {run_id!r}")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _die(msg: str, code: int = 2) -> None:
    _log("ERROR", msg)
    sys.exit(code)


def run_dir(run_id: str, must_exist: bool = True) -> Path:
    validate_run_id(run_id)
    p = RUNS_ROOT / run_id
    if must_exist and not p.exists():
        _die(f"run not found: {p}")
    return p


def manifest_path(run_id: str) -> Path:
    validate_run_id(run_id)
    return RUNS_ROOT / run_id / "manifest.yaml"


def timeline_path(run_id: str) -> Path:
    validate_run_id(run_id)
    return RUNS_ROOT / run_id / "timeline.jsonl"


def load_manifest(run_id: str) -> dict:
    p = manifest_path(run_id)
    if not p.exists():
        _die(f"manifest not found: {p}")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def save_manifest_atomic(run_id: str, data: dict) -> None:
    p = manifest_path(run_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")
    # Windows: Path.replace can raise FileExistsError if the destination exists.
    try:
        tmp.replace(p)
    except FileExistsError:
        p.unlink(missing_ok=True)
        tmp.replace(p)


# Stages that are per-unit in Construction — --unit is mandatory on open/close.
PER_UNIT_STAGES = frozenset({"code-generator", "build-test-agent"})


def _unit_id_of(entry: dict) -> str | None:
    if not isinstance(entry, dict):
        return None
    for key in ("id", "name", "unit_name"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _find_unit_entry(manifest: dict, unit: str) -> dict | None:
    for entry in manifest.get("units") or []:
        if _unit_id_of(entry) == unit:
            return entry
    return None


def _set_unit_status(manifest: dict, unit: str, status: str) -> bool:
    """Update manifest.units[].status for unit. Returns True if changed/found."""
    entry = _find_unit_entry(manifest, unit)
    if entry is None:
        # Construction may open a unit before units[] is populated — record it.
        entry = {"id": unit, "status": status}
        manifest.setdefault("units", []).append(entry)
        return True
    if entry.get("status") == status:
        return False
    entry["status"] = status
    return True


def _mark_progress_terminal(run_id: str, stage: str, unit: str | None, status: str) -> None:
    """Best-effort: mark the live progress cursor terminal when a unit closes."""
    if not unit or status not in {"complete", "failed", "blocked"}:
        return
    try:
        import factory_progress
    except ImportError:
        return
    path = factory_progress._live_path(run_id, stage, unit)
    if not path.exists():
        return
    data = factory_progress._load(path)
    now = factory_progress._now()
    factory_progress._ensure_timing(data, now)
    factory_progress._accrue_until(data, now)
    data["status"] = status
    data["updated_at"] = now
    if status == "complete":
        factory_progress._close_attempt_at(data, now)
    factory_progress._save(path, data)


def _matching_spawn_starts(
    events: list[dict], stage: str, *, unit: str | None, ts_start: str | None,
) -> list[tuple[int, dict]]:
    starts = [
        (index, event) for index, event in enumerate(events)
        if event.get("evt") == "spawn_start" and event.get("stage") == stage
    ]
    if unit:
        unit_hits = [
            (index, event) for index, event in starts
            if event.get("unit") == unit
        ]
        # Prefer unit-tagged opens; fall back to legacy untagged only with explicit ts.
        starts = unit_hits if unit_hits else [
            (index, event) for index, event in starts
            if "unit" not in event
        ]
    matching = [
        (index, event) for index, event in starts
        if not ts_start or event.get("ts") == ts_start
    ]
    return matching


def _spawn_end_matches(start: dict, end: dict) -> bool:
    if end.get("evt") != "spawn_end":
        return False
    if end.get("stage") != start.get("stage"):
        return False
    if end.get("ts_start") != start.get("ts"):
        return False
    start_unit = start.get("unit")
    end_unit = end.get("unit")
    if start_unit:
        # Prefer exact unit match; allow legacy closes that omitted unit.
        return end_unit in (start_unit, None)
    return True


def _open_spawns(events: list[dict], stage: str | None = None) -> list[dict]:
    opens: list[dict] = []
    for event in events:
        if event.get("evt") != "spawn_start":
            continue
        if stage and event.get("stage") != stage:
            continue
        if not any(_spawn_end_matches(event, end) for end in events):
            opens.append(event)
    return opens


def append_event(run_id: str, event: dict) -> None:
    p = timeline_path(run_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def _parse_field(kv: str):
    k, _, v = kv.partition("=")
    if not k:
        _die(f"invalid --field: {kv}")
    try:
        return k, json.loads(v)
    except json.JSONDecodeError:
        return k, v


def _set_dotted(obj: dict, dotted_key: str, value) -> None:
    """Set obj[a][b][c] = value given dotted_key 'a.b.c'.

    Intermediate keys missing or non-dict are replaced with empty dicts.
    Single-key (no dot) sets obj[key] = value as before.
    """
    parts = dotted_key.split(".")
    cur = obj
    for p in parts[:-1]:
        if not isinstance(cur.get(p), dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


# ---------------------------------------------------------------------------
# emit_audit_block — atomic "timeline event + audit.md append" helper.
#
# This compiles the substep-6 canonical sequence from orchestrator.md
# (Step 8 of shared primitives) into one call. The orchestrator used to
# inline the full procedure at every approval gate; that boilerplate now
# lives in `.aidlc-orchestrator/contracts/audit-block.protocol.md` and is
# enforced here.
#
# Canonical evt vocabulary (matches orchestrator.md spec):
#   user_answers_received  — requires --stage
#   user_decision          — requires --stage + --field decision=<approve|reject|amend|cancel>
#   stage_skipped          — requires --stage + --field reason=<text>
#   orchestrator_note      — requires --field summary=<text>
#
# Header format (locked, do not deviate):
#   ## <ts> <PHASE> - <LABEL>
#   - bullet1
#   - bullet2
# ---------------------------------------------------------------------------


AUDIT_BLOCK_EVT_VOCABULARY = {
    "user_answers_received": {"required_stage": True, "required_fields": ()},
    "user_decision":         {"required_stage": True, "required_fields": ("decision",)},
    "stage_skipped":         {"required_stage": True, "required_fields": ("reason",)},
    "orchestrator_note":     {"required_stage": False, "required_fields": ("summary",)},
    "spawn_start":           {"required_stage": True, "required_fields": ()},
    "spawn_end":             {"required_stage": True, "required_fields": ()},
}

VALID_PHASES = ("INCEPTION", "CONSTRUCTION", "OPERATIONS")


def audit_md_path() -> Path:
    return AIDLC_DOCS / "audit.md"


def _read_last_h2(audit_path: Path) -> tuple[str, str] | None:
    """Return (ts, '<PHASE> - <LABEL>') for the last H2 in audit.md, or None."""
    if not audit_path.exists():
        return None
    last = None
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            last = line
    if not last:
        return None
    # Format: "## <ts> <PHASE> - <LABEL>"
    body = last[3:].strip()
    parts = body.split(None, 1)
    if len(parts) < 2:
        return None
    ts, rest = parts[0], parts[1]
    return (ts, rest)


def _flock(path: Path):
    """Context manager for cross-platform advisory exclusive lock on `path`.

    Uses a separate lockfile (path + '.lock') so writers can read+write the
    target safely. Uses fcntl (POSIX) or msvcrt (Windows). Falls back to
    no-op on unsupported platforms (e.g. WASM).
    """
    import contextlib

    @contextlib.contextmanager
    def cm():
        path.parent.mkdir(parents=True, exist_ok=True)
        lockfile = path.with_suffix(path.suffix + ".lock")
        with lockfile.open("a") as lf:
            _acquire_lock(lf)
            try:
                yield
            finally:
                _release_lock(lf)
    return cm()


def _acquire_lock(lf) -> None:
    try:
        import fcntl
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        return
    except ImportError:
        pass
    try:
        import msvcrt
        msvcrt.locking(lf.fileno(), msvcrt.LK_LOCK, 1)
    except ImportError:
        pass


def _release_lock(lf) -> None:
    try:
        import fcntl
        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        return
    except ImportError:
        pass
    try:
        import msvcrt
        msvcrt.locking(lf.fileno(), msvcrt.LK_UNLCK, 1)
    except ImportError:
        pass


def _append_audit_block(
    ts: str, phase: str, label: str, bullets: list[str], *, _locked: bool = False,
) -> bool:
    """Append a block under flock with a dedupe guard. Returns True if appended,
    False if dedupe'd."""
    audit = audit_md_path()
    with nullcontext() if _locked else _flock(audit):
        if not audit.exists():
            audit.parent.mkdir(parents=True, exist_ok=True)
            audit.write_text("# Audit Log\n\n", encoding="utf-8")

        last = _read_last_h2(audit)
        new_rest = f"{phase} - {label}"
        if last and last[0] == ts and last[1] == new_rest:
            return False  # dedupe

        # Chronology check: never write a header with ts < the last header's ts.
        if last:
            try:
                from datetime import datetime as _dt
                if _dt.fromisoformat(ts) < _dt.fromisoformat(last[0]):
                    _die(f"chronology violation: ts {ts} < last audit ts {last[0]}")
            except (ValueError, TypeError):
                pass  # unparseable — let it through rather than blocking

        # Build the block. Always separate from preceding content by a blank line.
        prior = audit.read_text(encoding="utf-8")
        sep = "" if prior.endswith("\n\n") else ("\n" if prior.endswith("\n") else "\n\n")
        block = f"{sep}## {ts} {new_rest}\n"
        for b in bullets:
            block += f"- {b}\n"
        block += "\n"
        with audit.open("a", encoding="utf-8") as f:
            f.write(block)
    return True


def _emit_audit_event(
    run_id: str, evt: str, phase: str, label: str, bullets: list[str], fields: dict,
) -> tuple[str, bool]:
    # Assign fresh timestamps under the audit lock, in persisted audit order.
    # Microsecond precision also distinguishes rapid reopenings of one stage.
    with _flock(audit_md_path()):
        ts = now_iso()
        appended = _append_audit_block(ts, phase, label, bullets, _locked=True)
        append_event(run_id, {**fields, "ts": ts, "evt": evt, "run_id": run_id})
    return ts, appended


def _validate_emit_audit_args(args: argparse.Namespace) -> tuple[dict, list[str]]:
    """Validate emit_audit_block arguments and return (rules, errors).

    Aggregates all validation errors so callers see the full requirement set
    in a single failure instead of fixing one missing arg at a time.
    Fails fast on unknown evt since downstream rules are meaningless.
    """
    errors: list[str] = []

    if args.evt not in AUDIT_BLOCK_EVT_VOCABULARY:
        valid = ", ".join(sorted(AUDIT_BLOCK_EVT_VOCABULARY))
        _die(f"unknown evt: {args.evt!r}. Valid evt vocabulary: {valid}")
    rules = AUDIT_BLOCK_EVT_VOCABULARY[args.evt]

    if not args.phase:
        errors.append(f"--phase is required (one of: {', '.join(VALID_PHASES)})")
    elif args.phase not in VALID_PHASES:
        errors.append(f"invalid phase: {args.phase!r}. Valid phases: {', '.join(VALID_PHASES)}")

    if not args.label:
        errors.append("--label is required")
    if rules["required_stage"] and not args.stage:
        errors.append(f"evt {args.evt!r} requires --stage")
    if not args.bullet:
        errors.append("at least one --bullet is required")

    fields: dict = {}
    for kv in args.field or []:
        k, v = _parse_field(kv)
        fields[k] = v
    for required in rules["required_fields"]:
        if required not in fields:
            errors.append(f"evt {args.evt!r} requires --field {required}=<value>")

    return rules, errors, fields


def cmd_emit_audit_block(args: argparse.Namespace) -> None:
    args.bullet = _collect_bullets(args)
    _rules, errors, fields = _validate_emit_audit_args(args)

    if errors:
        joined = "\n  - ".join(errors)
        _die(
            f"emit_audit_block invocation has {len(errors)} problem(s):\n  - {joined}"
        )

    # Validate run exists (unless --ts is provided — retry semantics).
    if not args.ts:
        run_dir(args.run_id, must_exist=True)

    # Determine ts: either explicit (retry) or fresh emit.
    if args.ts:
        ts = args.ts
        appended = _append_audit_block(ts, args.phase, args.label, args.bullet)
    else:
        if args.stage:
            fields["stage"] = args.stage
        ts, appended = _emit_audit_event(
            args.run_id, args.evt, args.phase, args.label, args.bullet, fields,
        )
    if appended:
        print(ts)
    else:
        print(f"{ts} (dedupe skipped -- identical block already present)")


def cmd_list(args: argparse.Namespace) -> None:
    """List all runs sorted by modification time (newest first)."""
    if not RUNS_ROOT.exists():
        return
    entries = sorted(
        (e for e in RUNS_ROOT.iterdir() if e.is_dir() and (e / "manifest.yaml").exists()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for e in entries:
        print(e.name)


def cmd_generate_run_id(args: argparse.Namespace) -> None:
    """Generate a run-id of the form YYYY-MM-DDTHH-MM-SSZ-<slug>.

    Uses Python datetime (cross-platform) instead of the shell `date` command.
    Sanitizes the slug: lowercase, spaces→hyphens, strip non-alphanumeric.
    """
    slug = args.slug.lower().strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9_.-]", "", slug)
    slug = slug.strip("-.")
    if not slug:
        slug = "run"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    print(f"{ts}-{slug}")


def cmd_init(args: argparse.Namespace) -> None:
    rd = run_dir(args.run_id, must_exist=False)
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "handoffs").mkdir(exist_ok=True)
    if manifest_path(args.run_id).exists() and not args.force:
        _die(f"manifest already exists at {manifest_path(args.run_id)}; use --force")

    orch_version = "unknown"
    if SCRIPTS_VERSION.exists():
        orch_version = SCRIPTS_VERSION.read_text(encoding="utf-8").strip()
    manifest = {
        "run_id": args.run_id,
        "started_at": now_iso(),
        "last_checkpoint_at": now_iso(),
        "user_request": args.user_request,
        "project_slug": args.project_slug or REPO_ROOT.name.lower().replace(" ", "-"),
        "current_stage": "workspace-scout",
        "completed_stages": [],
        "skipped_stages": [],
        "failed_stages": [],
        "orchestrator_version": orch_version,
        "project_profile": {
            "ui": False,
            "api": False,
            "has_legacy": False,
            "framework": "none",
            "design_system_path": "",
            "has_figma_data": False,
            "has_stitch_data": False,
        },
        "units": [],
        "skill_paths": {},
    }
    save_manifest_atomic(args.run_id, manifest)
    append_event(args.run_id, {
        "ts": now_iso(),
        "evt": "run_init",
        "run_id": args.run_id,
        "user_request": args.user_request,
    })
    print(f"initialized run {args.run_id} at {rd}")


def cmd_set(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.run_id)
    for kv in args.field or []:
        k, v = _parse_field(kv)
        _set_dotted(manifest, k, v)
    manifest["last_checkpoint_at"] = now_iso()
    save_manifest_atomic(args.run_id, manifest)
    print(f"updated {len(args.field or [])} field(s)")


def _reconcile_state(run_id: str) -> dict:
    """Check for drift between manifest, timeline, units, and open spawns.

    Returns a dict with drift info used by status/resume to surface the
    Construction instrumentation failure mode (work done, index dead).
    """
    drift: dict = {"drift": False, "details": []}
    manifest_p = manifest_path(run_id)
    if not manifest_p.exists():
        return drift
    manifest = yaml.safe_load(manifest_p.read_text(encoding="utf-8")) or {}

    timeline_p = timeline_path(run_id)
    timeline_stages: set[str] = set()
    events: list[dict] = []
    if timeline_p.exists():
        events = _parse_timeline_events(timeline_p)
        for e in events:
            if e.get("evt") == "stage_complete" and e.get("stage"):
                timeline_stages.add(e["stage"])

    completed = set(manifest.get("completed_stages", []))
    missing = completed - timeline_stages
    if missing:
        drift["drift"] = True
        drift["details"].append({
            "kind": "completed_not_in_timeline",
            "stages": sorted(missing),
        })

    # Open Construction spawns (spawn_start without spawn_end) — the mountain-bike failure.
    open_spawns = _open_spawns(events)
    construction_opens = [
        e for e in open_spawns if e.get("stage") in PER_UNIT_STAGES
    ]
    if construction_opens:
        drift["drift"] = True
        drift["details"].append({
            "kind": "open_spawns",
            "count": len(construction_opens),
            "spawns": [
                {"stage": e.get("stage"), "unit": e.get("unit"), "ts": e.get("ts")}
                for e in construction_opens
            ],
            "fix": "run: factory_run.py check-spawns <run-id> --require-closed",
        })

    # Units stuck pending/in_progress while code-generator already has output handoffs.
    handoffs = run_dir(run_id) / "handoffs"
    stuck_units: list[dict] = []
    for entry in manifest.get("units") or []:
        unit = _unit_id_of(entry)
        if not unit:
            continue
        status = entry.get("status") or "pending"
        if status in {"complete", "failed", "blocked", "skipped"}:
            continue
        has_output = False
        if handoffs.exists():
            patterns = [
                f"code-generator.{unit}.output.yaml",
                f"code-generator.{unit}.*.output.yaml",
            ]
            has_output = any(handoffs.glob(p) for p in patterns)
        if has_output:
            stuck_units.append({"unit": unit, "status": status, "evidence": "handoff_output"})
    if stuck_units:
        drift["drift"] = True
        drift["details"].append({
            "kind": "units_pending_with_handoffs",
            "units": stuck_units,
            "fix": "stage-close --unit was skipped; close each unit or repair units[].status",
        })

    last_action = manifest.get("last_action_reason")
    if last_action:
        drift["last_action"] = last_action

    return drift


def cmd_complete_stage(args: argparse.Namespace, *, quiet: bool = False) -> None:
    manifest = load_manifest(args.run_id)
    manifest.setdefault("completed_stages", [])
    manifest.setdefault("failed_stages", [])
    if args.stage in manifest["completed_stages"]:
        if not quiet:
            print(f"stage {args.stage} already complete (idempotent)")
        return
    # Fail closed: do not mark Construction stages complete while spawns are open.
    if args.stage in PER_UNIT_STAGES:
        opens = _open_spawns(_parse_timeline_events(timeline_path(args.run_id)), stage=args.stage)
        if opens:
            detail = ", ".join(
                f"{e.get('unit') or '?'}@{e.get('ts')}" for e in opens[:5]
            )
            _die(
                f"cannot complete-stage {args.stage}: {len(opens)} open spawn(s) "
                f"without spawn_end ({detail}). "
                "Run stage-close --unit for each, then check-spawns --require-closed."
            )
    manifest["completed_stages"].append(args.stage)
    manifest["failed_stages"] = [
        f for f in manifest["failed_stages"] if f.get("stage") != args.stage
    ]
    manifest["last_checkpoint_at"] = now_iso()
    if args.reason:
        manifest["last_action_reason"] = args.reason
    if args.next_stage:
        manifest["current_stage"] = args.next_stage
    save_manifest_atomic(args.run_id, manifest)
    append_event(args.run_id, {
        "ts": now_iso(),
        "evt": "stage_complete",
        "run_id": args.run_id,
        "stage": args.stage,
        "next_stage": args.next_stage,
        "reason": args.reason,
    })
    if not quiet:
        print(f"marked {args.stage} complete")


def cmd_fail_stage(args: argparse.Namespace, *, quiet: bool = False) -> None:
    manifest = load_manifest(args.run_id)
    failures = manifest.setdefault("failed_stages", [])
    failures.append({"stage": args.stage, "reason": args.reason or "unspecified", "at": now_iso()})
    manifest["last_checkpoint_at"] = now_iso()
    save_manifest_atomic(args.run_id, manifest)
    append_event(args.run_id, {
        "ts": now_iso(),
        "evt": "stage_failed",
        "run_id": args.run_id,
        "stage": args.stage,
        "reason": args.reason,
    })
    if not quiet:
        print(f"marked {args.stage} failed: {args.reason or 'unspecified'}")


def cmd_emit(args: argparse.Namespace) -> None:
    fields = {}
    for kv in args.field or []:
        k, v = _parse_field(kv)
        fields[k] = v
    event = {"ts": now_iso(), "evt": args.evt, "run_id": args.run_id, **fields}
    if args.stage:
        event["stage"] = args.stage
    append_event(args.run_id, event)
    print(json.dumps(event))


def _stage_timing(events: list[dict]) -> dict[str, dict]:
    """Build per-stage timing events from timeline data."""
    stage_events: dict[str, dict] = {}
    for e in events:
        stage = e.get("stage")
        if not stage:
            continue
        if stage not in stage_events:
            stage_events[stage] = {}
        if e["evt"] in ("spawn_start", "stage_start"):
            stage_events[stage]["start"] = e["ts"]
        elif e["evt"] in ("spawn_end", "stage_complete"):
            stage_events[stage]["end"] = e["ts"]
        elif e["evt"] in ("needs_human",):
            stage_events[stage]["needs_human"] = e["ts"]
        elif e["evt"] in ("user_decision",):
            stage_events[stage]["decision"] = e["ts"]
    return stage_events


def _print_latency(run_id: str, manifest: dict) -> None:
    timeline_p = timeline_path(run_id)
    if not timeline_p.exists():
        print("no timeline available")
        return
    events = _parse_timeline_events(timeline_p)

    ne, sp, sd = None, None, None
    for e in events:
        if e.get("evt") == "needs_human":
            ne = e.get("ts")
        elif e.get("evt") == "spawn_end":
            sp = e.get("ts")
        elif e.get("evt") == "user_decision":
            sd = e.get("ts")

    lines = [f"Approval Gate Latency: {run_id}", "-" * 60]
    if ne and sd:
        try:
            from datetime import datetime as dt
            dur = (dt.fromisoformat(sd) - dt.fromisoformat(ne)).total_seconds() / 60.0
            lines.append(f"  needs_human -> user_decision:  {dur:.1f}m")
        except (ValueError, TypeError):
            lines.append("  needs_human -> user_decision:  parse error")
    elif ne:
        lines.append("  needs_human -> user_decision:  pending (no decision yet)")
    if sp and sd:
        try:
            from datetime import datetime as dt
            total = (dt.fromisoformat(sd) - dt.fromisoformat(sp)).total_seconds() / 60.0
            lines.append(f"  spawn_end -> user_decision:   {total:.1f}m")
        except (ValueError, TypeError):
            lines.append("  spawn_end -> user_decision:    parse error")

    stage_events = _stage_timing(events)
    for stage, ts in sorted(stage_events.items()):
        if ts.get("start") and ts.get("end"):
            try:
                from datetime import datetime as dt
                dur = (dt.fromisoformat(ts["end"]) - dt.fromisoformat(ts["start"])).total_seconds() / 60.0
                lines.append(f"  {stage:30s}  {dur:.1f}m")
            except (ValueError, TypeError):
                pass
        if ts.get("needs_human") and ts.get("decision"):
            try:
                from datetime import datetime as dt
                gate = (dt.fromisoformat(ts["decision"]) - dt.fromisoformat(ts["needs_human"])).total_seconds() / 60.0
                lines.append(f"  {stage:30s}  +- approval gate: {gate:.1f}m")
            except (ValueError, TypeError):
                pass

    lines.append("-" * 60)
    print("\n".join(lines))


# Stage → next slash command. Higher stages in PHASE_ORDER override lower
# ones so we always offer the deepest unmet phase. Single source of truth so
# orchestrator prompts don't have to format `<run-id>` themselves.
_NEXT_COMMAND_RULES = [
    # (stages that, when completed, mean we're past this phase, next-command)
    # Extended Inception order: product → design → arch → plan. Rules are
    # walked deepest-first, so order shallow→deep here.
    ({"workspace-scout", "requirements-analyst"}, "/factory-product-pass"),
    ({"product-pass"}, "/factory-design-pass"),
    ({"design-pass"}, "/factory-arch-pass"),
    ({"arch-pass"}, "/factory-plan"),
    ({"story-writer", "workflow-planner", "unit-decomposer"}, "/factory-build"),
    ({"code-generator", "build-test-agent"}, "/factory-review"),
    ({"reviewer-code", "reviewer-security", "reviewer-performance", "reviewer-simplifier"}, "/factory-ship"),
]


def _next_command(run_id: str, manifest: dict) -> str | None:
    """Return the next-step slash command with run_id literally substituted.

    Returns None when the run is finished (post ship-agent) or no progress
    has been made yet.
    """
    completed = set(manifest.get("completed_stages", []))
    if "ship-agent" in completed:
        return None
    # walk rules deepest-first so we offer the deepest unmet next-cmd
    for stages, next_cmd in reversed(_NEXT_COMMAND_RULES):
        if completed & stages:
            return f"{next_cmd} {run_id}"
    return None


def cmd_status(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.run_id)
    if args.next_cmd:
        nxt = _next_command(args.run_id, manifest)
        if nxt:
            print(nxt)
        else:
            print(end="")  # silent — run finished or not started
        return
    if args.latency:
        _print_latency(args.run_id, manifest)
        return
    reconcile = _reconcile_state(args.run_id)
    if args.json:
        payload = dict(manifest)
        payload["reconcile"] = reconcile
        print(json.dumps(payload, indent=2))
        return
    print(yaml.safe_dump(manifest, default_flow_style=False, sort_keys=False), end="")
    if reconcile.get("drift"):
        print("---")
        print("reconcile:")
        print(yaml.safe_dump(reconcile, default_flow_style=False, sort_keys=False), end="")


def _next_stage(manifest: dict) -> str | None:
    """Compute the next stage to spawn.

    Trust the manifest's current_stage field (set by the orchestrator via
    complete-stage --next-stage), since only the orchestrator knows the
    conditional flow (e.g. whether to skip reverse-engineer in greenfield).
    Fall back to PHASE_ORDER scan only if current_stage is missing or already
    completed. Stages in `skipped_stages[]` are passed over during the scan.
    """
    completed = set(manifest.get("completed_stages", []))
    skipped = set(manifest.get("skipped_stages", []))
    current = manifest.get("current_stage")
    if current and current not in completed and current not in skipped and current in PHASE_ORDER:
        return current
    # Compute start index: after current_stage if in PHASE_ORDER,
    # otherwise after the last completed stage (handles synthetic markers)
    if current and current in PHASE_ORDER:
        start_idx = PHASE_ORDER.index(current) + 1
    else:
        last_idx = max(
            (PHASE_ORDER.index(s) for s in manifest.get("completed_stages", [])
             if s in PHASE_ORDER),
            default=-1
        )
        start_idx = last_idx + 1
    for stage in PHASE_ORDER[start_idx:]:
        if stage not in completed and stage not in skipped:
            return stage
    return None


def cmd_resume(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.run_id)
    completed = manifest.get("completed_stages", [])
    nxt = _next_stage(manifest)

    result: dict = {
        "run_id": args.run_id,
        "completed_count": len(completed),
        "completed_stages": completed,
        "current_stage": manifest.get("current_stage"),
        "next_stage_suggestion": nxt,
        "last_checkpoint_at": manifest.get("last_checkpoint_at"),
    }

    handoffs = run_dir(args.run_id) / "handoffs"
    if handoffs.exists() and nxt:
        partial = sorted(handoffs.glob(f"{nxt}*.output.yaml"))
        if partial:
            result["partial_outputs"] = [str(p.relative_to(REPO_ROOT)) for p in partial]

    # Reconcile state drift
    result["reconcile"] = _reconcile_state(args.run_id)

    # Version compatibility check
    if SCRIPTS_VERSION.exists():
        current_ver = SCRIPTS_VERSION.read_text(encoding="utf-8").strip()
        manifest_ver = manifest.get("orchestrator_version", "0.0.0")
        if manifest_ver != current_ver:
            result["version_warning"] = (
                f"manifest built with orchestrator v{manifest_ver}, "
                f"current scripts are v{current_ver}"
            )

    print(json.dumps(result, indent=2))
    append_event(args.run_id, {
        "ts": now_iso(),
        "evt": "resume_requested",
        "run_id": args.run_id,
        "next_stage": nxt,
    })


def cmd_replay(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.run_id)
    manifest.setdefault("completed_stages", [])
    target = args.from_stage
    if target not in manifest["completed_stages"]:
        _die(f"cannot replay from {target}: not in completed_stages {manifest['completed_stages']}")

    idx = manifest["completed_stages"].index(target)
    rolled_back = manifest["completed_stages"][idx:]
    manifest["completed_stages"] = manifest["completed_stages"][:idx]
    manifest["current_stage"] = target
    manifest["last_checkpoint_at"] = now_iso()

    archived: list[str] = []
    handoffs = run_dir(args.run_id) / "handoffs"
    if handoffs.exists():
        ts = int(time.time())
        for stage in rolled_back:
            for f in handoffs.glob(f"{stage}*.output.yaml"):
                archived_path = f.with_name(f"{f.stem}.replay-{ts}.yaml")
                f.rename(archived_path)
                archived.append(str(archived_path.relative_to(REPO_ROOT)))

    save_manifest_atomic(args.run_id, manifest)
    append_event(args.run_id, {
        "ts": now_iso(),
        "evt": "replay_requested",
        "run_id": args.run_id,
        "from_stage": target,
        "rolled_back": rolled_back,
        "archived": archived,
    })
    print(json.dumps({
        "replayed_from": target,
        "rolled_back": rolled_back,
        "archived_outputs": archived,
    }, indent=2))




def _print_event(line: str, as_json: bool) -> None:
    if not line:
        return
    if as_json:
        print(line)
        return
    try:
        e = json.loads(line)
        ts = e.get("ts", "")
        evt = e.get("evt", "?")
        stage = e.get("stage", "")
        reserved = {"ts", "evt", "stage", "run_id"}
        details = ", ".join(f"{k}={v}" for k, v in e.items() if k not in reserved)
        print(f"{ts}  {evt:20s} {stage:30s} {details}")
    except json.JSONDecodeError:
        print(f"!malformed: {line}")


def _parse_timeline_events(timeline_p: Path) -> list[dict]:
    """Parse timeline.jsonl into a list of event dicts, skipping malformed lines."""
    events: list[dict] = []
    if not timeline_p.exists():
        return events
    for line in timeline_p.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _build_stage_stats(events: list[dict]) -> tuple[dict[str, dict], list[str]]:
    """Build per-stage stats dict and ordered stage list from timeline events."""
    stage_stats: dict[str, dict] = {}
    stage_order: list[str] = []
    for evt in events:
        stage = evt.get("stage") or evt.get("evt", "")
        if stage not in stage_stats:
            stage_stats[stage] = {"start": None, "end": None, "evt": evt.get("evt")}
            stage_order.append(stage)
        if evt["evt"] in ("spawn_start", "run_init", "stage_start"):
            stage_stats[stage]["start"] = evt["ts"]
        elif evt["evt"] in ("stage_complete", "spawn_end"):
            stage_stats[stage]["end"] = evt["ts"]
            stage_stats[stage]["status"] = "done"
        elif evt["evt"] == "stage_failed":
            stage_stats[stage]["status"] = "failed"
        elif evt["evt"] == "cost_govern_skip":
            stage_stats[stage]["status"] = "skipped"
    return stage_stats, stage_order


def _load_budget(run_dir_path: Path) -> tuple[int, float, int, float]:
    """Load token/wall-clock budget and usage from budget.yaml.

    Returns (token_max, wall_max, token_used, wall_used) with sensible defaults.
    """
    token_max = 5_000_000
    wall_max = 240.0
    token_used = 0
    wall_used = 0.0
    budget_p = run_dir_path / "budget.yaml"
    if budget_p and budget_p.exists():
        try:
            budget_data = yaml.safe_load(budget_p.read_text(encoding="utf-8")) or {}
            token_used = int(budget_data.get("used", {}).get("tokens", 0))
            wall_used = float(budget_data.get("used", {}).get("wall_clock_min", 0.0))
            token_max = int(budget_data.get("budget", {}).get("tokens_max", token_max))
            wall_max = float(budget_data.get("budget", {}).get("wall_clock_max_min", wall_max))
        except (ValueError, TypeError):
            pass
    return token_max, wall_max, token_used, wall_used


def _stage_bar(dur_minutes: float, bar_width: int = 12) -> str:
    """Render a duration bar (filled # + remaining .) for the timeline graph."""
    fill = min(int(dur_minutes / 5), bar_width)
    return "#" * fill + "." * (bar_width - fill)


def cmd_graph(args: argparse.Namespace) -> None:
    """Print a visual timeline bar chart of a completed run."""
    manifest = load_manifest(args.run_id)
    timeline_p = timeline_path(args.run_id)
    if not timeline_p.exists():
        _die(f"no timeline at {timeline_p}")

    events = _parse_timeline_events(timeline_p)
    stage_stats, _stage_order = _build_stage_stats(events)

    completed = set(manifest.get("completed_stages", []))
    skipped = set(manifest.get("skipped_stages", []))
    failed = {s.get("stage") for s in manifest.get("failed_stages", [])}

    token_max, wall_max, token_used, wall_used = _load_budget(RUNS_ROOT / args.run_id)

    bar_width = 12
    lines = ["", f"Timeline: {manifest.get('run_id', args.run_id)}", "-" * 60]
    for stage in PHASE_ORDER:
        stats = stage_stats.get(stage, {})
        status = "  "
        if stage in completed:
            status = "[OK]"
        elif stage in failed:
            status = "[FAIL]"
        elif stage in skipped:
            status = "[WARN]"
        elif manifest.get("current_stage") == stage:
            status = "> "

        duration_str = ""
        if stats.get("start") and stats.get("end"):
            try:
                from datetime import datetime as dt
                s = dt.fromisoformat(stats["start"])
                e = dt.fromisoformat(stats["end"])
                dur = (e - s).total_seconds() / 60.0
                duration_str = f"{dur:.1f}m"
                bar = _stage_bar(dur, bar_width)
            except (ValueError, TypeError):
                bar = "." * bar_width
        else:
            bar = "." * bar_width

        lines.append(f"  {stage:30s} {bar} {duration_str:8s} {status}")

    token_pct = round((token_used / token_max) * 100, 1) if token_max > 0 else 0
    wall_pct = round((wall_used / wall_max) * 100, 1) if wall_max > 0 else 0
    lines.append("-" * 60)
    lines.append(
        f"Budget: {token_used:,} / {token_max:,} tokens ({token_pct}%)  "
        f"{wall_used} / {wall_max} min ({wall_pct}%)"
    )
    lines.append("")
    print("\n".join(lines))


def cmd_tail(args: argparse.Namespace) -> None:
    p = timeline_path(args.run_id)
    if not p.exists():
        _die(f"no timeline at {p}")

    if not args.follow:
        for line in p.read_text(encoding="utf-8").splitlines():
            _print_event(line, args.json)
        return

    with p.open(encoding="utf-8") as f:
        for line in f:
            _print_event(line.rstrip("\n"), args.json)
        try:
            while True:
                line = f.readline()
                if not line:
                    if not p.exists():
                        print(f"[timeline removed: {p}]", file=sys.stderr)
                        return
                    time.sleep(0.5)
                    continue
                _print_event(line.rstrip("\n"), args.json)
        except KeyboardInterrupt:
            return


def _workspace_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def _read_bullet_source(path: Path) -> str:
    try:
        # Windows PowerShell 5.1's UTF8 writer includes a BOM.
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        _die(f"cannot read bullet source {path}: {exc}")


def _clean_bullets(entries: list[str]) -> list[str]:
    bullets = []
    for entry in entries:
        for raw in entry.splitlines():
            line = raw.strip()
            if line.startswith("- "):
                line = line[2:].strip()
            if line and not line.startswith("#"):
                bullets.append(line)
    return bullets


def _load_handoff(path: Path) -> dict:
    text = _read_bullet_source(path)
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        _die(f"invalid handoff YAML {path}: {exc}")
    if not isinstance(data, dict):
        _die(f"handoff must be a YAML object: {path}")
    entries = data.get("audit_entries", [])
    if not isinstance(entries, list) or any(not isinstance(e, str) for e in entries):
        _die(f"handoff audit_entries must be a list of strings: {path}")
    return data


def _collect_bullets(args: argparse.Namespace, handoff: dict | None = None) -> list[str]:
    entries = list(getattr(args, "bullet", None) or [])
    if getattr(args, "bullets_file", None):
        entries.append(_read_bullet_source(_workspace_path(args.bullets_file)))
    if getattr(args, "from_handoff", None):
        if handoff is None:
            handoff = _load_handoff(_workspace_path(args.from_handoff))
        entries.extend(handoff.get("audit_entries", []))
    return _clean_bullets(entries)


def _stage_phase(args: argparse.Namespace) -> str:
    if args.phase:
        return args.phase
    if args.stage.startswith(("code-generator", "build-test-agent", "reviewer-")):
        return "CONSTRUCTION"
    if args.stage == "ship-agent":
        return "OPERATIONS"
    return "INCEPTION"


def _stage_fields(args: argparse.Namespace) -> dict:
    fields = {}
    reserved = {"ts", "evt", "run_id", "stage", "status", "ts_start", "phase"}
    for kv in args.field or []:
        key, value = _parse_field(kv)
        if "=" not in kv or key in reserved:
            _die(f"invalid or reserved stage --field: {kv}")
        fields[key] = value
    return fields


def cmd_stage_open(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.run_id)
    unit = getattr(args, "unit", None) or None
    if args.stage in PER_UNIT_STAGES and not unit:
        _die(
            f"--unit is required for {args.stage} "
            "(Construction instrumentation is unit-keyed; omitting --unit "
            "leaves audit/manifest/progress unable to track parallel units)"
        )
    if unit:
        import factory_progress
        factory_progress._check_token(unit, "unit")
    fields = _stage_fields(args)
    phase = _stage_phase(args)
    label = args.stage.upper().replace("-", " ")
    if unit:
        label = f"{label} {unit}"
        fields["unit"] = unit
    event_fields = {**fields, "stage": args.stage, "phase": phase}
    if unit:
        event_fields["unit"] = unit
    bullets = ["[Orchestrator] stage opened"]
    if unit:
        bullets.append(f"unit: {unit}")
    ts, _appended = _emit_audit_event(
        args.run_id, "spawn_start", phase, f"{label} START", bullets, event_fields,
    )
    if unit:
        with _flock(manifest_path(args.run_id)):
            manifest = load_manifest(args.run_id)
            _set_unit_status(manifest, unit, "in_progress")
            manifest["last_checkpoint_at"] = now_iso()
            if args.stage in PER_UNIT_STAGES:
                manifest["current_stage"] = args.stage
            save_manifest_atomic(args.run_id, manifest)
        # Attach progress cursor immediately so started_at precedes first writes.
        # Idempotent if the orchestrator also calls begin. Suppress begin's JSON
        # so stage-open still returns a single JSON object on stdout.
        try:
            import io
            from argparse import Namespace
            from contextlib import redirect_stdout
            import factory_progress
            with redirect_stdout(io.StringIO()):
                factory_progress.cmd_begin(Namespace(
                    run_id=args.run_id, stage=args.stage, unit=unit, fresh=False,
                ))
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001 — never block open on progress attach
            _log("WARNING", f"progress begin after stage-open failed: {exc}")
    payload = {"ts": ts, "evt": "spawn_start", "stage": args.stage}
    if unit:
        payload["unit"] = unit
    print(json.dumps(payload))


def _attach_close_tokens(args: argparse.Namespace, ts_start: str, ts_end: str | None) -> None:
    if ts_end is None:
        return
    if args.tokens is None and args.tokens_in is None and args.tokens_out is None:
        return
    import factory_progress
    factory_progress.record_attempt_tokens(
        args.run_id, args.stage, ts_start, ts_end,
        unit=args.unit, tokens=args.tokens,
        tokens_in=args.tokens_in, tokens_out=args.tokens_out,
    )


def cmd_stage_close(args: argparse.Namespace) -> None:
    # Validate every supplied source and field before mutating any run files.
    load_manifest(args.run_id)
    fields = _stage_fields(args)
    handoff = None
    if args.from_handoff:
        handoff = _load_handoff(_workspace_path(args.from_handoff))
        if handoff.get("status") != args.status:
            _die("handoff status must match --status")
        # Prefer handoff unit_name when CLI omits --unit (legacy callers).
        if not args.unit and isinstance(handoff.get("unit_name"), str) and handoff["unit_name"]:
            args.unit = handoff["unit_name"]
    if args.stage in PER_UNIT_STAGES and not args.unit:
        _die(
            f"--unit is required for {args.stage} "
            "(pass the same --unit used in stage-open, or set unit_name in the handoff)"
        )
    bullets = _collect_bullets(args, handoff)
    phase = _stage_phase(args)
    for key in ("tokens", "tokens_in", "tokens_out", "wall_min"):
        value = getattr(args, key)
        if value is not None:
            if value < 0 or not value < float("inf"):
                _die(f"--{key.replace('_', '-')} must be finite and non-negative")
            fields[key] = value
    if args.unit:
        fields["unit"] = args.unit
    if args.unit or args.tokens is not None or args.tokens_in is not None or args.tokens_out is not None:
        import factory_progress
        factory_progress._check_token(args.stage, "stage")
        if args.unit:
            factory_progress._check_token(args.unit, "unit")

    # Serialize helper closes so parallel stages cannot overwrite manifest updates.
    with _flock(manifest_path(args.run_id)):
        events = _parse_timeline_events(timeline_path(args.run_id))
        matching = _matching_spawn_starts(
            events, args.stage, unit=args.unit, ts_start=args.ts_start,
        )
        if not matching:
            _die("no matching stage-open event for --stage / --unit / --ts-start")
        start_index, opened = matching[-1]
        ts_start = opened["ts"]
        if args.unit and opened.get("unit") not in (None, args.unit):
            _die("stage-close --unit does not match stage-open unit")
        if any(
            event.get("evt") == "replay_requested"
            and args.stage in event.get("rolled_back", [])
            for event in events[start_index + 1:]
        ):
            _die("stage attempt was invalidated by replay; run stage-open again")
        if opened.get("phase", phase) != phase:
            _die("stage-close phase must match stage-open")
        closed = next((
            event for event in events[start_index + 1:]
            if event.get("evt") == "spawn_end" and event.get("stage") == args.stage
            and event.get("ts_start") == ts_start
            and (
                not args.unit
                or event.get("unit") == args.unit
                or "unit" not in event
            )
        ), None)
        # Superseded check: only when matching without unit discrimination.
        later_same = [
            (index, event) for index, event in enumerate(events)
            if index > start_index
            and event.get("evt") == "spawn_start"
            and event.get("stage") == args.stage
            and (
                not args.unit
                or event.get("unit") == args.unit
                or ("unit" not in event and "unit" not in opened)
            )
        ]
        if closed and later_same:
            _die("--ts-start refers to a superseded stage attempt")
        if closed and closed.get("status") != args.status:
            _die("stage was already closed with a different status")
        ts_end = closed["ts"] if closed else None
        if not closed:
            label = args.stage.upper().replace("-", " ")
            if args.unit:
                label = f"{label} {args.unit}"
            end_fields = {
                **fields, "ts_start": ts_start, "stage": args.stage, "status": args.status,
            }
            if args.unit:
                end_fields["unit"] = args.unit
            ts_end, _appended = _emit_audit_event(
                args.run_id, "spawn_end", phase, f"{label} COMPLETE", [
                    f"status: {args.status}", *bullets,
                    *(
                        f"{key}: {fields[key]}"
                        for key in ("tokens", "tokens_in", "tokens_out", "wall_min")
                        if key in fields
                    ),
                ], end_fields,
            )
        _attach_close_tokens(args, ts_start, ts_end)
        if args.unit:
            unit_status = {
                "complete": "complete",
                "failed": "failed",
                "blocked": "blocked",
                "needs_human": "needs_human",
            }.get(args.status, args.status)
            # For code-generator, "complete" on a unit often means generated+approved
            # handoff; still mark unit complete. needs_human leaves unit in_progress-ish.
            if args.status == "needs_human":
                unit_status = "in_progress"
            manifest = load_manifest(args.run_id)
            _set_unit_status(manifest, args.unit, unit_status)
            manifest["last_checkpoint_at"] = now_iso()
            save_manifest_atomic(args.run_id, manifest)
            _mark_progress_terminal(args.run_id, args.stage, args.unit, args.status)
        if args.status == "complete" and not args.no_complete_stage:
            cmd_complete_stage(args, quiet=True)
        elif args.status == "failed":
            recorded = any(
                event.get("evt") == "stage_failed" and event.get("stage") == args.stage
                for event in events[start_index + 1:]
            )
            manifest = load_manifest(args.run_id)
            if not recorded and not any(
                failure.get("stage") == args.stage
                and failure.get("at", "") >= ts_start
                for failure in manifest.get("failed_stages", [])
            ):
                cmd_fail_stage(args, quiet=True)
    payload = {
        "ts_start": ts_start, "ts_end": ts_end, "status": args.status, "stage": args.stage,
    }
    if args.unit:
        payload["unit"] = args.unit
    print(json.dumps(payload))


def cmd_check_spawns(args: argparse.Namespace) -> None:
    load_manifest(args.run_id)
    events = _parse_timeline_events(timeline_path(args.run_id))
    opens = _open_spawns(events, stage=args.stage)
    payload = {
        "run_id": args.run_id,
        "stage": args.stage,
        "open_count": len(opens),
        "open_spawns": [
            {
                "stage": e.get("stage"),
                "unit": e.get("unit"),
                "ts": e.get("ts"),
                "phase": e.get("phase"),
            }
            for e in opens
        ],
    }
    print(json.dumps(payload, indent=2))
    if args.require_closed and opens:
        _log(
            "ERROR",
            f"[InstrumentationGap] {len(opens)} open spawn(s) without spawn_end — "
            "finish stage-close before continuing Construction",
        )
        sys.exit(1)


def cmd_ensure_dirs(args: argparse.Namespace) -> None:
    validate_run_id(args.run_id)
    base = RUNS_ROOT / args.run_id
    paths = [base, base / "handoffs", base / "tmp", AIDLC_DOCS]
    paths.extend(_workspace_path(raw) for raw in args.extra or [])
    for path in paths:
        if not path.resolve().is_relative_to(REPO_ROOT.resolve()):
            _die(f"directory must stay inside the workspace: {path}")
        if path.exists() and not path.is_dir():
            _die(f"directory path is a file: {path}")
    created = []
    for path in paths:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))
    print(json.dumps({"ok": True, "run_id": args.run_id, "created": created}))


def cmd_path_check(args: argparse.Namespace) -> None:
    results = []
    for raw in args.paths:
        path = _workspace_path(raw)
        check = {"file": path.is_file, "dir": path.is_dir, "any": path.exists}[args.type]
        results.append({"path": raw, "ok": check()})
    ok = all(result["ok"] for result in results)
    print(json.dumps({"ok": ok, "results": results}))
    if not ok and not args.soft:
        sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser(description="AIDLC Orchestrator Run Manager")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list",
        help="List all runs (directories with manifest.yaml)")
    p_list.set_defaults(func=cmd_list)

    p_gen = sub.add_parser("generate-run-id",
        help="Generate a run-id: YYYY-MM-DDTHH-MM-SSZ-<slug> (cross-platform)")
    p_gen.add_argument("--slug", default="run",
        help="slug suffix (default: run)")
    p_gen.set_defaults(func=cmd_generate_run_id)

    p_init = sub.add_parser("init")
    p_init.add_argument("run_id")
    p_init.add_argument("--user-request", required=True)
    p_init.add_argument("--project-slug")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_set = sub.add_parser("set")
    p_set.add_argument("run_id")
    p_set.add_argument("--field", action="append")
    p_set.set_defaults(func=cmd_set)

    p_cs = sub.add_parser("complete-stage")
    p_cs.add_argument("run_id")
    p_cs.add_argument("stage")
    p_cs.add_argument("--next-stage")
    p_cs.add_argument("--reason", help="reason for completion (crash resilience marker)")
    p_cs.set_defaults(func=cmd_complete_stage)

    p_fs = sub.add_parser("fail-stage")
    p_fs.add_argument("run_id")
    p_fs.add_argument("stage")
    p_fs.add_argument("--reason")
    p_fs.set_defaults(func=cmd_fail_stage)

    p_emit = sub.add_parser("emit")
    p_emit.add_argument("run_id")
    p_emit.add_argument("--evt", required=True)
    p_emit.add_argument("--stage")
    p_emit.add_argument("--field", action="append")
    p_emit.set_defaults(func=cmd_emit)

    p_eab = sub.add_parser("emit_audit_block",
        help="atomic timeline-emit + dedupe-guarded audit.md append (substep-6 helper)")
    p_eab.add_argument("run_id")
    p_eab.add_argument("--evt", required=True,
        help="one of: " + ", ".join(sorted(AUDIT_BLOCK_EVT_VOCABULARY)))
    p_eab.add_argument("--stage", help="stage_id (required for most evts)")
    p_eab.add_argument("--phase",
        help="one of: " + ", ".join(VALID_PHASES))
    p_eab.add_argument("--label",
        help="block label, e.g. 'User Decision (workflow-planner)'")
    p_eab.add_argument("--field", action="append",
        help="evt-required fields: decision=, reason=, summary= (per evt)")
    p_eab.add_argument("--bullet", action="append",
        help="audit bullet — at least one required; repeatable")
    p_eab.add_argument("--bullets-file", help="UTF-8 file, one bullet per non-empty line")
    p_eab.add_argument("--ts",
        help="override emitted ts (retry semantics; skips timeline emit)")
    p_eab.set_defaults(func=cmd_emit_audit_block)

    p_open = sub.add_parser("stage-open", help="open a stage without shell pipes")
    p_open.add_argument("--run-id", required=True)
    p_open.add_argument("--stage", required=True)
    p_open.add_argument("--phase", choices=VALID_PHASES)
    p_open.add_argument("--unit", help="unit id (required for code-generator / build-test-agent)")
    p_open.add_argument("--field", action="append")
    p_open.set_defaults(func=cmd_stage_open)

    p_close = sub.add_parser("stage-close", help="close a stage with file-based audit entries")
    p_close.add_argument("--run-id", required=True)
    p_close.add_argument("--stage", required=True)
    p_close.add_argument("--status", required=True,
                         choices=("complete", "failed", "blocked", "needs_human"))
    p_close.add_argument("--phase", choices=VALID_PHASES)
    p_close.add_argument("--ts-start", help="timestamp from stage-open (latest if omitted)")
    p_close.add_argument("--from-handoff", help="validated output handoff YAML")
    p_close.add_argument("--bullets-file", help="UTF-8 file, one bullet per non-empty line")
    p_close.add_argument("--bullet", action="append")
    p_close.add_argument("--field", action="append")
    p_close.add_argument("--tokens", type=int)
    p_close.add_argument("--tokens-in", type=int, dest="tokens_in")
    p_close.add_argument("--tokens-out", type=int, dest="tokens_out")
    p_close.add_argument(
        "--unit",
        help="unit id (required for code-generator / build-test-agent; stamps timeline + manifest)",
    )
    p_close.add_argument("--wall-min", type=float)
    p_close.add_argument("--next-stage")
    p_close.add_argument("--reason")
    p_close.add_argument("--no-complete-stage", action="store_true")
    p_close.set_defaults(func=cmd_stage_close)

    p_cs = sub.add_parser(
        "check-spawns",
        help="list open spawn_start events; --require-closed exits 1 if any remain",
    )
    p_cs.add_argument("run_id")
    p_cs.add_argument("--stage", help="limit to one stage")
    p_cs.add_argument(
        "--require-closed",
        action="store_true",
        help="exit 1 when any matched spawn_start lacks spawn_end",
    )
    p_cs.set_defaults(func=cmd_check_spawns)

    p_dirs = sub.add_parser("ensure-dirs", help="portable workspace directory creation")
    p_dirs.add_argument("--run-id", required=True)
    p_dirs.add_argument("--extra", nargs="+")
    p_dirs.set_defaults(func=cmd_ensure_dirs)

    p_check = sub.add_parser("path-check", help="portable file/directory existence checks")
    p_check.add_argument("paths", nargs="+")
    p_check.add_argument("--type", choices=("file", "dir", "any"), default="any")
    p_check.add_argument("--soft", action="store_true", help="exit 0 even if JSON ok is false")
    p_check.set_defaults(func=cmd_path_check)

    p_status = sub.add_parser("status")
    p_status.add_argument("run_id")
    p_status.add_argument("--json", action="store_true")
    p_status.add_argument("--latency", action="store_true",
                          help="print approval gate latency breakdown")
    p_status.add_argument("--next-cmd", dest="next_cmd", action="store_true",
                          help="print the next /factory-* slash command with run_id literally substituted; empty when run is finished")
    p_status.set_defaults(func=cmd_status)

    p_resume = sub.add_parser("resume")
    p_resume.add_argument("run_id")
    p_resume.set_defaults(func=cmd_resume)

    p_replay = sub.add_parser("replay")
    p_replay.add_argument("run_id")
    p_replay.add_argument("--from", dest="from_stage", required=True)
    p_replay.set_defaults(func=cmd_replay)

    p_graph = sub.add_parser("graph", help="visual timeline of a run")
    p_graph.add_argument("run_id")
    p_graph.set_defaults(func=cmd_graph)

    p_tail = sub.add_parser("tail")
    p_tail.add_argument("run_id")
    p_tail.add_argument("--follow", "-f", action="store_true")
    p_tail.add_argument("--json", action="store_true")
    p_tail.set_defaults(func=cmd_tail)

    p_timeline = sub.add_parser("timeline", help="print timeline events (alias for tail)")
    p_timeline.add_argument("run_id")
    p_timeline.add_argument("--follow", "-f", action="store_true")
    p_timeline.add_argument("--json", action="store_true")
    p_timeline.set_defaults(func=cmd_tail)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
