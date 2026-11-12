#!/usr/bin/env python3
"""factory_skill_sync.py — Sync skills via npx @aidlc-factory/autoskills.

Subcommands:

  sync          Install framework skills for given techs.
  select        List installed skills for stage handoffs (skill_paths_resolved[]).
  list-tech     List all technology IDs supported by autoskills.
  resolve-tech  Intersect project tech_stack with supported autoskills techs.

Usage:
    python3 aidlc-scripts/factory_skill_sync.py sync [--repo-root PATH] [--dry-run] [--tech react,nextjs]
    python3 aidlc-scripts/factory_skill_sync.py select [--repo-root PATH] [--output json|text]
    python3 aidlc-scripts/factory_skill_sync.py list-tech [--repo-root PATH]
    python3 aidlc-scripts/factory_skill_sync.py resolve-tech [manifest-path]

Exit codes:
    0  success (or graceful degradation — npx missing, network error)
    1  hard error (file-system write failure, or resolve-tech failed)
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
REPO_ROOT_DEFAULT = _SCRIPT_DIR.parent

sys.path.insert(0, str(_SCRIPT_DIR))
from skill_utils import discover_skills, sha256_file


PACKAGE_NAME = "@aidlc-factory/autoskills"
NODE_MIN = (22, 6, 0)


def _parse_node_version(version_str: str) -> tuple[int, int, int] | None:
    raw = version_str.strip().lstrip("v")
    if not raw:
        return None
    parts = raw.split(".")
    try:
        nums = [int(p) for p in parts[:3]]
    except ValueError:
        return None
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


def _resolve_npx() -> tuple[list[str], str, str | None] | None:
    """Check npx is available and Node >= 22.6.0. Returns (cmd, label, nvm_bin_path) or None."""
    # 1. Try plain node first
    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            parsed = _parse_node_version(r.stdout.strip())
            if parsed is not None and parsed >= NODE_MIN:
                return (["node"], f"system node ({r.stdout.strip()})", None)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # 2. Try nvm (user-level, no sudo needed)
    nvm_sh = Path.home() / ".nvm" / "nvm.sh"
    if nvm_sh.exists():
        try:
            r = subprocess.run(
                ["bash", "-c", f"source {nvm_sh} && nvm ls 22 --no-colors 2>/dev/null"],
                capture_output=True, text=True, timeout=15
            )
            if r.returncode == 0 and r.stdout.strip():
                best_ver: tuple[int, int, int] | None = None
                for line in r.stdout.strip().splitlines():
                    tokens = line.strip().split()
                    ver_str = next((t for t in tokens if t.startswith("v")), "")
                    if not ver_str:
                        continue
                    parsed = _parse_node_version(ver_str)
                    if parsed is not None and parsed >= NODE_MIN:
                        if best_ver is None or parsed > best_ver:
                            best_ver = parsed
                if best_ver is not None:
                    nvm_prefix = Path.home() / ".nvm" / "versions" / "node" / f"v{best_ver[0]}.{best_ver[1]}.{best_ver[2]}"
                    npx_path = nvm_prefix / "bin" / "npx"
                    nvm_bin = str(nvm_prefix / "bin")
                    if npx_path.exists():
                        return ([str(npx_path)],
                                f"nvm (v{best_ver[0]}.{best_ver[1]}.{best_ver[2]})",
                                nvm_bin)
        except (subprocess.TimeoutExpired, OSError):
            pass

    # 3. Try fnm
    try:
        r = subprocess.run(["fnm", "exec", "--using=22", "--", "node", "--version"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            parsed = _parse_node_version(r.stdout.strip())
            if parsed is not None and parsed >= NODE_MIN:
                return (["fnm", "exec", "--using=22", "--", "npx"], f"fnm ({r.stdout.strip()})", None)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # 4. Try volta
    try:
        r = subprocess.run(["volta", "run", "--node", "22", "node", "--version"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            parsed = _parse_node_version(r.stdout.strip())
            if parsed is not None and parsed >= NODE_MIN:
                return (["volta", "run", "--node", "22", "npx"], f"volta ({r.stdout.strip()})", None)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    return None


def _run_npx(
    npx_cmd: list[str],
    args: list[str],
    project_dir: Path | None = None,
    timeout: int = 180,
    nvm_bin: str | None = None,
) -> subprocess.CompletedProcess | None:
    """Run npx with the PACKAGE_NAME. If npx_cmd ends in 'node', append
    'npx -y <package>'. Otherwise assume the last element is the npx binary."""
    if npx_cmd[-1] == "node":
        cmd = npx_cmd + ["npx", "-y", PACKAGE_NAME] + args
    else:
        cmd = npx_cmd + ["-y", PACKAGE_NAME] + args
    cwd = str(project_dir) if project_dir else None
    env = None
    if nvm_bin:
        env = dict(os.environ)
        env["PATH"] = f"{nvm_bin}:{env.get('PATH', '')}"
    try:
        kwargs = dict(cwd=cwd, capture_output=True, text=True, timeout=timeout)
        if env is not None:
            kwargs["env"] = env
        return subprocess.run(cmd, **kwargs)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def _collect_installed_skills(project_dir: Path) -> list[Path]:
    installed: list[Path] = []
    skills_dir = project_dir / ".agents" / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                installed.append(skill_dir)
    return installed


# ── list-tech subcommand ──────────────────────────────────────

def cmd_list_tech(repo_root: Path, dry_run: bool = False) -> int:
    resolved = _resolve_npx()
    if resolved is None:
        print(f"[list-tech] SKIP (no Node >= {NODE_MIN[0]}.{NODE_MIN[1]} available)")
        return 0

    npx_cmd, node_label, nvm_bin = resolved

    if dry_run:
        print(f"[DRY-RUN] Would run: npx {PACKAGE_NAME} --list-tech")
        return 0

    result = _run_npx(npx_cmd, ["--list-tech"], nvm_bin=nvm_bin)

    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"[list-tech] autoskills exited {result.returncode}")
        if result.stderr:
            for line in result.stderr.strip().splitlines()[:10]:
                print(f"  {line}", file=sys.stderr)

    return 0


# ── sync subcommand ───────────────────────────────────────────

def cmd_sync(repo_root: Path, dry_run: bool = False, techs: list[str] | None = None) -> int:
    resolved = _resolve_npx()
    if resolved is None:
        print(f"[Sync] SKIP (no Node >= {NODE_MIN[0]}.{NODE_MIN[1]} available)")
        return 0
    npx_cmd, node_label, nvm_bin = resolved
    print(f"[Sync] using {node_label}")

    if dry_run:
        tech_flag = f" --tech {','.join(techs)}" if techs else ""
        print(f"[DRY-RUN] Would run: npx {PACKAGE_NAME} -y --path {repo_root}{tech_flag}")
        installed = _collect_installed_skills(repo_root)
        print(f"[Sync] dry-run — currently {len(installed)} skill(s) in .agents/skills/")
        return 0

    args = ["-y", "--path", str(repo_root)]
    if techs:
        args.extend(["--tech", ",".join(techs)])

    result = _run_npx(npx_cmd, args, project_dir=repo_root, nvm_bin=nvm_bin)
    if result is None:
        print("[Sync] SKIP (npx runner failed)")
        return 0

    if result.returncode != 0:
        print(f"[Sync] autoskills exited {result.returncode}")
        for line in result.stderr.strip().splitlines()[:5]:
            print(f"    {line}", file=sys.stderr)

    for line in (result.stdout + result.stderr).splitlines():
        lower = line.lower()
        if any(kw in lower for kw in ("flagged", "warning", "no skill", "warning:")):
            print(f"    [WARN] {line.strip()}")

    installed = _collect_installed_skills(repo_root)
    if not installed:
        print("[Sync] autoskills installed no skills (no matching technologies detected)")

    print(f"[Sync] done — {len(installed)} skill(s) in .agents/skills/")
    return 0


# ── resolve-tech subcommand ───────────────────────────────────

def cmd_resolve_tech(repo_root: Path, manifest_path: str | None = None) -> int:
    """List supported techs from autoskills, intersect with project tech_stack,
    output comma-separated matching tech IDs."""
    # Step 1: get supported techs from autoskills
    resolved = _resolve_npx()
    if resolved is None:
        print("[resolve-tech] SKIP (no Node >= 22.6.0)")
        return 1

    npx_cmd, node_label, nvm_bin = resolved
    result = _run_npx(npx_cmd, ["--list-tech"], nvm_bin=nvm_bin)
    if result is None or result.returncode != 0:
        print("[resolve-tech] failed to query autoskills --list-tech")
        return 1

    supported = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and not line.startswith(("┌", "├", "└", "│", " ", "▸", "◆", "")):
            supported.add(line.lower())
        elif "─" not in line and line and not line.startswith(("Auto", "npx")):
            # Parse "  react  6" format
            parts = line.split()
            if parts and not parts[0].startswith(("(", ")", "-", "•")):
                supported.add(parts[0].lower())

    # Step 2: read project tech_stack from manifest
    if not manifest_path:
        manifest_path = str(repo_root / ".aidlc-orchestrator" / "runs" / "latest" / "manifest.yaml")
        # Try to find most recent run
        runs_dir = repo_root / ".aidlc-orchestrator" / "runs"
        if runs_dir.exists():
            runs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], reverse=True)
            if runs:
                manifest_path = str(runs[0] / "manifest.yaml")

    try:
        import yaml
        with open(manifest_path) as f:
            m = yaml.safe_load(f)
    except Exception:
        print("[resolve-tech] no matching techs — universal skills only")
        return 0

    project_pkgs = {
        t.get("package", "").lower()
        for t in (m.get("workspace_state", {}).get("tech_stack", []) or [])
        if t.get("package")
    }

    # Common package-name → tech-ID mappings
    ALIASES = {
        "@angular/core": "angular",
        "@react-three/fiber": "@react-three/fiber",
        "typescript": None,  # universal, skip
        "eslint": None,
        "prettier": None,
    }

    matched = []
    for pkg in sorted(project_pkgs):
        mapped = ALIASES.get(pkg, pkg)
        if mapped is None:
            continue
        if mapped in supported:
            matched.append(mapped)

    if matched:
        print(",".join(matched))
    else:
        print("[resolve-tech] no matching techs — universal skills only")
    return 0


# ── select subcommand ─────────────────────────────────────────

def cmd_select(repo_root: Path, output_format: str = "json") -> int:
    skills = discover_skills(repo_root)

    custom_paths: list[str] = []
    framework_paths: list[str] = []

    for skill in skills:
        try:
            path_str = str(skill.path.relative_to(repo_root))
        except ValueError:
            path_str = str(skill.path)

        tier = skill.path.parent.parent.name
        if tier == "custom-skills":
            custom_paths.append(path_str)
        else:
            framework_paths.append(path_str)

    skill_paths_resolved = custom_paths + framework_paths

    framework_skill_names = sorted(set(
        Path(p).parent.name for p in framework_paths
        if p.startswith(".agents/skills/")
    ))

    warnings: list[str] = []
    resolved = _resolve_npx()
    if resolved is None:
        warnings.append(
            f"autoskills was SKIPPED: no Node >= {NODE_MIN[0]}.{NODE_MIN[1]} available"
        )
    elif not framework_paths:
        warnings.append(
            "no framework skills resolved — autoskills detected no matching technologies"
        )

    result = {
        "skill_paths_resolved": skill_paths_resolved,
        "framework_skill_names": framework_skill_names,
        "skill_count": len(skill_paths_resolved),
        "warnings": warnings,
    }

    if output_format == "json":
        print(json.dumps(result, indent=2))
    else:
        for path in skill_paths_resolved:
            print(path)

    return 0


# ── CLI ───────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="Repository root (default: parent of aidlc-scripts/)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_sync = sub.add_parser("sync", help="Install skills via autoskills")
    p_sync.add_argument("--dry-run", action="store_true",
                        help="Preview actions without installing")
    p_sync.add_argument("--tech", type=str, default=None,
                        help="Force specific technologies (comma-separated), e.g. react,nextjs,python")

    p_select = sub.add_parser("select", help="Output skill_paths_resolved[] for stage handoffs")
    p_select.add_argument("--output", choices=["json", "text"], default="json",
                          help="Output format (default: json)")

    p_list = sub.add_parser("list-tech", help="List all supported technology IDs from autoskills")
    p_list.add_argument("--dry-run", action="store_true",
                        help="Preview without calling npx")

    p_resolve = sub.add_parser("resolve-tech",
                                help="Intersect project tech_stack with autoskills supported techs")
    p_resolve.add_argument("manifest", type=str, nargs="?",
                           help="Path to manifest.yaml (auto-detects latest run)")

    args = parser.parse_args()
    repo_root = args.repo_root or REPO_ROOT_DEFAULT

    if args.command == "sync":
        techs = None
        if args.tech:
            techs = [t.strip() for t in args.tech.split(",") if t.strip()]
        sys.exit(cmd_sync(repo_root, dry_run=getattr(args, "dry_run", False), techs=techs))
    elif args.command == "select":
        sys.exit(cmd_select(repo_root, output_format=getattr(args, "output", "json")))
    elif args.command == "list-tech":
        sys.exit(cmd_list_tech(repo_root, dry_run=getattr(args, "dry_run", False)))
    elif args.command == "resolve-tech":
        sys.exit(cmd_resolve_tech(repo_root, manifest_path=args.manifest))
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
