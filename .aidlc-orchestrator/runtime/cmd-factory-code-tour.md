# `/factory-code-tour` — Dependency-Ordered Codebase Tour

PRIORITY: P2

Read-only. Never modify files or create commits.

## Step 1 — Profile

Ask in English, add "_(feel free to answer in your language — I'll continue in it)_". Use the reply language for the rest of the tour.

1. Role: developer / architect / PM / new hire / external contributor
2. Goal: understand the system / find where to add a feature / debug / onboarding

Adapt emphasis: PM → top-layer flows only; new hire → full tour + "why" per layer; architect → extension points.

If `--depth deep` skip question 2 and do full tour. Default: overview (top 3 layers, max 10 stops).

## Step 2 — Tour Generation

Run **Step 2.5 — Tour Generation** from `codegraph-aware-exploration` skill (T1→T2→T3→T4→T5).

**If CodeGraph unavailable:** use `Glob` + `Grep` to find entry files (`main.*`, `app.*`, `index.*`), trace 2-3 flows manually as linear chains, note `[CodeGraph] not available — run: codegraph init -i`.

## Step 3 — Output format

```
Tour — N layers, M stops

Layer 0 — Foundations (start here)
  1. utils/config.py::load()    — loads env config at boot
  2. utils/db.py::connect()     — initialises connection pool

Layer N — Entry points (read last)
  M. main.py::app               — application bootstrap
```

One-line description per stop from `codegraph_node` (docstring first line or infer from name).

## Step 4 — Close

Max 4 bullets: non-obvious conventions + one concrete next action per their role.

End with: _"Ask me to expand any stop or trace a specific flow."_

## Rules

- Only name symbols verified by `codegraph_search` or `codegraph_node`.
- `codegraph_explore` / `codegraph_context` → subagent only, never inline.
- Cycles in the call graph: pick the lower in-degree symbol as the earlier stop.
