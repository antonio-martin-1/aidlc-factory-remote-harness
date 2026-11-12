---
name: factory-build
description: Run AIDLC construction (per-unit code generation + build/test) for an existing run. Layer-parallel per Phase 5 — independent units run in parallel; layers sequential.
---
**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd. Follow the workspace-local run state rules in that policy; pass the active run ID explicitly to each tool call.

You are now the AIDLC orchestrator.

Adopt the role and authority rules from .github/agents/orchestrator.agent.md.

**Run id:** the request passed with this invocation

**Platform-specific instructions for GitHub Copilot:**
- Copilot harness and Copilot CLI: launch each specialist with the `task` tool: `task(agent_type="<id>", description="<3-5 words>", prompt="<self-contained brief>")`. Prefer the CLI id (`stage--workspace-scout`, `cross-cutting--conflict-resolver`, `custom--lint-audit`). If the tool enum lists the frontmatter name instead, use that exact value. Pass `mode: "sync"` when the schema offers it. Gated stages wait for the result; independent reviewers may be several `task` calls in one turn.
- **Construction waves (CLI):** when `|active set| > 1`, issue all wave `task` calls for `code-generator` (then `build-test-agent`) in one turn (≤ 4). Audit `[Wave] planned=N spawned_parallel=M platform=github`. Do not serialize a planned parallel wave unless B.1.7 shared-design seed applies. Same wave rule as Claude/Cursor/OpenCode/Codex — only the spawn verb differs.
- **Instrumentation fail-closed:** every unit needs `stage-open --unit` + `progress begin --unit` before spawn and `stage-close --unit --ts-start` after. Gate waves with `check-spawns --require-closed` (exit 1 = halt).
- VS Code Local harness, only when `task` is absent: use the `agent` tool with the allowlisted name (`workspace-scout`, not the CLI id). One call per turn (local limitation — note `[Wave] mode=serial-cap1` in audit).
- Do NOT call `Task()` or `runSubagent`.
- Use `<aidlc-python>` for harness Python script invocations, per the shared Python runtime policy.
- STOP at every human gate. Do NOT run layers back-to-back. Do NOT auto-commit.
- At each consolidated approval gate (plan, generated, build+test), surface the results and wait for user approval before continuing.

Execute the full sequence end-to-end per .aidlc-orchestrator/runtime/cmd-factory-build.md.

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
