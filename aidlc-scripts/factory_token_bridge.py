#!/usr/bin/env python3
"""factory_token_bridge.py — Orchestrate the Token Bridge pipeline.

Single entry point that the code-generator calls to prepare tokens for
any tech stack. Detects the project profile, generates CSS/Tailwind config,
and returns the tech-stack prompt to inject.

Usage:
    python3 aidlc-scripts/factory_token_bridge.py prepare \\
        --tech-stack react --framework react --output-dir .aidlc-orchestrator/runs/<run-id>/tokens

    python3 aidlc-scripts/factory_token_bridge.py list-prompts
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


_SCRIPT_DIR = Path(__file__).parent
REPO_ROOT_DEFAULT = _SCRIPT_DIR.parent
PROMPTS_DIR = _SCRIPT_DIR / "prompts" / "tech-stack"
TOKENS_DIR_REL = "design-system/tokens"


# ── Prepare tokens for a build ─────────────────────────────────────────────

def prepare(
    repo_root: Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Generate all token bridge artifacts.

    Auto-detects Tailwind and brownfield sources. No tech-stack param
    needed — the LLM already knows the tech stack from context.

    Returns metadata about what was generated.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "artifacts": [],
        "prompt_path": None,
    }

    # 1. Generate tokens.css (always)
    css_ok = _generate_css(repo_root, out)
    if css_ok:
        result["artifacts"].append({"type": "css", "path": str(out / "tokens.css")})

    # 2. Generate Tailwind config if detected
    if _tailwind_detected(repo_root):
        tw_ok = _generate_tailwind(repo_root, out)
        if tw_ok:
            result["artifacts"].append({"type": "tailwind", "path": str(out / "tailwind.config.js")})

    # 3. Copy generic prompt (always)
    prompt = _resolve_prompt()
    if prompt:
        dest = out / "token-prompt.md"
        shutil.copy2(prompt, dest)
        result["prompt_path"] = str(dest)
        result["artifacts"].append({"type": "prompt", "path": str(dest)})

    # 4. Detect project design system source (brownfield)
    ds_source = _detect_ds_source(repo_root)
    if ds_source:
        result["design_system_source"] = ds_source

    return result


def _tailwind_detected(repo_root: Path) -> bool:
    configs = ["tailwind.config.js", "tailwind.config.ts", "tailwind.config.mjs"]
    if any((repo_root / c).exists() for c in configs):
        return True
    pkg = repo_root / "package.json"
    if pkg.exists():
        try:
            import json
            deps = json.loads(pkg.read_text(encoding="utf-8"))
            all_deps = {**deps.get("dependencies", {}), **deps.get("devDependencies", {})}
            return any("tailwind" in k.lower() for k in all_deps)
        except Exception:
            pass
    # Tailwind v4: CSS-native config (@import "tailwindcss")
    css_dirs = [repo_root / "src", repo_root / "styles", repo_root / "app", repo_root]
    for css_dir in css_dirs:
        if css_dir.exists():
            for f in css_dir.glob("*.css"):
                content = f.read_text(encoding="utf-8", errors="ignore")
                if '@import "tailwindcss"' in content or "@import 'tailwindcss'" in content:
                    return True
    return False


def _generate_css(repo_root: Path, output_dir: Path) -> bool:
    try:
        from factory_token_to_css import generate_css
        css = generate_css(repo_root)
        if "No design-system/tokens/" in css:
            return False
        (output_dir / "tokens.css").write_text(css, encoding="utf-8")
        return True
    except Exception:
        return False


def _generate_tailwind(repo_root: Path, output_dir: Path) -> bool:
    try:
        from factory_token_to_tailwind import generate_tailwind_config
        config = generate_tailwind_config(repo_root)
        (output_dir / "tailwind.config.js").write_text(config, encoding="utf-8")
        return True
    except Exception:
        return False


def _resolve_prompt() -> Path | None:
    generic = PROMPTS_DIR / "tokens.md"
    return generic if generic.exists() else None


def _detect_ds_source(repo_root: Path) -> str | None:
    try:
        from factory_design_system_extract_brownfield import detect_sources
        sources = detect_sources(repo_root)
        if sources:
            return sources[0]["type"]
    except Exception:
        pass
    return None


# ── List available prompts ──────────────────────────────────────────────────

def list_prompts(repo_root: Path | None = None) -> list[dict]:
    prompts_dir = PROMPTS_DIR
    if not prompts_dir.exists():
        return []
    result: list[dict] = []
    for f in sorted(prompts_dir.glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        title = ""
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break
        result.append({
            "name": f.stem,
            "file": str(f),
            "title": title or f.stem,
            "size": len(lines),
        })
    return result


# ── Write a default design system (greenfield) ──────────────────────────────

GREENFIELD_TOKENS: dict[str, str] = {
    "spacing.md": """# Spacing Tokens
| Token | Pixels | Description |
|-------|--------|-------------|
| `spacing.xs` | 4 | Extra small |
| `spacing.sm` | 8 | Small |
| `spacing.md` | 12 | Medium |
| `spacing.lg` | 16 | Large |
| `spacing.xl` | 24 | Extra large |
| `spacing.xxl` | 32 | Double extra large |
""",
    "radius.md": """# Radius Tokens
| Token | Pixels | Description |
|-------|--------|-------------|
| `radius.none` | 0 | No rounding |
| `radius.sm` | 3 | Small |
| `radius.md` | 6 | Medium |
| `radius.lg` | 12 | Large |
| `radius.full` | 9999 | Fully rounded |
""",
    "typography.md": """# Typography Tokens
| Token | Pixels | Description |
|-------|--------|-------------|
| `font-size.caption` | 12 | Caption / metadata |
| `font-size.body` | 14 | Body text |
| `font-size.body-large` | 16 | Large body |
| `font-size.h4` | 20 | Heading 4 |
| `font-size.h3` | 24 | Heading 3 |
| `font-size.h2` | 32 | Heading 2 |
| `font-size.h1` | 40 | Heading 1 |
""",
    "color.md": """# Color Tokens
| Token | Hex | Description |
|-------|-----|-------------|
| `color.brand.primary` | #2563EB | Primary brand color |
| `color.brand.primary-hover` | #1D4ED8 | Primary hover state |
| `color.neutral.bg` | #FFFFFF | Page background |
| `color.neutral.surface` | #F9FAFB | Surface / card background |
| `color.neutral.border` | #E5E7EB | Border / divider |
| `color.neutral.text-primary` | #111827 | Primary text |
| `color.neutral.text-secondary` | #6B7280 | Secondary text |
| `color.semantic.danger` | #EF4444 | Error / destructive |
| `color.semantic.success` | #10B981 | Success |
| `color.semantic.warning` | #F59E0B | Warning |
""",
    "elevation.md": """# Elevation Tokens
| Token | Z-Index | Description |
|-------|---------|-------------|
| `elevation.sm` | 1 | Small shadow |
| `elevation.md` | 10 | Medium shadow |
| `elevation.lg` | 100 | Large shadow |
| `elevation.xl` | 1000 | Extra large shadow |
""",
}


def bootstrap_greenfield(repo_root: Path, force: bool = False) -> list[str]:
    """Create a default design system for greenfield projects."""
    ds_dir = repo_root / "design-system"
    tokens_dir = ds_dir / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    for filename, content in GREENFIELD_TOKENS.items():
        path = tokens_dir / filename
        if path.exists() and not force:
            continue
        path.write_text(content, encoding="utf-8")
        created.append(str(path))

    if created:
        from factory_token_to_css import generate_css
        css = generate_css(repo_root)
        css_path = tokens_dir / "tokens.css"
        css_path.write_text(css, encoding="utf-8")
        created.append(str(css_path))

    # Write INDEX.md if missing
    index_path = ds_dir / "INDEX.md"
    if not index_path.exists() or force:
        from factory_ds_bootstrap import INDEX_MD
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(INDEX_MD, encoding="utf-8")
        created.append(str(index_path))

    return created


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Token Bridge — prepare design tokens for code generation.",
    )
    parser.add_argument("--repo-root", type=str, default=str(REPO_ROOT_DEFAULT),
                        help="Repository root path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    prep_p = subparsers.add_parser("prepare", help="Prepare tokens for code generation")
    prep_p.add_argument("--output-dir", required=True,
                        help="Output directory for generated artifacts")

    subparsers.add_parser("list-prompts", help="List available prompts")

    subparsers.add_parser("bootstrap", help="Create default design system (greenfield)")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.command == "prepare":
        result = prepare(repo_root, args.output_dir)
        print(json.dumps(result, indent=2))

    elif args.command == "list-prompts":
        prompts = list_prompts()
        if not prompts:
            print("No prompts found.")
        else:
            print(f"Available prompts ({len(prompts)}):")
            for p in prompts:
                print(f"  {p['name']:12s} — {p['title']} ({p['size']} lines)")

    elif args.command == "bootstrap":
        created = bootstrap_greenfield(repo_root)
        if created:
            print(f"Created {len(created)} file(s):")
            for c in created:
                print(f"  {c}")
        else:
            print("All files already exist. Use --force to overwrite.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
