# -*- coding: utf-8 -*-
"""Small helpers for recolouring only SynapsePro's blue SVG brand layer."""

from __future__ import annotations

import re


_BRAND_BLUE = re.compile(r"#0071d3\b", re.IGNORECASE)
_SAFE_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def recoloured_brand_svg_bytes(path: str, accent: str) -> bytes:
    """Return *path* with only the original blue brand colour replaced.

    The white logo layer and its black stroke use different colour values and
    are deliberately left untouched.
    """
    colour = accent if isinstance(accent, str) and _SAFE_HEX.fullmatch(accent) else "#0071D3"
    with open(path, "r", encoding="utf-8") as handle:
        svg = handle.read()
    return _BRAND_BLUE.sub(colour, svg).encode("utf-8")
