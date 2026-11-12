**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# Custom subagents

PRIORITY: P3

Spawn any agent from `.claude/agents/custom/` via the standard spawn loop
([`spawn-loop.md`](spawn-loop.md)).
Discovery: `<aidlc-python> aidlc-scripts/factory_agent_discover.py list`.
Contracts: `custom-agent.{input,output}.v1.json`. Model: `custom-agent` entry
in `budgets/default.yaml` (`sonnet`).
