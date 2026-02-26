"""
Acceptance coverage for UI dispatcher, cache settings, and export mode selection.
"""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import WordStatApp
from storage.cache import WordstatCache
from ui.main_window import MainWindow


def test_post_to_ui_dispatches_from_thread():
    """UI dispatcher should run callbacks even when invoked from a worker thread."""
    results = []

    class DummyUI:
        post_to_ui = MainWindow.post_to_ui

        def after(self, _delay, fn):
            fn()

    def worker():
        ui = DummyUI()
        ui.post_to_ui(results.append, "ok")

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=5)

    assert results == ["ok"]


def test_apply_cache_settings_normalizes_and_applies():
    """Cache mode/TTL are normalized and applied to cache and parser."""
    class DummyParser:
        def __init__(self):
            self.cache_mode = None
            self.cache = None

        def set_cache_settings(self, cache, mode: str = "on"):
            self.cache = cache
            self.cache_mode = mode

    class DummyApp:
        def __init__(self):
            self.cache = None
            self.cache_mode = "on"
            self.parser = DummyParser()

    app = DummyApp()
    WordStatApp._apply_cache_settings(app, {"cache_mode": "ON", "cache_ttl_days": 1})

    assert isinstance(app.cache, WordstatCache)
    assert app.cache_mode == "on"
    assert app.parser.cache_mode == "on"

    app.cache.shutdown()

    WordStatApp._apply_cache_settings(app, {"cache_mode": "off", "cache_ttl_days": 1})
    assert app.cache is None
    assert app.cache_mode == "off"
    assert app.parser.cache_mode == "off"


def test_export_mode_selection_routes_to_exporter():
    """Export callback receives validated mode from UI."""
    calls = []

    class DummyVar:
        def __init__(self, value):
            self._value = value

        def get(self):
            return self._value

    class DummyWindow:
        def __init__(self, mode):
            self.export_mode_var = DummyVar(mode)
            self._statuses = []
            self.on_export_callback = lambda m: calls.append(m)
        _on_export = MainWindow._on_export

        def set_status(self, status):
            self._statuses.append(status)

    seo_window = DummyWindow("ppc")
    seo_window._on_export()
    assert calls[-1] == "ppc"

    fallback_window = DummyWindow("invalid")
    fallback_window._on_export()
    assert calls[-1] == "seo"
