---
name: ai-architecture-cookbook
description: Integrates the AI Architecture Cookbook (43 YAML standards) into AIDLC stages for pattern recommendation, checklist verification, and decision tree evaluation via MCP tools or inline YAML fallback.
stages: [workspace-scout, reverse-engineer, requirements-analyst, story-writer, workflow-planner, unit-decomposer, code-generator, reviewer-code, reviewer-security, reviewer-performance, ship-agent]
---

# AI Architecture Cookbook

Integrates 43 machine-readable architectural standards from the AI Architecture
Cookbook into AIDLC factory stages.

## Process (mandatory order)

### Step 0 — Detect MCP availability

The MCP server runs via npx (`@ai-architecture-cookbook/mcp-server`) whenever
the project's MCP config (`.mcp.json` etc.) includes the entry. Detection:

1. Check that `npx` is available on the system (`npx --version`)
2. Attempt one MCP tool call (e.g., `search_standards` with a broad query)
   - **Success** → flag MCP tools as available
   - **Failure** (timeout, npx not found, network error) → use YAML fallback

Log: `[Skill] ai-architecture-cookbook: MCP {detected|unavailable} — using {mcp|yaml-fallback}`

### Step 1 — Stage selection

Each stage maps to specific Cookbook tools:

| Stage | Primary Tool | When to Call | Budget |
|-------|-------------|--------------|--------|
| `workspace-scout` | `recommend_pattern_nl` | Pass project description as free text; let NLP extract domains and context | ≤ 2 calls |
| `reverse-engineer` | `search_standards` + `query_standard` | When brownfield and any domain detected in existing code patterns | ≤ 3 calls |
| `requirements-analyst` | `recommend_pattern_nl` or `recommend_workflow` | Pass user request as natural language to get recommendations + checklists | ≤ 3 calls |
| `story-writer` | `search_standards` | When stories reference architectural concerns (auth, API, compliance) | ≤ 2 calls |
| `workflow-planner` | `recommend_workflow` | Orchestrated validation + recommendation + cross-domain check | ≤ 3 calls |
| `unit-decomposer` | `get_decision_tree` | When decomposing into units that span different architectural domains | ≤ 2 calls |
| `code-generator` | `get_decision_tree` → `query_standard` → `get_checklist` | Before writing code in a relevant domain | ≤ 5 calls |
| `reviewer-code` | `get_checklist(severity: high)` | During five-axis review | ≤ 3 calls |
| `reviewer-security` | `get_checklist(severity: critical)` | During OWASP scan | ≤ 3 calls |
| `reviewer-performance` | `query_standard(performance-optimization)` | During hot-path analysis | ≤ 2 calls |
| `ship-agent` | `query_standard(compliance-data-privacy)` + `query_standard(secure-sdlc)` | During release notes compliance section | ≤ 3 calls |

**Total call budget across all stages per run:** ≤ 25 calls.

### Step 2 — Call the MCP tool

**Entry-point for recommendations (use this first):**

**recommend_pattern_nl** — Natural-language wrapper. The agent does NOT need to know the exact context keys.
```
Call MCP tool `recommend_pattern_nl` with:
- text: "Describe the project in plain language (e.g., 'Enterprise web app with auth, React frontend, PostgreSQL')"
- format: "human" | "machine" | "short"
- include_trace: true (optional)
```
The tool tokenizes the text, detects keywords, maps them to `context_inputs`, scores domains by tag relevance, and returns the top recommendations.

**recommend_workflow** — Orchestrated workflow (validation + recommendation + checklist + cross-domain check).
```
Call MCP tool `recommend_workflow` with:
- context: { projectName, summary, primaryGoals, scale, ... } (partial OK)
- mode: "quick" | "audit" | "scaffold"
- domains: [optional domain list]
- include_trace: true (optional)
- include_checklist: true (optional)
```
Even with incomplete context, this now returns a `mode: "discovery"` response with `suggested_domains` so the agent knows which inputs to ask for next.

**Lower-level tools (use after you know the domain):**

**search_standards:**
```
Call MCP tool `search_standards` with one of:
- query: "search terms"
- tags: ["tag1", "tag2"]
- categories: ["category-id"]
```

**get_decision_tree:**
```
Call MCP tool `get_decision_tree` with:
- domain: "domain-id"
```

**get_checklist:**
```
Call MCP tool `get_checklist` with:
- domain: "domain-id"
- severity: "critical" | "high" | "medium" | "low" (optional)
```

**query_standard:**
```
Call MCP tool `query_standard` with:
- domain: "domain-id"
- category: "category-id" (optional)
```

**Batch calls by domain when possible** — multiple domains in a single `get_checklist`
 or `recommend_pattern` call is cheaper than separate calls.

### Step 3 — Discovery Flow (when recommendations are empty)

If `recommend_pattern_nl` or `recommend_workflow` returns `mode: "discovery"` (no recommendations), the agent must **not** give up. Follow this recovery sequence:

1. **Inspect `suggested_domains`** — the response includes up to 6 domains with their `context_inputs` (name, type, description, required, default). Pick the most relevant ones.
2. **Call `get_decision_tree`** for each selected domain to see the exact inputs needed.
3. **Ask the user (or infer from the codebase) for the missing inputs.**
4. **Re-call `recommend_pattern` with the now-complete context** and the selected `domains`.

Example recovery:
```
First call: recommend_pattern_nl({ text: "build a web app" })
→ returns mode: "discovery", suggested_domains: [{ domain: "authentication", context_inputs: [...] }, ...]

Second call: get_decision_tree({ domain: "authentication" })
→ returns context_inputs: ["client_types", "needs_login", "security_level"]

Third call: recommend_pattern({
  context: { client_types: "web", needs_login: true, security_level: "medium" },
  domains: ["authentication"]
})
→ returns a concrete pattern recommendation
```

### Step 4 — Apply the result

- **Pattern recommendations** → include in code-generation plan output. Cite the
  Cookbook standard ID (e.g., `foundational/authentication/authentication.yaml`).
- **Decision trees** → evaluate context inputs against the tree. Log the matched
  node. If no match, use the fallback pattern.
- **Checklist items** → include in review reports with severity and Cookbook
  standard ID citations. Filter by severity (critical/high) for reviewers.
- **Standard details** → surface relevant implementation guidelines and anti-patterns.

**Empty recommendation:** if `recommend_pattern` returns no recommendations for
a domain, log `[Skill] ai-architecture-cookbook: no recommendation for <domain>` and
proceed without blocking. However, **always prefer `recommend_pattern_nl` first** —
it performs NLP discovery and rarely returns truly empty results.

### Step 5 — Audit entries

Emit at least one `[Skill]` audit entry per stage when Cookbook was consulted.
Format: `[Skill] ai-architecture-cookbook: <tool> called for <domain> — <result-summary>`

---

## When MCP is Unreachable

The MCP server is the primary and only supported data source — all 82 standards
are bundled inside the `@ai-architecture-cookbook/mcp-server` npm package. The
server runs via npx and caches locally after the first invocation, so it works
offline after initial use.

If the MCP call fails (network issue, npx not found, registry unreachable),
retry once after a short delay. If it still fails, skip the Cookbook call
for this stage — the standards data is not available locally.

**Audit entry on failure:** `[Skill] ai-architecture-cookbook: MCP call failed — <tool> skipped for <domain>`



## When NOT to Use (skip conditions)

Skip the Cookbook when:

- The task is a **trivial single-file change** (typo fix, config tweak, minor refactor)
- **No architectural decisions are involved** (e.g., updating docs, running tests)
- The MCP server is unreachable (retry once, then skip for this stage)
- The task has **already been verified** against Cookbook in a previous stage
- The stage agent's call budget is exhausted (≤ 5 calls per invocation per the budget column in Step 1)

**Defer to the stage agent's judgment:** if the cost of a Cookbook call exceeds
the value it provides for a trivial task, skip it.

---

## Standards Catalog (quick reference)

43 machine-readable YAML standards across 5 categories:

| Category | Count | Key domains |
|----------|-------|------------|
| Foundational | 11 | auth, api-design, error-handling, logging, data-persistence |
| Application Architecture | 9 | layered-architecture, service-architecture, DDD, state-management |
| Infrastructure | 7 | containerization, orchestration, ci-cd, IaC, cloud-architecture |
| Security & Quality | 10 | encryption, rate-limiting, testing-strategies, code-quality |
| Integration & Data | 6 | third-party-integration, webhooks, file-storage, search |

Each entry contains: patterns, anti-patterns, decision tree, checklist, examples,
prompt recipes, security hardening, compliance considerations.

---

## Verification (objective gates)

- [ ] `[Skill]` audit entry emitted for every stage that consulted Cookbook
- [ ] Call budget respected (≤ 5 per invocation, ≤ 25 per run)
- [ ] Empty MCP recommendation → logged, not blocking
- [ ] MCP unreachable → retry once, then skip gracefully (not crashed)
- [ ] Cookbook standard ID cited in code-generation plan or review report
- [ ] Checklist items filtered by severity for reviewer stages
- [ ] Skip conditions documented when Cookbook is explicitly not used

## Common Rationalizations (reject these)

- "The standard is too generic for this specific case" → Decision trees handle
  context-specific branching. Apply your context inputs before concluding.
- "I already know this pattern" → Cookbook provides anti-patterns and checklists
  that catch edge cases you might miss.
- "The MCP call might fail" → MCP caches locally after first npx invocation.
  Retry once on failure, then skip for this stage.
- "This task is too small" → Check the skip conditions in Step 1 before deciding.
  Single-file typos are valid skips. Feature work is not.
- "I'll batch later" → Batching by domain within one call is correct. Deferring
  to a later stage is NOT — each stage has its own call budget.

## Red Flags (escalate)

- **MCP server unreachable for 3+ consecutive calls** → report as `[Skill] ai-architecture-cookbook: MCP degraded — 3+ consecutive failures. Check npx/node setup.`
- **Recommendation contradicts another source** → log both recommendations and
  set `status: needs_human` with the conflict described.
- **Decision tree returns no match AND no fallback** → log the missing domain and
  proceed with minimal guidance.
- **Call budget exceeded** → log warning and skip remaining Cookbook calls for this stage.
- **Cross-domain mismatch** — if a recommendation references a domain that doesn't
  match the task context, log and skip. Use domain metadata to validate.
