# Run Manager

PRIORITY: P3

`factory_run.py` — owns `runs/<run-id>/manifest.yaml` + `timeline.jsonl`.

| Call | Subcommand |
|---|---|
| Init | `init <run-id> --user-request <text> --project-slug <slug>` |
| Pre-spawn | `stage-open --run-id <run-id> --stage <s> --field tokens_estimate=N` |
| Post-spawn | `stage-close --run-id <run-id> --stage <s> --status <status> --from-handoff <path> --tokens N --tokens-in N --tokens-out N --wall-min F [--unit <unit>]` |
| Directories | `ensure-dirs --run-id <run-id> [--extra <path> ...]` |
| Path existence/type | `path-check <path> --type file [--soft]` (inspect JSON `ok` when soft) |
| Stage success/fail | `complete-stage` / `fail-stage <run-id> <stage> --reason <text>` |
| Resume | see [`runtime/cmd-factory-resume.md`](cmd-factory-resume.md) |
| Replay | see [`runtime/cmd-factory-replay.md`](cmd-factory-replay.md) |
| Non-spawn audit | `emit_audit_block --bullets-file <path>` — see [`audit-block.protocol.md`](../contracts/audit-block.protocol.md) |
| Context snapshot | `factory_context_builder.py <run-id> --depth <depth>` — see [`runtime/contextualization.md`](contextualization.md) |
| In-stage cursor | `factory_progress.py begin`, `upsert`, `list`, `archive` — see [`runtime/progress-trace.md`](progress-trace.md) |
| Task, phase, and tokens | `factory_progress.py timings --run-id <run-id>` — wall clock, sum of attempts, and host token totals recorded at stage-close |

Use the shared Python launcher per `common/python-runtime.md`. Helpers print one
JSON object; check exit status before reading it. START is written at open and
COMPLETE contains all file/handoff bullets. Missing or malformed sources fail
before writes. `complete` advances the manifest, `failed` records failure, and
`needs_human` / `blocked` keep it pending. Completion never grants user approval.

Atomicity: manifest uses tmpfile+replace, timeline is append-only per line, and
audit writes are locked. There is no transaction spanning all three files.
Failed→skipped recovery: [`runtime/recovery.md`](recovery.md).
