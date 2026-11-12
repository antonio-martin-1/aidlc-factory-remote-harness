**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# Traceability Contextualization Protocol

PRIORITY: P4

Reference document. Defines how the orchestrator injects historical context
from traceability files into every stage input handoff.

---

## §1 Purpose

AIDLC generates traceability artifacts at every stage:
- `aidlc-docs/audit.md` — append-only event log
- `aidlc-docs/aidlc-state.md` — current state tracking
- `.aidlc-orchestrator/runs/<run-id>/manifest.yaml` — run manifest
- `.aidlc-orchestrator/runs/<run-id>/timeline.jsonl` — append-only event timeline
- `.aidlc-orchestrator/runs/<run-id>/handoffs/*.yaml` — stage I/O contracts

Without contextualization, each stage agent starts from an empty context,
unaware of prior decisions, rejected alternatives, or open items. This leads to:
- Re-asking questions already answered
- Reversing decisions already approved
- Generating code that contradicts earlier design

This protocol ensures every stage agent receives a condensed, relevant history
before it begins work.

---

## §2 Context Builder

The canonical tool is `aidlc-scripts/factory_context_builder.py`.

### Invocation

```bash
<aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> [--depth minimal|standard|comprehensive] [--output path] [--format markdown|yaml|json]
```

### Depth levels

| Depth | Tokens | Content | Stages |
|---|---|---|---|
| `minimal` | ~200 | Current stage + last 3 audit entries | workspace-scout |
| `standard` | ~800 | Full state + last 10 decisions + stage timing | requirements-analyst, story-writer, workflow-planner, application-designer, unit-decomposer, reviewer-* |
| `comprehensive` | ~2000 | Everything + handoff summaries | code-generator, build-test-agent, ship-agent |

### Output format

Default markdown with sections:
- **Project Context** — run id, project slug, version, profile
- **Current State** — stage, phase, completed/skipped/failed stages
- **Recent Decisions** — last N decision events from audit.md
- **Stage Timeline** — per-stage event summary from timeline.jsonl
- **Open Items** — incomplete units, pending approvals
- **Resolved Skills** — active skill paths from manifest
- **Recent Handoffs** — last N output handoff statuses (comprehensive only)

---

## §3 Injection Rules

### Where to inject

**Primary:** Add to the input handoff YAML under the key `context_snapshot:`.
Every stage contract already includes this as an optional field.

**Fallback:** If the contract lacks `context_snapshot:`, prepend the snapshot
as a YAML comment block at the top of the handoff file:
```yaml
# --- Context Snapshot ---
# <snapshot content>
# --- End Context ---
```

### When to inject

**Timing:** Immediately before writing the input handoff, after all other
fields are populated. Do NOT cache snapshots across stages.

**Reason:** The audit.md and timeline may have been updated by the previous
stage or by user decisions. A stale snapshot is worse than no snapshot.

### Size constraints

- The snapshot must fit within the stage's token budget (defined in
  `.aidlc-orchestrator/budgets/default.yaml`).
- If the snapshot exceeds the budget, truncate from the bottom (oldest entries
  first) and append `[truncated]`.

### Resume depth

When `continuation.mode` is `resume`, the spawn loop sets this snapshot's
depth to `minimal` and replaces its markdown with a one-line pointer at
`continuation.resume_from`. The open stage's cursor is the progress YAML in
[`progress-trace.md`](progress-trace.md).

---

## §4 Manual Inspection

Users can request a context snapshot at any time:

```
/factory-context <run-id> [--depth minimal|standard|comprehensive]
```

This is a read-only command. It does not modify state, handoffs, or the audit
trail. It is useful for:
- Returning to a project after a long pause
- Understanding why a decision was made
- Onboarding a new agent to an in-progress run
- Debugging stage behavior

---

## §5 Integration with Other Systems

### CodeGraph

If `.codegraph/codegraph.db` exists, the context snapshot may include:
- `codegraph_state: {indexed, nodes, files, backend}`
- `codegraph_queries_total` from telemetry

This is added by the workspace-scout stage and propagated through the snapshot.

### Engram

If Engram is available, the context snapshot may include:
- `engram_memory_count` — number of persisted observations
- `engram_topic_keys` — list of active topic keys

This is added by the knowledge-agent stage and propagated through the snapshot.

### Budget

The context snapshot is included in token budget calculations. The
`factory_context_builder.py` script estimates token count using a rough
4-chars-per-token heuristic. The orchestrator subtracts this from the stage's
available token budget before spawning.

---

## §6 Reference

- Implementation: `aidlc-scripts/factory_context_builder.py`
- Command: `.claude/commands/factory-context.md` (and equivalents in `.cursor/`, `.github/`, `.opencode/`, `.codex/`)
- Orchestrator rule: `<tool>/agents/orchestrator.md` § Traceability Contextualization
- Core workflow: `.aidlc-orchestrator/runtime/core-workflow.md` § MANDATORY: Traceability Contextualization
