"""Cursor executor — DOCUMENTED STUB.

This adapter satisfies the executor.v1.md interface shape, registers with
`registry.yaml`, and is discoverable by `install_aidlc.py --tool cursor`.

The actual Cursor subagent integration is **not yet implemented**. `spawn()`
raises `NotImplementedError` with a clear pointer to what's needed.

## Key difference from Claude Code

In Claude Code, the orchestrator uses `Task(subagent_type=<stage>)` — a
programmatic SDK primitive — to spawn stage agents. Cursor does not expose
an equivalent programmatic spawn API. Instead, stage agents are invoked via
Cursor's natural-language delegation: the orchestrator subagent tells Cursor
to "use the <stage-name> subagent" with the input handoff path as context.

This means the Python executor serves two purposes in Cursor:
  1. **Post-validation** — after the Cursor UI has run the stage agent and
     it has written its output handoff, this adapter validates the output.
  2. **Future programmatic integration** — if Cursor exposes a CLI or SDK
     for spawning subagents programmatically, implement `_invoke_cursor_task`
     below.

## Integration checklist

To complete this adapter:

1. When Cursor exposes a programmatic subagent API (CLI or SDK):
   - Import the Cursor SDK at the top of `_invoke_cursor_task`.
   - Submit a job referencing `.cursor/agents/stage/<stage_name>.md`.
   - Pass `input_handoff_path` as the agent's input context.
   - Honor `timeout_sec` per executor.v1.md §1.
   - Return the path to the produced output handoff.

2. Until programmatic spawn is available, use this adapter in
   **validation-only mode** — the orchestrator's `.cursor/agents/orchestrator.md`
   delegates to stage subagents via natural language, and this adapter
   validates their outputs after the fact.

3. Implement `cancel()` using the Cursor SDK's cancellation API when
   it becomes available.

4. Run `pytest tests/test_executor_conformance.py` — the suite is
   parameterized across registered executors. The Cursor rows will go
   from `skipped` to `passing` once `_invoke_cursor_task` is real.

Until step 4 is green, `health_check()` returns False so the orchestrator
falls back to the legacy single-agent flow instead of attempting spawns
that would fail.

## Cursor subagent paths

Stage agents live in `.cursor/agents/stage/<stage_name>.md`.
Cross-cutting agents live in `.cursor/agents/cross-cutting/<name>.md`.
The orchestrator lives in `.cursor/agents/orchestrator.md`.

These mirror the `.claude/agents/` structure with Cursor-specific frontmatter
(`model: inherit`, `readonly`, `is_background` fields) instead of Claude Code
frontmatter (`model: haiku/sonnet/opus`).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .base import (
    Capabilities,
    SpawnResult,
    StageExecutor,
    EXECUTOR_VERSION,
    IsolationMode,
    ExecutorUnavailableError,
)


class CursorExecutor(StageExecutor):
    """Adapter for Cursor's subagent spawn mechanism — STUB.

    In production, Cursor's orchestrator agent delegates to stage subagents
    via natural-language instructions in the Cursor UI. This Python adapter
    mirrors the post-delegation validation step so the conformance suite can
    exercise it and so a future programmatic Cursor API can call into the
    same logic.
    """

    name = "cursor"
    version = "0.1.0-stub"
    capabilities = Capabilities(
        max_concurrency=4,
        worktree_isolation=False,
        cancellation=False,
        target_tools=("cursor",),
        spec_version=EXECUTOR_VERSION,
    )

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def health_check(self) -> bool:
        """Returns False until `_invoke_cursor_task` is implemented.

        When the Cursor SDK exposes a programmatic subagent API, this should
        attempt a ping/version check and return True only on success.
        """
        return False

    def spawn(
        self,
        stage_name: str,
        input_handoff_path: Path,
        *,
        timeout_sec: Optional[int] = None,
        isolation: Optional[IsolationMode] = None,
    ) -> SpawnResult:
        start = time.monotonic()
        try:
            output_path = self._invoke_cursor_task(
                stage_name=stage_name,
                input_handoff_path=input_handoff_path,
                timeout_sec=timeout_sec,
                isolation=isolation,
            )
        except NotImplementedError as exc:
            return SpawnResult(
                status="unsupported",
                output_handoff_path=None,
                wall_clock_sec=time.monotonic() - start,
                error=str(exc),
            )

        err = self._validate_output_handoff(stage_name, output_path, self.repo_root)
        if err:
            return SpawnResult(
                status="failed",
                output_handoff_path=output_path,
                wall_clock_sec=time.monotonic() - start,
                error=err,
            )

        import yaml
        handoff = yaml.safe_load(output_path.read_text(encoding="utf-8")) or {}
        cost = handoff.get("cost") or {}
        return SpawnResult(
            status=handoff.get("status", "complete"),
            output_handoff_path=output_path,
            tokens_in=int(cost.get("tokens_in") or 0),
            tokens_out=int(cost.get("tokens_out") or 0),
            wall_clock_sec=time.monotonic() - start,
        )

    def validate_output(
        self,
        stage_name: str,
        output_handoff_path: Path,
    ) -> SpawnResult:
        """Validation-only mode for post-delegation use in Cursor UI flows.

        When the Cursor orchestrator has already delegated to a stage subagent
        via natural language, and the agent has written its output handoff, call
        this method to validate the output without re-spawning.

        This is the primary usage pattern until Cursor exposes a programmatic
        subagent API.
        """
        start = time.monotonic()
        err = self._validate_output_handoff(stage_name, output_handoff_path, self.repo_root)
        if err:
            return SpawnResult(
                status="failed",
                output_handoff_path=output_handoff_path,
                wall_clock_sec=time.monotonic() - start,
                error=err,
            )

        import yaml
        handoff = yaml.safe_load(output_handoff_path.read_text(encoding="utf-8")) or {}
        cost = handoff.get("cost") or {}
        return SpawnResult(
            status=handoff.get("status", "complete"),
            output_handoff_path=output_handoff_path,
            tokens_in=int(cost.get("tokens_in") or 0),
            tokens_out=int(cost.get("tokens_out") or 0),
            wall_clock_sec=time.monotonic() - start,
        )

    # -- internal --

    def _invoke_cursor_task(
        self,
        *,
        stage_name: str,
        input_handoff_path: Path,
        timeout_sec: Optional[int],
        isolation: Optional[IsolationMode],
    ) -> Path:
        """Implement this when Cursor exposes a programmatic subagent API.

        Expected behavior:
        1. Load the Cursor SDK client (or CLI wrapper).
        2. Submit a job referencing `.cursor/agents/stage/<stage_name>.md`
           (or the cross-cutting equivalent if stage is not in `stage/`).
        3. Pass `input_handoff_path` as the agent's input context.
        4. Honor `timeout_sec` per executor.v1.md §1.
        5. Return the path to the produced output handoff.

        Until implemented:
        """
        raise NotImplementedError(
            "CursorExecutor._invoke_cursor_task is a stub. "
            "Cursor does not yet expose a programmatic subagent API. "
            "Use the Cursor UI: the orchestrator subagent (.cursor/agents/orchestrator.md) "
            "delegates to stage agents via natural-language instructions. "
            "Use CursorExecutor.validate_output() after delegation to validate handoffs. "
            "See the module docstring of cursor_executor.py for the integration checklist."
        )
