#!/usr/bin/env python3
"""factory_stitch_mcp.py — Google Stitch MCP Registry & Health Check.

Manages the Stitch MCP server configuration and integration for the AIDLC
orchestrator. The Stitch MCP server (@_davideast/stitch-mcp) provides 36 tools
across 9 categories: design generation, code extraction, project management,
workspace persistence, dark mode, responsive variants, and more.

Subcommands:
  doctor        Check if Stitch MCP server is reachable and healthy
  config        Print MCP config JSON fragment for .mcp.json merge
  proxy-config  Print the npx proxy command for the Stitch MCP server

Usage:
    python3 aidlc-scripts/factory_stitch_mcp.py doctor
    python3 aidlc-scripts/factory_stitch_mcp.py config
    python3 aidlc-scripts/factory_stitch_mcp.py proxy-config
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

# The canonical Stitch MCP npm package
STITCH_MCP_PACKAGE = "@_davideast/stitch-mcp"
NODE_MIN_MAJOR = 18

# The Stitch MCP server proxy command (runs via npx)
STITCH_MCP_PROXY_CMD = ["npx", "-y", STITCH_MCP_PACKAGE, "proxy"]
STITCH_MCP_INIT_CMD = ["npx", "-y", STITCH_MCP_PACKAGE, "init"]
STITCH_MCP_DOCTOR_CMD = ["npx", "-y", STITCH_MCP_PACKAGE, "doctor", "--verbose"]

# MCP config fragment for .mcp.json merge
STITCH_MCP_CONFIG_ENTRY = {
    "stitch": {
        "command": "npx",
        "args": ["-y", STITCH_MCP_PACKAGE, "proxy"],
    },
}

STITCH_MCP_OPENCODE_ENTRY = {
    "type": "local",
    "command": ["npx", "-y", STITCH_MCP_PACKAGE, "proxy"],
    "enabled": True,
}

# Stitch MCP tools available via the proxy
STITCH_MCP_TOOLS = [
    # Design extraction
    "get_screen_code",
    "get_screen_image",
    "get_screen_html",
    "build_site",
    # Project management
    "list_projects",
    "list_screens",
    "get_project",
    "create_project",
    # Design intelligence
    "extract_design_context",
    "validate_against_design_system",
    "generate_dark_mode",
    "generate_responsive_variants",
    "generate_component_variants",
    # Workspace
    "stitch_init",
    "stitch_status",
]


def _check_node(min_major: int = NODE_MIN_MAJOR) -> tuple[bool, str]:
    """Check Node.js version. Returns (ok, version_string)."""
    try:
        result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=10
        )
        version_str = result.stdout.strip()
        major = int(version_str.lstrip("v").split(".")[0])
        return major >= min_major, version_str
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        return False, "not found"


def _check_npx() -> bool:
    """Check if npx is available on PATH."""
    return shutil.which("npx") is not None


def doctor() -> dict:
    """Check Stitch MCP health.

    Returns a dict with:
      - node: { ok, version }
      - npx: { ok }
      - stitch_mcp_package: { ok }
      - overall: "ok" | "degraded" | "unavailable"
    """
    result: dict = {
        "node": {"ok": False, "version": "unknown"},
        "npx": {"ok": False},
        "stitch_mcp_package": {"ok": False, "message": ""},
        "overall": "unavailable",
    }

    # Node check
    ok, version = _check_node()
    result["node"] = {"ok": ok, "version": version}
    if not ok:
        result["stitch_mcp_package"]["message"] = (
            f"Node >= {NODE_MIN_MAJOR} required, found {version}"
        )
        result["overall"] = "unavailable"
        return result

    # npx check
    result["npx"]["ok"] = _check_npx()
    if not result["npx"]["ok"]:
        result["stitch_mcp_package"]["message"] = "npx not found on PATH"
        result["overall"] = "unavailable"
        return result

    # Try the Stitch MCP doctor
    try:
        proc = subprocess.run(
            STITCH_MCP_DOCTOR_CMD,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0:
            result["stitch_mcp_package"] = {
                "ok": True,
                "message": proc.stdout.strip() or "Healthy",
            }
            result["overall"] = "ok"
        else:
            result["stitch_mcp_package"] = {
                "ok": False,
                "message": proc.stderr.strip() or f"Exit code {proc.returncode}",
            }
            result["overall"] = "degraded"
    except FileNotFoundError:
        result["stitch_mcp_package"]["message"] = (
            f"Package {STITCH_MCP_PACKAGE} not available via npx. "
            f"Run: npx {STITCH_MCP_PACKAGE} init"
        )
        result["overall"] = "degraded"
    except subprocess.TimeoutExpired:
        result["stitch_mcp_package"]["message"] = "Stitch MCP doctor timed out (30s)"
        result["overall"] = "degraded"

    return result


def proxy_config() -> dict:
    """Return the Stitch MCP proxy command and environment."""
    return {
        "package": STITCH_MCP_PACKAGE,
        "command": "npx",
        "args": ["-y", STITCH_MCP_PACKAGE, "proxy"],
        "env": {
            "GOOGLE_CLOUD_PROJECT": "${GOOGLE_CLOUD_PROJECT}",
        },
        "description": (
            "Google Stitch MCP proxy. Requires: Node 18+, gcloud auth, "
            "and GOOGLE_CLOUD_PROJECT env var set to your GCP project ID. "
            "Run 'npx @_davideast/stitch-mcp init' to set up."
        ),
    }


def config(format: str = "json") -> str:
    """Print MCP config for the given format.

    Supported formats:
      - json       Generic .mcp.json fragment
      - opencode   OpenCode opencode.json format
      - cursor     Cursor .cursor/mcp.json format
      - vscode     VS Code .vscode/mcp.json format
    """
    if format == "opencode":
        return json.dumps(STITCH_MCP_OPENCODE_ENTRY, indent=2)
    elif format == "cursor":
        # Cursor uses the same format as generic JSON but without 'type' field
        entry = {
            "command": "npx",
            "args": ["-y", STITCH_MCP_PACKAGE, "proxy"],
        }
        return json.dumps(entry, indent=2)
    elif format == "vscode":
        # VSCode uses { servers: { ... } } with 'type' field
        entry = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", STITCH_MCP_PACKAGE, "proxy"],
        }
        return json.dumps(entry, indent=2)
    else:
        return json.dumps(STITCH_MCP_CONFIG_ENTRY, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Google Stitch MCP registry & health check.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="Check Stitch MCP health")
    doctor_parser.add_argument("--json", action="store_true",
                               help="Output as JSON")

    # proxy-config
    subparsers.add_parser("proxy-config", help="Print proxy command details")

    # config
    config_parser = subparsers.add_parser("config", help="Print MCP config fragment")
    config_parser.add_argument("--format", type=str, default="json",
                               choices=["json", "opencode", "cursor", "vscode"],
                               help="Config format (default: json)")

    args = parser.parse_args()

    if args.command == "doctor":
        result = doctor()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status = result["overall"]
            icon = {"ok": "[OK]", "degraded": "[WARN]", "unavailable": "[FAIL]"}.get(status, "?")
            print(f"Stitch MCP Health: {icon} {status}")
            print(f"  Node: {result['node']['version'] } "
                  f"({'[OK]' if result['node']['ok'] else '[FAIL]'})")
            print(f"  npx:  {'[OK]' if result['npx']['ok'] else '[FAIL]'}")
            msg = result["stitch_mcp_package"]["message"]
            if msg:
                print(f"  Stitch: {msg}")

    elif args.command == "proxy-config":
        result = proxy_config()
        print(json.dumps(result, indent=2))

    elif args.command == "config":
        print(config(format=args.format))

    return 0


if __name__ == "__main__":
    sys.exit(main())
