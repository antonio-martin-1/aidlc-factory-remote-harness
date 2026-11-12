---
agent: orchestrator
mode: agent
description: Dependency-ordered codebase tour — foundations → entry points. Equivalent to Understand-Anything's tour-builder. Works in any AIDLC-installed project.
---

**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd. Follow the workspace-local run state rules in that policy; pass the active run ID explicitly to each tool call.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-code-tour.md.

Hard rules: read-only, never modify files or create commits.
