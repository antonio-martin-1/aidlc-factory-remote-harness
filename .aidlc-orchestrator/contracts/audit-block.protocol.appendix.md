# Audit-Block Protocol — Appendix (Reference)

Companion to [`audit-block.protocol.md`](audit-block.protocol.md). This file
holds the full helper-internals sequence, example renders, file-lifecycle
notes, and the historical rationale. None of it is load-bearing for an
agent emitting an audit block at runtime — the slim canonical doc is.

## Helper internals — full substep-6 sequence

`emit_audit_block` performs the following atomically per call:

1. Validate `--evt` against the canonical vocabulary.
2. Validate `--phase` ∈ {`INCEPTION`, `CONSTRUCTION`, `OPERATIONS`}.
3. Validate evt-required fields are present.
4. Validate the run exists (manifest.yaml on disk).
5. Validate at least one `--bullet` is supplied.
6. **Emit a timeline event first** (single source of ts truth).
7. Acquire advisory `flock` on `aidlc-docs/audit.md`.
8. **Dedupe guard:** if last `## ` header in `audit.md` has the same `ts` AND
   the same `"<PHASE> - <LABEL>"`, this is a retry — skip the append.
9. **Chronology guard:** the new ts MUST be ≥ the last header's ts; otherwise
   the helper dies non-zero rather than corrupting history.
10. Append the block under the lock.
11. Release the lock.
12. Print the ts to stdout for the caller to capture.

Wall-clocking `now()` for the audit header is **impossible** because the ts
comes from the timeline event the helper just emitted — not from a separate
clock read. Chronology is enforced against `timeline.jsonl`, not the system
clock.

## Example renders

```
## 2026-05-14T10:34:12+00:00 INCEPTION - User Decision (workflow-planner)
- [User] Approved execution plan
- [User] Free-text note: "the multi-unit decomposition is fine"

## 2026-05-14T10:51:08+00:00 INCEPTION - User Answers Received
- [User] Q1=A (security extension enabled)
- [User] Q2=C (no property-based testing)
- [Orchestrator] Tension flagged for Pass 2: 401 vs 403 disambiguation

## 2026-05-14T11:02:44+00:00 INCEPTION - Reverse-Engineer SKIPPED
- [Orchestrator] non-critical: workspace_state.next_phase != "reverse-engineering"
- [Orchestrator] Skipping per Failed→skipped recovery; downstream stages proceed
```

## Audit file lifecycle

- Path: `aidlc-docs/audit.md`. Append-only.
- If missing, the helper creates it with header `# Audit Log\n\n`.
- The archive rotation policy from `core-workflow.md` (entries > 30 → archive
  to `aidlc-docs/archive/audit-<phase>.md`) is **not** the helper's
  responsibility — keep that in the orchestrator's lifecycle code.

## Why this exists

Before Phase 1 of the refactor, `orchestrator.md` restated the substep-6
canonical sequence inline at every approval gate — six full restatements plus
~10 partial references, 60+ audit-protocol phrase hits across 12 phrases.
That was deterministic boilerplate the LLM had to re-read on every spawn.
By compiling it into this helper:

- The kernel no longer carries the protocol body (saves tokens on every load).
- The protocol exists in exactly one place (the canonical doc + the helper).
- Behavior is testable (12 pytest cases in `tests/test_emit_audit_block.py`).
- Race conditions are impossible (flock-guarded).
- Retries are idempotent (dedupe guard).
- Chronology violations fail loudly (chronology guard).
