# Executor Conformance Spec — Appendix (Reference)

Companion to [`executor.v1.md`](executor.v1.md). This file holds purpose,
vocabulary, the registration YAML, the full conformance test list, the
Phase 5 migration plan, and resolved open questions. Useful for adapter
authors and maintainers; not load-bearing for runtime decisions.

## Purpose

The AIDLC orchestrator's differentiating features (parallel codegen, reviewer
fan-out, conflict detection, kill-and-resume) currently rely on Claude Code's
`Task()` spawn primitive. This spec defines the contract a runtime must
satisfy so the same orchestration logic can run unchanged on any agentic tool
that meets the contract.

A conforming executor is **transparent to the orchestrator**: the orchestrator
spawns stages, validates handoffs, and emits audit blocks identically
regardless of which executor backs the spawn.

## Vocabulary

| Term | Meaning |
|---|---|
| **Stage agent** | A specialized agent for one AIDLC stage (`requirements-analyst`, `code-generator`, etc.). Defined at `.claude/agents/stage/<name>.md`. |
| **Input handoff** | A YAML document validated against `<stage>.input.v1.json` containing context_pointers, skill_paths, depth, etc. |
| **Output handoff** | A YAML document validated against `<stage>.output.v1.json` produced by the stage agent and committed to `<run-dir>/handoffs/`. |
| **Spawn** | A single execution of a stage agent against an input handoff that produces an output handoff. |
| **Run directory** | `.aidlc-orchestrator/runs/<run-id>/` — the per-run state directory holding manifest, handoffs, locks, timeline. |

## Conformance test list

A conformance test suite lives at `tests/test_executor_conformance.py`
(Phase 5 deliverable 5.4). Each registered executor MUST pass the suite
unmodified.

| Test | What it verifies |
|---|---|
| `test_spawn_emits_valid_output` | output_handoff validates against schema |
| `test_spawn_emits_cost_data` | tokens_in/out and wall_clock_sec are non-null |
| `test_spawn_two_pass_round_trip` | requirements-analyst Pass 1 → human → Pass 2 |
| `test_concurrent_spawns_succeed` | N=4 concurrent spawns all return cleanly |
| `test_timeout_respected` | spawn with timeout_sec=1 returns `timeout` within 2s |
| `test_cancel_works` | spawn cancelled mid-flight returns `cancelled` |
| `test_worktree_isolation` | parallel writes to overlapping globs don't conflict when isolated |
| `test_failed_output_validation_yields_failed` | invalid output → status:failed |
| `test_unsupported_isolation_declared_upfront` | adapters that can't isolate say so |

## Registration

Adapters register via `aidlc-scripts/executors/registry.yaml`:

```yaml
executors:
  - name: claude-code
    version: "0.2.0"
    module: aidlc-scripts.executors.claude_code_executor
    class: ClaudeCodeExecutor
    capabilities:
      max_concurrency: 8
      worktree_isolation: true
      cancellation: true
    target_tools: ["claude", "claude-code"]

  - name: opencode
    version: "0.1.0"
    module: aidlc-scripts.executors.opencode_executor
    class: OpenCodeExecutor
    capabilities:
      max_concurrency: 4
      worktree_isolation: true
      cancellation: true
    target_tools: ["opencode"]
```

The installer (`install_aidlc.py`) reads the registry to pick the right
executor per `--tool` value. Multi-tool installs (`--tool claude,opencode`)
register both — runtime picks by environment detection.

## Migration from current Claude-Code-only design

Phase 5 lands this contract by:

1. **5.1 (the canonical spec)** — write the contract.
2. **5.2** — extract current Claude-Code spawn behaviour from inline
   orchestrator prose into `aidlc-scripts/executors/claude_code_executor.py`
   as the reference implementation. Run the conformance suite against it;
   suite passes are the regression bar.
3. **5.3** — write `opencode_executor.py` (and optionally `cursor_executor.py`).
   Pass the same suite.
4. **5.4** — wire `install_aidlc.py` to use the registry. Update the
   workflow doc pointer block per tool.

No orchestrator `.md` changes are required if the executors honour the
contract — the orchestrator's `Task(subagent_type=..., prompt=...)` call
remains the same; the executor wraps the underlying spawn mechanism.

## Resolved open questions

- **Should the `spawn_id` be allocated by the orchestrator (passed in) or by
  the executor (returned)?** Allocated by the orchestrator via the run
  manifest — keeps cancellation deterministic.
- **How are streaming token counts surfaced for cost-governor downshifting?**
  v1 is batch-only — final counts at spawn completion. Streaming is a v2
  extension.
- **Multi-tenant orchestrator running spawns on different tools?** Out of
  scope for v1. One run, one executor.
