---
name: factory-onboarding
description: Walk through the AIDLC orchestrator system. Learn how runs work, what commands to use, and how to recover from failures.
include-custom-instructions: true
---
**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd. Follow the workspace-local run state rules in that policy; pass the active run ID explicitly to each tool call.

Display the full onboarding guide from .aidlc-orchestrator/runtime/cmd-factory-onboarding.md.

Present every section in full to the user. Do not summarize. After the last section, wait for the user to ask a follow-up question — do not auto-suggest a next command.

## Copilot CLI specifics

Launch stage subagents with the `task` tool. Do not call `Task()` or the VS Code
Local `agent` tool:

`task(agent_type="<id>", description="<3-5 words>", prompt="<self-contained brief>")`

The prompt is the subagent's only context: goal, handoff path, allowed edits, and the
result to return. Each call is stateless. Pass `mode: "sync"` when the schema offers
it, and wait for the result before the next gated stage. Independent reviewers may be
several `task` calls in one turn.

Pick `agent_type` from the tool enum. Prefer the CLI id: agents under
`.github/agents/stage/` are `stage--code-generator`, `stage--build-test-agent`, …;
cross-cutting agents are `cross-cutting--conflict-resolver`; custom agents are
`custom--lint-audit`. If the enum lists the frontmatter `name` instead, use that
exact value.

Do not dispatch `conflict-resolver` or `knowledge-agent` with `task`. Conflict checks
go through `aidlc-scripts/factory_conflict.py`. Skip Engram when it is absent.

- Use `<aidlc-python>` per `.aidlc-orchestrator/runtime/common/python-runtime.md`.
- STOP at every human gate. Do NOT auto-commit.
