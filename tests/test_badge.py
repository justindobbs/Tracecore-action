from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from badge import render_badge


def test_render_badge_success_strict() -> None:
    badge = render_badge(True, strict_spec=True)

    assert badge.alt_text == "TraceCore Verified Strict"
    assert badge.status_label == "Verified Strict"
    assert badge.color == "brightgreen"
    assert "TraceCore-Verified+Strict-brightgreen" in badge.url
    assert badge.markdown == f"[![{badge.alt_text}]({badge.url})](https://github.com/justindobbs/Tracecore)"


def test_render_badge_success_non_strict() -> None:
    badge = render_badge(True, strict_spec=False)

    assert badge.alt_text == "TraceCore Verified"
    assert badge.status_label == "Verified"
    assert badge.color == "brightgreen"
    assert "TraceCore-Verified-brightgreen" in badge.url
    assert "TraceCore Verified" in badge.markdown


def test_render_badge_failure_strict() -> None:
    badge = render_badge(False, strict_spec=True)

    assert badge.alt_text == "TraceCore Failed Strict"
    assert badge.status_label == "Failed Strict"
    assert badge.color == "critical"
    assert "TraceCore-Failed+Strict-critical" in badge.url
    assert "TraceCore Failed Strict" in badge.markdown


def test_render_badge_failure_non_strict() -> None:
    badge = render_badge(False, strict_spec=False)

    assert badge.alt_text == "TraceCore Failed"
    assert badge.status_label == "Failed"
    assert badge.color == "critical"
    assert "TraceCore-Failed-critical" in badge.url
    assert "TraceCore Failed" in badge.markdown
