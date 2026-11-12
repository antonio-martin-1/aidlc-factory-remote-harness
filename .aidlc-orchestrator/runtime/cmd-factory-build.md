**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-build` — Phase 1 build

PRIORITY: P2

Construction phase. **Layer-parallel:** units are topologically sorted by
`depends_on`; each layer runs in parallel (≤ 4 concurrent); layers are
sequential. Locks (file-glob) acquired per-unit before spawn; AST symbol
drift detected post-spawn for Python files.

**1. Validate stage prerequisites (MANDATORY):**
   ```bash
   <aidlc-python> aidlc-scripts/stage_gate.py check <run-id> code-generator
   ```
   Exit 0 → continue. Exit 1 → **HALT**. Do NOT proceed. Surface error to user
   with missing prerequisites list. This prevents agents from skipping mandatory
   stages (requirements-analyst, workflow-planner, etc.).

   Also read `manifest.yaml`. Refuse if missing or if `workflow-planner` hasn't
   completed with user approval.

**Construction Phase Entry Checkpoint** (run BEFORE first layer, MANDATORY — cannot be skipped):

1. Create construction directories (MUST exist before any unit spawns):
   ```bash
   <aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id> --extra aidlc-docs/construction/plans
   <aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id> --extra aidlc-docs/construction/design
   <aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id> --extra aidlc-docs/construction/build-and-test
   <aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id> --extra aidlc-docs/construction/qa-report
   ```

2. Verify audit.md has all Inception entries.

3. Verify `aidlc-docs/construction/plans/` exists (just created above).

4. Load execution plan from `aidlc-docs/inception/plans/<run-id>-execution-plan.md`. If missing → **HALT**.

5. **CRITICAL — per-unit loop enforcement**: The code-generator MUST run the FULL per-unit loop in this exact order — NO SHORTCUTS:
   ```
   Sub-stage 1: Plan → writes plan file to aidlc-docs/construction/plans/ → approval gate
   Sub-stage 2: Construction Design — ONCE per run
                → seed unit: shared_design_mode=write (create missing shared docs)
                → all later units: shared_design_mode=skip (no re-analysis)
   Sub-stage 3: Code Generation (TDD: Red → Green → Refactor per task)
   ```
   **NEVER instruct the code-generator to "build this code" or "generate code" directly.**
   The orchestrator MUST pass the input handoff with `unit_name`, `unit_spec_path`, and
   let the agent follow its own sub-stage protocol. Any shortcut bypasses hallucination
   prevention and produces undocumented code.
   **Do NOT tell later units to rewrite the five shared design docs.** That is a
   Construction protocol violation and the main wall-clock / token sink.

6. Set `Current Stage: CONSTRUCTION - Layer 1` in `aidlc-state.md`.

## Pre-Build Step 0 — Skill Sync

Runs ONCE before any unit is spawned.

1. **Resolve techs** — intersect project tech_stack with autoskills supported techs:
   ```bash
   TECH=$(<aidlc-python> aidlc-scripts/factory_skill_sync.py resolve-tech .aidlc-orchestrator/runs/<run-id>/manifest.yaml)
   ```
   This queries autoskills `--list-tech`, reads `manifest.workspace_state.tech_stack[]`,
   maps package names to tech IDs (e.g. `@angular/core` → `angular`), and outputs
   comma-separated matching techs. If output contains "no matching techs" or starts
   with "[", skip `--tech` — autoskills installs universal skills only.

2. **Sync** — install framework skills for the resolved techs:
   ```bash
   <aidlc-python> aidlc-scripts/factory_skill_sync.py sync ${TECH:+--tech "$TECH"}
   ```
   Capture stdout → append `[Sync]` lines to audit.md under `[Skills]` prefix.
   On non-zero exit or Node.js missing: log warning, skip, continue. Skill sync
   never blocks build. If no `--tech` was passed, audit note:
   `[Skills] no matching techs — universal skills only`.

4. **Select** — resolve all installed skills for stage handoffs:
   ```bash
   <aidlc-python> aidlc-scripts/factory_skill_sync.py select --output json
   ```
   Parse JSON → store in `manifest.yaml`:
   - `skill_paths_resolved` — all discovered skill paths (unfiltered)
   - `framework_skill_names` — framework skill names for `skills_required[]` injection

   When building per-stage handoffs in Step B.1, include ONLY the subset of
   `skill_paths_resolved[]` that matches `skills_required[]` for that stage agent,
   PLUS any conditional skills from [`project-profile.md`](project-profile.md) §65-78.

5. **Log** to audit.md:
   ```
   [Skills] resolved <N> skills: <name-list>
   [Skills] warnings: <list or "none">
   ```
   **Honesty rule:** if `[Sync]` was skipped but select's `warnings[]` doesn't
   mention it, append:
   ```
   [Skills] WARN: sync was skipped — see [Sync] block above
   ```
   Never emit `[Skills] warnings: none` while a sync skip sits above it.

## Pre-Build Step 0.5 — Prepare Token Bridge

Runs ONCE before any unit is spawned, when `manifest.project_profile.ui == true`.

1. **Resolve output directory** — use the per-run tokens directory:
   ```bash
   TOKENS_DIR=".aidlc-orchestrator/runs/<run-id>/tokens"
   ```

2. **Run Token Bridge prepare** — generates `tokens.css`, auto-detects Tailwind,
   copies `token-prompt.md`, and detects brownfield sources:
   ```bash
   <aidlc-python> aidlc-scripts/factory_token_bridge.py prepare \
       --repo-root . \
       --output-dir "$TOKENS_DIR"
   ```
   The bridge handles these cases silently:
   - No `design-system/` exists → skip with warning (no tokens, no CSS)
   - Tailwind detected → also generates `tailwind.config.js`
   - Brownfield sources found → logs `design_system_source` in result JSON

3. **Store artifacts in manifest** — parse the JSON result and persist:
   ```bash
   <aidlc-python> aidlc-scripts/factory_run.py set <run-id> \
       --field token_bridge_result=<result-json>
   ```

4. **Log to audit.md:**
   ```
   [TokenBridge] Prepared <N> artifact(s): <type-list>
   [TokenBridge] Tailwind: <detected|not-detected>
   [TokenBridge] Design source: <brownfield|greenfield|figma|stitch|none>
   ```

5. **Fallback**: if `prepare` returns empty artifacts (no tokens dir), log a
   warning and continue — the build proceeds without token enforcement.
   Token Bridge failure never blocks a build.

## Pre-Build Step 0.6 — Cookbook context load

**Cookbook**: Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present. For each unit's code-generator input handoff, inject the context's `techStack[]` so the code-generator's `recommend_workflow` and `query_standard` calls filter patterns to the project's tech stack (e.g., Prisma-specific repository patterns vs sqlx). Log: `[Cookbook] Context injected into <N> unit handoffs` or `[Cookbook] No context file found — tech stack filtering disabled`.

---

## Step A — Compute unit dependency waves

`factory_graph.py compute <run-id> --apply` (Kahn's algorithm over
`units_decomposed[].dependencies`; writes `manifest.unit_waves`,
`unit_wave_count`, `unit_max_parallelism`).

- Exit 1 (cycle) → log error, fall back to single sequential wave.
- No `unit-decomposer` output → synthesize `unit_waves: [["__monolith__"]]`.
- Validate against `shared/unit-graph.schema.json` (non-blocking warn only).

Emit `CONSTRUCTION - UNIT GRAPH` audit block. "Layer" = "wave".

## Step B — Per-layer execution

For each layer in order:

### B.1 — Sequential per-unit pre-flight (all before spawn)
1. **Budget gate**: `factory_run.py budget_gate <run-id> code-generator:<unit>`. Checks: ok / downshift / skip / halt.
2. Knowledge query: `mem_search` with unit tags; inject top-5 into `context_pointers[]`.
3. Build input handoff `code-generator.<unit>.input.yaml` (do **not** acquire locks yet):
   - Read `manifest.skill_paths_resolved` (full discovered set).
    - Apply conditional skill injection from [`project-profile.md`](project-profile.md) §65-78:
      read `manifest.project_profile`, add matching skills (e.g. `frontend-ui-engineering`,
      `unslop`, and `impeccable` when `ui: true`) to `skills_required[]`, resolve paths → merge into
      `skill_paths_resolved[]`.
    - **Framework skill injection**: add ALL entries from `manifest.framework_skill_names`
      to `skills_required[]` so framework skills (e.g. `react-best-practices`,
      `typescript-advanced-types`) are loaded by the code-generator.
    - **Cookbook integration**: when `architecture_cookbook_enabled` in manifest features
      is not explicitly `false` (defaults to `true`), add `ai-architecture-cookbook` to
      `skills_required[]` and merge its resolved path from `skill_paths_resolved[]`.
    - **Filter**: include only paths for skills referenced in `skills_required[]` plus
      context-enrichment skills (`codegraph-aware-exploration`, `context-engineering`).
      Discard paths for skills irrelevant to this stage.
    - **Inception plan tracking**: set `inception_plan_path` to
      `aidlc-docs/inception/plans/<run-id>-execution-plan.md` and set
      `inception_task_ids[]` to the list of task IDs from that plan whose `unit`
      field matches this unit (e.g. `["ING-T4", "ING-T5"]`). Parse the markdown
      task list — each task line has the form `- [ ] **<ID>** — <title>` with the
      unit either in a section header above it or inline as `(unit: <name>)`.
    - **Token Bridge artifacts**: when `manifest.project_profile.ui == true`, read
      `manifest.token_bridge_result.artifacts` and inject as `token_bridge_artifacts[]`
      in the handoff. This gives the code-generator direct paths to `tokens.css`,
      `tailwind.config.js` (if applicable), and `token-prompt.md`.
    - **Shared design mode** (set/refresh in B.1.7 after `check-shared`):
      `shared_design_mode: write` only on the seed unit when shared docs are
      missing; `shared_design_mode: skip` on every other unit. Never leave this
      ambiguous for multi-unit Construction — missing field invites re-analysis.
    - Validate against JSON Schema contract (`code-generator.input.v1.json`).

Candidate set = units that passed budget + handoff build.

### B.1.5 — Wave collision pre-flight (candidate set ≥ 2 only) — BEFORE lock acquire
`factory_conflict.py check-wave <run-id> --wave-idx <N>`. `safe: true` → continue.
`safe: false` → drop colliding units to next wave (do **not** acquire locks for dropped
units). If wave empties → halt.

### B.1.6 — Lock acquire + AST snapshot (active set only, after check-wave)
For each unit remaining in the wave:
1. Lock acquire: `factory_conflict.py acquire <run-id> code-generator:<unit> <locks>`.
   Default: `src/<unit>/**`, `tests/<unit>/**`. exit 1 = drop unit to next wave and
   `release` any partial acquire for that unit.
2. AST snapshot (Python): `factory_conflict.py snapshot <run-id> code-generator:<unit> <files>`.

Active set = units that passed check-wave + acquire.

### B.1.7 — Shared design readiness (once per run, then skip forever)
```bash
<aidlc-python> aidlc-scripts/factory_design_gap.py check-shared <run-id>
```
- Exit 0 → set `shared_design_mode: skip` on **every** unit handoff in this wave
  (and all later waves). Units must **not** re-run Construction Design analysis.
- Exit 1 → shared design missing:
  1. Set `shared_design_mode: write` on **one** seed unit only (prefer wave[0] /
     foundation). Set `shared_design_mode: skip` on everyone else **but do not
     spawn them yet**.
  2. Spawn the seed alone until shared docs exist (`check-shared` exit 0).
  3. Then spawn the remaining active units in parallel, all with
     `shared_design_mode: skip`.
  Log: `[Wave] shared_design_seed=<unit> planned=<N> deferred_parallel=<N-1>`

**Invariant:** the five shared design docs are analyzed/written **at most once
per run**. Units 2..N never pay Sub-stage 2 wall-clock or tokens for re-analysis.

### B.2 — Code generator (three sub-stages, parallel per sub_stage)

> **ORCHESTRATOR RULE — DO NOT BYPASS THE PER-UNIT LOOP.**
> You MUST NOT tell the code-generator to "build", "generate code", or skip to implementation.
> Pass only the structured input handoff (unit_name + unit_spec_path + skills + context).
> The agent owns the loop sequence — your job is to relay handoffs and approval gates.
> Violations produce undocumented code with no design artifacts and no traceability.

**Context Injection (per unit, before each sub-stage)**:

For each unit, regenerate the context snapshot with `comprehensive` depth before building the input handoff:

```bash
<aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth comprehensive --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
```

**Depth**: `comprehensive` (~2000 tokens) — code-generator needs full timeline, handoff summaries, and all prior decisions to avoid contradicting earlier design.

Inject the snapshot into each unit's `code-generator.<unit>.input.yaml` under `context_snapshot:`. The code-generator MUST read this before planning to understand:
- What units have already been built (to avoid duplication)
- What decisions were made in requirements/design (to respect constraints)
- What skills are active (to apply correct patterns)

Code-generator runs `plan` → `generated` → `approved`. For each sub_stage:

**HARD RULE — instrumentation before/after every unit spawn (fail-closed):**
For **each** unit in the active set, BEFORE spawning the agent:
```bash
<aidlc-python> aidlc-scripts/factory_run.py stage-open --run-id <run-id> --stage code-generator --phase CONSTRUCTION --unit <unit> --field tokens_estimate=N
# keep returned ts per unit
<aidlc-python> aidlc-scripts/factory_progress.py begin --run-id <run-id> --stage code-generator --unit <unit>
```
AFTER the unit returns and the output handoff validates:
```bash
<aidlc-python> aidlc-scripts/factory_run.py stage-close --run-id <run-id> --stage code-generator --phase CONSTRUCTION --status <s> --ts-start <ts> --unit <unit> --from-handoff <output> --no-complete-stage
```
Do **not** Task/delegate a unit without a prior `stage-open --unit` for that unit.
Do **not** treat the wave as done until:
```bash
<aidlc-python> aidlc-scripts/factory_run.py check-spawns <run-id> --stage code-generator --require-closed
```
exit 0. Skipping open/close is what previously left audit truncated, units
`pending`, and progress missing while code still shipped.

**HARD RULE — wave fan-out is mandatory on EVERY platform when `|active set| > 1`:**
- You MUST emit **all** active-set code-generator spawns in **ONE** orchestrator
  message/turn. Cap ≤ 4 per batch; if more, batch then next batch.
- Platform spawn primitive (same rule, different verb):

  | Platform | Parallel wave primitive |
  |---|---|
  | Claude Code (`.claude/`) | multiple `Task(...)` in one message |
  | OpenCode (`.opencode/`) | multiple `Task(...)` in one message |
  | Cursor (`.cursor/`) | multiple `delegate` / subagent requests in one message |
  | Copilot CLI / harness (`.github/`) | multiple `task(...)` in one turn |
  | Codex (`.codex/`) | multiple subagent launches in one turn |
  | Frida / portable skill (`.frida/`) | same as host IDE; follow this table |

- Spawning one unit, waiting for completion, then spawning the next unit of the
  **same wave** is a Construction protocol violation unless B.1.7 forced a
  single shared-design seed. Hosts that can only do one spawn/turn (e.g. Copilot
  VS Code Local `agent`) must audit `mode=serial-cap1` and still process the wave
  without inventing false dependencies — prefer CLI/`task` when available.
- After the spawn turn, append audit:
  `[Wave] idx=<N> planned=<P> spawned_parallel=<M> mode=<parallel|seed-then-parallel|serial-cap1> platform=<id>`
  If `planned > 1` and `mode=serial` without a B.1.7 seed reason or documented
  `serial-cap1` host limit → **HALT** and re-issue the parallel spawn. Do not
  continue Construction pretending the wave ran in parallel.

1. Parallel `Task(subagent_type="code-generator", ...)` in ONE message (≤ 4).
2. Wait for all returns. Per-unit post-processing (any order):
    - **Validate output (strict)** — for every returned output handoff:
      ```bash
      <aidlc-python> aidlc-scripts/factory_validate.py \
          .aidlc-orchestrator/contracts/code-generator.output.v1.json \
          <output-handoff-path> --strict
      ```
       `--strict` is MANDATORY: it enforces that any non-fast_path output with
       `sub_stage` in {`plan`, `generated`} declares a `kind: plan` artifact AND
       that the plan file exists on disk, AND that at `sub_stage: generated` the
       plan file has ZERO remaining unchecked `[ ]` checkboxes. This catches both
       the silent-skip failure where an agent claims `generated` without writing
       the plan, and the partial failure where an agent leaves tasks incomplete.
       At `sub_stage: plan` the checkbox scan does NOT apply: the plan is awaiting
       the human approval gate, so every box is unchecked by design. On exit≠0: mark unit
       `blocked`, log stderr to audit.md, DO NOT advance the unit, surface BEFORE
       the gate.
     - AST drift check → budget deduct → knowledge save → **stage-close --unit**
       (not a bare "audit append" — close owns audit + timeline + unit status).
3. If AST drift conflict OR strict-validation failure written, surface BEFORE approval gate.
 4. **Approval gate (structured contract) — code-generator:**
    
    1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.code-generator.input.yaml` per unit:
       ```yaml
       stage: code-generator
       run_id: <run-id>
       title: "Code Generation — <unit-name> Approval"
       units:
         - label: "<unit-name>"
           tasks:
             - id: "GEN"
               description: "Generated code for <unit-name>"
               status: complete
       artifacts:
         - path: "src/<unit-name>/..."
           kind: source
           description: "Generated source files"
         - path: "tests/<unit-name>/..."
           kind: test
           description: "Generated tests"
       resolution:
         options: [approve, request_changes, cancel]
         note_prompt: "Describe what changes are needed"
       next_command:
         command: "/factory-build <run-id>"
         description: "Continue to build & test for this unit"
       context: "<AST drift check results + strict validation summary>"
       ```
    
    2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.
    
    3. **Surface** ALL units using the Structured Approval Format. **Explicitly ask the user for approval.** Do NOT proceed without an explicit approval signal. User can approve all, reject specific units (re-plan with revised context), or cancel layer.

### B.2.5 — Design artifact verification (BLOCKING — before B.3)

After code-generator returns `sub_stage: generated`, verify artifacts with the
shared+per-unit checker (not a per-unit rewrite ritual):

```bash
# Per unit (non-fast_path): shared design (once per run) + this unit's plan
<aidlc-python> aidlc-scripts/factory_design_gap.py check <run-id> --unit <unit-name>
```

Exit 0 → continue. Exit 1 → **HALT** with the script's `[DesignGap]` stderr and
the JSON `missing[]` list.

Semantics:
- The five shared design docs under `aidlc-docs/construction/design/<run-id>-*.md`
  are **run-scoped**. They must exist once; later units must REUSE them.
- The only mandatory **per-unit** design/plan artifact is
  `aidlc-docs/construction/plans/<run-id>-<unit-name>-code-generation-plan.md`.
- Do **not** fail a unit because it did not rewrite shared docs.

**Do NOT proceed to B.3 with missing shared design or missing unit plan.**

### B.3 — Build & test (parallel per unit, after all reach `approved`)

**Context Injection (per unit)**:

For each unit, regenerate the context snapshot:

```bash
<aidlc-python> aidlc-scripts/factory_context_builder.py <run-id> --depth comprehensive --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
```

**Depth**: `comprehensive` — build-test-agent needs full context to understand what was generated and what constraints apply.

Inject the snapshot into each unit's `build-test-agent.<unit>.input.yaml` under `context_snapshot:`.

**Changed-files injection (MANDATORY for subset tests):**
From `code-generator.<unit>.output.yaml`, copy `files_written[]` (fallback: `artifacts[].path`
where `kind` ∈ {source, test, config}) into `changed_files[]` on the build-test input
handoff. Do **not** rely on `git diff HEAD~1` during Construction — unit work is often
uncommitted and that filter silently expands to the full suite.

Same instrumentation HARD RULE as B.2 with `--stage build-test-agent --unit <unit>`
(open+begin before spawn; close after validate; `check-spawns --stage build-test-agent --require-closed` before the next wave).

Parallel `Task(subagent_type="build-test-agent", ...)` in ONE message (≤ 4) — same
wave fan-out HARD RULE as B.2 (`[Wave] ... build-test spawned_parallel=...`).
Build input handoffs per B.1 handoff guidelines (filter to BTA-relevant skills only).
If `manifest.project_profile.ui == true`: add `browser-testing-with-devtools` to
`skills_required[]` and set `design_system_path` from `manifest.project_profile.design_system_path`
(mirrors code-generator Step B.1 pattern — see [`project-profile.md`](project-profile.md) §65-78).

Per-unit post-processing same as B.2. Additionally verify the per-unit QA report:
`aidlc-docs/construction/qa-report/<run-id>-<unit-name>-qa-report.md` must exist and its
`## Build & Test Execution` section must be populated. Missing/empty → mark unit `blocked`,
log `[QAReport]` entry to audit.md, surface BEFORE the gate.

**Per-unit tests = affected subset.** Full regression suite is **not** required inside
each unit. After **all** units in the wave are build-test-approved (or after the final
Construction wave in Step C), run one full-suite build-test pass (or instruct a single
build-test-agent with `changed_files: []` / `test_scope: full`) and log
`[Wave] full_suite_after_wave=<N>` or `[Construction] full_suite_after_all_waves`.

**Approval gate (structured contract) — build-test-agent:**

1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.build-test.input.yaml` per unit:
   ```yaml
   stage: build-test-agent
   run_id: <run-id>
   title: "Build & Test — <unit-name> Approval"
   units:
     - label: "<unit-name>"
       tasks:
         - id: "BUILD"
           description: "Build and test completed for <unit-name>"
           status: complete
   artifacts:
     - path: "tests/<unit-name>/..."
       kind: test
       description: "Test results"
   resolution:
     options: [approve, request_changes, cancel]
     note_prompt: "Describe what changes are needed"
   next_command:
     command: "/factory-build <run-id>"
     description: "Continue to next layer or review"
   context: "<build_status> | <tests_passing>/<tests_total> tests | <coverage>% coverage"
   ```

2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.

3. **Surface** all summaries. **Explicitly ask the user for approval.** Do NOT proceed without an explicit approval signal.

### B.4 — Release locks (always — leaks block future runs)
```bash
<aidlc-python> aidlc-scripts/factory_conflict.py release <run-id> code-generator:<unit>
```

### B.5 — Per-unit commits (on explicit approval only)
After the build-test approval gate (B.3) accepts a unit:
```bash
git add -A && git commit -m "feat(<unit-name>): generate <unit> code"
git add -A && git commit -m "build(<unit-name>): complete build and test"
```
If any commit fails, log warning and continue.

For each approved unit, **record** `approval.output.yaml` with decision, timestamp, and commit_sha. Validate against `.aidlc-orchestrator/contracts/approval.output.v1.json`.

**If the user did not approve, do NOT run this step. Do NOT commit.**

## Step C — After all layers
- If no full-suite pass ran at end of the last wave, run it now and log
  `[Construction] full_suite_after_all_waves`.
- Set `Current Stage: CONSTRUCTION - Complete`.
- Present per-unit summary with key metrics (files changed, tests passing, coverage).
- Present the **literal next command** (substitute the actual run_id, never output `<run-id>` as placeholder text):
  ```
  Next command: /factory-review <run-id>
  ```
- Do NOT auto-execute `/factory-review`. Wait for the user to run it explicitly.

## Concurrency cap
Phase 5 honors cap of 4 (`unit_max_parallelism` from Step A is advisory upper
bound; never exceed 4). Batch >4 units within a layer; lock acquire+release per
batch. Cap is enforced by batching in B.2/B.3, not by serializing the whole wave.

---

## Hard rules

- Hard rules from the orchestrator apply.
- **NEVER bypass the per-unit loop.** The code-generator sub-stage sequence (Plan → Design → Code) is MANDATORY. Telling the agent to "build" or "generate code" directly skips hallucination prevention and produces undocumented code. This is a workflow violation.
- **Shared design is analyzed/written at most once per run.** Seed unit gets
  `shared_design_mode: write`; every later unit gets `skip` (Sub-stage 2 no-op).
  Rewriting or re-analyzing the five shared design docs on units 2..N is forbidden.
  B.1.7 / B.2.5 / `factory_design_gap.py` enforce this.
- **Wave fan-out is mandatory.** Same-wave units must spawn in one turn (≤ 4) unless B.1.7 seed applies. Serializing a parallel wave is a protocol violation.
- **Unit instrumentation is mandatory.** `stage-open --unit` + `progress begin --unit` before every Construction spawn; `stage-close --unit --ts-start` after; `check-spawns --require-closed` before the next wave. Skipping this truncates audit and leaves units `pending`.
- **Design artifacts are BLOCKING prerequisites for code.** Shared `aidlc-docs/construction/design/<run-id>-*.md` must exist before `sub_stage: generated` is accepted. B.2.5 enforces this.
- **Construction directories must exist before first unit spawns.** Entry Checkpoint Step 1 creates them — never skip it.
- **Conflict resolution (Phase 5)**: escalation-only. On path collision or interface drift, surface to user; user re-plans, manually merges, or cancels. Full protocol: see the orchestrator's conflict-resolver agent.
