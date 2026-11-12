from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SnapResult:
    """Result of snapping raw design data to canonical tokens."""
    snapped: dict[str, Any]
    corrections: list[dict]
    correction_count: int
    quality_score: float
    archaeologist_mode: bool


@dataclass
class SourceProfile:
    """Metadata about a design source's quality and structure."""
    source_type: str
    quality_score: float
    has_auto_layout: bool
    has_components: bool
    has_variables: bool
    archaeologist_recommended: bool
    warnings: list[str] = field(default_factory=list)
    formats: list[str] = field(default_factory=lambda: ["json"])


class DesignSourceAdapter(ABC):
    """Base class for all design source adapters.

    Each adapter knows how to:
      1. `fetch()` — retrieve raw design data from its source
      2. `snap()` — snap raw values to canonical design tokens
      3. `profile()` — score the quality of the source data
      4. `archaeologist()` — extract intent from chaotic data

    Subclasses live in harness_adapters/source/<name>.py.
    """

    def __init__(self, repo_root: str | Path | None = None):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()

    # ── Public API ───────────────────────────────────────────────────────

    @abstractmethod
    def fetch(self, source: str | Path | dict, **kwargs) -> dict[str, Any]:
        """Retrieve raw design data from the source.

        Args:
            source: URL, file path, or raw dict depending on adapter type.
            **kwargs: Adapter-specific options.

        Returns:
            Normalized raw data dict (before snapping).
        """
        ...

    @abstractmethod
    def snap(self, raw_data: dict[str, Any], **kwargs) -> SnapResult:
        """Snap raw design values to canonical design tokens.

        Args:
            raw_data: Output from fetch() or raw input.
            **kwargs: Override token sets, thresholds, etc.

        Returns:
            SnapResult with snapped data and correction log.
        """
        ...

    def profile(self, raw_data: dict[str, Any] | None = None) -> SourceProfile:
        """Score the quality of the source data.

        Evaluates structure, auto-layout usage, component instances,
        and variable usage. Returns a SourceProfile.

        Lower scores (< 0.4) suggest archaeologist mode.
        """
        profile = SourceProfile(
            source_type=self.__class__.__name__.replace("Adapter", "").lower(),
            quality_score=1.0,
            has_auto_layout=True,
            has_components=True,
            has_variables=True,
            archaeologist_recommended=False,
        )
        return profile

    @abstractmethod
    def archaeologist(self, raw_data: dict[str, Any], **kwargs) -> dict[str, Any]:
        """Extract usable intent from chaotic/low-quality data.

        Activated when score < 0.4 or explicitly requested.
        Strips positions, sizes, colors — keeps only text, inputs,
        and reading order.

        Returns a simplified SemanticIntent-compatible dict.
        """
        ...

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _nearest(value: float, candidates: list[int]) -> int:
        return min(candidates, key=lambda c: abs(c - value))

    @staticmethod
    def _parse_px(raw: str | float | int) -> float:
        if isinstance(raw, (int, float)):
            return float(raw)
        import re
        m = re.search(r"([-+]?\d*\.?\d+)", str(raw))
        return float(m.group(1)) if m else 0.0

    @staticmethod
    def _normalize_hex(hex_str: str) -> str:
        h = hex_str.strip().lower().lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return f"#{h}"

    @staticmethod
    def _hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
        h = hex_str.strip().lower().lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) != 6:
            return None
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except ValueError:
            return None

    @staticmethod
    def _color_distance(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
        return sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5
