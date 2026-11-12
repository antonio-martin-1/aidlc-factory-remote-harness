**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd. Follow the workspace-local run state rules in that policy; pass the active run ID explicitly to each tool call.

# AIDLC Commit Message Conventions

Use conventional commits. The PR title and squashed commit MUST follow:

```
<type>(<scope>): <description>
```

## Types

| Type | When to use |
|------|-------------|
| `feat` | New agent, command, stage, skill, or Python script |
| `fix` | Bug fix in orchestrator logic, contract validation, or runtime |
| `build` | CI/CD workflow changes, dependency updates, installer changes |
| `docs` | Rule file changes, README, ADRs, documentation-only updates |
| `refactor` | Restructuring without functional change |
| `perf` | Performance optimization |
| `test` | Adding or fixing tests |
| `chore` | Tooling, config, gitignore, non-functional changes |
| `style` | Formatting, whitespace |
| `ci` | GitHub Actions workflow changes |

## Scopes

| Scope | When |
|-------|------|
| `orchestrator` | `.claude/agents/orchestrator.md` or `.github/agents/orchestrator.agent.md` |
| `workspace-scout` | Workspace Scout agent |
| `requirements-analyst` | Requirements Analyst agent |
| `code-generator` | Code Generator agent |
| `build-test` | Build & Test agent |
| `reviewer-*` | Any reviewer agent |
| `ship` | Ship agent |
| `inception` | Inception-stage rule files |
| `construction` | Construction-stage rule files |
| `contracts` | JSON Schema handoff contracts |
| `scripts` | Python scripts in `aidlc-scripts/` |
| `installer` | `aidlc-scripts/install_aidlc.py` |
| `ci` | `.github/workflows/` |
| `docs` | Documentation files |
| `copilot` | Copilot-specific config (`.github/copilot-*.md`) |
| `cursor` | Cursor-specific config (`.cursor/`) |
| `opencode` | OpenCode-specific config (`.opencode/`) |
| `claude` | Claude Code-specific config (`.claude/`) |

## Body (optional)

For `feat` and `fix`, include a body with:
- **Why** the change was made (avoid describing what the code does)
- **Breaking changes** prefixed with `BREAKING CHANGE:`
- **Related issues** with `Closes #123` or `Refs #456`

## Examples

```
feat(workspace-scout): add monorepo workspace detection
fix(code-generator): validate plan artifact before sub-stage transition
docs(inception): clarify reverse-engineering routing rules
ci: add CodeQL workflow for Python scripts
chore(copilot): add review and commit instructions
```
