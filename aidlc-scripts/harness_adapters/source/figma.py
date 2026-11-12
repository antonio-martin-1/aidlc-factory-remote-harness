from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# Relative import works when imported as a module; fallback for direct execution
try:
    from .base import DesignSourceAdapter, SnapResult, SourceProfile
except ImportError:
    from base import DesignSourceAdapter, SnapResult, SourceProfile

_COLOR_DISTANCE_THRESHOLD = 60.0

_AUTO_LAYOUT_KEYS = {"layoutMode", "primaryAxisAlignItems", "counterAxisAlignItems", "itemSpacing"}
_COMPONENT_KEYS = {"componentId", "componentProperties", "instanceId"}


class FigmaAdapter(DesignSourceAdapter):
    """Adapter for Figma design sources.

    Handles:
      - Figma JSON exports (node attributes from the REST API)
      - Figma Variables (via API or exported JSON)
      - Figma Component Sets (via API)

    Raw values are snapped to canonical design tokens using nearest-neighbor
    for spacing/radius/typography and hex mapping for colors.
    """

    DEFAULT_SPACING = [4, 8, 12, 16, 24, 32]
    DEFAULT_RADIUS = [0, 3, 6, 12, 9999]
    DEFAULT_FONT_SIZES = [12, 14, 16, 20, 24, 32, 40]

    STYLE_KEYS = [
        "paddingLeft", "paddingRight", "paddingTop", "paddingBottom",
        "padding", "itemSpacing", "gap",
        "marginLeft", "marginRight", "marginTop", "marginBottom",
        "cornerRadius", "borderRadius", "cornerSmoothing",
        "fontSize", "letterSpacing",
        "fills", "strokes", "background", "backgroundColor",
        "color", "borderColor", "strokeColor", "fillColor",
        "effects",
    ]

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

    # ── Color map loading ───────────────────────────────────────────────

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
            raise FileNotFoundError(f"Figma source not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    # ── Snap ─────────────────────────────────────────────────────────────

    def snap(self, raw_data: dict[str, Any], **kwargs) -> SnapResult:
        spacing = kwargs.get("spacing", self.spacing)
        radius = kwargs.get("radius", self.radius)
        font_sizes = kwargs.get("font_sizes", self.font_sizes)
        color_map = kwargs.get("color_map", self.color_map)

        if isinstance(raw_data, list):
            snapped_list: list[dict] = []
            all_corrections: list[dict] = []
            for item in raw_data:
                snapped, corrections = self._snap_node(item, spacing, radius, font_sizes, color_map)
                snapped_list.append(snapped)
                all_corrections.extend(corrections)
            result_data = snapped_list
        else:
            result_data, all_corrections = self._snap_node(raw_data, spacing, radius, font_sizes, color_map)

        quality = self._calculate_quality(raw_data)

        return SnapResult(
            snapped=result_data,
            corrections=all_corrections,
            correction_count=len(all_corrections),
            quality_score=quality,
            archaeologist_mode=quality < 0.4,
        )

    def _snap_node(
        self,
        node: dict,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> tuple[dict, list[dict]]:
        result = dict(node)
        corrections: list[dict] = []

        for key in self.STYLE_KEYS:
            if key not in node:
                continue
            entry = self._snap_value(key, node[key], spacing, radius, font_sizes, color_map)
            if entry["was_corrected"]:
                result[key] = entry["snapped"]
                corrections.append(entry)

        if "children" in node and isinstance(node["children"], list):
            result["children"] = []
            for child in node["children"]:
                child_result, child_corrections = self._snap_node(
                    child, spacing, radius, font_sizes, color_map
                )
                result["children"].append(child_result)
                corrections.extend(child_corrections)

        return result, corrections

    def _snap_value(
        self,
        key: str,
        raw_value: str | float | int,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> dict:
        result = {
            "key": key,
            "raw": str(raw_value),
            "snapped": str(raw_value),
            "token_category": None,
            "was_corrected": False,
        }
        key_lower = key.lower()

        is_spacing = any(k in key_lower for k in ("padding", "margin", "gap", "inset", "itemspacing"))
        is_radius = any(k in key_lower for k in ("radius", "rounded", "corner"))
        is_font_size = any(k in key_lower for k in ("font-size", "fontsize", "font_size"))
        is_color = any(k in key_lower for k in ("color", "background", "fill", "stroke", "border-color", "background-color"))

        try:
            px = self._parse_px(raw_value)
        except (ValueError, TypeError):
            px = 0.0

        if is_spacing and spacing:
            snapped = self._nearest(px, spacing)
            if abs(snapped - px) > 0.01:
                result["snapped"] = f"{snapped}px"
                result["token_category"] = f"spacing.{self._spacing_key(snapped, spacing)}"
                result["was_corrected"] = True
            else:
                result["snapped"] = f"{px:.0f}px" if px == int(px) else f"{px}px"
                result["token_category"] = f"spacing.{self._spacing_key(int(px), spacing)}"

        elif is_radius and radius:
            snapped = self._nearest(px, radius)
            val_str = "9999px" if snapped >= 9999 else f"{snapped}px"
            if abs(snapped - px) > 0.01:
                result["snapped"] = val_str
                result["token_category"] = f"radius.{self._radius_key(snapped, radius)}"
                result["was_corrected"] = True
            else:
                result["snapped"] = val_str
                result["token_category"] = f"radius.{self._radius_key(int(px), radius)}"

        elif is_font_size and font_sizes:
            snapped = self._nearest(px, font_sizes)
            if abs(snapped - px) > 0.01:
                result["snapped"] = f"{snapped}px"
                result["token_category"] = f"font-size.{self._font_key(snapped, font_sizes)}"
                result["was_corrected"] = True
            else:
                result["snapped"] = f"{px:.0f}px"
                result["token_category"] = f"font-size.{self._font_key(int(px), font_sizes)}"

        elif is_color and color_map:
            snapped_token, _ = self._snap_color(str(raw_value), color_map)
            if snapped_token != str(raw_value):
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
            if best_token and best_dist < _COLOR_DISTANCE_THRESHOLD:
                return best_token, raw
        return raw, None

    # ── Profile ──────────────────────────────────────────────────────────

    def profile(self, raw_data: dict[str, Any] | None = None) -> SourceProfile:
        if raw_data is None:
            return SourceProfile(
                source_type="figma",
                quality_score=0.5,
                has_auto_layout=False,
                has_components=False,
                has_variables=False,
                archaeologist_recommended=True,
                warnings=["No data provided — defaulting to conservative score"],
            )

        has_auto = self._check_auto_layout(raw_data)
        has_comps = self._check_components(raw_data)
        has_vars = self._check_variables(raw_data)
        warnings: list[str] = []

        score = 1.0
        if not has_auto:
            score -= 0.4
            warnings.append("No Auto Layout detected — archaeologist mode recommended")
        if not has_comps:
            score -= 0.2
            warnings.append("No component instances detected")
        if not has_vars:
            score -= 0.1
            warnings.append("No Figma Variables detected")

        score = max(0.0, min(1.0, score))

        return SourceProfile(
            source_type="figma",
            quality_score=score,
            has_auto_layout=has_auto,
            has_components=has_comps,
            has_variables=has_vars,
            archaeologist_recommended=score < 0.4,
            warnings=warnings,
        )

    @staticmethod
    def _check_auto_layout(node: dict) -> bool:
        if any(k in node for k in _AUTO_LAYOUT_KEYS):
            return True
        for child in node.get("children", []):
            if isinstance(child, dict) and FigmaAdapter._check_auto_layout(child):
                return True
        return False

    @staticmethod
    def _check_components(node: dict) -> bool:
        if any(k in node for k in _COMPONENT_KEYS):
            return True
        for child in node.get("children", []):
            if isinstance(child, dict) and FigmaAdapter._check_components(child):
                return True
        return False

    @staticmethod
    def _check_variables(node: dict) -> bool:
        if "boundVariables" in node and node["boundVariables"]:
            return True
        for child in node.get("children", []):
            if isinstance(child, dict) and FigmaAdapter._check_variables(child):
                return True
        return False

    def _calculate_quality(self, raw_data: dict[str, Any] | list) -> float:
        data = raw_data if isinstance(raw_data, dict) else raw_data[0] if raw_data else {}
        profile = self.profile(data)
        return profile.quality_score

    # ── Archaeologist ────────────────────────────────────────────────────

    def archaeologist(self, raw_data: dict[str, Any], **kwargs) -> dict[str, Any]:
        data = raw_data if isinstance(raw_data, dict) else raw_data
        extracted = self._extract_intent(data)
        return {
            "type": "archaeologist_output",
            "source": "figma",
            "content": extracted,
            "components": self._extract_components(data),
        }

    def _extract_intent(self, node: dict) -> list[dict]:
        items: list[dict] = []
        text = self._get_text(node)
        if text:
            items.append({
                "type": "text",
                "value": text,
                "y": node.get("y", 0),
                "x": node.get("x", 0),
            })
        placeholder = self._get_placeholder(node)
        if placeholder:
            items.append({
                "type": "input",
                "placeholder": placeholder,
                "y": node.get("y", 0),
                "x": node.get("x", 0),
            })
        for child in node.get("children", []):
            if isinstance(child, dict):
                items.extend(self._extract_intent(child))
        items.sort(key=lambda i: (i.get("y", 0), i.get("x", 0)))
        return items

    def _extract_components(self, node: dict) -> list[dict]:
        components: list[dict] = []
        comp_id = node.get("componentId") or node.get("instanceId")
        if comp_id:
            components.append({
                "id": comp_id,
                "name": node.get("name", ""),
                "type": node.get("type", ""),
            })
        for child in node.get("children", []):
            if isinstance(child, dict):
                components.extend(self._extract_components(child))
        return components

    @staticmethod
    def _get_text(node: dict) -> str:
        for key in ("characters", "text", "label", "name"):
            val = node.get(key)
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    @staticmethod
    def _get_placeholder(node: dict) -> str:
        for key in ("placeholder", "hint", "description"):
            val = node.get(key)
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    # ── Token key helpers ────────────────────────────────────────────────

    @staticmethod
    def _spacing_key(value: int, candidates: list[int]) -> str:
        mapping = {4: "xs", 8: "sm", 12: "md", 16: "lg", 24: "xl", 32: "xxl"}
        return mapping.get(value, f"_{value}px")

    @staticmethod
    def _radius_key(value: int, candidates: list[int]) -> str:
        mapping = {0: "none", 3: "sm", 6: "md", 12: "lg", 9999: "full"}
        return mapping.get(value, f"_{value}px")

    @staticmethod
    def _font_key(value: int, candidates: list[int]) -> str:
        mapping = {12: "caption", 14: "body", 16: "body-large", 20: "h4",
                   24: "h3", 32: "h2", 40: "h1"}
        return mapping.get(value, f"_{value}px")


# ── CLI ─────────────────────────────────────────────────────────────────────

def snap_file(input_path: str, output_path: str | None = None) -> dict:
    """Snap a Figma JSON file to canonical design tokens."""
    from pathlib import Path
    adapter = FigmaAdapter()
    raw = adapter.fetch(Path(input_path))
    result = adapter.snap(raw)
    if output_path:
        import json
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.snapped, indent=2), encoding="utf-8")
        print(f"Wrote {out} ({result.correction_count} corrections, score={result.quality_score:.2f})")
    return result.snapped


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Snap Figma JSON to design tokens")
    parser.add_argument("--input", required=True, help="Input Figma JSON file")
    parser.add_argument("--output", default=None, help="Output snapped JSON file")
    args = parser.parse_args()
    snap_file(args.input, args.output)
