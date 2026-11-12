# Python runtime and shell protocol

Read this policy **before the first shell command** of any factory command or
stage, including validation and CodeGraph probes. Python >=3.10 is required by
the harness; the separately managed evaluator requires >=3.13.

## Workspace-local run state (all platforms)

Factory bookkeeping MUST stay inside the project workspace. This applies to
Linux, macOS, WSL and Windows, regardless of which shell runs a command.

- Keep the active `run_id` in orchestration context and pass its actual value
  explicitly to each subsequent tool call and stage handoff. Shell variables are
  local to a shell process; do not assume they survive another tool call.
- The existing `.aidlc-orchestrator/runs/<run-id>/manifest.yaml` is the persistent
  run record. Do not invent a second global "current run" file. Multiple runs
  can coexist; never choose the latest manifest as a substitute for the active ID.
- If a scratch file is necessary, use
  `.aidlc-orchestrator/runs/<run-id>/tmp/` (create it inside the workspace first).
  Use distinct filenames for concurrent stages. Resolve paths from the project
  root, not from the user's home directory or the shell's temporary directory.
- Do not store run IDs, command output, handoffs or context snapshots in `/tmp`,
  `/var/tmp`, `$TMPDIR`, `%TEMP%`, `$env:TEMP` or any other directory outside the
  workspace. In particular, never introduce `/tmp/aidlc_run_id.txt` or read it
  again to continue an existing run. Reuse the known ID from context/handoff or
  the explicitly selected run's manifest instead.
- For an interrupted run with a legacy external scratch file, recover the active
  ID from the conversation, supplied run argument or selected workspace manifest.
  If the active run is ambiguous, surface that ambiguity instead of silently
  switching runs or reading an external scratch file.
- Use the tool's working-directory option for the project root when available.
  Invoke state updates and context generation as separate tool calls, capturing
  each exit code. Do not append `| head` or `| Select-Object` before checking the
  Python command's status; those filters can hide the original failure.

These rules govern agent-authored bookkeeping commands, not dependency tools'
internal temporary files, explicitly requested external user inputs, or isolated
CI test fixtures. Do not broaden `external_directory` permissions to work around
an agent's choice of an external scratch file.

## Python launcher

`<aidlc-python>` in instructions is a command placeholder, **never literal shell
syntax**. From the project root, replace it with the launcher for the actual shell:

| Execution shell | Expansion of `<aidlc-python>` |
|---|---|
| Windows PowerShell 5.1 / PowerShell on Windows | `& ./aidlc-scripts/aidlc-python.ps1` |
| Windows cmd | `aidlc-scripts\aidlc-python.cmd` |
| Linux/macOS/WSL POSIX shell, or Git Bash | `sh ./aidlc-scripts/aidlc-python.sh` |

For example, `<aidlc-python> aidlc-scripts/factory_validate.py ...` becomes
`& ./aidlc-scripts/aidlc-python.ps1 aidlc-scripts/factory_validate.py ...`
in Windows PowerShell, or
`sh ./aidlc-scripts/aidlc-python.sh aidlc-scripts/factory_validate.py ...`
in Linux/macOS. Keep Python 3 as the language requirement; do not assume the
executable is named `python3` on Windows or `python` on Unix.

The launchers use only shell facilities and Python's standard library. They probe
with a five-second limit and select: explicit `AIDLC_PYTHON` executable path,
project `.venv`, active `VIRTUAL_ENV`, then platform defaults (Windows: `python`,
`py -3`, `python3`; Unix: `python3`, `python`). Invalid explicit overrides and
broken existing environments fail with a diagnostic; do not silently change
dependencies. No activation, global alias, package install or policy change is
required. WSL uses Linux paths; Git Bash is detected separately as MSYS/MINGW.

Run `<aidlc-python> --resolve` once per shell/project context when spawning
subagents. Pass the returned absolute executable as `AIDLC_PYTHON` in their
execution environment, or pass this policy and the launcher invocation if their
tool cannot set environment variables. Never store machine paths in distributed
prompts or manifests. Python subprocesses must use `sys.executable` and argument
lists. Use `<aidlc-python> -m pip` to manage that interpreter's dependencies.

## Translate the shell as well as the command

Code fences showing `$()` assignments, `command -v`, `/dev/null`, `find`, `head`,
`grep`, trailing `\`, `&&` or `${VAR:+...}` describe POSIX shell examples. They
are not portable PowerShell or cmd commands. Before execution:

- Prefer separate tool calls or one-line commands with explicit argument lists.
- PowerShell: assign `$value = & ./aidlc-scripts/aidlc-python.ps1 ...`; inspect
  `$LASTEXITCODE` immediately, use `if`, `Get-Command`, `Get-ChildItem` and
  `Select-Object`; discard output via `$null` and errors via `2>$null`.
- cmd: use its own conditionals and `NUL`, or invoke the native PowerShell launcher
  for Python. Do not send Bash assignments or continuations to cmd.
- For optional arguments, inspect the value and include each argument explicitly;
  never reuse `${VAR:+...}` in PowerShell. Never use `eval`/`Invoke-Expression`.
- Capture each exit code before another command overwrites it. A failed Python
  script is a script failure, not a reason to retry under a different interpreter.

If the launchers are missing, report an incomplete/outdated installation and
repair it through the installer; do not guess an interpreter for the first script.

## Portable factory helpers and audit text

Use `factory_run.py` helpers through the selected launcher on every platform:

```text
<aidlc-python> aidlc-scripts/factory_run.py ensure-dirs --run-id <run-id>
<aidlc-python> aidlc-scripts/factory_run.py path-check .codegraph/codegraph.db --type file --soft
<aidlc-python> aidlc-scripts/factory_run.py stage-open --run-id <run-id> --stage <stage>
<aidlc-python> aidlc-scripts/factory_run.py stage-close --run-id <run-id> --stage <stage> --status <status> --from-handoff <output-handoff-path>
```

Read JSON output directly in orchestration context, without shell pipelines or
command substitution. `path-check` exits 1 for absent/wrong-type paths; `--soft`
always exits 0, so inspect JSON `ok` / `results[]` for optional checks.

OpenCode may reject long commands or Unicode punctuation before the process runs.
Use short ASCII labels and metadata. Write long or Unicode audit bullets with
the file editing tool to `.aidlc-orchestrator/runs/<run-id>/tmp/<stage>-<evt>-bullets.txt`
and pass only its path as `--bullets-file`. Files accept UTF-8 with or without BOM;
`stage-close --from-handoff` reads every audit entry from the output YAML. Avoid
shell redirection/pipes to construct those files. Keep filenames distinct for
concurrent stages. See `spawn-loop.md` for lifecycle/state and approval semantics.
