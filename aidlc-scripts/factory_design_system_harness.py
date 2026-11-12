from __future__ import annotations

import sys
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# ── Public types ─────────────────────────────────────────────────────────────

@dataclass
class TokenSet:
    spacing: dict[str, int] = field(default_factory=dict)
    radius: dict[str, int] = field(default_factory=dict)
    typography: dict[str, dict] = field(default_factory=dict)
    color: dict[str, str] = field(default_factory=dict)
    elevation: dict[str, dict] = field(default_factory=dict)


@dataclass
class TokenWarning:
    category: str
    message: str
    severity: str  # "info" | "warning" | "critical"


@dataclass
class QualityScore:
    overall: float
    categories_present: int
    details: list[str] = field(default_factory=list)


@dataclass
class ComplianceReport:
    passed: bool
    total_elements: int = 0
    deviations: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SemanticIntent:
    tokens: dict
    components: list[dict]
    layout: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SemanticIntent:
        return cls(
            tokens=data.get("tokens", {}),
            components=data.get("components", []),
            layout=data.get("layout", []),
            meta=data.get("meta", {}),
        )


# ── DesignSystemHarness ──────────────────────────────────────────────────────

class DesignSystemHarness:
    """Core engine: loads design system tokens, validates them, scores quality,
    and produces SemanticIntent for any FrameworkAdapter."""

    REQUIRED_CATEGORIES = {"spacing", "color"}
    OPTIONAL_CATEGORIES = {"radius", "typography", "elevation"}

    def __init__(self, design_system_path: str | Path):
        self.ds_path = Path(design_system_path)
        self.tokens: TokenSet = TokenSet()
        self.warnings: list[TokenWarning] = []
        self._loaded = False

    # ── Loading ───────────────────────────────────────────────────────────

    def load(self) -> None:
        tokens_dir = self.ds_path / "tokens"
        if not tokens_dir.exists():
            self.warnings.append(TokenWarning(
                "load", f"Tokens directory not found: {tokens_dir}", "critical"
            ))
            self._loaded = True
            return

        parsers = {
            "spacing": (_parse_spacing_md, self.tokens.spacing),
            "radius": (_parse_radius_md, self.tokens.radius),
            "typography": (_parse_typography_md, self.tokens.typography),
            "color": (_parse_color_md, self.tokens.color),
            "elevation": (_parse_elevation_md, self.tokens.elevation),
        }

        for name, (parser, store) in parsers.items():
            path = tokens_dir / f"{name}.md"
            if not path.exists():
                self.warnings.append(TokenWarning(
                    name, f"Token file missing: {path.name}", "warning"
                ))
                continue
            try:
                parsed = parser(path)
                store.update(parsed)
                self.warnings.append(TokenWarning(
                    name, f"Loaded {len(parsed)} tokens from {path.name}", "info"
                ))
            except Exception as e:
                self.warnings.append(TokenWarning(
                    name, f"Failed to parse {path.name}: {e}", "warning"
                ))

        self._loaded = True

    # ── Validation ────────────────────────────────────────────────────────

    def validate(self) -> list[TokenWarning]:
        if not self._loaded:
            self.load()

        results: list[TokenWarning] = []

        present = self._categories_present()
        for cat in self.REQUIRED_CATEGORIES:
            if cat not in present:
                results.append(TokenWarning(
                    cat, f"Required token category missing: {cat}", "critical"
                ))
        for cat in self.OPTIONAL_CATEGORIES:
            if cat not in present:
                results.append(TokenWarning(
                    cat, f"Optional token category missing: {cat}", "info"
                ))

        if self.tokens.spacing:
            bad = [k for k, v in self.tokens.spacing.items() if v % 4 != 0]
            if bad:
                results.append(TokenWarning(
                    "spacing",
                    f"Values not multiples of 4: {bad}",
                    "warning",
                ))
            if len(self.tokens.spacing) < 4:
                results.append(TokenWarning(
                    "spacing",
                    f"Only {len(self.tokens.spacing)} spacing values (recommend >=4)",
                    "warning",
                ))

        if self.tokens.color:
            all_keys = " ".join(self.tokens.color.keys())
            if not re.search(r"brand|primary", all_keys):
                results.append(TokenWarning(
                    "color", "No brand/primary color token found", "warning"
                ))
            if not re.search(r"neutral|text|bg|surface|border", all_keys):
                results.append(TokenWarning(
                    "color", "No neutral/background token found", "warning"
                ))
            if not re.search(r"danger|success|warning|error|info", all_keys):
                results.append(TokenWarning(
                    "color", "No semantic color token (danger/success/warning)", "info"
                ))

        if self.tokens.radius and len(self.tokens.radius) < 3:
            results.append(TokenWarning(
                "radius",
                f"Only {len(self.tokens.radius)} radius values (recommend >=3)",
                "warning",
            ))

        if self.tokens.typography and len(self.tokens.typography) < 4:
            results.append(TokenWarning(
                "typography",
                f"Only {len(self.tokens.typography)} typography entries (recommend >=4)",
                "warning",
            ))

        return results

    # ── Quality scoring ───────────────────────────────────────────────────

    def quality_score(self) -> QualityScore:
        if not self._loaded:
            self.load()

        present = self._categories_present()
        score = 0.0
        details: list[str] = []

        total_possible = len(self.REQUIRED_CATEGORIES | self.OPTIONAL_CATEGORIES)
        base = len(present) / total_possible
        score += base * 0.5
        details.append(f"Categories: {len(present)}/{total_possible} (base={base:.1f})")

        if self.tokens.spacing:
            if all(v % 4 == 0 for v in self.tokens.spacing.values()):
                score += 0.1
                details.append("+0.1 spacing multiples of 4")
            if len(self.tokens.spacing) >= 4:
                score += 0.05
                details.append("+0.05 spacing >=4 values")

        if self.tokens.color:
            key_str = " ".join(self.tokens.color.keys())
            if "brand" in key_str or "primary" in key_str:
                score += 0.1
                details.append("+0.1 brand color present")
            if "danger" in key_str or "success" in key_str or "warning" in key_str:
                score += 0.05
                details.append("+0.05 semantic colors present")
            if len(self.tokens.color) >= 5:
                score += 0.05
                details.append("+0.05 color >=5 entries")

        if self.tokens.radius and len(self.tokens.radius) >= 3:
            score += 0.05
            details.append("+0.05 radius >=3 values")

        if self.tokens.typography and len(self.tokens.typography) >= 4:
            score += 0.05
            details.append("+0.05 typography >=4 entries")

        if self.tokens.elevation and len(self.tokens.elevation) >= 2:
            score += 0.05
            details.append("+0.05 elevation >=2 levels")

        return QualityScore(
            overall=min(round(score, 2), 1.0),
            categories_present=len(present),
            details=details,
        )

    # ── Composition ───────────────────────────────────────────────────────

    def compose_intent(
        self,
        component_types: list[str],
        *,
        source: str = "manual",
        source_quality: float | None = None,
        framework_hint: str | None = None,
        layout_hint: list[dict] | None = None,
    ) -> SemanticIntent:
        if not self._loaded:
            self.load()

        token_dict = self._token_dict()
        components = [_make_component(t) for t in component_types]

        meta: dict[str, Any] = {
            "source": source,
            "archaeologist_mode": False,
        }
        if source_quality is not None:
            meta["source_quality"] = source_quality
        if framework_hint:
            meta["framework_hint"] = framework_hint

        return SemanticIntent(
            tokens=token_dict,
            components=components,
            layout=layout_hint or [],
            meta=meta,
        )

    # ── Drift comparison ─────────────────────────────────────────────────

    def check_drift(self, baseline: SemanticIntent, current: SemanticIntent) -> ComplianceReport:
        deviations: list[dict] = []
        warnings: list[str] = []

        b_tokens = baseline.tokens
        c_tokens = current.tokens
        for cat in b_tokens:
            if cat not in c_tokens:
                warnings.append(f"Drift: token category '{cat}' removed in current")
                continue
            b_keys = set(b_tokens[cat].keys()) if isinstance(b_tokens[cat], dict) else set()
            c_keys = set(c_tokens[cat].keys()) if isinstance(c_tokens[cat], dict) else set()
            missing = b_keys - c_keys
            if missing:
                deviations.append({
                    "category": "tokens",
                    "subcategory": cat,
                    "type": "missing_tokens",
                    "detail": f"Tokens removed: {missing}",
                })
            for key in b_keys & c_keys:
                bv = b_tokens[cat][key]
                cv = c_tokens[cat][key]
                if bv != cv:
                    deviations.append({
                        "category": "tokens",
                        "subcategory": cat,
                        "type": "value_changed",
                        "detail": f"Token '{key}': {bv} -> {cv}",
                    })

        b_comps = {(c.get("type"), c.get("label")) for c in baseline.components}
        c_comps = {(c.get("type"), c.get("label")) for c in current.components}
        removed = b_comps - c_comps
        added = c_comps - b_comps
        if removed:
            warnings.append(f"Drift: components removed: {removed}")
        if added:
            warnings.append(f"Drift: components added: {added}")

        return ComplianceReport(
            passed=len(deviations) == 0,
            total_elements=len(current.components),
            deviations=deviations,
            warnings=warnings,
        )

    # ── Validation ─────────────────────────────────────────────────────

    VALID_COMPONENT_TYPES = {"button", "input", "text", "link", "icon"}
    REQUIRED_TOKEN_CATS = {"spacing", "color"}
    PREFERRED_TOKEN_CATS = {"radius", "typography"}

    def validate_intent(self, intent: SemanticIntent) -> ComplianceReport:
        deviations: list[dict] = []
        warnings: list[str] = []

        for cat in self.REQUIRED_TOKEN_CATS:
            if cat not in intent.tokens or not intent.tokens.get(cat):
                deviations.append({
                    "validator": "DesignSystemHarness",
                    "category": "tokens",
                    "subcategory": cat,
                    "type": "missing_category",
                    "detail": f"Required token category '{cat}' is missing or empty",
                })
        for cat in self.PREFERRED_TOKEN_CATS:
            if cat not in intent.tokens or not intent.tokens.get(cat):
                warnings.append(f"Preferred token category '{cat}' is missing")

        for comp in intent.components:
            ctype = comp.get("type", "")
            if ctype not in self.VALID_COMPONENT_TYPES:
                deviations.append({
                    "validator": "DesignSystemHarness",
                    "category": "component",
                    "subcategory": "type",
                    "type": "invalid_type",
                    "detail": f"Invalid component type '{ctype}'. Valid: {sorted(self.VALID_COMPONENT_TYPES)}",
                })

        if intent.layout:
            self._validate_layout(intent.layout, deviations, warnings)

        return ComplianceReport(
            passed=len(deviations) == 0,
            total_elements=len(intent.components) + len(intent.layout),
            deviations=deviations,
            warnings=warnings,
        )

    def _validate_layout(self, nodes: list[dict], deviations: list[dict], warnings: list[str],
                         depth: int = 0) -> None:
        valid_types = {"stack", "inline", "box", "grid", "surface"}
        for node in nodes:
            ntype = node.get("type", "")
            if ntype not in valid_types:
                warnings.append(f"Unknown layout type '{ntype}' at depth {depth}")
            for child in node.get("children", []):
                if isinstance(child, dict) and "type" in child:
                    self._validate_layout([child], deviations, warnings, depth + 1)

    def _token_dict(self) -> dict:
        d: dict[str, Any] = {}
        if self.tokens.spacing:
            d["spacing"] = dict(self.tokens.spacing)
        if self.tokens.radius:
            d["radius"] = dict(self.tokens.radius)
        if self.tokens.typography:
            d["typography"] = dict(self.tokens.typography)
        if self.tokens.color:
            d["color"] = dict(self.tokens.color)
        if self.tokens.elevation:
            d["elevation"] = dict(self.tokens.elevation)
        return d

    def _categories_present(self) -> set[str]:
        present: set[str] = set()
        if self.tokens.spacing:
            present.add("spacing")
        if self.tokens.radius:
            present.add("radius")
        if self.tokens.typography:
            present.add("typography")
        if self.tokens.color:
            present.add("color")
        if self.tokens.elevation:
            present.add("elevation")
        return present


# ── Helpers ─────────────────────────────────────────────────────────────────

def _parse_spacing_md(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`spacing\.(\w+)`\s*\|\s*(\d+)", line)
        if m:
            result[m.group(1)] = int(m.group(2))
    return result


def _parse_radius_md(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`radius\.(\w+)`\s*\|\s*(\d+)", line)
        if m:
            result[m.group(1)] = int(m.group(2))
    return result


def _parse_typography_md(path: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`font-size\.(\w+)`\s*\|\s*(\d+)", line)
        if m:
            result[m.group(1)] = {"size": int(m.group(2))}
    return result


def _parse_color_md(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`([a-z.]+)`\s*\|\s*(#[0-9A-Fa-f]{3,8})\s*\|", line)
        if m:
            result[m.group(1)] = m.group(2)
    return result


def _parse_elevation_md(path: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`elevation\.(\w+)`\s*\|\s*(\d+)", line)
        if m:
            result[m.group(1)] = {"zIndex": int(m.group(2))}
    return result


def _make_component(comp_type: str) -> dict:
    valid = {"button", "input", "text", "icon", "link"}
    t = comp_type.lower()
    if t not in valid:
        t = "text"
    return {
        "type": t,
        "label": comp_type.capitalize(),
        "variant": "primary" if t == "button" else "default",
        "size": "md",
    }
