from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Relative import works when imported as a module; fallback for direct execution
try:
    from .base import DesignSourceAdapter, SnapResult, SourceProfile
except ImportError:
    from base import DesignSourceAdapter, SnapResult, SourceProfile


_INLINE_STYLE_RE = re.compile(r'style="([^"]*)"')
_CSS_DECL_RE = re.compile(r"([a-z-]+)\s*:\s*([^;{}]+)")
_DESIGN_MD_TOKEN_RE = re.compile(r"\|\s*`([^`]+)`\s*\|\s*`?([^`|\n]+)`?\s*\|")


class StitchAdapter(DesignSourceAdapter):
    """Adapter for Google Stitch design sources.

    Handles:
      - Stitch-generated HTML with inline styles
      - Stitch DESIGN.md (token definitions)
      - CSS files with declarations

    Snaps raw style values to canonical design tokens.
    """

    DEFAULT_SPACING = [4, 8, 12, 16, 24, 32]
    DEFAULT_RADIUS = [0, 3, 6, 12, 9999]
    DEFAULT_FONT_SIZES = [12, 14, 16, 20, 24, 32, 40]

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
            raise FileNotFoundError(f"Stitch source not found: {path}")
        content = path.read_text(encoding="utf-8")
        ext = path.suffix.lower()
        return {
            "_source_path": str(path),
            "_source_ext": ext,
            "_content": content,
            "_type": "html" if ext in (".html", ".htm") else "css" if ext == ".css" else "designmd",
        }

    # ── Snap ─────────────────────────────────────────────────────────────

    def snap(self, raw_data: dict[str, Any], **kwargs) -> SnapResult:
        spacing = kwargs.get("spacing", self.spacing)
        radius = kwargs.get("radius", self.radius)
        font_sizes = kwargs.get("font_sizes", self.font_sizes)
        color_map = kwargs.get("color_map", self.color_map)

        source_type = raw_data.get("_type", "html")
        content = raw_data.get("_content", "")

        if source_type == "designmd":
            return self._snap_designmd(content, spacing, radius, font_sizes, color_map)
        elif source_type == "css":
            return self._snap_css(content, spacing, radius, font_sizes, color_map)
        else:
            # Check if it has inline styles or is raw JSON
            if isinstance(raw_data, dict) and "padding" in raw_data or any(
                k in raw_data for k in ("padding", "margin", "gap", "cornerRadius")
            ):
                return self._snap_dict(raw_data, spacing, radius, font_sizes, color_map)
            return self._snap_html(content, spacing, radius, font_sizes, color_map)

    # ── HTML snapping ────────────────────────────────────────────────────

    def _snap_html(
        self,
        html: str,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> SnapResult:
        corrections: list[dict] = []

        def _replace_style(m: re.Match) -> str:
            style_block = m.group(1)
            new_decls: list[str] = []
            for decl in style_block.split(";"):
                decl = decl.strip()
                if not decl or ":" not in decl:
                    new_decls.append(decl)
                    continue
                key, val = decl.split(":", 1)
                snapped = self._snap_declaration(
                    key.strip(), val.strip(), spacing, radius, font_sizes, color_map
                )
                if snapped["was_corrected"]:
                    corrections.append(snapped)
                new_decls.append(f"{key.strip()}: {snapped['snapped']}")
            return f'style="{"; ".join(new_decls)}"'

        snapped_html = _INLINE_STYLE_RE.sub(_replace_style, html)

        return SnapResult(
            snapped={"html": snapped_html, "original_html": html},
            corrections=corrections,
            correction_count=len(corrections),
            quality_score=self._calculate_quality(html, spacing, radius, font_sizes, color_map),
            archaeologist_mode=False,
        )

    # ── CSS snapping ─────────────────────────────────────────────────────

    def _snap_css(
        self,
        css: str,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> SnapResult:
        corrections: list[dict] = []

        def _replace_decl(m: re.Match) -> str:
            key = m.group(1).strip()
            val = m.group(2).strip()
            snapped = self._snap_declaration(key, val, spacing, radius, font_sizes, color_map)
            if snapped["was_corrected"]:
                corrections.append(snapped)
            return f"{key}: {snapped['snapped']}"

        snapped_css = _CSS_DECL_RE.sub(_replace_decl, css)

        return SnapResult(
            snapped={"css": snapped_css, "original_css": css},
            corrections=corrections,
            correction_count=len(corrections),
            quality_score=1.0,
            archaeologist_mode=False,
        )

    # ── DESIGN.md snapping ───────────────────────────────────────────────

    def _snap_designmd(
        self,
        content: str,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> SnapResult:
        mapped: dict[str, list[dict]] = {"spacing": [], "radius": [], "typography": [], "color": []}
        unmapped: list[dict] = []
        corrections: list[dict] = []

        for line in content.splitlines():
            m = _DESIGN_MD_TOKEN_RE.search(line)
            if not m:
                continue
            token_name = m.group(1).strip()
            token_value = m.group(2).strip()
            key_lower = token_name.lower()

            if any(k in key_lower for k in ("padding", "margin", "gap", "spacing")):
                mapped["spacing"].append({"token": token_name, "value": token_value})
            elif any(k in key_lower for k in ("radius", "rounded", "corner")):
                mapped["radius"].append({"token": token_name, "value": token_value})
            elif any(k in key_lower for k in ("font", "size", "typography", "type")):
                mapped["typography"].append({"token": token_name, "value": token_value})
            elif any(k in key_lower for k in ("color", "fill", "stroke", "background")):
                mapped["color"].append({"token": token_name, "value": token_value})
            else:
                unmapped.append({"token": token_name, "value": token_value})

        written_files: list[str] = []
        for category, entries in mapped.items():
            if not entries:
                continue
            out_path = self.repo_root / "design-system" / "tokens" / f"stitch-{category}.md"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            lines = [
                f"# Stitch-imported tokens ({category})",
                f"# Imported at {datetime.now(timezone.utc).isoformat()}",
                "",
                "| Token | Value | Source |",
                "|-------|-------|--------|",
            ]
            for e in entries:
                lines.append(f"| `{e['token']}` | `{e['value']}` | Stitch import |")
            lines.append("")
            out_path.write_text("\n".join(lines), encoding="utf-8")
            written_files.append(str(out_path))

        return SnapResult(
            snapped={
                "mapped": {k: v for k, v in mapped.items() if v},
                "unmapped": unmapped,
                "written_files": written_files,
            },
            corrections=corrections,
            correction_count=len(corrections),
            quality_score=0.8 if mapped["color"] else 0.5,
            archaeologist_mode=False,
        )

    # ── Raw dict snapping ────────────────────────────────────────────────

    def _snap_dict(
        self,
        data: dict,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> SnapResult:
        corrections: list[dict] = []
        result = dict(data)

        for key in list(data.keys()):
            entry = self._snap_declaration(key, str(data[key]), spacing, radius, font_sizes, color_map)
            if entry["was_corrected"]:
                result[key] = entry["snapped"]
                corrections.append(entry)

        return SnapResult(
            snapped=result,
            corrections=corrections,
            correction_count=len(corrections),
            quality_score=1.0,
            archaeologist_mode=False,
        )

    # ── Declaration snap (shared) ────────────────────────────────────────

    def _snap_declaration(
        self,
        key: str,
        raw_value: str,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> dict:
        result = {
            "property": key,
            "raw": raw_value,
            "snapped": raw_value,
            "token_category": None,
            "was_corrected": False,
        }
        key_lower = key.lower()

        is_spacing = any(k in key_lower for k in ("padding", "margin", "gap", "inset"))
        is_radius = any(k in key_lower for k in ("radius", "rounded", "corner"))
        is_font_size = any(k in key_lower for k in ("font-size", "fontsize", "font_size"))
        is_color = any(k in key_lower for k in ("color", "background", "fill", "stroke", "border-color", "background-color"))

        try:
            px = self._parse_px(raw_value)
        except (ValueError, TypeError):
            px = 0.0

        if is_spacing and spacing:
            snapped = self._nearest(px, spacing)
            result["snapped"] = f"{snapped}px"
            result["token_category"] = f"spacing.{self._spacing_key(snapped)}"
            if abs(snapped - px) > 0.01:
                result["was_corrected"] = True

        elif is_radius and radius:
            snapped = self._nearest(px, radius)
            val_str = "9999px" if snapped >= 9999 else f"{snapped}px"
            result["snapped"] = val_str
            result["token_category"] = f"radius.{self._radius_key(snapped)}"
            if abs(snapped - px) > 0.01:
                result["was_corrected"] = True

        elif is_font_size and font_sizes:
            snapped = self._nearest(px, font_sizes)
            result["snapped"] = f"{snapped}px"
            result["token_category"] = f"font-size.{self._font_key(snapped)}"
            if abs(snapped - px) > 0.01:
                result["was_corrected"] = True

        elif is_color and color_map:
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
                source_type="stitch",
                quality_score=0.5,
                has_auto_layout=False,
                has_components=False,
                has_variables=False,
                archaeologist_recommended=True,
                warnings=["No data provided"],
            )
        source_type = raw_data.get("_type", "html")
        has_designmd = "designmd" in str(raw_data.get("_source_ext", ""))
        score = 0.9 if has_designmd else 0.5
        return SourceProfile(
            source_type="stitch",
            quality_score=score,
            has_auto_layout=False,
            has_components=True,
            has_variables=False,
            archaeologist_recommended=score < 0.4,
            warnings=[] if has_designmd else ["No DESIGN.md — reduced confidence"],
        )

    # ── Archaeologist ────────────────────────────────────────────────────

    def archaeologist(self, raw_data: dict[str, Any], **kwargs) -> dict[str, Any]:
        content = raw_data.get("_content", "")
        if not content:
            content = str(raw_data)
        texts: list[str] = []
        for text in re.findall(r">([^<]+)<", content):
            cleaned = text.strip()
            if cleaned and len(cleaned) > 2:
                texts.append(cleaned)
        return {
            "type": "archaeologist_output",
            "source": "stitch",
            "content": texts,
            "note": "Stitch archaeologist mode: extracted text content from HTML",
        }

    # ── Quality ──────────────────────────────────────────────────────────

    def _calculate_quality(
        self,
        html: str,
        spacing: list[int],
        radius: list[int],
        font_sizes: list[int],
        color_map: dict[str, str],
    ) -> float:
        inline_styles = _INLINE_STYLE_RE.findall(html)
        if not inline_styles:
            return 0.3
        raw_count = 0
        total = 0
        for block in inline_styles:
            for decl in block.split(";"):
                if ":" not in decl:
                    continue
                total += 1
                key, val = decl.split(":", 1)
                snapped = self._snap_declaration(
                    key.strip(), val.strip(), spacing, radius, font_sizes, color_map
                )
                if snapped["was_corrected"]:
                    raw_count += 1
        if total == 0:
            return 0.5
        ratio = 1.0 - (raw_count / total)
        return max(0.1, min(1.0, ratio))

    # ── Token key helpers ────────────────────────────────────────────────

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


# ── CLI ─────────────────────────────────────────────────────────────────────

def snap_file(input_path: str, output_path: str | None = None) -> dict:
    """Snap a Stitch HTML/CSS/DESIGN.md file to canonical design tokens."""
    from pathlib import Path
    adapter = StitchAdapter()
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
    parser = argparse.ArgumentParser(description="Snap Stitch HTML/CSS/DESIGN.md to design tokens")
    parser.add_argument("--input", required=True, help="Input Stitch file (HTML, CSS, or DESIGN.md)")
    parser.add_argument("--output", default=None, help="Output snapped JSON file")
    args = parser.parse_args()
    snap_file(args.input, args.output)
