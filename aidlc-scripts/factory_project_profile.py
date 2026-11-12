#!/usr/bin/env python3
"""factory_project_profile.py — Project Profile Classification & Design System Bootstrap.

Implements the logic from runtime/project-profile.md as an executable script.
Called by the orchestrator after workspace-scout completes.

Subcommands:
  classify              Read workspace-scout output, emit project_profile JSON
  bootstrap             Create design-system/ from scratch when ui=true and missing
  snap-figma            Run figma snap + import if has_figma_data
  snap-stitch           Run stitch snap + import if has_stitch_data
  reverse-engineer-ui   Scan existing CSS/SCSS/styled-components for tokens (brownfield fallback)
  set-manifest          Persist profile fields to manifest.yaml via factory_run.py set
  run                   Full pipeline: classify → bootstrap → snap → reverse-engineer → set-manifest

Usage:
    python3 aidlc-scripts/factory_project_profile.py run <run-id> --workspace-output <path>
    python3 aidlc-scripts/factory_project_profile.py classify --workspace-output <path>
    python3 aidlc-scripts/factory_project_profile.py bootstrap --repo-root <path> [--force]
    python3 aidlc-scripts/factory_project_profile.py reverse-engineer-ui --repo-root <path> --output <json>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print(f"missing dependency: {sys.executable} -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)

_SCRIPT_DIR = Path(__file__).parent
REPO_ROOT_DEFAULT = _SCRIPT_DIR.parent

# ── Helpers ──────────────────────────────────────────────────────────────────


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)


def _find_files(root: Path, patterns: list[str], max_depth: int = 4) -> list[Path]:
    """Best-effort find without shelling out, respecting depth."""
    found: list[Path] = []
    for pat in patterns:
        for p in root.rglob(pat):
            # Compute depth relative to root
            try:
                depth = len(p.relative_to(root).parts)
            except ValueError:
                continue
            if depth <= max_depth:
                found.append(p)
    return found


# ── classify ─────────────────────────────────────────────────────────────────


def _detect_ui(workspace_state: dict) -> bool:
    """Heuristic from project-profile.md §A."""
    langs = " ".join(workspace_state.get("programming_languages", [])).lower()
    structure = workspace_state.get("project_structure", "").lower()
    tech = workspace_state.get("tech_stack", [])
    tech_names = " ".join(t.get("package", "").lower() for t in tech)

    # Condition 1: TS/JS + frontend-y structure
    frontend_stack = bool(re.search(r"react|vue|svelte|angular|next|nuxt|spa|frontend|web", structure))
    has_ts_js = bool(re.search(r"typescript|javascript|tsx|jsx", langs))
    if has_ts_js and frontend_stack:
        return True

    # Condition 2: package.json declares UI framework
    ui_packages = {"react", "vue", "svelte", "@angular/core", "next", "nuxt", "sveltekit"}
    for t in tech:
        pkg = t.get("package", "").lower()
        # Strip scope
        bare = pkg.split("/")[-1]
        if bare in ui_packages:
            # React-native exclusion
            if bare == "react":
                has_react_dom = any(
                    x.get("package", "").lower() == "react-dom" for x in tech
                )
                has_rn = any(
                    x.get("package", "").lower() == "react-native" for x in tech
                )
                if has_rn and not has_react_dom:
                    continue
            return True
    return False


def _detect_api(workspace_state: dict, user_request: str = "") -> bool:
    tech = workspace_state.get("tech_stack", [])
    tech_names = " ".join(t.get("package", "").lower() for t in tech)
    api_packages = {"express", "fastify", "hono", "nestjs", "fastapi", "flask", "django"}
    for t in tech:
        if t.get("package", "").lower() in api_packages:
            return True
    if re.search(r"endpoint|route|rest|graphql|api|webhook|/[a-z][a-z0-9_-]+", user_request, re.I):
        return True
    return False


def _detect_legacy(workspace_state: dict, user_request: str = "") -> bool:
    if workspace_state.get("reverse_engineering_artifacts_present"):
        return True
    if re.search(r"migrat|refactor|deprecat|legacy|rewrite|port", user_request, re.I):
        return True
    return False


def _detect_framework(workspace_state: dict) -> str:
    tech = workspace_state.get("tech_stack", [])
    counts: dict[str, int] = {}
    ui_packages = {
        "react": "react", "next": "react",
        "@angular/core": "angular", "angular": "angular",
        "vue": "vue", "nuxt": "vue",
        "svelte": "svelte", "sveltekit": "svelte",
    }
    for t in tech:
        pkg = t.get("package", "").lower()
        for key, fw in ui_packages.items():
            if pkg == key or pkg.endswith(f"/{key}"):
                counts[fw] = counts.get(fw, 0) + 1
    if counts:
        return max(counts, key=counts.get)
    return "unknown"


def classify(workspace_output: Path, user_request: str = "") -> dict:
    data = _load_yaml(workspace_output)
    ws = data.get("workspace_state", {})

    ui = _detect_ui(ws)
    api = _detect_api(ws, user_request)
    has_legacy = _detect_legacy(ws, user_request)
    framework = _detect_framework(ws) if ui else "none"

    # design_system_path
    design_system_path = ""
    if ui:
        ds = REPO_ROOT_DEFAULT / "design-system"
        if ds.exists():
            design_system_path = "design-system/"
        else:
            design_system_path = ""  # bootstrap will create it

    profile = {
        "ui": ui,
        "api": api,
        "has_legacy": has_legacy,
        "framework": framework,
        "design_system_path": design_system_path,
        "has_figma_data": ws.get("has_figma_data", False),
        "has_stitch_data": ws.get("has_stitch_data", False),
    }
    return profile


# ── bootstrap ────────────────────────────────────────────────────────────────


def bootstrap(repo_root: Path, force: bool = False, dry_run: bool = False) -> dict:
    ds = repo_root / "design-system"
    if ds.exists() and not force:
        return {"action": "skip", "reason": "design-system/ already exists"}

    bootstrap_script = _SCRIPT_DIR / "factory_ds_bootstrap.py"
    if not bootstrap_script.exists():
        return {"action": "error", "reason": f"{bootstrap_script} not found"}

    cmd = [sys.executable, str(bootstrap_script), "init"]
    if force:
        cmd.append("--force")
    if dry_run:
        cmd.append("--dry-run")
    cmd.extend(["--repo-root", str(repo_root)])

    result = _run(cmd, cwd=repo_root)
    return {
        "action": "bootstrap",
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


# ── snap figma ───────────────────────────────────────────────────────────────


def snap_figma(repo_root: Path, dry_run: bool = False) -> dict:
    ws_out = repo_root / ".aidlc-orchestrator" / "runs"
    # We expect the caller to tell us explicitly; this is a thin wrapper.
    # The orchestrator should place figma raw data at figma/raw-data.json
    raw = repo_root / "figma" / "raw-data.json"
    snapped = repo_root / "figma" / "snapped.json"

    if not raw.exists():
        return {"action": "skip", "reason": f"{raw} not found"}

    snap_script = _SCRIPT_DIR / "factory_design_system_snap.py"
    if not snap_script.exists():
        return {"action": "error", "reason": f"{snap_script} not found"}

    cmd = [
        sys.executable, str(snap_script), "snap-file",
        "--input", str(raw),
        "--output", str(snapped),
        "--repo-root", str(repo_root),
    ]
    result = _run(cmd, cwd=repo_root)
    if result.returncode != 0:
        return {"action": "error", "returncode": result.returncode, "stderr": result.stderr}

    # Import snapped tokens into design system
    bootstrap_script = _SCRIPT_DIR / "factory_ds_bootstrap.py"
    import_cmd = [
        sys.executable, str(bootstrap_script), "import",
        "--source", str(snapped), "--format", "json", "--force",
        "--repo-root", str(repo_root),
    ]
    if dry_run:
        import_cmd.append("--dry-run")
    import_result = _run(import_cmd, cwd=repo_root)

    return {
        "action": "snap-and-import",
        "snap_returncode": result.returncode,
        "import_returncode": import_result.returncode,
        "snapped_path": str(snapped.relative_to(repo_root)),
    }


# ── snap stitch ──────────────────────────────────────────────────────────────


def snap_stitch(repo_root: Path, dry_run: bool = False) -> dict:
    raw_html = repo_root / "stitch" / "export.html"
    raw_design = repo_root / "stitch" / "DESIGN.md"
    snapped = repo_root / "stitch" / "snapped.json"

    snap_script = _SCRIPT_DIR / "factory_stitch_snap.py"
    if not snap_script.exists():
        return {"action": "error", "reason": f"{snap_script} not found"}

    # Prefer DESIGN.md if available; else try HTML
    source = raw_design if raw_design.exists() else (raw_html if raw_html.exists() else None)
    if source is None:
        return {"action": "skip", "reason": "no stitch export.html or DESIGN.md found"}

    if source.suffix == ".md":
        cmd = [
            sys.executable, str(snap_script), "snap-design",
            "--input", str(source),
            "--repo-root", str(repo_root),
        ]
    else:
        cmd = [
            sys.executable, str(snap_script), "snap-file",
            "--input", str(source),
            "--output", str(snapped),
            "--repo-root", str(repo_root),
        ]

    if dry_run:
        cmd.append("--dry-run")

    result = _run(cmd, cwd=repo_root)
    if result.returncode != 0:
        return {"action": "error", "returncode": result.returncode, "stderr": result.stderr}

    # Import
    bootstrap_script = _SCRIPT_DIR / "factory_ds_bootstrap.py"
    import_cmd = [
        sys.executable, str(bootstrap_script), "import",
        "--source", str(source), "--format", "stitch", "--force",
        "--repo-root", str(repo_root),
    ]
    if dry_run:
        import_cmd.append("--dry-run")
    import_result = _run(import_cmd, cwd=repo_root)

    return {
        "action": "snap-and-import",
        "snap_returncode": result.returncode,
        "import_returncode": import_result.returncode,
        "snapped_path": str(snapped.relative_to(repo_root)) if snapped.exists() else None,
    }


# ── reverse-engineer-ui ──────────────────────────────────────────────────────


def _extract_hex_from_css(content: str) -> list[str]:
    return re.findall(r"#(?:[0-9a-fA-F]{3,8})", content)


def _extract_numbers_near(content: str, keywords: list[str]) -> list[float]:
    vals: list[float] = []
    for kw in keywords:
        for m in re.finditer(rf"{re.escape(kw)}\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", content, re.I):
            vals.append(float(m.group(1)))
    return vals


def _scan_for_tokens(repo_root: Path) -> dict[str, Any]:
    """Lightweight scan of CSS/SCSS/less/styled-components/Tailwind for token extraction."""
    tokens: dict[str, Any] = {"spacing": {}, "radius": {}, "typography": {}, "color": {}}

    css_files: list[Path] = []
    for ext in ("*.css", "*.scss", "*.less", "*.styled.js", "*.styled.ts"):
        css_files.extend(_find_files(repo_root, [ext], max_depth=5))

    # Also search inside .tsx/.jsx for styled-components / inline styles
    for ext in ("*.tsx", "*.jsx", "*.js", "*.ts"):
        for p in _find_files(repo_root, [ext], max_depth=5):
            text = p.read_text(encoding="utf-8", errors="ignore")
            if "styled" in text.lower() or "css`" in text or "createGlobalStyle" in text:
                css_files.append(p)

    all_text = ""
    for p in css_files:
        try:
            all_text += p.read_text(encoding="utf-8", errors="ignore") + "\n"
        except Exception:
            continue

    if not all_text:
        return tokens

    # Colors
    hex_vals = _extract_hex_from_css(all_text)
    # Deduplicate and keep top N
    from collections import Counter
    top_colors = Counter(hex_vals).most_common(20)
    # Map to simple names (naive)
    color_map: dict[str, str] = {}
    for hex_val, _ in top_colors:
        # Normalize
        h = hex_val.lower()
        if len(h) == 4:
            h = "#" + "".join(c * 2 for c in h[1:])
        if h not in color_map:
            if len(color_map) < 3:
                color_map[h] = "color.brand.primary"
            elif len(color_map) < 6:
                color_map[h] = "color.neutral.text-primary"
            elif len(color_map) < 9:
                color_map[h] = "color.semantic.danger"
            else:
                break
    tokens["color"] = color_map

    # Spacing (padding, margin, gap)
    spacing_vals = _extract_numbers_near(all_text, ["padding", "margin", "gap"])
    spacing_set = sorted(set(int(v) for v in spacing_vals if 0 < v <= 64))
    tokens["spacing"] = {f"v{i}": v for i, v in enumerate(spacing_set[:6])}

    # Radius (border-radius)
    radius_vals = _extract_numbers_near(all_text, ["border-radius", "borderRadius"])
    radius_set = sorted(set(int(v) for v in radius_vals if 0 <= v <= 50))
    tokens["radius"] = {f"v{i}": v for i, v in enumerate(radius_set[:5])}

    # Typography (font-size)
    font_vals = _extract_numbers_near(all_text, ["font-size", "fontSize"])
    font_set = sorted(set(int(v) for v in font_vals if 8 <= v <= 72))
    tokens["typography"] = {f"v{i}": {"size": v} for i, v in enumerate(font_set[:7])}

    return tokens


def reverse_engineer_ui(repo_root: Path, output_json: Path | None = None, dry_run: bool = False) -> dict:
    tokens = _scan_for_tokens(repo_root)

    # Only proceed if we found anything meaningful
    total = sum(len(v) for v in tokens.values() if isinstance(v, dict))
    if total < 3:
        return {"action": "skip", "reason": "insufficient token data extracted from codebase"}

    if dry_run:
        return {"action": "dry-run", "tokens": tokens}

    # Write a temp JSON and import it
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
        tmp_path = Path(f.name)

    bootstrap_script = _SCRIPT_DIR / "factory_ds_bootstrap.py"
    cmd = [
        sys.executable, str(bootstrap_script), "import",
        "--source", str(tmp_path), "--format", "json", "--force",
        "--repo-root", str(repo_root),
    ]
    result = _run(cmd, cwd=repo_root)
    tmp_path.unlink(missing_ok=True)

    return {
        "action": "reverse-engineer",
        "returncode": result.returncode,
        "tokens": tokens,
    }


# ── set-manifest ─────────────────────────────────────────────────────────────


def set_manifest(run_id: str, profile: dict) -> dict:
    run_py = _SCRIPT_DIR / "factory_run.py"
    fields = [
        f"project_profile.ui={json.dumps(profile['ui'])}",
        f"project_profile.api={json.dumps(profile['api'])}",
        f"project_profile.has_legacy={json.dumps(profile['has_legacy'])}",
        f"project_profile.framework={profile['framework']}",
        f"project_profile.design_system_path={profile['design_system_path']}",
        f"project_profile.has_figma_data={json.dumps(profile.get('has_figma_data', False))}",
        f"project_profile.has_stitch_data={json.dumps(profile.get('has_stitch_data', False))}",
    ]
    cmd = [sys.executable, str(run_py), "set", run_id]
    for f in fields:
        cmd.extend(["--field", f])
    result = _run(cmd)
    return {
        "action": "set-manifest",
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


# ── run (full pipeline) ──────────────────────────────────────────────────────


def run_pipeline(run_id: str, workspace_output: Path, repo_root: Path,
                 force: bool = False, dry_run: bool = False) -> dict:
    logs: list[str] = []

    # 1. classify
    profile = classify(workspace_output)
    logs.append(f"[Profile] ui={profile['ui']}, api={profile['api']}, has_legacy={profile['has_legacy']}, framework={profile['framework']}")

    # 2. bootstrap if needed
    if profile["ui"]:
        ds = repo_root / "design-system"
        if not ds.exists() or force:
            logs.append("[Bootstrap] design-system/ missing — running init")
            r = bootstrap(repo_root, force=force, dry_run=dry_run)
            logs.append(f"[Bootstrap] {r['action']}")
            if r["action"] == "bootstrap" and r.get("returncode", -1) == 0:
                profile["design_system_path"] = "design-system/"
        else:
            profile["design_system_path"] = "design-system/"
            logs.append("[Bootstrap] design-system/ already exists")
    else:
        logs.append("[Bootstrap] ui=false — skipping")

    # 3. snap figma
    if profile.get("has_figma_data"):
        logs.append("[Figma] has_figma_data=true — snapping")
        r = snap_figma(repo_root, dry_run=dry_run)
        logs.append(f"[Figma] {r['action']}")
        if r.get("snapped_path"):
            profile["figma_snapped_path"] = r["snapped_path"]
    else:
        logs.append("[Figma] no figma data")

    # 4. snap stitch
    if profile.get("has_stitch_data"):
        logs.append("[Stitch] has_stitch_data=true — snapping")
        r = snap_stitch(repo_root, dry_run=dry_run)
        logs.append(f"[Stitch] {r['action']}")
        if r.get("snapped_path"):
            profile["stitch_snapped_path"] = r["snapped_path"]
    else:
        logs.append("[Stitch] no stitch data")

    # 5. reverse-engineer UI (brownfield fallback)
    ws = _load_yaml(workspace_output).get("workspace_state", {})
    if (profile["ui"] and
        not profile.get("has_figma_data") and
        not profile.get("has_stitch_data") and
        ws.get("project_type") == "brownfield"):
        logs.append("[ReverseEngineer] brownfield UI without figma/stitch — scanning existing CSS")
        r = reverse_engineer_ui(repo_root, dry_run=dry_run)
        logs.append(f"[ReverseEngineer] {r['action']}")
    else:
        logs.append("[ReverseEngineer] conditions not met — skipping")

    # 6. persist
    logs.append("[Manifest] persisting project_profile")
    r = set_manifest(run_id, profile)
    logs.append(f"[Manifest] {r['action']} rc={r['returncode']}")

    return {
        "profile": profile,
        "logs": logs,
    }


# ── CLI ────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Project profile & design system bootstrap")
    parser.add_argument("--repo-root", type=str, default=str(REPO_ROOT_DEFAULT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # classify
    classify_parser = subparsers.add_parser("classify", help="Classify project profile")
    classify_parser.add_argument("--workspace-output", type=str, required=True,
                                  help="Path to workspace-scout.output.yaml")

    # bootstrap
    subparsers.add_parser("bootstrap", help="Bootstrap design-system/")

    # snap-figma
    subparsers.add_parser("snap-figma", help="Snap Figma data to tokens")

    # snap-stitch
    subparsers.add_parser("snap-stitch", help="Snap Stitch data to tokens")

    # reverse-engineer-ui
    re_parser = subparsers.add_parser("reverse-engineer-ui", help="Extract tokens from existing CSS")
    re_parser.add_argument("--output", type=str, default=None, help="Output JSON path")

    # set-manifest
    set_parser = subparsers.add_parser("set-manifest", help="Persist profile to manifest")
    set_parser.add_argument("run_id")
    set_parser.add_argument("--profile-json", type=str, required=True)

    # run
    run_parser = subparsers.add_parser("run", help="Full pipeline")
    run_parser.add_argument("run_id")
    run_parser.add_argument("--workspace-output", type=str, required=True)

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.command == "classify":
        profile = classify(Path(args.workspace_output))
        print(json.dumps(profile, indent=2))

    elif args.command == "bootstrap":
        result = bootstrap(repo_root, force=args.force, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))

    elif args.command == "snap-figma":
        result = snap_figma(repo_root, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))

    elif args.command == "snap-stitch":
        result = snap_stitch(repo_root, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))

    elif args.command == "reverse-engineer-ui":
        out = Path(args.output) if args.output else None
        result = reverse_engineer_ui(repo_root, output_json=out, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))

    elif args.command == "set-manifest":
        profile = json.loads(args.profile_json)
        result = set_manifest(args.run_id, profile)
        print(json.dumps(result, indent=2))

    elif args.command == "run":
        result = run_pipeline(
            args.run_id, Path(args.workspace_output), repo_root,
            force=args.force, dry_run=args.dry_run,
        )
        for line in result["logs"]:
            print(line)
        print("---")
        print(json.dumps(result["profile"], indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
