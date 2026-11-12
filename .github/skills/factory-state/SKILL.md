---
name: factory-state
description: Show the current state of a run — completed stages, current stage, next steps, budget, and any issues.
---
**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd. Follow the workspace-local run state rules in that policy; pass the active run ID explicitly to each tool call.

You are now the AIDLC orchestrator.

Adopt the role and authority rules from .github/agents/orchestrator.agent.md.

**Run id:** the request passed with this invocation

**Platform-specific instructions for GitHub Copilot:**
- Use `<aidlc-python>` for harness Python script invocations, per the shared Python runtime policy.

Execute the full sequence end-to-end per .aidlc-orchestrator/runtime/cmd-factory-state.md.

Hard rules from .github/agents/orchestrator.agent.md apply.

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
