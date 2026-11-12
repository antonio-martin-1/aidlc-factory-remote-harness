---
name: codegraph-aware-exploration
description: When .codegraph/ exists in the workspace, prefer codegraph_* MCP tools over grep/glob/Read for any symbol lookup, call-graph traversal, or impact analysis. Universal skill — applies to every stage agent.
---

**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# Skill: codegraph-aware-exploration

## Purpose

Replace O(N) grep/glob/Read scans with O(1) graph queries when the project
has been indexed. Upstream benchmarks show 92% fewer tool calls and 71% faster
contextualization on real-world codebases.

## Process

### Step 1 — Detect

Check for `.codegraph/codegraph.db` at project root:

```bash
test -f .codegraph/codegraph.db && echo "indexed" || echo "not-indexed"
```

- **Not indexed** → log `[CodeGraph] not initialized — falling back to grep/Read` and STOP.
  The stage proceeds normally using grep/glob/Read. Do NOT fail.
- **Indexed** → log `[CodeGraph] active — routing symbol queries through graph`.
  Continue to Step 2.

Also check backend:
```bash
codegraph status --json 2>/dev/null | <aidlc-python> -c "import sys,json; s=json.load(sys.stdin); print(s.get('backend','unknown'))" 2>/dev/null
```
If backend is `wasm`: log `[CodeGraph] backend: wasm — 5x slower than native; prefer native install`.

### Step 2 — Route queries through the decision table

When CodeGraph is active, use the following routing for every lookup:

| Task | Tool |
|---|---|
| Find symbol X | `codegraph_search` with the symbol name |
| Where is X called? | `codegraph_callers` |
| What does X call? | `codegraph_callees` |
| What breaks if I change X? | `codegraph_impact` at depth 2 |
| Get source of X | `codegraph_node` |
| What files exist? | `codegraph_files` (limit depth to avoid context saturation; increase for specific subtrees as needed) |
| Summarize this codebase | `codegraph_context` — **SUBAGENT ONLY** — never call from main session |
| List packages indexed | `codegraph_status` |

Exceptions — still use Read for:
- Configuration files (`.env`, YAML/TOML config, Docker files)
- Build manifests (`package.json`, `Cargo.toml`, `go.mod`)
- READMEs and documentation files

### Step 2.5 — Tour Generation (invoked by `/factory-code-tour`)

When tour generation is requested, build a dependency-ordered learning sequence using the call graph — the same approach as Understand-Anything's `tour-builder` agent.

**T1 — Find entry points**

Search for root symbols using `codegraph_search` with terms: `main`, `app`, `index`, `init`, `run`, `start`, `cli`, `server`, `handler`, `router`.
Also use `codegraph_files` to locate files named `main.*`, `app.*`, `index.*`, `__main__.*`, `cli.*`.
Collect up to 10 candidate entry symbols. If none found, use the largest file by symbol count as root.

**T2 — Build call graph (depth ≤ 3)**

For each entry symbol call `codegraph_callees` (depth 1).
For each returned callee that is a project symbol (not stdlib/vendor), call `codegraph_callees` again.
Repeat one more level. Stop when the set exceeds 50 symbols or depth 3.
Track directed edges: `caller → [callees]`. Skip external dependencies (stdlib, node_modules, site-packages).

**T3 — Topological sort (Kahn's algorithm)**

1. Compute in-degree for every symbol: how many project symbols call it.
2. Seed queue with symbols whose in-degree is 0 (leaf utilities — nothing project-internal calls them).
3. Process queue: emit symbol, decrement in-degree of its callees, enqueue callees that reach 0.
4. Result: symbols ordered from "most fundamental" (no deps) → "entry points" (depend on everything).

**T4 — Group into layers**

Assign each symbol to a layer = its longest path distance from any leaf (BFS from leaves):
- **Layer 0** — leaf utilities: pure functions, helpers, config loaders, DB connectors
- **Layer 1** — modules that only call Layer 0
- **Layer 2+** — progressively higher-level orchestration
- **Top layer** — entry points and bootstrappers

**T5 — Emit the tour**

Present as ordered stops grouped by layer. Use `codegraph_node` to get a one-line description for each stop (docstring first line, or infer from symbol name + signature):

```
Tour — N layers, M stops

Layer 0 — Foundations (start here)
  1. utils/config.py::load()        — loads env config at boot
  2. utils/db.py::connect()         — initialises connection pool

Layer 1 — Core logic
  3. auth/tokens.py::sign()         — signs JWT with RS256
  4. auth/tokens.py::verify()       — verifies and decodes JWT

Layer 2 — Service layer
  5. services/auth.py::AuthService  — orchestrates login/logout flows

Layer 3 — Entry points (read last)
  6. api/routes.py::router          — registers all HTTP routes
  7. main.py::app                   — application bootstrap
```

**Fallback (CodeGraph not active):** skip Tour Generation entirely; the caller falls back to the manual key-flows description in Step 5.

### Step 3 — Audit entries

Every stage that runs with CodeGraph active MUST emit at least one `[CodeGraph]`
audit entry per stage. Minimum format:

```
[CodeGraph] active — queries: <N>, file_reads_avoided: <N>
```

For reverse-engineer, also emit per-artifact:
```
[CodeGraph] architecture.md — codegraph_context call replaced ~<N> file reads
```

### Step 4 — Blast-radius gate (code-generator only)

When generating or modifying code, after `codegraph_impact`:
- Log: `[Impact] <symbol> → <callers_count> callers, <callees_count> callees`
- If `callers_count > 20`: set `status: needs_human` with reason
  `"high-blast-radius edit: <symbol> has <N> callers — needs human approval before proceeding"`

## Verification

- `audit_entries[]` contains at least one `[CodeGraph]` entry per stage when
  `.codegraph/codegraph.db` is present.
- `codegraph_context` is NEVER called from the orchestrator's main session —
  only from spawned stage subagents.
- When CodeGraph is absent, the stage completes normally (graceful degradation).

## Common Rationalizations (reject these)

| Rationalization | Correct response |
|---|---|
| "grep is faster for this one lookup" | Use codegraph_search — it is always faster when indexed |
| "I'll just read the file, it's only one" | codegraph_node returns the same content in one deterministic call |
| "codegraph_context might saturate the main session" | Correct — ONLY call it from a spawned subagent |
| "the index might be stale" | Log `[CodeGraph] sync recommended` and still use it — WAL mode allows concurrent reads |
| "I don't know if it's indexed" | Always check Step 1 first |

## Red Flags

- Calling `codegraph_context` from the orchestrator's main session → escalate to `needs_human`.
- Using `Glob` or `find` for symbol lookup when CodeGraph is active → log as `[Rationalization-rejected]`.
- Index appears stale (file watcher died, recent `git checkout`): log `[CodeGraph] index may be stale — run codegraph sync`.
