# Executor Conformance Specification — v1

**Status:** DRAFT — reference contract for tool-agnostic executor adapters.
First concrete adopter: ClaudeCodeExecutor. Phase 5 adds OpenCodeExecutor.

**Audience:** anyone writing an AIDLC adapter for an agentic coding tool
other than Claude Code.

For purpose, vocabulary, registration YAML, the Phase 5 migration plan, the
full conformance test table, and resolved open questions, see
[`executor.v1.appendix.md`](executor.v1.appendix.md).

---

## 1. Required interface

A conforming executor MUST implement the following operation with these
semantics, regardless of language or transport:

```
spawn(
    stage_name: str,
    input_handoff_path: pathlib.Path,
    *,
    timeout_sec: int | None = None,
    isolation: "worktree" | None = None,
) -> SpawnResult
```

### Inputs
- `stage_name`: the basename of the stage agent file (e.g. `"requirements-analyst"`).
- `input_handoff_path`: absolute path to a YAML handoff that validates against `<stage>.input.v1.json`.
- `timeout_sec`: optional wall-clock cap. Executors MUST respect this. On timeout, the executor MUST return a `SpawnResult` with `status: timeout`, NOT raise.
- `isolation`: optional. `"worktree"` requests an isolated git worktree for write isolation (used by parallel codegen). Executors that cannot satisfy this MUST refuse the spawn with `status: unsupported`.

### Output — `SpawnResult`
```yaml
status: "complete" | "blocked" | "failed" | "needs_human" | "timeout" | "unsupported"
output_handoff_path: <absolute path to validated output YAML>
tokens_in: <int>
tokens_out: <int>
wall_clock_sec: <float>
worktree_path: <optional path if isolation=worktree was honored>
error: <optional string if status in {failed, unsupported}>
```

### Invariants
1. The executor MUST validate the output handoff against `<stage>.output.v1.json` before returning. A schema-invalid output MUST yield `status: failed`.
2. The executor MUST NOT mutate `<run-dir>/manifest.yaml` or `<run-dir>/timeline.jsonl`. Those are orchestrator-owned.
3. The executor MUST append every spawn to `<run-dir>/handoffs/` with the canonical filename `<stage>.output.yaml` (or `<stage>.output.pass2.yaml` for two-pass stages).
4. The executor MUST surface cost data — `tokens_in`, `tokens_out`, `wall_clock_sec` — even on failure (best-effort when possible; zero is allowed when unknown).

---

## 2. Concurrency

Executors MUST support at least `N=4` concurrent in-flight `spawn()` calls.
Below that, layer-parallel codegen degrades to sequential and the AIDLC
orchestrator's parallelism guarantees are broken.

Adapters that cannot meet `N≥4` MUST:
- Declare `max_concurrency` in their registration metadata.
- Cause `/factory-build` to fall back to sequential mode and emit
  `[Executor] DEGRADED: concurrency cap <N>` in audit.

---

## 3. Cancellation

Executors MUST support cooperative cancellation:

```
cancel(spawn_id: str) -> CancelResult
```

After `cancel()`:
- The corresponding `spawn()` MUST return within `timeout_sec / 4` (or 30s if no timeout was set) with `status: cancelled`.
- Any partially-written output MUST be moved to `<run-dir>/handoffs/<stage>.output.cancelled-<ts>.yaml` (not the canonical filename, to avoid downstream consumption).

Adapters that cannot satisfy cancellation MUST advertise it and the
orchestrator will refuse to enter mid-flight cancellation flows — replays
become the only recovery primitive.

---

## 4. Audit emission

Executors MUST emit the following audit block at the END of each spawn (the
orchestrator appends it to `aidlc-docs/audit.md`):

```markdown
## <ISO8601> <PHASE> - <STAGE> COMPLETE
- [Executor] adapter: <executor-name> version: <version>
- [Executor] tokens_in: <N>, tokens_out: <N>, wall_clock_sec: <F>
- [Executor] worktree: <path|none>
- [Executor] cancelled: <true|false>
```

The orchestrator's existing audit-block helper (`factory_run.py emit_audit_block`)
handles atomic append, dedupe, and flock. Adapters only need to produce the
content rows; the orchestrator handles the file write.

---

## 5. Skill resolution

Executors MUST NOT load skill `SKILL.md` content into orchestrator-side
context (see `aidlc-docs/refactor/skills-audit.md`). The orchestrator stores
only resolved file paths in the manifest. Skill content is loaded by the
stage agent *inside its own isolated context*.

The executor's responsibility is to ensure the stage agent's isolated context
has filesystem access to the resolved paths.

For Claude Code: `.agents/skills/`, `~/.agents/skills/` — accessible because
the spawn runs in the same filesystem.
For OpenCode / others: the adapter MUST set up the same filesystem visibility
or fail-fast with `status: unsupported`.

---

## 6. Two-pass stage handling

Two-pass stages (`requirements-analyst`, `product-pass-agent`,
`design-pass-agent`, `arch-pass-agent`, and `story-writer`) need special
treatment.

**Single-file convention**: each two-pass stage owns exactly ONE questions
file (e.g. `<run-id>-requirement-verification-questions.md`,
`<run-id>-product-questions.md`, `<run-id>-design-questions.md`,
`<run-id>-arch-questions.md`). The user answers **in-place** by filling the
`[Answer]:` tags in that same file. There is NO separate `*answered*` /
`*-answered.md` copy.

- Pass 1: the questions file does not yet exist, or exists with empty
  `[Answer]:` tags. Stage emits `status: needs_human` with
  `questions_artifact_path`. Executor MUST surface this to the orchestrator as
  `status: needs_human` — NOT as `failed`.
- Pass 2: the same questions file now has its `[Answer]:` tags filled. Stage
  emits `status: complete`. Executor writes output as `<stage>.output.pass2.yaml`.

The orchestrator distinguishes pass1/pass2 via the input handoff content (it
re-invokes the stage pointing at the same, now-answered questions file); the
executor does not need state for this — it is stateless per spawn. Executors
MUST NOT create, rename to, or expect a separate `*answered*` file.

---

## 7. Worktree isolation

When `isolation="worktree"`, the executor MUST:

1. Create a temporary worktree of the current branch via `git worktree add`.
2. Run the spawn against that worktree as CWD.
3. If the spawn produces ZERO changes, remove the worktree silently.
4. If the spawn produces changes, leave the worktree intact and return
   its absolute path in `worktree_path`.

The orchestrator owns merge / cleanup of populated worktrees.

Adapters that cannot satisfy git-worktree semantics MUST return
`status: unsupported` for worktree spawns. Phase 5's OpenCode adapter is
expected to support worktrees (OpenCode runs against a filesystem too).

---

## 8. Conformance & versioning

- Conformance suite: `tests/test_executor_conformance.py`. Every registered executor MUST pass the suite unmodified. Full test list in the appendix.
- This is `executor.v1`. Backward-incompatible changes (signature changes, new required fields, behavioural reinterpretation) MUST bump to v2 with a new spec file. Adapters declare which version they implement; orchestrator refuses to register an adapter whose version it does not support.

---

*End of canonical spec. Reference material (purpose, vocabulary, registration,
migration plan, open questions) lives in `executor.v1.appendix.md`.*
