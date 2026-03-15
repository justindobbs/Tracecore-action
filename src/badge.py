from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import quote_plus

BADGE_BASE_URL = "https://img.shields.io/badge"
_BADGE_TARGET = "https://github.com/justindobbs/Tracecore"


@dataclass(frozen=True)
class Badge:
    alt_text: str
    url: str
    markdown: str
    status_label: str
    color: Literal["brightgreen", "yellow", "red", "critical"]


def _status_label(success: bool, strict_spec: bool) -> tuple[str, str]:
    """Return (label_text, color) tuple for the badge."""
    if success:
        label = "Verified Strict" if strict_spec else "Verified"
        return label, "brightgreen"
    label = "Failed Strict" if strict_spec else "Failed"
    return label, "critical"


def render_badge(success: bool, *, strict_spec: bool) -> Badge:
    """Render a shields.io badge for the given outcome."""
    label_text, color = _status_label(success, strict_spec)

    badge_url = (
        f"{BADGE_BASE_URL}/TraceCore-{quote_plus(label_text)}-{color}"
        "?style=flat-square&labelColor=0b0d11"
    )

    alt_text = f"TraceCore {label_text}"
    markdown = f"[![{alt_text}]({badge_url})]({_BADGE_TARGET})"
    return Badge(
        alt_text=alt_text,
        url=badge_url,
        markdown=markdown,
        status_label=label_text,
        color=color,
    )
