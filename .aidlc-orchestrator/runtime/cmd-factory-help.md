**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-help` — Command Reference

PRIORITY: P2

Start any new feature with:

```
/factory-spec "<request>"
```

## Orchestrator workflow

The orchestrator uses specialized subagents per stage. Start with:

```
/factory-spec "add JWT auth to the API gateway"
```

This triggers triage (TINY → FastPath, or SMALL+ → full pipeline).

### Full pipeline (Extended Inception)

```
── INCEPTION ───────────────────────────────────────────────────────────────
/factory-spec <request>          →  workspace-scout → requirements-analyst
/factory-product-pass <run-id>   →  product vision → personas → stories
/factory-design-pass <run-id>    →  UX flows → UI components → design-system mapping
/factory-arch-pass <run-id>      →  ADRs → tech stack → component map → interfaces
── CONTEXT PASS ─────────────────────────────────────────────────────────────
/factory-plan <run-id>           →  workflow-planner → unit-decomposer
── CONSTRUCTION ─────────────────────────────────────────────────────────────
/factory-build <run-id>          →  code-generator × N units + build-test-agent
/factory-review <run-id>         →  4 parallel reviewers → merged report
/factory-ship <run-id>           →  release notes, ADRs, changelog, CI/CD
```

Each command waits for your approval before proceeding. You inspect, approve,
and move to the next stage.

**Gate rule**: `/factory-plan` requires all three inception passes to be complete.
Running `/factory-plan` directly after `/factory-spec` will halt with a checklist
of missing passes.

### Fast Path (TINY tier)

For trivial requests (typo, README fix, one-file change), the orchestrator
skips all stages and goes directly to code-generator:

```
/factory-spec "fix typo in README"
→ triage: TINY (score 0)
→ code-generator → commit
→ done. No manifest, no audit, no multi-agent overhead.
```

---

## Command reference

| Command | When to use | What happens |
|---------|-------------|-------------|
| `/factory-onboarding` | First time using the orchestrator | Guided tour of the system |
| `/factory-code-tour` | Onboard a human to any codebase | Architecture map, key flows, conventions, next steps |
| `/factory-spec "<request>"` | **Start here** for any new feature | Triages your request, spawns scout + analyst |
| `/factory-product-pass <run-id>` | After `/factory-spec` completes | Product vision, personas, user stories (Phase 0.1) |
| `/factory-design-pass <run-id>` | After `/factory-product-pass` completes | UX flows, UI components, design-system mapping (Phase 0.2) |
| `/factory-arch-pass <run-id>` | After `/factory-design-pass` completes | ADRs, tech stack, component map, service interfaces (Phase 0.3 — final inception gate, two-pass) |
| `/factory-plan <run-id>` | After all inception passes complete | Creates execution plan + design units (Context Pass) |
| `/factory-build <run-id>` | After plan is approved | Generates code + runs tests in parallel |
| `/factory-review <run-id>` | After build completes | 4 reviewers analyze code in parallel |
| `/factory-ship <run-id>` | After review passes | Release notes, ADRs, changelog |
| `/factory-state <run-id>` | Check progress anytime | Shows current stage, next step, timeline |
| `/factory-resume <run-id>` | Run crashed mid-flight | Picks up from the last completed stage |
| `/factory-replay <run-id> --from <stage>` | Stage produced wrong output | Rolls back and re-runs from that stage |
| `/factory-self "<task>"` | Improve the orchestrator itself | Runs pipeline against orchestrator's own code |
| `/factory-help [command]` | Remember a command | This page |

---

## Monitoring

```bash
# Visual timeline of what ran and how long it took
<aidlc-python> aidlc-scripts/factory_run.py graph <run-id>

# Approval gate delays
<aidlc-python> aidlc-scripts/factory_run.py status <run-id> --latency

# Task, attempt, stage, and phase time, plus host token totals
<aidlc-python> aidlc-scripts/factory_progress.py timings --run-id <run-id>

# Live event feed
<aidlc-python> aidlc-scripts/factory_run.py tail <run-id> --follow
```

---

## Recovery

| Situation | Solution |
|-----------|----------|
| Run crashed or you closed the session | `/factory-resume <run-id>` |
| A stage produced wrong output | `/factory-replay <run-id> --from <stage>` |
| An agent crashed and left stale locks | `<aidlc-python> aidlc-scripts/factory_conflict.py release <run-id> --stale --older-than 120` |
| Need to know what happened | `<aidlc-python> aidlc-scripts/factory_run.py timeline <run-id> --follow` |

---

## Custom subagents

Create your own specialized agents in the tool's `agents/custom/` directory:

```bash
# Discover available agents
<aidlc-python> aidlc-scripts/factory_agent_discover.py list
<aidlc-python> aidlc-scripts/factory_agent_discover.py show lint-audit
```

Custom agents use generic contracts and default to `sonnet` model.
See `README.md` for details.

---

## CLI tools

```bash
# Validate a handoff contract
<aidlc-python> aidlc-scripts/factory_validate.py schema.json doc.yaml --strict

# Scan for secrets in handoff files
<aidlc-python> aidlc-scripts/factory_secretscan.py handoff.yaml
```

---

## Documentation

- `docs/TROUBLESHOOTING.md` — common failures and fixes
- `.aidlc-orchestrator/contracts/REFERENCE.md` — all handoff schemas
- `ORCHESTRATOR-PLAN.md` — full design doc
- `ORCHESTRATOR-SIMPLIFY-PLAN.md` — architecture roadmap
