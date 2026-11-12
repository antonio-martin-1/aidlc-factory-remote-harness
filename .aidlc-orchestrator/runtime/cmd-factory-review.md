**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-review` — Phase 1 review

PRIORITY: P2

Post-generation quality gate. **Parallel fan-out:** active reviewers in one
`Task()` batch (≤ 4 concurrent).

**1. Validate stage prerequisites (MANDATORY):**
   ```bash
   <aidlc-python> aidlc-scripts/stage_gate.py check <run-id> reviewer-code
   ```
   Exit 0 → continue. Exit 1 → **HALT**. Do NOT proceed.

   Also read `manifest.yaml`. Refuse if construction isn't complete.

1.5. **State update + audit (MANDATORY — do NOT skip):**

```bash
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id> --extra aidlc-docs/construction/reviews
```

Update `aidlc-docs/aidlc-state.md`:
- `Current Stage: REVIEW (in progress)`
- Add: `- [ ] Review — started <ISO date>`

Emit audit block:
Write `.aidlc-orchestrator/runs/<run-id>/tmp/reviewer-pool-start-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

- `[Orchestrator] Review phase started — active reviewers: <reviewer-list>`

```text
<aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt orchestrator_note --stage reviewer-pool --phase CONSTRUCTION --label "REVIEWER POOL PHASE START" --field summary="reviewer-pool start" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/reviewer-pool-start-bullets.txt
```

1.6. **Collect framework skills from build** (Pre-Review Step 0.5): read
`manifest.skill_paths` + all `code-generator.*.output.yaml` handoffs; extract
skills not in the base set. Store as `framework_skill_paths`. Log the list
even if empty.

1.75. **Build validation** (Pre-Review Step 0.75): detect build system, run
compile/check command, surface approval gate on failure. Skip if no build
system detected.

## Reviewer pool

| Reviewer | Stage ID | Skill | Active by default |
|---|---|---|---|
| Code quality | `reviewer-code` | code-review-and-quality | **Yes** |
| Security | `reviewer-security` | security-and-hardening | **Yes** |
| Performance | `reviewer-performance` | performance-optimization | No — `--full` only |
| Simplifier | `reviewer-simplifier` | code-simplification | No — `--full` only |

All share `reviewer.input.v1.json` / `reviewer.output.v1.json`.

**Default active set**: `[reviewer-code, reviewer-security]` — covers the findings that block
shipping. Pass `/factory-review --full` to activate all four (adds performance + simplifier).

> **Model note:** `reviewer-security` runs on Sonnet. For high-stakes audits pass
> `/factory-review --model opus` to upgrade the security reviewer only.

> **Framework skills** propagation: after Pre-Build Step 0, autoskills (e.g., `angular-developer`,
> `typescript-advanced-types`) are stored in `manifest.skill_paths` (and in each
> `code-generator.*.output.yaml` under `skill_paths_resolved`). Pre-Review Step 0.5 collects
> them and injects them into `reviewer-code`'s input handoff so the code reviewer has the same
> framework context as the generator.

**Phase 4 acceptance**: review wall-clock should be ~`max(reviewer wall-clocks)`, not their sum. Track via `manifest.events[]` timestamps and reviewer `cost.wall_clock_min`.

## Flow

### Pre-Review Step 0 — CodeGraph symbol cache (skip if `.codegraph/codegraph.db` absent)

Run inline in the orchestrator before spawning any reviewers. Goal: compute callers + impact
for every symbol in the generated unit ONCE, share the result via a cache file so reviewers
never duplicate these queries.

1. Collect `source_paths[]`: read all `code-generator.output.yaml` handoffs for this run;
   extract `artifacts[].path` where `kind == "source"`.
2. For each unique parent directory in `source_paths[]`, call `codegraph_files <dir>` →
   accumulate all symbol names. Deduplicate. Cap at 60 symbols (prioritise exported/public ones
   if over cap — heuristic: no leading `_`, not `test_*`).
3. For each symbol (sequentially, batch of ≤ 60):
   - `codegraph_callers <symbol>` → record `caller_count` + caller list
   - `codegraph_impact <symbol> --depth 2` → record `blast_radius` + impact list
4. Write to `.aidlc-orchestrator/runs/<run-id>/codegraph-cache.json`:
   ```json
   {
     "generated_at": "<ISO8601>",
     "source_files": ["<path>", ...],
     "symbols": {
       "<symbol_name>": {
         "file": "<path>",
         "caller_count": 0,
         "callers": [],
         "blast_radius": 0,
         "impact": []
       }
     }
   }
   ```
5. Set `codegraph_cache_path: .aidlc-orchestrator/runs/<run-id>/codegraph-cache.json` in every
   reviewer's input handoff.

Log: `[CodeGraph] Pre-computed <N> symbols → codegraph-cache.json`

If any step fails (codegraph unavailable, timeout): write an empty cache
`{"symbols": {}}` and continue — reviewers fall back to live calls transparently.

### Pre-Review Step 0.5 — Collect framework skills from build

Run inline before building reviewer handoffs. Goal: propagate autoskill (framework) context
from the build phase into `reviewer-code` so it applies framework-specific idioms during review.

**Base skills** are defined by the union of workflow-required skills in
`aidlc-scripts/install_aidlc.py:WORKFLOW_REQUIRED_SKILLS` and `using-agent-skills`.
These are the universal process/quality skills that every agent should always load.
Everything else discovered by `select` is a **framework skill** (conditional, tech-stack-specific).

1. Read `manifest.yaml` → collect `skill_paths_resolved` map (all discovered skills).
2. Additionally, read all `code-generator.*.output.yaml` handoffs; union their `skill_paths_resolved[]`.
3. **Framework skills** = any skill NOT in the base set (from `WORKFLOW_REQUIRED_SKILLS`)
   whose SKILL.md exists on disk.
4. Store as `framework_skill_paths: {name: path, ...}` in the orchestrator's working state (not
   persisted to manifest — this is ephemeral per review run).
5. Log: `[Review] Framework skills from build: [<name>, ...]` (empty list is fine — log it anyway).

If no code-generator handoffs exist (review invoked without a prior build): `framework_skill_paths = {}`.

---

### Pre-Review Step 0.75 — Build Validation

Run inline before spawning reviewers. Goal: catch cross-unit integration issues
that per-unit builds (Step B.3 of `/factory-build`) may miss — the full merged
tree must still compile before quality review begins.

1. **Detect build system** — probe workspace root for known build files in this
   priority order. First match wins:

   | Detection file | Build command | Notes |
   |---|---|---|
   | `package.json` | `npm run build 2>&1` | Uses the `build` script. If `build` script missing, fall back to `npx tsc --noEmit 2>&1` if `typescript` in devDependencies; else skip (log WARN). |
   | `Cargo.toml` | `cargo check 2>&1` | Preferred over `cargo build` — faster, same correctness signal. |
   | `go.mod` | `go build ./... 2>&1` | |
   | `pyproject.toml` | `<aidlc-python> -m pip install -e .` | Install as a lightweight packaging gate. Inspect exit status before continuing. |
   | `Makefile` | `make build 2>&1 \|\| make all 2>&1 \|\| make 2>&1` | Tries `build` target first, then `all`, then default. |
   | `pom.xml` | `mvn compile -q 2>&1` | |
   | `build.gradle` | `gradle classes -q 2>&1` | |
   | `requirements.txt` | `<aidlc-python> -m py_compile $(find . -name '*.py' -not -path '*/\.*') 2>&1` | Pure-Python syntax check as a lightweight alternative. |

   If multiple build files exist, use the first match in this table order.
   If none found: log `[Build Validation] SKIPPED — no supported build system detected`
   and proceed (skip build check).

2. **Run build** — execute the detected command in the workspace root. Cap
   execution at 120 seconds (use `timeout 120` prefix). Capture exit code +
   merged stdout/stderr.

3. **On failure** (exit ≠ 0):
   ```
   [Build Validation] FAILED — <tool> exited <code>
   ```
   Append full output to `aidlc-docs/audit.md` under `[Build Validation] FAILED`.
   **Surface approval gate to user** with options:
   - `Abort review, return to /factory-build` — set `current_stage: CONSTRUCTION`,
     do NOT spawn reviewers.
   - `Proceed with review anyway` — log `[Build Validation] BYPASSED` to audit.

4. **On success** (exit = 0):
   a. Log `[Build Validation] OK — <tool> <command>` to audit.
   b. **Run tests** — detect the test runner from the build system and execute:
      - `npm test` (Node.js), `pytest` (Python), `cargo test` (Rust), `go test ./...` (Go)
      - Cap execution at 120 seconds.
      - Capture pass/fail counts.
   c. **On test failure**: log `[Build Validation] Tests FAILED — <N> passing, <N> failing` to audit.
      Append full test output. Surface same approval gate as build failure:
      `Abort review, return to /factory-build` or `Proceed with review anyway`.
   d. **On test success**: log `[Build Validation] Tests OK — <N> passing, 0 failing` to audit.

5. **Store result** in orchestrator working state as `build_validation:
   {status: "ok"|"failed"|"skipped", tool: "<name>", output: "<first-200-chars>"}`.

---

1. **Active set** — default `[reviewer-code, reviewer-security]`; use all four if `--full` flag set; constrain to `manifest.reviewer_pool[]` if set.
2. **Knowledge queries** (sequential): `mem_search` per reviewer with specific tags; inject top-5.
2.5. **Build reviewer input handoffs** — for each active reviewer:

    a. **Base** `skills_required`: reviewer's own base skill + `using-agent-skills` +
       `codegraph-aware-exploration`.

    b. **Conditional skills** (per [`project-profile.md`](project-profile.md) §65-78):
       - Read `manifest.project_profile`.
       - If `ui: true`, ALL 4 reviewers get `frontend-ui-engineering`, `design-system-composer`,
         and `ui-constraint-validator` added to `skills_required[]`.
       - If `ui: true`, `reviewer-code` also gets `unslop` and `impeccable`. Use them to
         compare the UI with `design-direction.md` and to run `npx impeccable detect`.
         Report tells. Do not rewrite the screen and do not run live, bolder, or overdrive.
       - Resolve matching SKILL.md paths → add to `skill_paths_resolved[]`.

    c. **Framework skills from build** (per Pre-Review Step 0.5 above):
       - `reviewer-code` **only**: append ALL keys from `framework_skill_paths` to
         `skills_required[]` and merge their paths into `skill_paths_resolved[]`.
       - `reviewer-security` **only**: append security-relevant framework skills (name contains
         `security`, `auth`, or `hardening`) from `framework_skill_paths`.
               - Other reviewers: base + conditional only (no framework skills).

     c1. **Cookbook integration**: when `architecture_cookbook_enabled` is not explicitly
        `false`, add `ai-architecture-cookbook` to `skills_required[]` for `reviewer-code`,
        `reviewer-security`, and `reviewer-performance`, and merge its resolved path
        into `skill_paths_resolved[]`.

    d. **Filter**: include ONLY paths for skills present in `skills_required[]`. Discard
       paths for irrelevant skills. Deduplicate if conditional + framework paths overlap.

    e. **Design system**: if `manifest.project_profile.ui == true` AND `manifest.project_profile.design_system_path`
       is set, inject `design_system_path` into ALL reviewer handoffs so each can run its axis-specific
       design system review checks.
3. **Parallel spawn** — ONE message, all `Task()` calls together. Wait for returns.
4. **Per-reviewer post-processing** (any order): validate → knowledge save → audit append.
5. **Merge**: `factory_merge_reviews.py <run-id> --reviewers <reviewer-names> --output aidlc-docs/construction/reviews/<run-id>-review-report.md` → review report.
   **Always pass `--output`** pointing at `aidlc-docs/construction/reviews/<run-id>-review-report.md` — the review report belongs to the Construction phase (it is the quality gate over generated code), NOT to `operations/`. The script default now also points here, but keep `--output` explicit so the location is unambiguous across all tools. This is the path the approval handoff (Step 6) and the pre-created folder (Step 1.5 `mkdir`) both expect.
   `--reviewers` takes the **`reviewer` field values**, not `stage_id` values:
   - `reviewer-code` → `code-quality`
   - `reviewer-security` → `security`
   - `reviewer-performance` → `performance`
   - `reviewer-simplifier` → `simplifier`
   Example: `factory_merge_reviews.py <run-id> --reviewers code-quality security --output aidlc-docs/construction/reviews/<run-id>-review-report.md`
 6. **Approval gate (structured contract)** — before presenting, build the approval handoff:

    1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.review.input.yaml`:
       ```yaml
       stage: reviewer-pool
       run_id: <run-id>
       title: "Review Report — Approval Gate"
       units:
         - label: "Code Quality"
           tasks:
             - id: "RQ"
               description: "Code quality review findings"
               status: complete
         - label: "Security"
           tasks:
             - id: "SEC"
               description: "Security review findings"
               status: complete
       artifacts:
         - path: "aidlc-docs/construction/reviews/<run-id>-review-report.md"
           kind: report
           description: "Merged review report with all findings"
       skill_compliance:
         - skill: "code-review-and-quality"
           status: "<PASS|FAIL>"
         - skill: "security-and-hardening"
           status: "<PASS|FAIL>"
       resolution:
         options: [approve, request_changes, cancel]
         note_prompt: "Describe fixes needed or approve to continue"
       next_command:
         command: "/factory-ship <run-id>"
         description: "Generate release notes and ship"
       context: "<review findings summary + severity breakdown>"
       ```
    
    2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.
    
    3. **Surface** the report using the Structured Approval Format. **Explicitly ask the user for approval.** Do NOT proceed without an explicit approval signal.

    On user response:
    - **Fixes requested** → suggest the user run `/factory-build <run-id>` for the affected
      units (code generation + build-test-agent with review findings as context). The build
      is a separate command — do NOT auto-execute it.

      After the user completes the re-build and comes back to `/factory-review`, the
      reviewers repeat against the fixed code. Log each iteration in audit.md:
      `[Review-Fix] iteration <N>: <build-status> | <review-findings-count>`.

      If `manifest.project_profile.ui == true` AND `design_system_path` is set, capture the
      rejection feedback as a design system antipattern before the fix loop:
      ```bash
      <aidlc-python> aidlc-scripts/factory_design_system_learn.py reject \
          --component <inferred-primitive> \
          --reason "<user feedback or reviewer finding>" \
          --source <primary-ui-file> \
          --run-id <run-id>
      ```
    - **Approved** → proceed to Step 7.

 7. **Auto-commit + present next**

    **On EXPLICIT user approval only:**
    ```bash
    git add -A && git commit -m "docs(review): complete review report"
    ```

    Update `aidlc-docs/aidlc-state.md`:
    - `Current Stage: REVIEW (complete)`
    - Mark: `[x] Review — <ISO date>`

    Emit audit block:
    Write `.aidlc-orchestrator/runs/<run-id>/tmp/reviewer-pool-complete-bullets.txt` as UTF-8 using the file editing tool, containing these bullets (one per line):

    - `[Orchestrator] Review complete — <N> findings (<N> critical, <N> high, <N> medium, <N> low)`

    ```text
    <aidlc-python> aidlc-scripts/factory_run.py emit_audit_block <run-id> --evt orchestrator_note --stage reviewer-pool --phase CONSTRUCTION --label "REVIEWER POOL PHASE COMPLETE" --field summary="reviewer-pool complete" --bullets-file .aidlc-orchestrator/runs/<run-id>/tmp/reviewer-pool-complete-bullets.txt
    ```

    2. **Record** `approval.output.yaml` with decision, timestamp, and commit_sha. Validate against `.aidlc-orchestrator/contracts/approval.output.v1.json`.

    **If the user did not approve, do NOT run this step. Do NOT commit.**

    Present completion with the **literal next command** (substitute the actual run_id, never output `<run-id>` as placeholder text):
    ```
    Run complete: <run-id>

    Next command: /factory-ship <run-id>
    ```
    Do NOT auto-execute `/factory-ship`.

---

## Hard rules

- Hard rules from the orchestrator apply.
- **Phase 4 acceptance**: review wall-clock should be ~`max(reviewer wall-clocks)`, not their sum. Track via `manifest.events[]` timestamps and reviewer `cost.wall_clock_min`.
