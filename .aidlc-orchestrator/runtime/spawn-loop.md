**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# Shared Spawn Loop

PRIORITY: P1

> **Load-critical.** This file is read on every stage spawn (~5.5 KB, ~1.4K tokens). Keep under 200 lines. Cold-path content (FAST_PATH, recovery, replay/adopt, project-profile) belongs in their respective `runtime/*.md` files, NOT here.

Two execution modes: **Full spawn loop** (parallel stages — uses `Task()`) and
**Post-execution loop** (sequential inline stages — no `Task()`). Both produce
identical timeline, audit, and state outcomes.

Before every bookkeeping call, use the active `run_id` supplied by the
orchestrator or handoff, per `common/python-runtime.md` workspace-local run state
rules. Do not recover it by reading an external temporary file. Timeline output
and context snapshots must stay under the selected workspace run directory.

## Full spawn loop (parallel stages)

Every parallel stage spawn follows this 10-step sequence. Steps 3-5 (handoff
validate → Task() → output validate) are SKIPPED for inline sequential stages.

0. **Open stage and attach the progress cursor.** Run stage-open and keep `ts`
   from its JSON in orchestration context:
   ```text
   <aidlc-python> aidlc-scripts/factory_run.py stage-open --run-id <run-id> --stage <stage> --phase <PHASE> [--unit <unit>] --field tokens_estimate=N
   ```
   **`--unit` is MANDATORY** for `code-generator` and `build-test-agent` (Construction).
   It stamps `unit` on `spawn_start`, sets `manifest.units[].status=in_progress`, and
   labels the audit block. Omitting it fails closed. This writes START immediately,
   so interleaved stages never insert an older START block after another stage's
   audit. Do not use shell pipes or `$()`.
   Then attach the in-stage cursor once for this spawn. Include `--unit` when
   the handoff has `unit_name` (required for Construction). Pass `--fresh` only
   when the user chose to discard that cursor:
   ```text
   <aidlc-python> aidlc-scripts/factory_progress.py begin --run-id <run-id> --stage <stage> [--unit <unit>]
   ```
   For Construction: always pass `--unit`. Call `begin` **before** spawning the
   agent so `started_at` is not after the first file write.
   Merge the JSON into the input handoff as `continuation`. When `mode` is
   `resume`, set `context_snapshot.depth` to `minimal` and replace
   `context_snapshot.markdown` with `Resume in progress; follow continuation.resume_from.`
   The stage agent follows [`progress-trace.md`](progress-trace.md).

1. **Knowledge query (pre-spawn)**: call `mcp__plugin_engram_engram__mem_search` TWICE — once scoped to `aidlc/<project_slug>/*` (top-5), once to `aidlc/_shared/*` (top-5) if `features.shared_corpus_injection=true`. Inject results (after confidence/deprecation filtering, antipattern boosting) into input handoff's `context_pointers[]` as markdown strings, each tagged with `scope: project` or `scope: shared`. Log `[Knowledge] Query <stage>: <N> project priors + <M> shared priors retrieved` to audit. Full namespace + lifecycle: [`runtime/knowledge-agent.md`](knowledge-agent.md). If engram is unavailable, leave `context_pointers[]` empty and log `[Knowledge] DEGRADED: engram unavailable`.

2. **Model resolution**: `<aidlc-python> aidlc-scripts/factory_model.py resolve <stage>`. If output is non-empty and not the tool default, add `model_override: <model>` to input handoff. If user passed `--model` on the slash command, use that instead and skip the script.

3. **Validate input handoff** against its JSON Schema contract.

4. **Spawn subagent**: platform primitive with the input handoff path
   (`Task(...)` on Claude/OpenCode, parallel `delegate` on Cursor, `task(...)`
   on Copilot CLI, Codex subagent launch). If input handoff has `model_override`,
   pass as `model=<model_override>`.
   **Wave fan-out:** for Construction code-generator / build-test and the review
   pool, step 4 MUST issue all independent spawns of the active set in **one**
   turn (≤ 4). See `cmd-factory-build.md` B.2 HARD RULE — applies to all IDEs.

5. **Validate output handoff** against its JSON Schema contract.

6. **Knowledge save (post-return)**: iterate `output.emitted_knowledge[]`. For each entry, call `mcp__plugin_engram_engram__mem_save` with topic_key `aidlc/<project_slug>/<kind>/<title-slug>`, project scope. If response includes `judgment_required: true`, apply the judgment heuristic from `knowledge-agent.md` (silent for related/compatible/scoped; surface low-confidence supersedes/conflicts_with on ADRs). Log `[Knowledge] Saved <kind>: <title>` each.

7. **Close stage**: validate the output handoff first, then:
   ```text
   <aidlc-python> aidlc-scripts/factory_run.py stage-close --run-id <run-id> --stage <stage> --phase <PHASE> --status <s> --ts-start <ts> [--unit <unit>] --from-handoff <output-handoff-path> --next-stage <next>
   ```
   Omit `--next-stage` for the final stage. **`--unit` is MANDATORY** for
   `code-generator` / `build-test-agent` (or supply `unit_name` in the handoff).
   Close matches `(stage, unit, ts_start)`, stamps `unit` on `spawn_end`, updates
   `manifest.units[].status`, bumps `last_checkpoint_at`, and marks the progress
   cursor terminal. Optional `--tokens N`, `--tokens-in N`, `--tokens-out N`, and
   `--wall-min F` record measured host usage. COMPLETE contains every
   `audit_entries[]` item; none are truncated. Missing/invalid files and
   mismatched status fail before any state update. Output is one JSON object;
   check the exit code before using it. Retry the same close after an
   interruption; it does not duplicate audit or events. Replayed attempts cannot
   be closed. Concurrent units of one stage must each pass their own `--ts-start`
   **and** `--unit`; use `--no-complete-stage` until the group finishes. Before
   advancing to the next wave, run:
   ```text
   <aidlc-python> aidlc-scripts/factory_run.py check-spawns <run-id> --stage <stage> --require-closed
   ```
   Exit 1 = instrumentation gap — do not continue Construction. Do not retry a
   previously closed attempt after reopening it. Audit writes are locked; audit,
   timeline and manifest are separate files, not one filesystem transaction.

   **Non-spawn blocks**: use `emit_audit_block --bullets-file` per
   [`audit-block.protocol.md`](../contracts/audit-block.protocol.md). Write UTF-8
   bullets using the file editing tool under the active run's `tmp/` directory;
   use distinct names for concurrent stages. Keep labels/metadata short and ASCII.
   Unicode and long text belong in the file, outside the scanned shell command.

8. **Update `aidlc-docs/aidlc-state.md`**: set `Current Stage` and `Stage Progress`.

9. **Auto-commit — DEFERRED**: do NOT commit per-stage. Commits fire ONLY at the command boundary (`cmd-factory-*.md` final step) AFTER explicit user approval. Per-stage commits create unauthorized git history for unapproved artifacts (e.g. story-writer output committed before the user has approved the plan it feeds). See `aws-aidlc-rules/core-workflow.md` § "Auto-Commit on Approval".

10. **State update**: `stage-close` marks `complete` or records `failed`.
    `needs_human` / `blocked` never advance the manifest. Use
    `--no-complete-stage` when a group/wave must finish before completion is recorded.
    Do not repeat `complete-stage` / `fail-stage` after the helper.

11. **Halt or surface**:
    - `status == needs_human`: pause, surface in [`## Structured Approval Format`](../../.claude/agents/orchestrator.md), wait for user response, log to audit, then continue.
    - `status != complete` (failed, blocked): halt and surface.
    - `status == complete`: this means the stage agent finished its work. **It does NOT mean the user approved.** Continue to the next step in the active `cmd-factory-*.md` procedure, which may include a command-boundary approval gate. Do NOT auto-commit here.

## Post-execution loop (inline sequential stages)

Sequential stages (workspace-scout, requirements-analyst, workflow-planner,
ship-agent) execute inline in the orchestrator instead of via `Task()`. Steps
3-5 are skipped. **Context compaction** is mandatory after every inline stage
— discard transient reasoning, preserve only structured outputs and artifacts.

After inline stage execution, run these steps in order:

0. **Open stage before inline execution**: use full-loop step 0 (stage-open plus the progress cursor) and retain its `ts`. The inline stage follows [`progress-trace.md`](progress-trace.md).
1. Knowledge query (pre-spawn context injection).
2. **Inline execution**: read `stage/<s>.md` and execute directly; no `Task()`.
   Write the output handoff to `.aidlc-orchestrator/runs/<run-id>/handoffs/`
   with `status` and `audit_entries[]`, even when JSON Schema validation is skipped.
3. **Lightweight validation**: verify required fields, artifacts and structural invariants.
4. **Context compaction**: preserve structured outputs and artifacts, discard transient reasoning.
5. Knowledge save.
6. **Audit + manifest**: use full-loop step 7 (`stage-close --from-handoff`).
7. Update `aidlc-docs/aidlc-state.md`.
8. Auto-commit remains deferred to explicit command-boundary user approval.
9. Halt or surface according to the returned status.

## Stage-specific deltas

| Stage | Delta |
|-------|-------|
| requirements-analyst | Two-pass: inline execution runs twice (Pass 1 → surface → Pass 2) |
| application-designer | Two-pass: questions → `needs_human` with `needs_user_input: true` → re-spawn with answers → 5 design artifacts |
| code-generator | Three sub-stages (plan → generated → approved); each runs full spawn loop with Task(). Same-wave units MUST spawn in ONE turn (≤ 4); serializing a parallel wave is a protocol violation unless shared-design seed (cmd-factory-build B.1.7). Shared design is write-once / reuse. |
| reviewers (pool) | Step 4 spawns all active reviewers in parallel (≤ 4); full spawn loop |
| build-test-agent | Per-unit affected subset via `changed_files` (not HEAD~1); parallel per wave (≤ 4); full suite at wave/Construction close |

## See also
- Audit block protocol: [`contracts/audit-block.protocol.md`](../contracts/audit-block.protocol.md)
- Cold-path recovery: [`runtime/recovery.md`](recovery.md)
