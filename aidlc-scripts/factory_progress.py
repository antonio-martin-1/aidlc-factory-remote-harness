#!/usr/bin/env python3
"""factory_progress.py — in-stage resume cursor.

Owns one YAML state file per stage (and per unit, when the stage is per-unit):

    .aidlc-orchestrator/runs/<run-id>/progress/<stage>[.<unit>].yaml

The orchestrator calls `begin` once per spawn and merges the JSON into the
input handoff as `continuation`. The stage agent calls `upsert` after each
completed step. A later spawn reads that YAML and continues at cursor.next_action
instead of reloading skills and re-scanning the repo.

Subcommands
-----------
    begin --run-id --stage [--unit] [--fresh]
        Create the cursor, or bump attempt and keep it. --fresh archives the
        live file first. Prints the continuation object as JSON.

    upsert --run-id --stage [--unit] --phase --next-action [...]
        Rewrite the live YAML with the new cursor. Caps the log at 5 beats.

    show --run-id --stage [--unit]
        Print the live YAML.

    list --run-id
        Print JSON for every live cursor in the run.

    archive --run-id --stage
        Archive every live cursor for that stage (all units). Used by replay.

    timings --run-id [--json]
        Print task, attempt, stage, and phase durations from the live YAML.
        The script stamps every beat. Wall clock is first start to last end.
        Sum of attempts excludes the idle gap between spawns. Approval wait
        stays in `factory_run.py status --latency`. Host token totals recorded
        by stage-close are summed beside that time. A missing count stays blank.

    record-tokens --run-id --stage --ts-start --ts-end
                  [--unit] [--tokens N] [--tokens-in N] [--tokens-out N]
        Store host usage on the attempt that overlaps that stage-close.
        stage-close calls this. The stage agent does not.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print(f"missing dependency: {sys.executable} -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(os.environ.get("AIDLC_ROOT", Path(__file__).resolve().parents[1]))
RUNS_ROOT = REPO_ROOT / ".aidlc-orchestrator" / "runs"

_TOKEN_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")
LOG_CAP = 5
LIST_CAPS = {
    "done": 200,
    "skills_satisfied": 40,
    "do_not_redo": 20,
    "artifacts_touched": 40,
    "decisions": 20,
}
PHASES = (
    "skills_loaded",
    "plan_written",
    "task_started",
    "task_done",
    "suspending",
    "beat",
)
STATUSES = ("in_progress", "suspending", "complete")


def _die(msg: str, code: int = 2) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def _check_token(value: str, label: str) -> str:
    if value in (".", "..") or ".." in value or not _TOKEN_RE.match(value):
        _die(f"invalid {label}: {value!r}")
    return value


def _now() -> str:
    override = os.environ.get("AIDLC_PROGRESS_NOW", "").strip()
    if override:
        return override
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(value: str) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _seconds_between(start: str, end: str) -> float:
    try:
        delta = (_parse_ts(end) - _parse_ts(start)).total_seconds()
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, delta), 3)


def _aidlc_phase(stage: str) -> str:
    if stage.startswith(("code-generator", "build-test-agent", "reviewer-")):
        return "CONSTRUCTION"
    if stage == "ship-agent":
        return "OPERATIONS"
    return "INCEPTION"


_STAGE_ORDER = (
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
)
_PHASE_ORDER = ("INCEPTION", "CONSTRUCTION", "OPERATIONS")


def _ensure_timing(data: dict, now: str) -> None:
    data.setdefault("task_seconds", {})
    data.setdefault("overhead_seconds", 0)
    if data.get("attempts"):
        data.setdefault("attempt_started_at", data["attempts"][-1].get("started_at") or now)
        return
    started = data.get("attempt_started_at") or data.get("updated_at") or now
    data["attempt_started_at"] = started
    data["attempts"] = [{
        "n": int(data.get("attempt") or 1),
        "started_at": started,
        "ended_at": None,
    }]


def _last_beat_at(data: dict, attempt_n: int) -> str | None:
    for entry in reversed(data.get("log") or []):
        if not isinstance(entry, dict) or not entry.get("at"):
            continue
        marked = entry.get("attempt")
        if marked is None or int(marked) == attempt_n:
            return str(entry["at"])
    return None


def _close_attempt_at_last_beat(data: dict) -> None:
    attempts = data.get("attempts") or []
    if not attempts or attempts[-1].get("ended_at"):
        return
    current = attempts[-1]
    ended = _last_beat_at(data, int(current.get("n") or 0)) or current.get("started_at")
    current["ended_at"] = ended


def _close_attempt_at(data: dict, at: str) -> None:
    attempts = data.get("attempts") or []
    if not attempts:
        return
    current = attempts[-1]
    if int(current.get("n") or 0) != int(data.get("attempt") or 0):
        return
    current["ended_at"] = at


def _interval_start(data: dict) -> str:
    log = data.get("log") or []
    if log and isinstance(log[-1], dict) and log[-1].get("at"):
        return str(log[-1]["at"])
    return str(data.get("attempt_started_at") or data.get("updated_at") or _now())


def _add_seconds(data: dict, task_id: str, seconds: float) -> None:
    if seconds <= 0:
        return
    if task_id:
        totals = data.setdefault("task_seconds", {})
        totals[task_id] = round(float(totals.get(task_id) or 0) + seconds, 3)
        return
    data["overhead_seconds"] = round(float(data.get("overhead_seconds") or 0) + seconds, 3)


def _accrue_until(data: dict, now: str) -> None:
    log = data.get("log") or []
    task_id = ""
    if log and isinstance(log[-1], dict):
        task_id = str(log[-1].get("task_id") or "")
    _add_seconds(data, task_id, _seconds_between(_interval_start(data), now))


def _attempt_open(data: dict) -> bool:
    attempts = data.get("attempts") or []
    if not attempts:
        return data.get("status") != "complete"
    return not attempts[-1].get("ended_at")


def _reported_tasks(data: dict, now: str) -> tuple[dict[str, float], float]:
    totals = {str(key): float(value) for key, value in (data.get("task_seconds") or {}).items()}
    overhead = float(data.get("overhead_seconds") or 0)
    if not _attempt_open(data):
        return totals, round(overhead, 3)
    tail = _seconds_between(_interval_start(data), now)
    log = data.get("log") or []
    task_id = ""
    if log and isinstance(log[-1], dict):
        task_id = str(log[-1].get("task_id") or "")
    if task_id:
        totals[task_id] = round(totals.get(task_id, 0.0) + tail, 3)
    else:
        overhead += tail
    return totals, round(overhead, 3)


def _progress_dir(run_id: str) -> Path:
    _check_token(run_id, "run-id")
    path = (RUNS_ROOT / run_id / "progress").resolve()
    runs = RUNS_ROOT.resolve()
    if path != runs and runs not in path.parents:
        _die("progress path escapes the runs directory")
    return path


def _live_path(run_id: str, stage: str, unit: str | None) -> Path:
    _check_token(stage, "stage")
    name = stage if not unit else f"{stage}.{_check_token(unit, 'unit')}"
    return _progress_dir(run_id) / f"{name}.yaml"


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        _die(f"progress file is not a mapping: {path}")
    return data


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _skeleton(stage: str, unit: str | None, attempt: int = 1) -> dict:
    now = _now()
    data = {
        "attempt": attempt,
        "stage": stage,
    }
    if unit:
        data["unit"] = unit
    data.update({
        "updated_at": now,
        "status": "in_progress",
        "attempt_started_at": now,
        "attempts": [{"n": attempt, "started_at": now, "ended_at": None}],
        "task_seconds": {},
        "overhead_seconds": 0,
        "cursor": {"task_id": "", "next_action": ""},
        "done": [],
        "skills_satisfied": [],
        "do_not_redo": [],
        "artifacts_touched": [],
        "decisions": [],
        "log": [],
    })
    return data


def _archive_file(path: Path, attempt: int) -> Path:
    dest = path.with_name(f"{path.stem}.attempt-{attempt}.yaml")
    if dest.exists():
        dest = path.with_name(f"{path.stem}.attempt-{attempt}-{int(time.time())}.yaml")
    os.replace(path, dest)
    return dest


def _has_cursor(data: dict) -> bool:
    cursor = data.get("cursor") or {}
    if str(cursor.get("next_action") or "").strip():
        return True
    return bool(data.get("done") or data.get("log") or data.get("skills_satisfied"))


def _continuation(data: dict, mode: str, path: Path) -> dict:
    body: dict = {"mode": mode, "progress_path": _rel(path)}
    if mode == "fresh":
        body["resume_from"] = None
        return body
    log = data.get("log") or []
    last_seq = 0
    if log and isinstance(log[-1], dict):
        last_seq = int(log[-1].get("seq") or 0)
    cursor = data.get("cursor") or {}
    body["resume_from"] = {
        "last_seq": last_seq,
        "attempt": int(data.get("attempt") or 1),
        "task_id": cursor.get("task_id") or "",
        "next_action": cursor.get("next_action") or "",
        "completed_task_ids": list(data.get("done") or []),
        "skills_satisfied": list(data.get("skills_satisfied") or []),
    }
    return body


def _cap(items: list, limit: int) -> list:
    if len(items) <= limit:
        return items
    return items[-limit:]


def _unique(items: list) -> list:
    seen = set()
    out = []
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False) if isinstance(item, (dict, list)) else item
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def cmd_begin(args: argparse.Namespace) -> None:
    path = _live_path(args.run_id, args.stage, args.unit)
    if args.fresh and path.exists():
        data = _load(path)
        _archive_file(path, int(data.get("attempt") or 1))
    if path.exists():
        data = _load(path)
        now = _now()
        _ensure_timing(data, now)
        _close_attempt_at_last_beat(data)
        data["attempt"] = int(data.get("attempt") or 1) + 1
        data["attempt_started_at"] = now
        data["updated_at"] = now
        data["status"] = "in_progress"
        data["attempts"].append({"n": data["attempt"], "started_at": now, "ended_at": None})
        _save(path, data)
        mode = "resume" if _has_cursor(data) else "fresh"
        print(json.dumps(_continuation(data, mode, path), ensure_ascii=False))
        return
    data = _skeleton(args.stage, args.unit, attempt=1)
    _save(path, data)
    print(json.dumps(_continuation(data, "fresh", path), ensure_ascii=False))


def _parse_skill(raw: str) -> dict:
    name, _, evidence = raw.partition("=")
    name = name.strip()
    if not name:
        _die(f"invalid --skill: {raw!r}")
    return {"name": name, "evidence": evidence.strip()}


def cmd_upsert(args: argparse.Namespace) -> None:
    if args.mark_done and not args.task_id:
        _die("--mark-done requires --task-id")
    if not str(args.next_action).strip():
        _die("--next-action is empty")
    if len(args.next_action) > 500:
        _die("--next-action exceeds 500 characters")
    path = _live_path(args.run_id, args.stage, args.unit)
    data = _load(path) if path.exists() else _skeleton(args.stage, args.unit, attempt=1)
    now = _now()
    _ensure_timing(data, now)
    _accrue_until(data, now)
    status = args.status
    if status is None:
        status = "suspending" if args.phase == "suspending" else "in_progress"
    cursor = dict(data.get("cursor") or {})
    if args.task_id:
        cursor["task_id"] = args.task_id
    cursor["next_action"] = args.next_action
    data["cursor"] = {"task_id": cursor.get("task_id") or "", "next_action": cursor["next_action"]}
    data["status"] = status
    data["updated_at"] = now
    if data["status"] == "complete":
        _close_attempt_at(data, now)

    done = list(data.get("done") or [])
    if args.task_id and (args.mark_done or args.phase == "task_done"):
        done.append(args.task_id)
    for task_id in args.done or []:
        done.append(task_id)
    data["done"] = _cap(_unique(done), LIST_CAPS["done"])

    skills = [item for item in (data.get("skills_satisfied") or []) if isinstance(item, dict)]
    for raw in args.skill or []:
        skill = _parse_skill(raw)
        skills = [item for item in skills if item.get("name") != skill["name"]]
        skills.append(skill)
    data["skills_satisfied"] = _cap(skills, LIST_CAPS["skills_satisfied"])

    skips = list(data.get("do_not_redo") or [])
    skips.extend(args.skip or [])
    data["do_not_redo"] = _cap(_unique(skips), LIST_CAPS["do_not_redo"])

    artifacts = list(data.get("artifacts_touched") or [])
    artifacts.extend(args.artifact or [])
    data["artifacts_touched"] = _cap(_unique(artifacts), LIST_CAPS["artifacts_touched"])

    decisions = list(data.get("decisions") or [])
    decisions.extend(args.decision or [])
    data["decisions"] = _cap(_unique(decisions), LIST_CAPS["decisions"])

    log = list(data.get("log") or [])
    last_seq = 0
    if log and isinstance(log[-1], dict):
        last_seq = int(log[-1].get("seq") or 0)
    entry = {
        "seq": last_seq + 1,
        "at": now,
        "attempt": int(data.get("attempt") or 1),
        "phase": args.phase,
        "next_action": args.next_action,
    }
    if data["cursor"]["task_id"]:
        entry["task_id"] = data["cursor"]["task_id"]
    log.append(entry)
    data["log"] = log[-LOG_CAP:]
    _save(path, data)
    print(json.dumps({
        "path": _rel(path),
        "seq": entry["seq"],
        "attempt": int(data.get("attempt") or 1),
        "status": data["status"],
    }, ensure_ascii=False))


def cmd_show(args: argparse.Namespace) -> None:
    path = _live_path(args.run_id, args.stage, args.unit)
    if not path.exists():
        _die(f"no progress file: {path}", code=1)
    sys.stdout.write(path.read_text(encoding="utf-8"))


def _live_files(run_id: str) -> list[Path]:
    directory = _progress_dir(run_id)
    if not directory.exists():
        return []
    return sorted(
        path for path in directory.glob("*.yaml")
        if path.is_file() and ".attempt-" not in path.name and not path.name.endswith(".tmp")
    )


def cmd_list(args: argparse.Namespace) -> None:
    rows = []
    for path in _live_files(args.run_id):
        data = _load(path)
        cursor = data.get("cursor") or {}
        rows.append({
            "path": _rel(path),
            "stage": data.get("stage") or "",
            "unit": data.get("unit") or "",
            "status": data.get("status") or "",
            "attempt": int(data.get("attempt") or 1),
            "task_id": cursor.get("task_id") or "",
            "next_action": cursor.get("next_action") or "",
        })
    print(json.dumps(rows, ensure_ascii=False, indent=2))


_TIMING_NOTE = (
    "Approval wait is reported by factory_run.py status --latency. "
    "Token totals sum recorded host usage. Attempts without a host count stay blank."
)


def _fmt_seconds(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return f"{seconds:.1f}s"
    whole = int(round(seconds))
    minutes, rem = divmod(whole, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {rem:02d}s"
    return f"{minutes}m {rem:02d}s"


def _coerce_token_count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 0:
        return None
    return value


def _attempt_token_total(attempt: dict) -> int | None:
    total = _coerce_token_count(attempt.get("tokens"))
    if total is not None:
        return total
    incoming = _coerce_token_count(attempt.get("tokens_in"))
    outgoing = _coerce_token_count(attempt.get("tokens_out"))
    if incoming is None or outgoing is None:
        return None
    return incoming + outgoing


def _sum_token_field(items: list[dict], key: str) -> int | None:
    known = [item[key] for item in items if item.get(key) is not None]
    if not known:
        return None
    return int(sum(known))


def _token_payload(
    tokens: int | None, tokens_in: int | None, tokens_out: int | None,
) -> dict:
    payload: dict = {}
    if tokens_in is not None:
        payload["tokens_in"] = int(tokens_in)
    if tokens_out is not None:
        payload["tokens_out"] = int(tokens_out)
    total = tokens
    if total is None and tokens_in is not None and tokens_out is not None:
        total = int(tokens_in) + int(tokens_out)
    if total is not None:
        payload["tokens"] = int(total)
    return payload


def _progress_files_for_stage(run_id: str, stage: str, unit: str | None) -> list[Path]:
    if unit:
        path = _live_path(run_id, stage, unit)
        return [path] if path.exists() else []
    exact = f"{stage}.yaml"
    prefix = f"{stage}."
    return [
        path for path in _live_files(run_id)
        if path.name == exact or path.name.startswith(prefix)
    ]


def _attempt_for_close(data: dict, ts_start: str, ts_end: str) -> dict | None:
    try:
        start_ts = _parse_ts(ts_start)
        end_ts = _parse_ts(ts_end)
    except (TypeError, ValueError):
        return None
    chosen = None
    for attempt in data.get("attempts") or []:
        if not isinstance(attempt, dict) or not attempt.get("started_at"):
            continue
        try:
            started_dt = _parse_ts(str(attempt["started_at"]))
        except (TypeError, ValueError):
            continue
        if started_dt > end_ts:
            continue
        ended = attempt.get("ended_at")
        if ended:
            try:
                if _parse_ts(str(ended)) < start_ts:
                    continue
            except (TypeError, ValueError):
                continue
        chosen = attempt
    return chosen


def record_attempt_tokens(
    run_id: str,
    stage: str,
    ts_start: str,
    ts_end: str,
    unit: str | None = None,
    tokens: int | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> bool:
    """Stamp host usage on the attempt that overlaps a stage-close.

    Sets the count. A retry with the same numbers does not add to it.
    Missing files stay untouched. Several live cursors and no unit is a skip:
    guessing would attach one spawn's usage to every unit.
    """
    payload = _token_payload(tokens, tokens_in, tokens_out)
    if not payload:
        return False
    _check_token(run_id, "run-id")
    _check_token(stage, "stage")
    if unit:
        _check_token(unit, "unit")
    files = _progress_files_for_stage(run_id, stage, unit)
    if len(files) != 1:
        if len(files) > 1:
            print(
                f"[progress] {stage}: more than one live cursor; "
                "pass --unit to attach the token count",
                file=sys.stderr,
            )
        return False
    path = files[0]
    data = _load(path)
    attempt = _attempt_for_close(data, ts_start, ts_end)
    if attempt is None:
        label = stage if not unit else f"{stage}.{unit}"
        print(
            f"[progress] {label}: no attempt overlaps this stage-close; "
            "token count left on the timeline",
            file=sys.stderr,
        )
        return False
    if all(attempt.get(key) == value for key, value in payload.items()):
        return True
    attempt.update(payload)
    _save(path, data)
    return True


def cmd_record_tokens(args: argparse.Namespace) -> None:
    for key in ("tokens", "tokens_in", "tokens_out"):
        value = getattr(args, key)
        if value is not None and value < 0:
            _die(f"--{key.replace('_', '-')} must be finite and non-negative")
    if args.tokens is None and args.tokens_in is None and args.tokens_out is None:
        _die("record-tokens needs --tokens, --tokens-in, or --tokens-out")
    attached = record_attempt_tokens(
        args.run_id, args.stage, args.ts_start, args.ts_end,
        unit=args.unit, tokens=args.tokens,
        tokens_in=args.tokens_in, tokens_out=args.tokens_out,
    )
    print(json.dumps({"attached": attached}, ensure_ascii=False))


def _attempt_seconds(attempt: dict, now: str) -> float:
    start = attempt.get("started_at")
    if not start:
        return 0.0
    return _seconds_between(str(start), str(attempt.get("ended_at") or now))


def _unit_timing(data: dict, now: str) -> dict:
    _ensure_timing(data, now)
    attempts = []
    total = 0.0
    starts: list[str] = []
    ends: list[str] = []
    for attempt in data.get("attempts") or []:
        start = attempt.get("started_at")
        end = attempt.get("ended_at") or now
        if start:
            starts.append(str(start))
            ends.append(str(end))
        seconds = _attempt_seconds(attempt, now)
        total += seconds
        attempts.append({
            "n": int(attempt.get("n") or 0),
            "seconds": round(seconds, 3),
            "open": not attempt.get("ended_at"),
            "tokens": _attempt_token_total(attempt),
            "tokens_in": _coerce_token_count(attempt.get("tokens_in")),
            "tokens_out": _coerce_token_count(attempt.get("tokens_out")),
        })
    tasks, overhead = _reported_tasks(data, now)
    open_task = ""
    if _attempt_open(data):
        log = data.get("log") or []
        if log and isinstance(log[-1], dict):
            open_task = str(log[-1].get("task_id") or "")
    wall = _seconds_between(min(starts), max(ends)) if starts else 0.0
    return {
        "stage": data.get("stage") or "",
        "unit": data.get("unit") or "",
        "wall_seconds": round(wall, 3),
        "sum_seconds": round(total, 3),
        "overhead_seconds": overhead,
        "started_at": min(starts) if starts else "",
        "ended_at": max(ends) if ends else "",
        "tokens": _sum_token_field(attempts, "tokens"),
        "tokens_in": _sum_token_field(attempts, "tokens_in"),
        "tokens_out": _sum_token_field(attempts, "tokens_out"),
        "attempts": attempts,
        "tasks": [
            {"task_id": key, "seconds": round(value, 3), "open": key == open_task and bool(open_task)}
            for key, value in tasks.items()
        ],
    }


def _stage_sort(stage: str) -> tuple:
    try:
        return (_STAGE_ORDER.index(stage), stage)
    except ValueError:
        return (len(_STAGE_ORDER), stage)


def _span(items: list[dict]) -> tuple[float, float]:
    starts = [item["started_at"] for item in items if item.get("started_at")]
    ends = [item["ended_at"] for item in items if item.get("ended_at")]
    wall = _seconds_between(min(starts), max(ends)) if starts and ends else 0.0
    total = round(sum(float(item["sum_seconds"]) for item in items), 3)
    return round(wall, 3), total


def _timing_report(run_id: str, now: str) -> dict:
    units = [_unit_timing(_load(path), now) for path in _live_files(run_id)]
    phases = []
    for phase in _PHASE_ORDER:
        grouped: dict[str, list[dict]] = {}
        for unit in units:
            if _aidlc_phase(unit["stage"]) != phase:
                continue
            grouped.setdefault(unit["stage"], []).append(unit)
        if not grouped:
            continue
        stages = []
        for stage in sorted(grouped, key=_stage_sort):
            stage_units = sorted(grouped[stage], key=lambda item: item.get("unit") or "")
            wall, total = _span(stage_units)
            starts = [unit["started_at"] for unit in stage_units if unit.get("started_at")]
            ends = [unit["ended_at"] for unit in stage_units if unit.get("ended_at")]
            stages.append({
                "stage": stage,
                "wall_seconds": wall,
                "sum_seconds": total,
                "tokens": _sum_token_field(stage_units, "tokens"),
                "tokens_in": _sum_token_field(stage_units, "tokens_in"),
                "tokens_out": _sum_token_field(stage_units, "tokens_out"),
                "started_at": min(starts) if starts else "",
                "ended_at": max(ends) if ends else "",
                "units": stage_units,
            })
        wall, total = _span(stages)
        phases.append({
            "phase": phase,
            "wall_seconds": wall,
            "sum_seconds": total,
            "tokens": _sum_token_field(stages, "tokens"),
            "tokens_in": _sum_token_field(stages, "tokens_in"),
            "tokens_out": _sum_token_field(stages, "tokens_out"),
            "stages": stages,
        })
    return {"run_id": run_id, "now": now, "phases": phases, "note": _TIMING_NOTE}


def _fmt_tokens(value: int | None) -> str:
    if value is None:
        return ""
    return f"  tokens {int(value)}"


def _print_timings(report: dict) -> None:
    lines = [f"Timings: {report['run_id']}", f"now: {report['now']}"]
    if not report["phases"]:
        lines.append("no progress yet")
    for phase in report["phases"]:
        lines.append(
            f"{phase['phase']}  wall {_fmt_seconds(phase['wall_seconds'])}"
            f"  sum {_fmt_seconds(phase['sum_seconds'])}"
            f"{_fmt_tokens(phase['tokens'])}"
        )
        for stage in phase["stages"]:
            lines.append(
                f"  {stage['stage']}  wall {_fmt_seconds(stage['wall_seconds'])}"
                f"  sum {_fmt_seconds(stage['sum_seconds'])}"
                f"{_fmt_tokens(stage['tokens'])}"
            )
            for unit in stage["units"]:
                label = unit["unit"] or "(stage)"
                lines.append(
                    f"    {label}  wall {_fmt_seconds(unit['wall_seconds'])}"
                    f"  sum {_fmt_seconds(unit['sum_seconds'])}"
                    f"  overhead {_fmt_seconds(unit['overhead_seconds'])}"
                    f"{_fmt_tokens(unit['tokens'])}"
                )
                for attempt in unit["attempts"]:
                    state = "  open" if attempt["open"] else ""
                    lines.append(
                        f"      attempt {attempt['n']}  {_fmt_seconds(attempt['seconds'])}"
                        f"{_fmt_tokens(attempt['tokens'])}{state}"
                    )
                for task in unit["tasks"]:
                    state = "  open" if task["open"] else ""
                    lines.append(f"      {task['task_id']}  {_fmt_seconds(task['seconds'])}{state}")
    lines.append(report["note"])
    print("\n".join(lines))


def cmd_timings(args: argparse.Namespace) -> None:
    _check_token(args.run_id, "run-id")
    report = _timing_report(args.run_id, _now())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    _print_timings(report)


def cmd_archive(args: argparse.Namespace) -> None:
    _check_token(args.stage, "stage")
    archived = []
    prefix = f"{args.stage}."
    exact = f"{args.stage}.yaml"
    for path in _live_files(args.run_id):
        if path.name != exact and not path.name.startswith(prefix):
            continue
        data = _load(path)
        dest = _archive_file(path, int(data.get("attempt") or 1))
        archived.append(_rel(dest))
    print(json.dumps({"archived": archived}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="AIDLC in-stage progress cursor")
    sub = parser.add_subparsers(dest="cmd", required=True)

    begin = sub.add_parser("begin")
    begin.add_argument("--run-id", required=True)
    begin.add_argument("--stage", required=True)
    begin.add_argument("--unit")
    begin.add_argument("--fresh", action="store_true")
    begin.set_defaults(func=cmd_begin)

    upsert = sub.add_parser("upsert")
    upsert.add_argument("--run-id", required=True)
    upsert.add_argument("--stage", required=True)
    upsert.add_argument("--unit")
    upsert.add_argument("--phase", required=True, choices=PHASES)
    upsert.add_argument("--next-action", required=True)
    upsert.add_argument("--task-id")
    upsert.add_argument("--mark-done", action="store_true")
    upsert.add_argument("--status", choices=STATUSES)
    upsert.add_argument("--skill", action="append")
    upsert.add_argument("--done", action="append")
    upsert.add_argument("--artifact", action="append")
    upsert.add_argument("--decision", action="append")
    upsert.add_argument("--skip", action="append")
    upsert.set_defaults(func=cmd_upsert)

    show = sub.add_parser("show")
    show.add_argument("--run-id", required=True)
    show.add_argument("--stage", required=True)
    show.add_argument("--unit")
    show.set_defaults(func=cmd_show)

    listing = sub.add_parser("list")
    listing.add_argument("--run-id", required=True)
    listing.set_defaults(func=cmd_list)

    archive = sub.add_parser("archive")
    archive.add_argument("--run-id", required=True)
    archive.add_argument("--stage", required=True)
    archive.set_defaults(func=cmd_archive)

    timings = sub.add_parser("timings")
    timings.add_argument("--run-id", required=True)
    timings.add_argument("--json", action="store_true")
    timings.set_defaults(func=cmd_timings)

    recorded = sub.add_parser("record-tokens")
    recorded.add_argument("--run-id", required=True)
    recorded.add_argument("--stage", required=True)
    recorded.add_argument("--unit")
    recorded.add_argument("--ts-start", required=True)
    recorded.add_argument("--ts-end", required=True)
    recorded.add_argument("--tokens", type=int)
    recorded.add_argument("--tokens-in", type=int, dest="tokens_in")
    recorded.add_argument("--tokens-out", type=int, dest="tokens_out")
    recorded.set_defaults(func=cmd_record_tokens)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
