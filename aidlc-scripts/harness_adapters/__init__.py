from __future__ import annotations

from .source.base import DesignSourceAdapter
from .source.figma import FigmaAdapter
from .source.stitch import StitchAdapter
from .source.raw_json import RawJsonAdapter

__all__ = [
    "DesignSourceAdapter",
    "FigmaAdapter",
    "StitchAdapter",
    "RawJsonAdapter",
]
