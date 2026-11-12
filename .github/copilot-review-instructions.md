**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd. Follow the workspace-local run state rules in that policy; pass the active run ID explicitly to each tool call.

# AIDLC Copilot Code Review Instructions

You are reviewing code in the AIDLC toolchain — a multi-agent orchestrator that
routes development requests through specialized stage agents. Apply the
five-axis self-review from the `code-review-and-quality` skill:

## Review axes

### 1. Correctness
- Does the change match its stated intent (commit message, PR body, ADR)?
- Are handoff contracts respected? JSON Schema in `.aidlc-orchestrator/contracts/`
  is the interface — validate if in doubt.
- No fabricated fields in stage output handoffs.
- Audit.md is append-only; stage agents emit `audit_entries[]`, orchestrator wraps them.

### 2. Security
- No secrets committed (API keys, tokens, credentials).
- No command injection vectors in shell commands within agent prompts.
- No path traversal in file operations.
- Python scripts: no `eval()`, no `subprocess(shell=True)` without sanitization.

### 3. Performance
- Agent prompts should not duplicate rule file logic — rule files are source of truth.
- Python scripts: avoid O(n²) patterns in hot paths (handoff validation, conflict detection).
- CI workflows: cache dependencies, avoid unnecessary installs on every run.

### 4. Maintainability
- Follows existing patterns in neighboring files (agent prompts, Python scripts).
- No dead code, no commented-out code, no TODO without an issue reference.
- Agent frontmatter matches the tool's convention (Copilot: `*.agent.md`, `tools`, `agents`, `user-invocable`; Claude: `model`).

### 5. Parity
- Changes to `.claude/agents/` must have corresponding updates in `.github/agents/`,
  `.cursor/agents/`, and `.opencode/agents/`.
- Changes to `.claude/commands/` must have corresponding updates in
  `.github/prompts/`, `.cursor/commands/`, and `.opencode/commands/`.
- `.opencode/` must have an AGENTS.md equivalent (the main instructions file).

## Severity levels

| Label | Meaning |
|-------|---------|
| `blocking` | Must fix before merge. Safety, correctness, contract violation. |
| `should-fix` | Strongly recommended. Maintainability, performance, parity gap. |
| `nit` | Style preference. Author may resolve or defer. |

## Output format

For each finding, include: file path, line number, severity, and recommendation.
