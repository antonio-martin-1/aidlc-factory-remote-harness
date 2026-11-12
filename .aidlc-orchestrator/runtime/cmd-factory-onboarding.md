**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# `/factory-onboarding` — Guided System Tour

PRIORITY: P2

> **PRESENT THE FOLLOWING SECTIONS IN FULL TO THE USER.**
> Do not summarize. Do not assume the user has seen this before.
> Render every numbered section (1 through 9) as written, including code blocks
> and tables. After section 9 ("Self-hosting"), wait for the user to ask a
> follow-up question — do not auto-suggest a next command.

# 🏭 AIDLC Orchestrator — Onboarding

This guide walks through the multi-agent factory. If you just want to ship
code, start at step 1. Each section explains the *why* so you understand the
system.

---

## 1. How it works

Use `/factory-spec "<request>"`. A dedicated orchestrator agent spawns
specialized subagents (scout, analyst, code-gen, reviewer, etc.) per stage.

**When to use the orchestrator:**
- Multi-component features (several files, services, or modules)
- Brownfield work (needs reverse-engineering existing code)
- Runs where you want budget caps, crash recovery, or a parallel reviewer pool

---

## 2. Start a run

```
/factory-spec "add JWT auth to the API gateway"
```

The orchestrator:

1. **Triages** your request: TINY (Fast Path) or SMALL/MEDIUM/LARGE (full pipeline)
2. **Generates a run-id** like `2026-05-12T14-23-00Z-jwt-auth-api-gateway`
3. **Spawns workspace-scout** to learn your codebase
4. **Spawns requirements-analyst** to write a spec (may ask you questions)

At the end, you get a `run-id`. Keep it — you'll need it for subsequent commands.

**Fast Path (TINY):** if your request scores 0 complexity signals (e.g. "fix typo"),
the orchestrator goes directly to code-generator and commits. No multi-agent overhead.
You'll see: `🏎️ FAST_PATH completed | 1 file changed | 1 test | commit=abc123`

---

## 3. Inception passes — product → design → architecture

After `/factory-spec`, the run enters **extended Inception**: three mandatory
passes that run **in this order**. Each ends at a human approval gate, and
`/factory-plan` is **blocked** until all three are complete.

```
/factory-product-pass <run-id>   # 0.1 — WHAT & WHY
/factory-design-pass  <run-id>   # 0.2 — user-facing HOW (UX/UI)
/factory-arch-pass    <run-id>   # 0.3 — technical HOW (final gate)
```

| Pass | Command | Produces |
|------|---------|----------|
| **Product** (0.1) | `/factory-product-pass` | Product vision, personas, INVEST user stories |
| **Design** (0.2) | `/factory-design-pass` | UX flows (+ information architecture), UI component inventory, design-system mapping — **UX/UI only** |
| **Architecture** (0.3) | `/factory-arch-pass` | Validates product + design, then ADRs, tech stack, technical component map, service interfaces — **two-pass with a human validation gate; final Inception gate** |

**Why this order:** Product defines what you're building and why. Design defines
the user experience grounded in the product. Architecture runs **last** so it
can validate both before committing technical decisions (tech stack, endpoints,
data models). Design never decides endpoints or data models — those belong to
Architecture.

Each pass surfaces an approval prompt; approve to advance to the next. After
`/factory-arch-pass` is approved, Inception is complete and `/factory-plan`
unlocks.

---

## 4. Plan the work

With all three inception passes complete, you'll have a `run-id` and the full
product + design + architecture model.

```
/factory-plan <run-id>
```

This spawns:
- **workflow-planner** — designs the execution plan
- **unit-decomposer** — splits the work into parallel design units (for complex features)

You'll get a plan with units like `auth-middleware`, `token-verification`, `route-guards`.
Each unit is a chunk of work that can be code-gen'd in parallel.

> **Gate:** `/factory-plan` halts with a checklist if `product-pass`,
> `design-pass`, or `arch-pass` is missing from the run. Complete the missing
> pass(es) first.

---

## 5. Build

```
/factory-build <run-id>
```

This is the heavy lifter. It spawns **code-generator** × N units in parallel
waves, then **build-test-agent** × N to verify each one.

The orchestrator enforces:
- **File-glob locks** — two units writing to the same file must wait
- **AST drift detection** — if one unit changes a function another depends on,
  a conflict is flagged for human resolution
- **Budget gates** — pre-flight check before each spawn (ok / downshift / skip / halt)

---

## 6. Review

```
/factory-review <run-id>
```

Fans out 4 reviewers in parallel:
| Reviewer | Focus |
|----------|-------|
| code-quality | correctness, maintainability, readability, testing, design |
| security | OWASP top 10, CWEs, secrets, auth logic |
| performance | Big-O, N+1 queries, caching, bottlenecks |
| simplifier | dead code, over-engineering, unnecessary abstraction |

Results are merged into `aidlc-docs/construction/reviews/<run-id>-review-report.md`.

---

## 7. Ship

```
/factory-ship <run-id>
```

Final stage: release notes, ADRs, CHANGELOG update, CI/CD wiring suggestions.

---

## 8. If something goes wrong

| Situation | Command |
|-----------|---------|
| Run crashed mid-stage | `/factory-resume <run-id>` |
| Stage produced wrong output | `/factory-replay <run-id> --from <stage>` |
| Stale locks from dead agent | `<aidlc-python> aidlc-scripts/factory_conflict.py release <run-id> --stale --older-than 120` |
| Need to see what happened | `<aidlc-python> aidlc-scripts/factory_run.py graph <run-id>` |
| Model assignment wrong | Edit `.aidlc-orchestrator/budgets/default.yaml` per-stage `model` fields |

If a stage returns `needs_human`, the orchestrator pauses and presents a
structured approval prompt:

```
⏸️  Approval — <Stage>
  [Approve] [Request Changes] [Cancel Layer]
```

You review, decide, and the orchestration continues.

---

## 9. Self-hosting

Want to improve the orchestrator itself? Use:

```
/factory-self "add --stale flag to factory_conflict.py release"
```

This runs the full pipeline against `aidlc-scripts/`, the tool's agents directory, and
`tests/` — the orchestrator building itself.

---

## Reference

- `/factory-state <run-id>` — current stage, next step, budget, timeline
- `/factory-help` — quick command reference
- `docs/TROUBLESHOOTING.md` — failure modes and fixes
- `.aidlc-orchestrator/contracts/REFERENCE.md` — all handoff schemas
- `ORCHESTRATOR-PLAN.md` — design rationale, phase plan, acceptance criteria
