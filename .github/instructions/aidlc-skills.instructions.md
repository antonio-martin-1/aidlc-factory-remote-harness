---
description: 'AIDLC skill resolution order for GitHub Copilot agents and prompts'
applyTo: '**/.github/agents/**,**/.github/prompts/**'
---

**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd. Follow the workspace-local run state rules in that policy; pass the active run ID explicitly to each tool call.

# AIDLC skill resolution (Copilot)

When a stage agent or prompt references skills, resolve each skill path in this order (first match wins):

1. `.github/skills/<name>/SKILL.md` — installed by `install_aidlc.py --tool copilot`
2. `.agents/custom-skills/<name>/SKILL.md` — fork-specific skills (repo source)
3. `.agents/skills/<name>/SKILL.md` — synced via `factory_skill_sync.py` or `--with-agent-skills`
4. `~/.agents/skills/<name>/SKILL.md` — user-global fallback

Log `[Skill] MISSING: <name>` when no path resolves; use inline fallback from the stage rule file.
