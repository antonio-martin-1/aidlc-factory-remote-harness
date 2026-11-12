"""Dependency-free Python selection for the shell launchers (Python >=3.10)."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

MIN_VERSION = (3, 10)
PROBE = (
    "import json,sys; "
    "print(json.dumps({'version':list(sys.version_info[:3]),'executable':sys.executable}))"
)


class RuntimeSelectionError(RuntimeError):
    """No compatible interpreter was selected."""


def probe(command: list[str]) -> str:
    """Return the interpreter path, rejecting aliases, old versions and hangs."""
    try:
        result = subprocess.run(
            [*command, "-c", PROBE], capture_output=True, text=True,
            timeout=5, check=True,
        )
        data = json.loads(result.stdout)
        if tuple(data["version"][:2]) < MIN_VERSION:
            raise ValueError("Python >=3.10 required")
        executable = data["executable"]
        if not isinstance(executable, str) or not Path(executable).is_file():
            raise ValueError("interpreter did not report an existing executable")
        # Do not resolve symlinks: that would bypass Unix virtual environments.
        return os.path.abspath(executable)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeSelectionError(f"{command[0]}: {exc}") from exc


def environment_python(directory: Path) -> Path:
    return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def select_python(root: Path) -> str:
    override = os.environ.get("AIDLC_PYTHON")
    if override:
        candidate = Path(override).expanduser()
        if not candidate.is_file():
            raise RuntimeSelectionError("AIDLC_PYTHON must be a valid executable path")
        return probe([str(candidate)])

    dedicated = root / ".venv"
    if dedicated.exists() or dedicated.is_symlink():
        candidate = environment_python(dedicated)
        if not candidate.is_file():
            raise RuntimeSelectionError(f"Project venv is broken: {candidate} is missing")
        try:
            return probe([str(candidate)])
        except RuntimeSelectionError as exc:
            raise RuntimeSelectionError(f"Project venv is incompatible: {exc}") from exc

    active = os.environ.get("VIRTUAL_ENV")
    if active:
        try:
            return probe([str(environment_python(Path(active)))])
        except RuntimeSelectionError as exc:
            raise RuntimeSelectionError(f"Active venv is incompatible: {exc}") from exc

    # Bootstrap is already validated by the launcher in platform candidate order.
    return probe([sys.executable])


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["--encoded-args"]:
        try:
            if len(args) != 2:
                raise ValueError("expected one base64-encoded argument array")
            decoded = json.loads(base64.b64decode(args[1], validate=True).decode("utf-8"))
            if not isinstance(decoded, list) or any(not isinstance(arg, str) for arg in decoded):
                raise ValueError("expected a JSON array containing only strings")
            args = decoded
        except ValueError as exc:
            print(f"[AIDLC Python] Invalid encoded arguments: {exc}", file=sys.stderr)
            return 2
    root = Path(__file__).absolute().parent.parent
    try:
        executable = select_python(root)
    except RuntimeSelectionError as exc:
        print(f"[AIDLC Python] {exc}", file=sys.stderr)
        return 1
    if args == ["--resolve"]:
        print(executable)
        return 0
    if not args:
        print("Usage: aidlc-python <script.py | -m module | -c code> [args]", file=sys.stderr)
        return 2
    env = os.environ.copy()
    env["AIDLC_PYTHON"] = executable
    try:
        return subprocess.call([executable, *args], env=env)
    except OSError as exc:
        print(f"[AIDLC Python] Cannot execute {executable}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
