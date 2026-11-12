#!/usr/bin/env python3
"""factory_figma_mcp.py — Figma MCP Registry & Health Check.

Manages the Figma MCP server configuration for the AIDLC orchestrator.
Supports two modes:
  - Remote (HTTP/OAuth): official Figma MCP at https://mcp.figma.com/mcp
    OAuth-based, works with Claude Code, Cursor, OpenCode.
  - Community (stdio/PAT): figma-mcp package via npx with FIGMA_API_KEY.
    Works with all MCP clients where OAuth is unavailable.

Subcommands:
  doctor        Check if Figma MCP is reachable
  config        Print MCP config fragment for .mcp.json merge
  proxy-config  Print the remote endpoint or npx proxy details

Usage:
    python3 aidlc-scripts/factory_figma_mcp.py doctor
    python3 aidlc-scripts/factory_figma_mcp.py config
    python3 aidlc-scripts/factory_figma_mcp.py proxy-config
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

# The canonical Figma MCP server info
FIGMA_MCP_REMOTE_URL = "https://mcp.figma.com/mcp"
FIGMA_MCP_COMMUNITY_PACKAGE = "figma-mcp"

NODE_MIN_MAJOR = 18

# MCP config fragment for .mcp.json — HTTP (remote, OAuth mode)
FIGMA_MCP_REMOTE_CONFIG_ENTRY = {
    "figma": {
        "type": "http",
        "url": FIGMA_MCP_REMOTE_URL,
    },
}

# MCP config fragment for stdio (community, PAT mode)
FIGMA_MCP_COMMUNITY_CONFIG_ENTRY = {
    "figma": {
        "command": "npx",
        "args": ["-y", FIGMA_MCP_COMMUNITY_PACKAGE],
    },
}

FIGMA_MCP_OPENCODE_REMOTE_ENTRY = {
    "type": "http",
    "url": FIGMA_MCP_REMOTE_URL,
    "enabled": True,
}

FIGMA_MCP_OPENCODE_COMMUNITY_ENTRY = {
    "type": "local",
    "command": ["npx", "-y", FIGMA_MCP_COMMUNITY_PACKAGE],
    "environment": {
        "FIGMA_API_KEY": "${FIGMA_API_KEY}",
    },
    "enabled": True,
}

# Figma MCP tools (remote server exposes 16+ tools)
FIGMA_MCP_TOOLS = [
    "get_design_context",
    "get_screenshot",
    "get_node_info",
    "get_style_info",
    "get_component_info",
    "get_image_fills",
    "get_exportables",
    "use_figma",
    "generate_figma_design",
    "whoami",
    "get_file_components",
    "get_file_styles",
    "get_file_variables",
    "read_comments",
    "post_comment",
    "reply_to_comment",
]


def _check_node(min_major: int = NODE_MIN_MAJOR) -> tuple[bool, str]:
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
    return shutil.which("npx") is not None


def doctor(mode: str = "auto") -> dict:
    """Check Figma MCP health.

    Args:
      mode: "remote" — probe the HTTP endpoint via curl
            "community" — probe the npx package via node
            "auto" — try remote first, fall back to community

    Returns a dict with:
      - mode: "remote" | "community" | "none"
      - node: { ok, version }
      - npx: { ok } (community mode only)
      - endpoint: { ok, message } (remote mode only)
      - package: { ok, message } (community mode only)
      - overall: "ok" | "degraded" | "unavailable"
    """
    result: dict = {
        "mode": mode,
        "node": {"ok": False, "version": "unknown"},
        "npx": {"ok": False},
        "endpoint": {"ok": False, "message": ""},
        "package": {"ok": False, "message": ""},
        "overall": "unavailable",
    }

    ok, version = _check_node()
    result["node"] = {"ok": ok, "version": version}
    if not ok:
        result["package"]["message"] = (
            f"Node >= {NODE_MIN_MAJOR} required, found {version}"
        )
        result["overall"] = "unavailable"
        return result

    result["npx"]["ok"] = _check_npx()

    if mode == "remote":
        return _probe_remote(result)
    elif mode == "community":
        return _probe_community(result)
    else:
        result = _probe_remote(result)
        if result["overall"] == "unavailable" and result["npx"]["ok"]:
            result = _probe_community(dict(result))  # fresh dict to avoid partial merge
            result["mode"] = "auto"
        return result


def _probe_remote(result: dict) -> dict:
    """Probe the Figma Remote MCP endpoint via curl."""
    curl = shutil.which("curl")
    if not curl:
        result["endpoint"] = {"ok": False, "message": "curl not found on PATH"}
        result["overall"] = "degraded"
        return result

    try:
        proc = subprocess.run(
            [curl, "-s", "-o", os.devnull, "-w", "%{http_code}",
             "--max-time", "10", FIGMA_MCP_REMOTE_URL],
            capture_output=True, text=True, timeout=15,
        )
        http_code = proc.stdout.strip()
        if http_code and http_code[0] in ("2", "3"):
            result["endpoint"] = {
                "ok": True,
                "message": f"HTTP {http_code} — endpoint reachable",
            }
            result["overall"] = "ok"
        else:
            result["endpoint"] = {
                "ok": False,
                "message": f"HTTP {http_code or 'unknown'} — endpoint unreachable",
            }
            result["overall"] = "degraded"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        result["endpoint"] = {"ok": False, "message": str(e)}
        result["overall"] = "degraded"

    return result


def _probe_community(result: dict) -> dict:
    """Probe the community figma-mcp package."""
    try:
        proc = subprocess.run(
            ["npx", "-y", FIGMA_MCP_COMMUNITY_PACKAGE, "--version"],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0:
            version = proc.stdout.strip() or "ok"
            result["package"] = {
                "ok": True,
                "message": f"Package available ({version})",
            }
            result["overall"] = "ok"
        else:
            result["package"] = {
                "ok": False,
                "message": proc.stderr.strip() or f"Exit code {proc.returncode}",
            }
            result["overall"] = "degraded"
    except FileNotFoundError:
        result["package"]["message"] = (
            f"Package {FIGMA_MCP_COMMUNITY_PACKAGE} not available via npx"
        )
        result["overall"] = "degraded"
    except subprocess.TimeoutExpired:
        result["package"]["message"] = "Package probe timed out (30s)"
        result["overall"] = "degraded"

    return result


def proxy_config() -> dict:
    """Return Figma MCP endpoint details for both modes."""
    return {
        "remote": {
            "url": FIGMA_MCP_REMOTE_URL,
            "auth": "OAuth (via browser)",
            "description": (
                "Official Figma MCP Remote Server. "
                "Requires: Figma account, OAuth login on first use. "
                "Run 'claude mcp add --transport http figma https://mcp.figma.com/mcp' "
                "to trigger OAuth flow."
            ),
        },
        "community": {
            "package": FIGMA_MCP_COMMUNITY_PACKAGE,
            "command": "npx",
            "args": ["-y", FIGMA_MCP_COMMUNITY_PACKAGE],
            "env": {
                "FIGMA_API_KEY": "${FIGMA_API_KEY}",
            },
            "description": (
                "Community Figma MCP server (figma-mcp). "
                f"Requires: Node {NODE_MIN_MAJOR}+, "
                "and FIGMA_API_KEY env var set to your Figma Personal Access Token. "
                "Generate token at: Figma Account Settings > Personal access tokens."
            ),
        },
    }


def config(format: str = "json", mode: str = "remote") -> str:
    """Print MCP config for the given format and mode.

    Supported formats:
      - json       Generic .mcp.json fragment
      - opencode   OpenCode opencode.json format
      - cursor     Cursor .cursor/mcp.json format
      - vscode     VS Code .vscode/mcp.json format

    Supported modes:
      - remote     HTTP/OAuth (default)
      - community  stdio/PAT
    """
    if mode == "community":
        if format == "opencode":
            return json.dumps(FIGMA_MCP_OPENCODE_COMMUNITY_ENTRY, indent=2)
        elif format == "cursor":
            entry = {
                "command": "npx",
                "args": ["-y", FIGMA_MCP_COMMUNITY_PACKAGE],
            }
            return json.dumps(entry, indent=2)
        elif format == "vscode":
            entry = {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", FIGMA_MCP_COMMUNITY_PACKAGE],
            }
            return json.dumps(entry, indent=2)
        else:
            return json.dumps(FIGMA_MCP_COMMUNITY_CONFIG_ENTRY, indent=2)
    else:
        # remote (HTTP/OAuth)
        if format == "opencode":
            return json.dumps(FIGMA_MCP_OPENCODE_REMOTE_ENTRY, indent=2)
        elif format == "cursor":
            entry = {
                "type": "http",
                "url": FIGMA_MCP_REMOTE_URL,
            }
            return json.dumps(entry, indent=2)
        elif format == "vscode":
            # VS Code does not support HTTP transport MCP — fall back to community
            entry = {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", FIGMA_MCP_COMMUNITY_PACKAGE],
            }
            return json.dumps(entry, indent=2)
        else:
            return json.dumps(FIGMA_MCP_REMOTE_CONFIG_ENTRY, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Figma MCP registry & health check.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="Check Figma MCP health")
    doctor_parser.add_argument("--json", action="store_true",
                               help="Output as JSON")
    doctor_parser.add_argument("--mode", type=str, default="auto",
                               choices=["auto", "remote", "community"],
                               help="Probe mode (default: auto)")

    # proxy-config
    subparsers.add_parser("proxy-config", help="Print endpoint details")

    # config
    config_parser = subparsers.add_parser("config", help="Print MCP config fragment")
    config_parser.add_argument("--format", type=str, default="json",
                               choices=["json", "opencode", "cursor", "vscode"],
                               help="Config format (default: json)")
    config_parser.add_argument("--mode", type=str, default="remote",
                               choices=["remote", "community"],
                               help="MCP mode (default: remote)")

    args = parser.parse_args()

    if args.command == "doctor":
        result = doctor(mode=args.mode)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status = result["overall"]
            icon = {"ok": "[OK]", "degraded": "[WARN]", "unavailable": "[FAIL]"}.get(status, "?")
            print(f"Figma MCP Health: {icon} {status} (mode: {args.mode})")
            print(f"  Node: {result['node']['version']} "
                  f"({'[OK]' if result['node']['ok'] else '[FAIL]'})")
            print(f"  npx:  {'[OK]' if result['npx']['ok'] else '[FAIL]'}")
            if result["endpoint"]["message"]:
                print(f"  Remote: {result['endpoint']['message']}")
            if result["package"]["message"]:
                print(f"  Package: {result['package']['message']}")

    elif args.command == "proxy-config":
        print(json.dumps(proxy_config(), indent=2))

    elif args.command == "config":
        print(config(format=args.format, mode=args.mode))

    return 0


if __name__ == "__main__":
    sys.exit(main())
