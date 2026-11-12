**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd. Follow the workspace-local run state rules in that policy; pass the active run ID explicitly to each tool call.

# AIDLC Pull Request Instructions

## Title

Must follow conventional commits: `<type>(<scope>): <description>`
(See `.github/copilot-commit-instructions.md` for types and scopes.)

## Description template

```markdown
## Summary

<!-- 1-3 bullet points describing what this PR does and why -->

## Changes

<!-- List of key changes with file paths -->

## Parity checklist

- [ ] `.claude/agents/` updated
- [ ] `.github/agents/` updated
- [ ] `.cursor/agents/` updated
- [ ] `.opencode/agents/` updated
- [ ] `.claude/commands/` updated (if applicable)
- [ ] `.github/prompts/` updated (if applicable)
- [ ] `.cursor/commands/` updated (if applicable)
- [ ] `.opencode/commands/` updated (if applicable)

## Test plan

<!-- How reviewers should verify this change -->

## Related

Closes #<!-- issue number -->
```

## Review requirements

- All CI checks must pass (PR lint, security scanners, CodeQL, labeler).
- Contributor statement must be present (auto-validated by CI).
- PR must not carry a `do-not-merge` label.
- At least one CODEOWNER approval required per `.github/CODEOWNERS`.

## Merging

- Squash merge preferred. The squashed commit message MUST be the PR title.
- The `do-not-merge` label blocks merging. Remove it only when the PR is ready.
- Do NOT merge while a `release/*` branch has an open PR (enforced by CI).
