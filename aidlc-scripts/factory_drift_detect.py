#!/usr/bin/env python3
"""factory_drift_detect.py — Drift detection for generated UI.

Two modes:
  - Structural (always available): compares code snapshots, tokens, components.
  - Visual (Playwright optional): screenshot capture + pixel diff.

Subcommands:
  snapshot      Capture a code snapshot (JSON) from generated output.
  diff-structural  Compare two snapshots for structural drift.
  diff-visual   Screenshot + pixel diff (requires Playwright).
  baseline-init Create baseline directory structure.
  baseline-list List all baselines.
  capture       Take a screenshot (Playwright, graceful skip if unavailable).

Usage:
    python3 aidlc-scripts/factory_drift_detect.py snapshot \\
        --component Button --variant primary --code-dir src/components \\
        --output drift-snapshots/button-v1.json

    python3 aidlc-scripts/factory_drift_detect.py diff-structural \\
        --baseline drift-snapshots/button-v1.json \\
        --current drift-snapshots/button-v2.json

    python3 aidlc-scripts/factory_drift_detect.py baseline-init \\
        --ds-path design-system
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Public types ─────────────────────────────────────────────────────────────

DEFAULT_WARNING_THRESHOLD = 5.0
DEFAULT_BLOCKING_THRESHOLD = 15.0
DRIFT_THRESHOLD_ENV_VAR = "AIDLC_DRIFT_THRESHOLD"


def _resolve_thresholds(
    warning_threshold: float | None,
    blocking_threshold: float | None,
) -> tuple[float, float]:
    env = os.environ.get(DRIFT_THRESHOLD_ENV_VAR, "")
    parts = env.split(",") if env else []
    wt = warning_threshold or (float(parts[0]) if len(parts) >= 1 else DEFAULT_WARNING_THRESHOLD)
    bt = blocking_threshold or (float(parts[1]) if len(parts) >= 2 else DEFAULT_BLOCKING_THRESHOLD)
    return wt, bt


@dataclass
class DriftReport:
    passed: bool
    diff_percentage: float = 0.0
    structural_changes: list[dict] = field(default_factory=list)
    token_changes: list[dict] = field(default_factory=list)
    visual_diff_path: str | None = None
    baseline_path: str | None = None
    current_path: str | None = None
    warnings: list[str] = field(default_factory=list)
    score: float = 1.0
    needs_human: bool = False


@dataclass
class CodeSnapshot:
    component: str
    variant: str
    timestamp: str
    files: list[dict]
    tokens_used: dict[str, list[str]]
    components_used: list[str]
    code_hash: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CodeSnapshot:
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


# ── Snapshot creation ────────────────────────────────────────────────────────

_TOKEN_RE = re.compile(
    r"(spacing|radius|font-size|color|elevation)\.([a-z][a-z0-9-]*)"
)
_COMPONENT_RE = re.compile(
    r"(Button|Stack|Inline|Box|Input|Text|Surface|Icon)\s*(?:\{|\(|>)"
)


def create_snapshot(
    component: str,
    variant: str,
    code_dir: str | Path,
    ds_path: str | Path | None = None,
) -> CodeSnapshot:
    code_path = Path(code_dir)
    files: list[dict] = []
    all_tokens: dict[str, list[str]] = {}
    all_components: list[str] = []

    for fpath in sorted(code_path.rglob("*")):
        if not fpath.is_file() or fpath.suffix not in (".tsx", ".jsx", ".ts", ".js", ".html", ".css"):
            continue
        try:
            content = fpath.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = str(fpath.relative_to(code_path))

        tokens_found: dict[str, list[str]] = {}
        for m in _TOKEN_RE.finditer(content):
            cat, name = m.group(1), m.group(2)
            tokens_found.setdefault(cat, []).append(name)
            all_tokens.setdefault(cat, []).append(name)

        comps_found = list(set(_COMPONENT_RE.findall(content)))
        all_components.extend(comps_found)

        files.append({
            "path": rel,
            "size": len(content),
            "tokens": tokens_found,
            "components": comps_found,
        })

    # Build a hash of all file contents
    hash_input = "".join(f["path"] + str(f["size"]) for f in files)
    code_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    return CodeSnapshot(
        component=component,
        variant=variant,
        timestamp=datetime.now(timezone.utc).isoformat(),
        files=files,
        tokens_used={k: list(set(v)) for k, v in all_tokens.items()},
        components_used=list(set(all_components)),
        code_hash=code_hash,
    )


# ── Structural diff ──────────────────────────────────────────────────────────

def diff_structural(
    baseline: CodeSnapshot,
    current: CodeSnapshot,
    warning_threshold: float | None = None,
    blocking_threshold: float | None = None,
) -> DriftReport:
    changes: list[dict] = []
    token_changes: list[dict] = []
    warnings: list[str] = []

    # Component drift
    b_comps = set(baseline.components_used)
    c_comps = set(current.components_used)
    removed_comps = b_comps - c_comps
    added_comps = c_comps - b_comps
    if removed_comps:
        changes.append({"type": "components_removed", "items": list(removed_comps)})
    if added_comps:
        changes.append({"type": "components_added", "items": list(added_comps)})

    # Token drift
    b_tokens = baseline.tokens_used
    c_tokens = current.tokens_used
    for cat in b_tokens:
        b_set = set(b_tokens[cat])
        c_set = set(c_tokens.get(cat, []))
        removed = b_set - c_set
        added = c_set - b_set
        if removed:
            token_changes.append({
                "category": cat,
                "type": "removed",
                "tokens": list(removed),
            })
        if added:
            token_changes.append({
                "category": cat,
                "type": "added",
                "tokens": list(added),
            })
    for cat in c_tokens:
        if cat not in b_tokens:
            token_changes.append({
                "category": cat,
                "type": "added_category",
                "tokens": c_tokens[cat],
            })

    # File drift
    b_files = {f["path"]: f for f in baseline.files}
    c_files = {f["path"]: f for f in current.files}
    removed_files = set(b_files) - set(c_files)
    added_files = set(c_files) - set(b_files)
    if removed_files:
        changes.append({"type": "files_removed", "items": list(removed_files)})
    if added_files:
        changes.append({"type": "files_added", "items": list(added_files)})

    # Code hash drift
    if baseline.code_hash != current.code_hash:
        changes.append({
            "type": "code_changed",
            "baseline_hash": baseline.code_hash,
            "current_hash": current.code_hash,
        })

    # Score
    total_factors = len(changes) + len(token_changes)
    score = max(0.0, 1.0 - total_factors * 0.15)

    wt, bt = _resolve_thresholds(warning_threshold, blocking_threshold)
    diff_pct = round((1 - score) * 100, 1)
    needs_human = diff_pct >= bt

    if total_factors > 0:
        warnings.append(f"Drift detected: {len(changes)} structural, {len(token_changes)} token changes")
    if needs_human:
        warnings.append(f"High structural drift ({diff_pct}%) — needs human review")

    return DriftReport(
        passed=diff_pct < wt,
        diff_percentage=diff_pct,
        structural_changes=changes,
        token_changes=token_changes,
        warnings=warnings,
        score=round(score, 2),
        needs_human=needs_human,
    )


# ── Visual diff (Playwright optional) ────────────────────────────────────────

def _playwright_available() -> bool:
    try:
        import playwright  # noqa
        return True
    except ImportError:
        return False


def capture_screenshot(html_path: str | Path, output_path: str | Path) -> dict:
    """Take a screenshot of an HTML file using Playwright.
    
    Returns {'path': ..., 'success': True/False, 'error': ...}.
    """
    if not _playwright_available():
        return {
            "path": str(output_path),
            "success": False,
            "error": (
                "Playwright not installed. Use the launcher from "
                ".aidlc-orchestrator/runtime/common/python-runtime.md with "
                "-m pip install playwright, then -m playwright install chromium"
            ),
        }
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"path": str(output_path), "success": False, "error": "Playwright import failed"}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(f"file://{Path(html_path).resolve()}", wait_until="networkidle")
            page.screenshot(path=str(output_path), full_page=True)
            browser.close()
        return {"path": str(output_path), "success": True, "error": None}
    except Exception as e:
        return {"path": str(output_path), "success": False, "error": str(e)}


def diff_visual(
    baseline_path: str | Path,
    current_path: str | Path,
    output_dir: str | Path,
    warning_threshold: float | None = None,
    blocking_threshold: float | None = None,
) -> DriftReport:
    """Compare two screenshots using pixel comparison.
    
    Uses Pillow if available, falls back to filesize comparison.
    """
    b_path = Path(baseline_path)
    c_path = Path(current_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not b_path.exists():
        return DriftReport(
            passed=True,
            warnings=[f"No baseline at {b_path} — first capture only"],
            baseline_path=str(b_path),
            current_path=str(c_path),
        )

    if not c_path.exists():
        return DriftReport(
            passed=False,
            warnings=["Current screenshot not found"],
            baseline_path=str(b_path),
            current_path=str(c_path),
        )

    diff_percentage = 0.0
    diff_image_path = None

    try:
        from PIL import Image, ImageChops

        b_img = Image.open(b_path).convert("RGB")
        c_img = Image.open(c_path).convert("RGB")

        # Resize larger to smaller for comparison
        if b_img.size != c_img.size:
            c_img = c_img.resize(b_img.size)

        diff = ImageChops.difference(b_img, c_img)
        diff_path = out_dir / f"diff_{b_path.stem}_vs_{c_path.stem}.png"
        # Enhance contrast for visibility
        from PIL import ImageEnhance
        diff = ImageEnhance.Contrast(diff).enhance(3.0)
        diff.save(diff_path)
        diff_image_path = str(diff_path)

        # Calculate diff percentage
        bbox = diff.getbbox()
        if bbox is None:
            diff_percentage = 0.0
        else:
            total_px = b_img.width * b_img.height
            diff_px = sum(
                1 for px in diff.getdata() if any(c > 10 for c in px)
            )
            diff_percentage = round(diff_px / total_px * 100, 2)

    except ImportError:
        # Fallback: compare file sizes
        b_size = b_path.stat().st_size
        c_size = c_path.stat().st_size
        if abs(b_size - c_size) / max(b_size, c_size) > 0.1:
            diff_percentage = 50.0
    except Exception as e:
        return DriftReport(
            passed=False,
            warnings=[f"Visual diff error: {e}"],
            baseline_path=str(b_path),
            current_path=str(c_path),
        )

    wt, bt = _resolve_thresholds(warning_threshold, blocking_threshold)
    passed = diff_percentage < wt
    needs_human = diff_percentage >= bt
    warnings: list[str] = []
    if needs_human:
        warnings.append(f"High visual drift ({diff_percentage}%) — needs human review")
    elif not passed:
        warnings.append(f"Visual drift detected ({diff_percentage}%) — above warning threshold ({wt}%)")

    return DriftReport(
        passed=passed,
        diff_percentage=diff_percentage,
        visual_diff_path=diff_image_path,
        baseline_path=str(b_path),
        current_path=str(c_path),
        warnings=warnings,
        score=round(max(0, 1 - diff_percentage / 100), 2),
        needs_human=needs_human,
    )


# ── Baseline management ──────────────────────────────────────────────────────

def baseline_init(ds_path: str | Path) -> list[str]:
    ds = Path(ds_path)
    screenshots = ds / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)

    primitives_dir = ds / "primitives"
    created: list[str] = []
    if primitives_dir.exists():
        for p_dir in sorted(primitives_dir.iterdir()):
            if p_dir.is_dir():
                comp_dir = screenshots / p_dir.name
                comp_dir.mkdir(exist_ok=True)
                created.append(str(comp_dir))
    else:
        samples = screenshots / "_samples"
        samples.mkdir(exist_ok=True)
        created.append(str(samples))

    return created


def baseline_list(ds_path: str | Path) -> list[dict]:
    ds = Path(ds_path)
    screenshots = ds / "screenshots"
    if not screenshots.exists():
        return []

    entries: list[dict] = []
    for comp_dir in sorted(screenshots.iterdir()):
        if not comp_dir.is_dir():
            continue
        images = sorted(comp_dir.glob("*.png"))
        if images:
            entries.append({
                "component": comp_dir.name,
                "count": len(images),
                "images": [str(i) for i in images],
            })
    return entries


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Drift detection for generated UI.",
    )
    parser.add_argument("--ds-path", type=str, default="design-system",
                        help="Path to design-system/ directory")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # snapshot
    snap_p = subparsers.add_parser("snapshot", help="Capture a code snapshot")
    snap_p.add_argument("--component", required=True)
    snap_p.add_argument("--variant", default="default")
    snap_p.add_argument("--code-dir", required=True, help="Directory with generated code")
    snap_p.add_argument("--output", required=True, help="Output snapshot JSON path")

    # diff-structural
    ds_p = subparsers.add_parser("diff-structural", help="Compare two snapshots")
    ds_p.add_argument("--baseline", required=True, help="Baseline snapshot JSON")
    ds_p.add_argument("--current", required=True, help="Current snapshot JSON")
    ds_p.add_argument("--warning-threshold", type=float, default=None,
                      help=f"Warning threshold %% (default: {DEFAULT_WARNING_THRESHOLD}, env: {DRIFT_THRESHOLD_ENV_VAR})")
    ds_p.add_argument("--blocking-threshold", type=float, default=None,
                      help=f"Blocking threshold %% (default: {DEFAULT_BLOCKING_THRESHOLD}, env: {DRIFT_THRESHOLD_ENV_VAR})")

    # diff-visual
    dv_p = subparsers.add_parser("diff-visual", help="Screenshot + pixel diff")
    dv_p.add_argument("--baseline", required=True, help="Baseline screenshot PNG")
    dv_p.add_argument("--current", required=True, help="Current screenshot PNG")
    dv_p.add_argument("--output-dir", default="design-system/screenshots/diff",
                      help="Diff output directory")
    dv_p.add_argument("--warning-threshold", type=float, default=None,
                      help=f"Warning threshold %% (default: {DEFAULT_WARNING_THRESHOLD}, env: {DRIFT_THRESHOLD_ENV_VAR})")
    dv_p.add_argument("--blocking-threshold", type=float, default=None,
                      help=f"Blocking threshold %% (default: {DEFAULT_BLOCKING_THRESHOLD}, env: {DRIFT_THRESHOLD_ENV_VAR})")

    # capture
    cap_p = subparsers.add_parser("capture", help="Take a screenshot (Playwright)")
    cap_p.add_argument("--html", required=True, help="HTML file to screenshot")
    cap_p.add_argument("--output", required=True, help="Output PNG path")

    # baseline-init
    subparsers.add_parser("baseline-init", help="Create baseline directory structure")

    # baseline-list
    subparsers.add_parser("baseline-list", help="List all baselines")

    args = parser.parse_args()

    if args.command == "snapshot":
        snap = create_snapshot(args.component, args.variant, args.code_dir)
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(snap.to_dict(), indent=2), encoding="utf-8"
        )
        print(f"Snapshot saved -> {args.output}")
        print(f"  Component: {snap.component} / {snap.variant}")
        print(f"  Files: {len(snap.files)}")
        print(f"  Tokens: {sum(len(v) for v in snap.tokens_used.values())}")
        print(f"  Hash: {snap.code_hash}")

    elif args.command == "diff-structural":
        b_data = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        c_data = json.loads(Path(args.current).read_text(encoding="utf-8"))
        baseline = CodeSnapshot.from_dict(b_data)
        current = CodeSnapshot.from_dict(c_data)
        report = diff_structural(baseline, current, args.warning_threshold, args.blocking_threshold)
        print(json.dumps(asdict(report), indent=2))

    elif args.command == "diff-visual":
        report = diff_visual(args.baseline, args.current, args.output_dir,
                             args.warning_threshold, args.blocking_threshold)
        print(json.dumps(asdict(report), indent=2))

    elif args.command == "capture":
        result = capture_screenshot(args.html, args.output)
        print(json.dumps(result, indent=2))

    elif args.command == "baseline-init":
        created = baseline_init(args.ds_path)
        for c in created:
            print(f"Created: {c}")

    elif args.command == "baseline-list":
        entries = baseline_list(args.ds_path)
        if not entries:
            print("No baselines found.")
        else:
            for e in entries:
                print(f"  {e['component']}: {e['count']} screenshot(s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
