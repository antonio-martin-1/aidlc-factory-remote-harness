---
name: library-docs-with-context7
description: When you need current API/SDK/framework/CLI documentation, query the Context7 MCP server first (resolve-library-id → query-docs / get-library-docs) before WebFetch, WebSearch, or relying on training-data recall. Universal skill — applies to every stage agent, every reviewer, and the main orchestrator session.
---

# Skill: library-docs-with-context7

## Purpose

Training data goes stale fast. Library APIs, SDK signatures, CLI flags, and
cloud-service configuration drift week-to-week. Context7 is a Model Context
Protocol server that returns current, version-aware documentation for ~10k
libraries and frameworks. When it is available, it is the cheapest correct
answer for any "what is the current shape of X" question. WebFetch and
WebSearch are slower, noisier, and reproduce upstream churn.

This skill exists because the Context7 MCP server's own `instructions` block is
session-level only — subagents spawned via `Task()` do not inherit it. Without
this skill, stage agents fall back to training-data recall and silently produce
deprecated code.

## Process

### Step 1 — Detect availability

Context7 MCP tools appear with one of these prefixes depending on the host:

- Claude Code (project MCP):  `mcp__context7__*`
- Claude Code (plugin):       `mcp__plugin_context7_context7__*`
- Cursor / OpenCode / Copilot: tool-prefix varies; both tool names always end in `resolve-library-id` and `query-docs` (or `get-library-docs` in older builds)

Check at the start of any stage that may need library docs. If neither tool
is available, log `[Context7] unavailable — falling back to WebFetch/WebSearch`
and STOP this skill. Do not fail the stage.

### Step 2 — Route every library-doc question through Context7

Whenever the task requires **current** information about any of the categories
below, Context7 is the FIRST tool to try:

| Category                              | Examples                                      |
|---------------------------------------|-----------------------------------------------|
| Framework APIs                        | React hooks, Vue composables, Angular signals |
| SDK signatures                        | AWS SDK v3, Stripe Node SDK, OpenAI SDK       |
| CLI flag syntax                       | `gh`, `gcloud`, `aws`, `docker`, `kubectl`    |
| Cloud-service configuration           | Cloudflare Workers, Vercel, Supabase, Fly.io  |
| Library setup / quickstart            | Prisma init, Drizzle migrations, tRPC server  |
| Version migration                     | Next 14 → 15, React 18 → 19, Tailwind 3 → 4   |
| Library-specific debugging            | "Why does X throw Y when Z?"                  |

### Step 3 — Two-call protocol

Context7 always uses two calls:

1. **resolve-library-id** with the human library name
   - Input: `{"libraryName": "react"}` (or `"next.js"`, `"@aws-sdk/client-s3"`, etc.)
   - Output: a Context7-compatible ID like `/facebook/react` or `/vercel/next.js`
   - If multiple matches: pick the one whose trust score is highest AND whose
     `description` matches the user's intent. When ambiguous, ask the user
     which one to use rather than guessing.

2. **query-docs** (or **get-library-docs**) with the resolved ID
   - Input: `{"context7CompatibleLibraryID": "/facebook/react", "topic": "useEffect cleanup", "tokens": 5000}`
   - Use a focused `topic` — narrow topics return higher-quality docs than
     "everything about React"
   - Default `tokens: 5000`. Bump to 10000 only when the first call returns
     truncated content that is clearly insufficient.

### Step 4 — When NOT to use Context7

Do not use Context7 for:

- Your own codebase — use `codegraph_*` tools or Read instead
- Conceptual / general programming questions (algorithm design, data
  structures, language fundamentals)
- Internal/proprietary libraries (Context7 only indexes public docs)
- Debugging business logic — read the code, don't fetch docs
- Refactoring or code review of existing code — review what's there, don't
  fetch external docs

### Step 5 — Fallback order when Context7 is unavailable or returns nothing

1. Context7 (`resolve-library-id` → `query-docs`)
2. Official docs via WebFetch (only if you have a known URL)
3. WebSearch with the library name + version
4. Last resort: training-data recall, prefixed with the disclaimer
   `[Context7-unavailable] my training data may be stale; verify against docs.`

### Step 6 — Audit entry

When Context7 is invoked, emit one audit line per call:

```
[Context7] resolved <libraryName> → <libraryID>
[Context7] queried <libraryID> topic="<topic>" tokens=<N>
```

When skipped because the question doesn't qualify, no audit line is required.

## Verification

- For any stage output that cites a library API, SDK method, or CLI flag,
  at least one `[Context7]` audit entry SHOULD exist — unless the topic
  fits Step 4's "do not use" list.
- `query-docs` is never called without first calling `resolve-library-id`
  for that library in the same session.
- Subagents that need library docs invoke this skill instead of relying on
  the MCP server's session-level `instructions` block.

## Common Rationalizations (reject these)

| Rationalization | Correct response |
|-----------------|------------------|
| "I already know this API" | Your training cutoff was months ago — verify with Context7 |
| "It's faster to just write it from memory" | Stale code costs more later than one MCP call costs now |
| "WebSearch will work" | WebSearch returns noise; Context7 returns indexed, version-aware docs |
| "The MCP server's own instructions will tell the subagent" | They are session-level. Subagents do not inherit them. That's why this skill exists. |
| "Context7 might not be installed" | Step 1 already covers that — detect, then degrade gracefully |
| "I'll fetch the official docs page" | Only after Context7 fails — and only if you already have the URL |

## Red Flags

- Stage agent writes code against a library API without any `[Context7]` audit
  entry and without a Step-4 justification → likely using stale training data.
- Calling `query-docs` without first resolving the library ID → wrong protocol.
- Using Context7 to look up internal/proprietary code → category mismatch;
  use codegraph or Read.
- Bumping `tokens` to maximum on the first call → wasteful; narrow the `topic`
  instead.
