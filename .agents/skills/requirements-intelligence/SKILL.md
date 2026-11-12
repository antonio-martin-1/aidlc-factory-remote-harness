---
name: requirements-intelligence
description: Adaptive elicitation engine for the Requirements Analyst stage. Routes between Socratic probing, pre-mortem, ambiguity detection, and assumption mining based on request signals. Enforces a coverage map (Purpose / Needs / Limits / Expectations / Context / Risks / Acceptance / Unknowns) so no axis goes unasked. Also used in a reduced "plan-stage pre-mortem" mode by workflow-planner.
---

# Requirements Intelligence

Adaptive elicitation skill that makes question generation deliberate. Routes
between four elicitation techniques based on signals from the user's request and
enforces a coverage map so the questions file always probes **purpose, needs,
limits, expectations, context, risks, acceptance, and unknowns** at the depth
the request warrants.

## Why this skill exists

Generic MCQs miss the real ambiguities. A user types
`"build a fast chat app with angular + socketio, no database"` and a naive
analyst asks "What database?" — wasting a question — instead of *"What does
'fast' mean? Latency target? Throughput? UX feel?"*.

This skill closes that gap by:

1. **Reading first.** The stage's embedded rule block must be quoted before any question is generated.
2. **Routing by signal.** Cheap techniques (ambiguity-detection, coverage-map)
   run at all depths; expensive ones (socratic, pre-mortem, assumption-mining)
   only when the signal warrants.
3. **Enforcing coverage.** Every axis required at the active depth gets ≥1
   question or generation halts.
4. **Surfacing assumptions** before they become spec bugs.

## Process (mandatory order)

### Step 1 — Read first, ask later

Before generating ANY question:

1. Read the `## Two-pass execution` block of the requirements-analyst stage
   definition (`.github/agents/stage/requirements-analyst.agent.md`, or the
   matching `.claude/`, `.cursor/`, `.opencode/` variant) — Steps 1–6 plus the
   embedded Depth Levels, Question Format, and Stage Conventions protocols.
   The upstream `aidlc-rules/` corpus is dev-only and is not shipped to target
   projects; this embedded block is the authoritative copy for the stage.
2. Read prior artifacts referenced by the stage input:
   workspace-scout output, reverse-engineering docs (brownfield), any pasted
   intent.
3. Quote ≥1 line from each prior artifact in `audit_entries[]` prefixed
   `[SkillRead]`. Format: `[SkillRead] <relative-path> L<n>: "<verbatim quote>"`.

**Rationalization to reject:** *"I already know roughly what to ask."* If you
have not quoted the embedded rule block, you do not.

### Step 2 — Classify signals (silent)

Score five axes from the request and prior context:

| Signal | Source | Values |
|---|---|---|
| `clarity` | `request_classification.clarity` (Step 2 of the embedded Two-pass execution protocol) | Clear / Vague / Incomplete |
| `risk` | reversibility × blast radius | low / medium / high |
| `novelty` | brownfield reuse (low) vs greenfield (high) | low / medium / high |
| `stakes` | request signal: prototype/internal/prod-grade | prototype / internal / prod |
| `ambiguity_count` | result of `ambiguity-detection.md` lexicon scan | integer ≥ 0 |

Emit one audit entry: `[SignalScore] {clarity, risk, novelty, stakes, ambiguity_count}`.

### Step 3 — Apply the routing policy

Routing matrix (full version in `questioning-policy.md`):

| Technique | Always at | Triggered by signal |
|---|---|---|
| coverage-map | all depths | always (axes required vary by depth) |
| ambiguity-detection | standard, comprehensive | `ambiguity_count ≥ 3` (even at minimal) |
| socratic | comprehensive | `clarity == Vague` at any depth |
| assumption-mining | comprehensive | `novelty == high` at any depth |
| pre-mortem | comprehensive | `stakes == prod` AND `risk ∈ {medium, high}` |

For each triggered technique, load its reference file from this skill folder
and follow its rubric. Do NOT load technique files that did not trigger —
deferred loading keeps token cost near zero in the common case.

Emit: `[Techniques] applied: [<list>]`.

### Step 4 — Build the coverage map

Load `coverage-map.md`. For each axis required at the active depth, mark which
generated question covers it. Emit the table to `audit_entries[]` prefixed
`[CoverageMap]`:

```markdown
| Axis | Required at | Question IDs | Status |
|---|---|---|---|---|
| Purpose | all | Q1 | covered |
| Needs | all | Q2, Q3 | covered |
| Limits | all | Q4 | covered |
| Expectations | all | Q5 | covered |
| Context | all | Q6 | covered |
| Risks | all | Q7 | covered |
| Acceptance | all | Q8 | covered |
| Unknowns | all | Q9 | covered |
```

If any axis required at the active depth is missing, STOP and add a question
before continuing. This is a hard gate.

### Step 5 — Apply techniques

For each triggered technique, follow its reference file:

- `ambiguity-detection.md` — scan for weasel words, convert each to a quantifier MCQ.
- `socratic.md` — why-chain up to L3 on the top stated goal.
- `pre-mortem.md` — generate ≥3 failure-mode questions across functional / operational / strategic categories.
- `assumption-mining.md` — list implicit assumptions, convert to confirm/reject MCQ.

Each technique outputs candidate questions tagged with the axis it covers.

### Step 6 — Merge, dedupe, budget

1. Deduplicate candidates that probe the same axis with overlapping intent — keep the most specific.
2. Order: Purpose → Needs → Expectations → Limits → Context → Risks → Acceptance → Unknowns.
3. Apply the depth budget:
   | Depth | Min Qs | Max Qs |
   |---|---|---|
   | minimal | 8 | 14 |
   | standard | 12 | 20 |
   | comprehensive | 18 | 30 |
4. Below min → escalate depth per questioning-policy.md (minimal→standard→comprehensive). Above max → drop lowest-priority candidates (Unknowns drops first, Purpose never drops).
5. Write to `aidlc-docs/inception/requirements/<run-id>-requirement-verification-questions.md`
   using the `[Answer]:` MCQ format from the embedded `#### Question Format Guide` in the stage agent.
   Every question MUST end with `X) Other (please describe after [Answer]: tag below)`.
6. **MANDATORY axis tag.** Each `## Question` MUST be immediately preceded by an HTML comment naming the coverage axis it probes:
   - Single-axis: `<!-- axis: Purpose -->`
   - Multi-axis (assumption-mining): `<!-- axis: Needs, Limits, Context -->`
   - Allowed values: `Purpose`, `Needs`, `Limits`, `Expectations`, `Context`, `Risks`, `Acceptance`, `Unknowns`.
   The post-stage content validator (`aidlc-scripts/factory_content_validate.py requirements <handoff>`) parses these tags to verify your `[CoverageMap]` claims. Untagged questions are invisible to it; a claim with no matching tag is a FAIL in strict mode (a WARN in soft-launch mode).

Emit: `[QuestionBudget] used/max: <n>/<max>`.

### Step 7 — Emit evidence

`audit_entries[]` MUST include all five:

1. `[SkillRead] <path> L<n>: "<quote>"` — at least one quote per prior artifact.
2. `[SignalScore] {clarity, risk, novelty, stakes, ambiguity_count}`.
3. `[Techniques] applied: [...]`.
4. `[CoverageMap]` table (markdown).
5. `[QuestionBudget] used/max: <n>/<max>`.

`skill_compliance[]` MUST include an entry for `requirements-intelligence`:

```yaml
- skill: requirements-intelligence
  status: PASS
  evidence: "axes covered: 8/8; techniques: [coverage-map, ambiguity-detection, socratic]; questions: 14/20; rule-block quoted: Two-pass execution (embedded)"
```

## Verification (objective gates)

| Check | How to verify |
|---|---|
| Embedded rule block was quoted | ≥1 `[SkillRead]` entry in `audit_entries[]` |
| Coverage map complete | all 8 axes show `status: covered` at any depth |
| No chat questions | zero `?` in the chat reply outside artifact paths |
| Ambiguity sweep performed | weasel words from `ambiguity-detection.md` lexicon either flagged or addressed |
| MCQ format respected | every question has ≥2 options plus `X) Other` |
| Budget respected | question count within the depth cap |

## Common rationalizations (REJECT)

| Rationalization | Reality |
|---|---|
| "The request is clear, no questions needed" | Even clear requests have implicit assumptions. Run ambiguity-detection first. If `ambiguity_count == 0` AND classification is `Trivial + Single File + Clear`, the existing rule allows skipping — but log the skip with evidence. |
| "I'll ask follow-up questions later in chat" | Forbidden by the embedded `#### Question Format Guide`. All questions live in the file. |
| "Coverage map is overkill for a small feature" | Even at `minimal` depth, all 8 axes are required. Use the Trivial+Clear+Single File skip path if eligible, or generate tighter questions instead of skipping axes. |
| "I already have enough context from workspace-scout" | Quote it. If you cannot quote, you do not have it. |
| "Pre-mortem only matters for big stuff" | Pre-mortem fires only at `comprehensive` depth with prod stakes. If you are there, it IS the big stuff. |

## Red flags (escalate)

If any fire, set output `status: needs_human` and add the red flag verbatim to
`audit_entries[]` prefixed `[RedFlag] requirements-intelligence:`:

- Request contradicts itself ("must support 1M users" + "no database" + "no caching").
- User refuses to answer a question on an axis required at the active depth.
- Ambiguity count exceeds 8 — the request is too vague for an MCQ file; needs conversational triage first.
- Pre-mortem surfaces a failure mode the stated requirements cannot prevent
  (e.g. "no data loss tolerance" + "no persistence specified").

## Plan-stage variant (workflow-planner mode)

When invoked by `workflow-planner` (not `requirements-analyst`):

- Only `pre-mortem.md` fires. Other techniques are skipped.
- The pre-mortem operates on the *plan*, not the request: "If this plan fails
  during construction, where will it break?"
- Output ≤3 plan-risk questions appended to the plan approval surface.
- Coverage map is not enforced (plan stage has its own structure).

## See also

- `coverage-map.md` — axis taxonomy + required-at-depth gates
- `questioning-policy.md` — full routing matrix
- `ambiguity-detection.md` — weasel-word lexicon + quantifier templates
- `socratic.md` — why-chain probing rubric
- `pre-mortem.md` — failure-mode generation rubric
- `assumption-mining.md` — implicit-assumption extraction rubric
- Stage agent `#### Question Format Guide` — MCQ format contract (embedded)
- Stage agent `#### Depth Levels Protocol` — depth model (embedded)
