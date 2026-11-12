# Handoff Contracts

JSON Schema definitions for every stage agent's input and output.

## Why these exist

Subagents start cold. The orchestrator validates every handoff against
these schemas — no agent runs on a malformed input, no stage closes with
a malformed output. Without contracts, multi-agent systems silently drift.

## File naming

```
<stage-id>.input.v<N>.json    # what the orchestrator sends in
<stage-id>.output.v<N>.json   # what the agent must return
```

Versioning is semver-compatible:
- **Minor version bump (v1 → v1.1)**: additive only — new optional fields.
- **Major version bump (v1 → v2)**: breaking. The orchestrator refuses to
  resume runs that started against an older major. Re-run from scratch.

## Validation

```bash
python3 aidlc-scripts/factory_validate.py \
    .aidlc-orchestrator/contracts/workspace-scout.output.v1.json \
    .aidlc-orchestrator/runs/<run-id>/handoffs/workspace-scout.output.yaml
```

Exit 0 = valid. Exit 1 = invalid (with path to failing field on stderr).

Stage inputs accept an optional `continuation` object
(`shared/continuation.v1.json`). The orchestrator attaches it from the
progress YAML so a respawned subagent resumes the open stage.

## What's currently shipped

| Stage | Input | Output | Notes |
|---|---|---|---|
| workspace-scout | v1 | v1 | Phase 0 |
| requirements-analyst | v1 | v1 | Phase 0 — two-pass with question gate |
| reverse-engineer | v1 | v1 | Phase 1 — conditional (brownfield) |
| story-writer | v1 | v1 | Phase 1 — conditional, two-pass |
| application-designer | v1 | v1 | Phase 1 — two-pass with question gate, 5 design artifacts |
| workflow-planner | v1 | v1 | Phase 1 — Opus |
| unit-decomposer | v1 | v1 | Phase 1 — conditional |
| code-generator | v1 | v1 | Phase 1 — per unit, three sub-stages (plan/generated/approved) |
| build-test-agent | v1 | v1 | Phase 1 — per unit |
| reviewer (shared) | v1 | v1 | Phase 1 — shared across 4 reviewer types. `stage_id` (e.g. `reviewer-code`) maps to `reviewer` (e.g. `code-quality`) |
| ship-agent | v1 | v1 | Phase 1 |
| custom-agent | v1 | v1 | Generic contract for user-defined subagents (see `.claude/agents/custom/` or `.opencode/agents/custom/`) |
| **approval gate** | **v1** | **v1** | **Structured approval input/output. Validates `run_id`, `artifacts[]`, `next_command`, and `resolution.options`. Ensures consistent approval format across all /factory-* commands.** |

Phase 4+ refinements (parallelism, knowledge, conflict resolution) layer on
top of these contracts without breaking them.
