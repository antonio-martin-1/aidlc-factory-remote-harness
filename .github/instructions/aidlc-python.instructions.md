---
description: 'Python conventions for AIDLC runtime scripts'
applyTo: 'aidlc-scripts/**,tests/**,src/**'
---

**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd. Follow the workspace-local run state rules in that policy; pass the active run ID explicitly to each tool call.

# AIDLC Python scripts

- Prefer `pathlib.Path` over string paths; use `AIDLC_ROOT` when resolving repo root.
- Never use `subprocess(..., shell=True)` without sanitization; no `eval()`.
- Factory scripts exit non-zero on validation failure — propagate errors, do not swallow.
- Handoff validation: `<aidlc-python> aidlc-scripts/factory_validate.py <schema> <handoff> [--strict]`.
- Run state lives in `.aidlc-orchestrator/runs/` (gitignored) — never commit manifests or handoffs from runs.
