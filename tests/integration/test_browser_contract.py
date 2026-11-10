"""Browser assets use safe text and same-origin owned endpoints."""

from pathlib import Path


def test_browser_has_no_html_insertion_or_raw_streaming():
    web = Path(__file__).resolve().parents[2] / "src/parking/web"
    script = (web / "app.mjs").read_text(encoding="utf-8")
    assert "textContent" in script
    assert "innerHTML" not in script
    assert "EventSource" not in script
    assert "/requests/" in script and "parking-chat" in script
    html = (web / "index.html").read_text(encoding="utf-8")
    assert 'for="message"' in html and 'id="new-chat"' in html
