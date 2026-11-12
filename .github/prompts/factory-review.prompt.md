---
agent: orchestrator
mode: agent
description: Run AIDLC post-generation reviewer pool (code quality, security, performance, simplification) in parallel. Phase 4 of the orchestrator.
---

**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd. Follow the workspace-local run state rules in that policy; pass the active run ID explicitly to each tool call.

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.github/agents/orchestrator.agent.md.

**Run id:** $ARGUMENTS

**Platform-specific instructions for GitHub Copilot:**
- Copilot harness and Copilot CLI: launch each specialist with the `task` tool: `task(agent_type="<id>", description="<3-5 words>", prompt="<self-contained brief>")`. Prefer the CLI id (`stage--workspace-scout`, `cross-cutting--conflict-resolver`, `custom--lint-audit`). If the tool enum lists the frontmatter name instead, use that exact value. Pass `mode: "sync"` when the schema offers it. Gated stages wait for the result; independent reviewers may be several `task` calls in one turn.
- VS Code Local harness, only when `task` is absent: use the `agent` tool with the allowlisted name (`workspace-scout`, not the CLI id). One call per turn.
- Do NOT call `Task()` or `runSubagent`.
- Use `<aidlc-python>` for harness Python script invocations, per the shared Python runtime policy.
- STOP at the approval gate — do NOT auto-commit. Surface the merged review report and wait for explicit user approval before committing or routing to the next stage.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-review.md.

Hard rules from @.github/agents/orchestrator.agent.md apply.
