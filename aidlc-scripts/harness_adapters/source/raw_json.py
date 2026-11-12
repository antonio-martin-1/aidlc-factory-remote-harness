from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .base import DesignSourceAdapter, SnapResult, SourceProfile


class RawJsonAdapter(DesignSourceAdapter):
    """Adapter for arbitrary JSON with design-related keys.

    Accepts any JSON object with keys like padding, margin, gap,
    cornerRadius, fontSize, color, etc. and snaps them to canonical
    design tokens using nearest-neighbor matching.

    Useful for:
      - Custom design export formats
      - Third-party APIs that return style objects
      - Ad-hoc JSON from manual input
    """

    DEFAULT_SPACING = [4, 8, 12, 16, 24, 32]
    DEFAULT_RADIUS = [0, 3, 6, 12, 9999]
    DEFAULT_FONT_SIZES = [12, 14, 16, 20, 24, 32, 40]

    STYLE_KEYS = {
        "padding": "spacing",
        "paddingLeft": "spacing",
        "paddingRight": "spacing",
        "paddingTop": "spacing",
        "paddingBottom": "spacing",
        "margin": "spacing",
        "marginLeft": "spacing",
        "marginRight": "spacing",
        "marginTop": "spacing",
        "marginBottom": "spacing",
        "gap": "spacing",
        "rowGap": "spacing",
        "columnGap": "spacing",
        "itemSpacing": "spacing",
        "spacing": "spacing",
        "cornerRadius": "radius",
        "borderRadius": "radius",
        "cornerSmoothing": "radius",
        "radius": "radius",
        "fontSize": "typography",
        "font-size": "typography",
        "textSize": "typography",
        "color": "color",
        "background": "color",
        "backgroundColor": "color",
        "background-color": "color",
        "borderColor": "color",
        "stroke": "color",
        "fill": "color",
        "strokeColor": "color",
        "fillColor": "color",
    }

    def __init__(
        self,
        repo_root: str | Path | None = None,
        spacing: list[int] | None = None,
        radius: list[int] | None = None,
        font_sizes: list[int] | None = None,
        color_map: dict[str, str] | None = None,
    ):
        super().__init__(repo_root)
        self.spacing = spacing or self.DEFAULT_SPACING[:]
        self.radius = radius or self.DEFAULT_RADIUS[:]
        self.font_sizes = font_sizes or self.DEFAULT_FONT_SIZES[:]
        self._color_map: dict[str, str] | None = color_map

    @property
    def color_map(self) -> dict[str, str]:
        if self._color_map is not None:
            return self._color_map
        self._color_map = self._load_color_map()
        return self._color_map

    def _load_color_map(self) -> dict[str, str]:
        color_file = self.repo_root / "design-system" / "tokens" / "color.md"
        if not color_file.exists():
            return {}
        color_map: dict[str, str] = {}
        for line in color_file.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*`([^`]+)`\s*\|\s*(#[0-9A-Fa-f]{3,8})\s*\|", line)
            if m:
                color_map[m.group(2)] = m.group(1)
        return color_map

    # ── Fetch ────────────────────────────────────────────────────────────

    def fetch(self, source: str | Path | dict, **kwargs) -> dict[str, Any]:
        if isinstance(source, dict):
            return source
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"JSON source not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    # ── Snap ─────────────────────────────────────────────────────────────

    def snap(self, raw_data: dict[str, Any], **kwargs) -> SnapResult:
        spacing = kwargs.get("spacing", self.spacing)
        radius = kwargs.get("radius", self.radius)
        font_sizes = kwargs.get("font_sizes", self.font_sizes)
        color_map = kwargs.get("color_map", self.color_map)

        if isinstance(raw_data, list):
            return self._snap_list(raw_data, spacing, radius, font_sizes, color_map)

        return self._snap_single(raw_data, spacing, radius, font_sizes, color_map)

    def _snap_list(
        self,
        items: list,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> SnapResult:
        corrections: list[dict] = []
        snapped_items: list = []

        for item in items:
            if isinstance(item, dict):
                snapped, item_corrections = self._snap_node(item, spacing, radius, font_sizes, color_map)
                snapped_items.append(snapped)
                corrections.extend(item_corrections)
            else:
                snapped_items.append(item)

        return SnapResult(
            snapped=snapped_items,
            corrections=corrections,
            correction_count=len(corrections),
            quality_score=self._score_data(corrections, items),
            archaeologist_mode=False,
        )

    def _snap_single(
        self,
        data: dict,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> SnapResult:
        snapped, corrections = self._snap_node(data, spacing, radius, font_sizes, color_map)

        return SnapResult(
            snapped=snapped,
            corrections=corrections,
            correction_count=len(corrections),
            quality_score=self._score_data(corrections, [data]),
            archaeologist_mode=False,
        )

    def _snap_node(
        self,
        data: dict,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> tuple[dict, list[dict]]:
        result = dict(data)
        corrections: list[dict] = []

        for key, value in list(data.items()):
            if not isinstance(value, (str, int, float)):
                continue
            key_lower = key.lower()
            category = self._find_category(key_lower)
            if not category:
                continue

            entry = self._snap_entry(key, str(value), spacing, radius, font_sizes, color_map)
            if entry["was_corrected"]:
                result[key] = entry["snapped"]
                corrections.append(entry)

        for key, value in data.items():
            if isinstance(value, dict):
                _, child_corrections = self._snap_node(value, spacing, radius, font_sizes, color_map)
                corrections.extend(child_corrections)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _, child_corrections = self._snap_node(item, spacing, radius, font_sizes, color_map)
                        corrections.extend(child_corrections)

        return result, corrections

    def _snap_entry(
        self,
        key: str,
        raw_value: str,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> dict:
        result = {
            "key": key,
            "raw": raw_value,
            "snapped": raw_value,
            "token_category": None,
            "was_corrected": False,
        }
        key_lower = key.lower()
        category = self._find_category(key_lower) or ""

        try:
            px = self._parse_px(raw_value)
        except (ValueError, TypeError):
            px = 0.0

        if category == "spacing" and spacing:
            snapped = self._nearest(px, spacing)
            result["snapped"] = f"{snapped}px"
            result["token_category"] = f"spacing.{self._spacing_key(snapped)}"
            if abs(snapped - px) > 0.01:
                result["was_corrected"] = True

        elif category == "radius" and radius:
            snapped = self._nearest(px, radius)
            val_str = "9999px" if snapped >= 9999 else f"{snapped}px"
            result["snapped"] = val_str
            result["token_category"] = f"radius.{self._radius_key(snapped)}"
            if abs(snapped - px) > 0.01:
                result["was_corrected"] = True

        elif category == "typography" and font_sizes:
            snapped = self._nearest(px, font_sizes)
            result["snapped"] = f"{snapped}px"
            result["token_category"] = f"font-size.{self._font_key(snapped)}"
            if abs(snapped - px) > 0.01:
                result["was_corrected"] = True

        elif category == "color" and color_map:
            snapped_token, _ = self._snap_color(raw_value.strip(), color_map)
            if snapped_token != raw_value.strip():
                result["snapped"] = snapped_token
                result["token_category"] = "color"
                result["was_corrected"] = True

        return result

    def _snap_color(self, raw: str, color_map: dict[str, str]) -> tuple[str, str | None]:
        normalized = self._normalize_hex(raw)
        for known_hex, token in color_map.items():
            if self._normalize_hex(known_hex) == normalized:
                return token, raw
        raw_rgb = self._hex_to_rgb(normalized)
        if raw_rgb:
            best_dist = float("inf")
            best_token = None
            for known_hex, token in color_map.items():
                known_rgb = self._hex_to_rgb(known_hex)
                if known_rgb:
                    dist = self._color_distance(raw_rgb, known_rgb)
                    if dist < best_dist:
                        best_dist = dist
                        best_token = token
            if best_token and best_dist < 60.0:
                return best_token, raw
        return raw, None

    # ── Profile ──────────────────────────────────────────────────────────

    def profile(self, raw_data: dict[str, Any] | None = None) -> SourceProfile:
        if raw_data is None:
            return SourceProfile(
                source_type="raw_json",
                quality_score=0.5,
                has_auto_layout=False,
                has_components=False,
                has_variables=False,
                archaeologist_recommended=True,
            )
        recognized = sum(1 for k in raw_data if k.lower() in self.STYLE_KEYS)
        score = min(1.0, recognized / max(len(self.STYLE_KEYS) * 0.1, 1))
        return SourceProfile(
            source_type="raw_json",
            quality_score=score,
            has_auto_layout=False,
            has_components=False,
            has_variables=False,
            archaeologist_recommended=score < 0.3,
        )

    # ── Archaeologist ────────────────────────────────────────────────────

    def archaeologist(self, raw_data: dict[str, Any], **kwargs) -> dict[str, Any]:
        return {
            "type": "archaeologist_output",
            "source": "raw_json",
            "content": [],
            "note": "Raw JSON archaeologist: no content extraction available",
        }

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _find_category(key_lower: str) -> str | None:
        for known_key, category in RawJsonAdapter.STYLE_KEYS.items():
            if key_lower == known_key.lower():
                return category
        return None

    @staticmethod
    def _score_data(corrections: list[dict], items: list) -> float:
        total_values = sum(len(i) for i in items if isinstance(i, dict))
        if total_values == 0:
            return 0.5
        ratio = 1.0 - (len(corrections) / total_values)
        return max(0.1, min(1.0, ratio))

    @staticmethod
    def _spacing_key(value: int) -> str:
        mapping = {4: "xs", 8: "sm", 12: "md", 16: "lg", 24: "xl", 32: "xxl"}
        return mapping.get(value, f"_{value}px")

    @staticmethod
    def _radius_key(value: int) -> str:
        mapping = {0: "none", 3: "sm", 6: "md", 12: "lg", 9999: "full"}
        return mapping.get(value, f"_{value}px")

    @staticmethod
    def _font_key(value: int) -> str:
        mapping = {12: "caption", 14: "body", 16: "body-large", 20: "h4",
                   24: "h3", 32: "h2", 40: "h1"}
        return mapping.get(value, f"_{value}px")
