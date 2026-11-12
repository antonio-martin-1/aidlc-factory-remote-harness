**Python and shell bootstrap:** Before the first command, read `.aidlc-orchestrator/runtime/common/python-runtime.md`. Expand `<aidlc-python>` for the actual shell; translate POSIX shell examples before running them in PowerShell/cmd.

# Project-Profile Classification & Reverse-Engineer Routing

PRIORITY: P3

Orchestrator runtime spec for **Step 3.5** of `/factory-spec`. Runs after `workspace-scout` completes, before any further stage spawns. Both decisions read from `workspace-scout.output.yaml`.

## A. Classify `project_profile` (Bug #8 fix — gates conditional-skill loading)

Read `workspace-scout.output.yaml.workspace_state` and the original `user_request`. Apply each flag independently:

**`ui = true` iff** EITHER:
- `workspace_state.programming_languages` contains `TypeScript|JavaScript|TSX|JSX` AND `workspace_state.project_structure` matches `/SPA|frontend|React|Vue|Svelte|Angular|Next|Nuxt|web/i`, OR
- the workspace's `package.json` declares a UI framework dependency (`react`/`vue`/`svelte`/etc.)

**`ui` is `false` if** the only detected UI framework dependency is `react-native` without `react-dom`
(mobile-only React → no web design system needed).

**`api = true` iff** EITHER:
- the user_request matches `/endpoint|route|REST|GraphQL|API|webhook|\/[a-z][a-z0-9_-]+/i`, OR
- the workspace has `express`/`fastify`/`hono`/`nestjs`/`fastapi`/`flask`/`django` in `package.json`/`pyproject.toml`/etc.

**`has_legacy = true` iff** EITHER:
- `workspace_state.reverse_engineering_artifacts_present == true`, OR
- the user_request matches `/migrat|refactor|deprecat|legacy|rewrite|port/i`

**`framework`** — when `ui: true`, detect from `workspace_state.tech_stack[]`:
1. Scan `tech_stack[]` entries for known UI framework packages:
   - `react`, `next` → `react`
   - `@angular/core`, `angular` → `angular`
   - `vue`, `nuxt` → `vue`
   - `svelte`, `sveltekit` → `svelte`
   - `flutter` (from `pubspec.yaml`) → `flutter`
2. If multiple detected: use the one with the most references, emit `[Orchestrator] Multiple frameworks detected, selected <framework> by majority`
3. If none found and `ui: true`: set `framework = "unknown"`
4. Set `framework = <detected>` in project_profile (informational — the LLM uses this in prompts, no adapter needed)

**`design_system_path`** — when `ui: true`:
1. Check if `design-system/` exists at repo root
2. If yes: set `design_system_path = "design-system/"`
3. If no:
   a. If brownfield (`workspace_state.project_type == brownfield`), first try
      to extract existing tokens:
      ```bash
      <aidlc-python> aidlc-scripts/factory_design_system_extract_brownfield.py \
          --repo-root . extract --source auto
      ```
      If extraction created `design-system/tokens/`, skip bootstrap.
   b. If no tokens exist yet, bootstrap a default DS:
      ```bash
      <aidlc-python> aidlc-scripts/factory_token_bridge.py bootstrap
      ```
   c. Set `design_system_path = "design-system/"`
   d. Log: `[Bootstrap] Created default design system at design-system/`
   e. Run Token Bridge prepare to generate tokens.css:
      ```bash
      <aidlc-python> aidlc-scripts/factory_token_bridge.py prepare \
          --output-dir design-system/tokens/
      ```
   f. Log: `[TokenBridge] Prepared tokens at design-system/tokens/tokens.css`
   g. After bootstrap, the system has full token enforcement, snap, and drift detection

**`has_figma_data`** — when `ui: true`:
1. Check if `figma/` directory exists OR any `*.figma.json` files exist in the workspace
2. Check `workspace-scout.output.yaml.workspace_state` for figma references in `project_structure`
3. If yes: set `has_figma_data = true`
4. If no: set `has_figma_data = false`

**Figma input snap** — when `has_figma_data == true`:
1. Run snap using V2 FigmaAdapter (replaces deprecated `factory_design_system_snap.py`):
   ```bash
   <aidlc-python> aidlc-scripts/harness_adapters/source/figma.py \
       --input figma/raw-data.json \
       --output figma/snapped.json
   ```
   The adapter handles Auto Layout detection, nearest-neighbor snapping,
   and archaeologist mode automatically.
2. Run Token Bridge prepare to regenerate tokens.css with brownfield data:
   ```bash
   <aidlc-python> aidlc-scripts/factory_token_bridge.py prepare \
       --output-dir .aidlc-orchestrator/runs/<run-id>/tokens
   ```
3. Set `figma_snapped_path = "figma/snapped.json"` in the code-generator input
4. The snap script reports `correction_count`. If >10 corrections, set flag
   `figma_archaeologist_mode: true` — triggers "Arqueólogo" fallback in
   `design-system-composer` skill §7.

**`has_stitch_data`** — when `ui: true`:
1. Check if `stitch/` directory exists OR any `*.stitch.json` files exist in the workspace
2. Check if `.stitch-project.json` exists (created by Stitch MCP workspace persistence)
3. Check `workspace-scout.output.yaml.workspace_state` for stitch references in `project_structure`
4. If yes: set `has_stitch_data = true`
5. If no: set `has_stitch_data = false`

**Stitch MCP setup** — when `has_stitch_data == true`:
1. Before code-generator runs, run health check:
   ```bash
   <aidlc-python> aidlc-scripts/factory_stitch_mcp.py doctor
   ```
2. If healthy, optionally fetch Stitch designs for pre-processing using V2
   StitchAdapter (replaces deprecated `factory_stitch_snap.py`):
   ```bash
   <aidlc-python> aidlc-scripts/harness_adapters/source/stitch.py \
       --input stitch/export.html \
       --output stitch/snapped.json
   ```
   The adapter handles HTML, CSS, and DESIGN.md files automatically.
3. Run Token Bridge prepare to regenerate tokens.css with stitch data:
   ```bash
   <aidlc-python> aidlc-scripts/factory_token_bridge.py prepare \
       --output-dir .aidlc-orchestrator/runs/<run-id>/tokens
   ```
4. Set `stitch_snapped_path = "stitch/snapped.json"` in the code-generator input
5. The snap script reports `correction_count`. If >10 corrections, set flag
   `stitch_archaeologist_mode: true` — triggers "Arqueólogo" fallback in
   `design-system-composer` skill §7 (same fallback as Figma).

**Inject into downstream handoffs:**
When building input handoffs for code-generator, reviewers, build-test-agent, and ship-agent, add:
- `framework` from the resolved value (when `ui: true`)
- `design_system_path` from the resolved value
- `token_bridge_artifacts[]` — array of token bridge outputs, each with `{type, path}`:
  - `{type: "css", path: "<output-dir>/tokens.css"}`
  - `{type: "tailwind", path: "<output-dir>/tailwind.config.js"}` (if Tailwind detected)
  - `{type: "prompt", path: "<output-dir>/token-prompt.md"}`
- `has_figma_data` from the resolved value
- `figma_snapped_path` when figma snapping ran
- `figma_archaeologist_mode` when >10 corrections
- `has_stitch_data` from the resolved value
- `stitch_snapped_path` when stitch snapping ran
- `stitch_archaeologist_mode` when >10 corrections
- `skills_required[]` adds `frontend-ui-engineering`, `design-system-composer`, `ui-constraint-validator`, `unslop`, AND `impeccable` when `ui: true`

**Persist:**
```bash
<aidlc-python> aidlc-scripts/factory_run.py set <run-id> \
    --field project_profile.ui=<true|false> \
    --field project_profile.api=<true|false> \
    --field project_profile.has_legacy=<true|false> \
    --field project_profile.framework=<detected|none> \
    --field project_profile.design_system_path=<design-system/ when ui:true else empty> \
    --field project_profile.token_bridge_artifacts=<json-array when ui:true else empty>
```

**Audit**: append a single bullet to the NEXT stage's audit block (NOT a standalone header):
`[Orchestrator] Classified project_profile: ui=<bool>, api=<bool>, has_legacy=<bool>, framework=<detected>, design_system_path=<path>, token_bridge_artifacts=<N>`

## Conditional-skill injection (downstream consumer)

When building input handoffs for `code-generator`, `build-test-agent`, and `ship-agent`, read `manifest.project_profile` and add to `skills_required[]`:

| Flag | Affected stage(s) | Skill to add |
|---|---|---|
| `ui: true` | `code-generator` | `frontend-ui-engineering` (generic patterns) |
| `ui: true` | `code-generator` | `design-system-composer` (design-system composition) |
| `ui: true` | `code-generator` | `ui-constraint-validator` |
| `ui: true` | `code-generator` | `unslop` (nine craft passes against design-direction.md) |
| `ui: true` | `code-generator` | `impeccable` (detector only; missing skill does not skip the bans) |
| `ui: true` | `reviewer-code` | `unslop`, `impeccable` (report tells; do not rewrite) |
| `ui: true` | `build-test-agent` | `browser-testing-with-devtools` |
| `api: true` | `code-generator` | `api-and-interface-design` |
| `has_legacy: true` | `ship-agent` | `deprecation-and-migration` |

Resolve the matching `SKILL.md` path and add to `skill_paths_resolved[]`. If the skill file isn't found, log `[Skill] MISSING: <name> (conditional)` and continue — the stage's rule file has an inline fallback.

## Framework-skill injection (downstream consumer)

After the conditional-skill injection above, inject ALL framework skills from
autoskills so stage agents load tech-stack-specific guidance (e.g.
`react-best-practices`, `typescript-advanced-types`) alongside process skills.

| Source | Stage(s) | How |
|---|---|---|
| `manifest.framework_skill_names[]` | `code-generator`, `reviewer-code`, `reviewer-security` | Add EVERY entry to `skills_required[]`. Paths resolved automatically from `manifest.skill_paths_resolved[]`. |

Framework skills are installed by `factory_skill_sync.py sync` in Pre-Build Step 0.
`factory_skill_sync.py select` emits `framework_skill_names[]` (deduplicated skill
names from `.agents/skills/`). The orchestrator stores this in `manifest.yaml`
alongside `skill_paths_resolved[]`.

- `reviewer-security` only injects skills with `security`, `auth`, or `hardening` in the name.
- All other stages get the full list.

## B. Reverse-engineer routing (Bug #9 fix)

**If** `workspace_state.next_phase == "reverse-engineering"` **AND** `workspace_state.reverse_engineering_artifacts_present == false` **→** surface the approval gate (do NOT silently skip):

```
⏸️  Reverse-Engineer Recommendation

Workspace Scout detected:
  - project_type: brownfield (existing code present)
  - reverse_engineering_artifacts_present: false

Running `reverse-engineer` first produces:
  - aidlc-docs/inception/reverse-engineering/<run-id>-business-overview.md  (MUST substitute actual run_id)
  - architecture.md, code-structure.md, api-docs.md, component-inventory.md
  - interaction-diagrams.md, tech-stack.md, dependencies.md

Recommended for: major refactors, new modules touching existing systems,
                 or any change where requirements-analyst would benefit from
                 codebase context.

Skip-OK for: small features (a single endpoint, a config change, doc-only).

Run reverse-engineer now? [Y/n]
```

Use `AskUserQuestion` with options:
- `"Run reverse-engineer first (recommended for big changes)"`
- `"Skip and go straight to requirements-analyst (OK for small features)"`

On user response, call `emit_audit_block` per [`audit-block.protocol.md` § reverse-engineer gate](../contracts/audit-block.protocol.md).

**On approve**: spawn `reverse-engineer` via shared spawn loop. On completion, append to `manifest.completed_stages[]`, set `current_stage: requirements-analyst`.

**On reject**: `factory_run.py set <run-id> --field skipped_stages='[..., "reverse-engineer"]'` (read-modify-write).

**Else** (greenfield, or brownfield-with-RE-artifacts already present): no prompt; proceed directly to Step 4.

## Why this is a separate runtime doc

Project-profile classification runs once per `/factory-spec` invocation (loaded on demand). This contrasts with `spawn-loop.md` which is **load-critical** — read on every spawn. Keeping cold paths in separate runtime files shrank unconditionally-loaded kernel context by ~78%.
