# Audit-Block Protocol — Canonical Reference

**Python and shell bootstrap:** Read `.aidlc-orchestrator/runtime/common/python-runtime.md`
and expand `<aidlc-python>` for the actual shell before running these commands.
Write long or Unicode text to the indicated file; use short ASCII labels and metadata.
Create the run's `tmp/` directory with `factory_run.py ensure-dirs --run-id <run-id>`.

**Single source of truth** for non-spawn audit blocks (user decisions, user
answers, stage-skipped events, orchestrator notes). Enforced by
`aidlc-scripts/factory_run.py emit_audit_block`. For helper internals,
example renders, file lifecycle, and history, see
[`audit-block.protocol.appendix.md`](audit-block.protocol.appendix.md).

## Invocation

Every non-spawn audit block is created with **one call**:

Write `.aidlc-orchestrator/runs/<run-id>/tmp/stage-id-evt-name-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `<text>`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt <evt-name> --stage <stage-id> --phase <PHASE> --label "<BLOCK LABEL>" --field key=value --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/stage-id-evt-name-bullets.txt
```

The helper validates inputs, emits a timeline event for the canonical `ts`,
acquires `flock` on `aidlc-docs/audit.md`, dedupes retries, enforces
chronology, appends the block, and prints the `ts` to stdout. On failure it
returns non-zero with no mutation. Full sequence in the appendix.

## Canonical evt vocabulary

The ONLY allowed evt names for non-spawn audit blocks:

| Trigger | evt | Required fields | Required `--stage` |
|---|---|---|:---:|
| User answered clarifying questions (e.g. Pass 1 of requirements-analyst) | `user_answers_received` | — | yes |
| User approved / rejected / amended a stage artifact at an approval gate | `user_decision` | `decision=<approve\|reject\|amend\|cancel>` | yes |
| A non-critical stage spawn failed and the orchestrator recovered by skipping | `stage_skipped` | `reason=<text>` | yes |
| Orchestrator-side state mutation that doesn't fit the above (rare) | `orchestrator_note` | `summary=<text>` | no |

**Spawn cycles** use `factory_run.py stage-open` / `stage-close`. START is written
at open; all agent audit entries are written in COMPLETE at close. This helper is for the four non-spawn evts above.

## Header format (locked)

```
## <ts> <PHASE> - <BLOCK LABEL>
- bullet1
- bullet2
```

Followed by exactly one blank line as the section separator. The H2 header is
the only structural marker; reviewers and downstream tools parse against this
pattern. `<PHASE>` ∈ {`INCEPTION`, `CONSTRUCTION`, `OPERATIONS`}.

## Failure modes (all return non-zero, no mutation)

| Condition | Error |
|---|---|
| evt not in vocabulary | `unknown evt: ... Valid evt vocabulary: ...` |
| phase ∉ {INCEPTION, CONSTRUCTION, OPERATIONS} | `invalid phase: ...` |
| evt requires `--stage` but none given | `evt 'X' requires --stage` |
| evt requires `--field K=V` but K is missing | `evt 'X' requires --field K=<value>` |
| no usable bullets from `--bullet` / `--bullets-file` | `at least one --bullet is required` |
| supplied bullets file is missing, unreadable or not UTF-8 | `cannot read bullet source ...` |
| run_id doesn't have a manifest.yaml | `run not found: ...` |
| ts < last header's ts (chronology violation) | `chronology violation: ts <new> < last audit ts <old>` |

## Retry semantics

If a stage spawn fails after `emit_audit_block` succeeded but before the
orchestrator commits its own state, the orchestrator may re-invoke
`emit_audit_block` with `--ts <previous-ts>` to retry idempotently. The
dedupe guard will detect the identical block and skip; the helper still
exits 0 and prints `<ts> (dedupe skipped — identical block already present)`.

## Concurrency

POSIX `fcntl.flock` or Windows `msvcrt` on `audit.md.lock`. Multiple parallel writers (e.g.
layer-parallel `/factory-build` writing audit entries per unit) serialize
correctly; no two writers can interleave into the same `## ` block.
Verified by `tests/test_emit_audit_block.py::test_emit_audit_block_concurrent_writers_serialize`.

## Exact invocations per gate

The orchestrator references these sections by name from `.claude/agents/orchestrator.md`. Each block is the literal command to run when that gate fires.

### § reverse-engineer gate

Write `.aidlc-orchestrator/runs/<run-id>/tmp/reverse-engineer-user_decision-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[User] <Approved reverse-engineer spawn | Skipped reverse-engineer (small-scope: <truncated request>)>`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt user_decision --stage reverse-engineer --phase INCEPTION --label "User Decision (reverse-engineer)" --field decision=<approve|reject> --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/reverse-engineer-user_decision-bullets.txt
```

### § user_answers_received

For requirements-analyst Pass 1 (after the user provides letter picks):

Write `.aidlc-orchestrator/runs/<run-id>/tmp/requirements-analyst-user_answers_received-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[User] Q1=<letter> (<gloss>)`
- `[User] Q2=<letter> (<gloss>)`
- `[Orchestrator] Tension flagged for Pass 2: <text>`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt user_answers_received --stage requirements-analyst --phase INCEPTION --label "User Answers Received" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/requirements-analyst-user_answers_received-bullets.txt
```

Write one file line per answered question and per Pass 2 tension carry-forward.

### § workflow-planner gate

Write `.aidlc-orchestrator/runs/<run-id>/tmp/workflow-planner-user_decision-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[User] <Approved|Rejected|Amended> <run-id>-execution-plan.md (<gloss>)`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt user_decision --stage workflow-planner --phase INCEPTION --label "User Decision (workflow-planner)" --field decision=<approve|reject|amend> --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/workflow-planner-user_decision-bullets.txt
```

### § code-generator gate

For each approval inside `/factory-build` (sub-stages `plan` and `generated`):

Write `.aidlc-orchestrator/runs/<run-id>/tmp/code-generator-user_decision-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[User] <decision summary per unit>`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt user_decision --stage code-generator --phase CONSTRUCTION --label "User Decision (code-generator <sub_stage>)" --field decision=<approve|reject|cancel> --field sub_stage=<plan|generated> --field rejected_units="<csv>" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/code-generator-user_decision-bullets.txt
```

### § build-test-agent gate

Write `.aidlc-orchestrator/runs/<run-id>/tmp/build-test-agent-user_decision-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[User] <decision summary>`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt user_decision --stage build-test-agent --phase CONSTRUCTION --label "User Decision (layer <n> build/test)" --field decision=<approve|reject|amend> --field layer=<n> --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/build-test-agent-user_decision-bullets.txt
```

### § review gate

Write `.aidlc-orchestrator/runs/<run-id>/tmp/review-user_decision-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[User] <outcome summary>`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt user_decision --stage review --phase CONSTRUCTION --label "User Decision (review)" --field decision=<approve|request_fixes> --field rejected_units="<csv>" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/review-user_decision-bullets.txt
```

### § stage_skipped

For Failed→skipped recovery when a non-critical stage spawn fails:

Write `.aidlc-orchestrator/runs/<run-id>/tmp/s-stage_skipped-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[Orchestrator] failure cause: <text>`
- `[Orchestrator] skip decision rationale: <text>`
- `[Orchestrator] fallback: <text>`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt stage_skipped --stage <s> --phase <PHASE> --label "<STAGE LABEL> SKIPPED" --field reason="non-critical failure" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/s-stage_skipped-bullets.txt
```

Critical stages (`workspace-scout`, `requirements-analyst`, `workflow-planner`, `code-generator`, `build-test-agent`) MUST halt instead — use `factory_run.py fail-stage`, not this helper.
