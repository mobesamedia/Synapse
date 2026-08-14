# -*- coding: utf-8 -*-
"""HTML configuration dialog for the dashboard statistics widget."""

import json
import os
from typing import Dict, Optional

from aqt.qt import QDialog, QVBoxLayout, QUrl, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView

from . import constants
from .theme import palette
from .locales import _


_UI_STRINGS = (
    "Statistics Settings",
    "Choose the periods and decide which insights appear on your dashboard.",
    "Time ranges", "Statistics period",
    "Used for Efficiency, Accuracy and Retention.",
    "Consistency period", "Controls only the review activity graph.",
    "Visible insights", "Review activity graph.",
    "Efficiency and Accuracy bars.", "Retention percentage circle.",
    "Unseen cards percentage circle.", "Cancel", "Save",
    "Consistency", "Efficiency", "Retention", "New Cards",
)


class _StatisticsSettingsPage(QWebEnginePage):
    message = pyqtSignal(str)

    def javaScriptConsoleMessage(self, level, message, line, source):
        prefix = "SYNAPSEPRO_STATS_SETTINGS:"
        if isinstance(message, str) and message.startswith(prefix):
            self.message.emit(message[len(prefix):])
        elif message:
            print(f"SynapsePro statistics settings JS ({line}): {message}")


class StatisticsSettingsDialog(QDialog):
    def __init__(self, current_config: Dict, parent=None):
        super().__init__(parent)
        self.current_config = dict(current_config or {})
        self._result: Optional[Dict] = None
        self._injected = False

        self.setWindowTitle(f"SynapsePro - {_('Statistics Settings')}")
        self.resize(680, 590)
        self.setMinimumSize(560, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._view = QWebEngineView(self)
        self._page = _StatisticsSettingsPage(self._view)
        self._view.setPage(self._page)
        self._page.message.connect(self._on_message)
        self._view.loadFinished.connect(self._on_load_finished)
        layout.addWidget(self._view)

        night = False
        try:
            from aqt import mw
            night = bool(mw and mw.pm.night_mode())
        except Exception:
            pass
        try:
            self._page.setBackgroundColor(QColor("#1c1c1e" if night else "#ffffff"))
        except Exception:
            pass

        # Read the page ourselves instead of relying on constants.addon_path.
        # During some Anki startup/profile sequences that shared path can still
        # be empty, which makes QWebEngine display an entirely blank page.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "settings_web", "statistics.html")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                html = handle.read()
            self._view.setHtml(
                html,
                QUrl.fromLocalFile(os.path.join(base_dir, "settings_web") + os.sep),
            )
        except Exception as exc:
            print(f"SynapsePro: could not load statistics settings HTML: {exc}")
            self._view.setHtml(
                "<html><body style='font-family:sans-serif;padding:24px'>"
                "<h3>Statistics Settings</h3>"
                "<p>The settings page could not be loaded.</p></body></html>"
            )

    def get_new_settings(self) -> Dict:
        return dict(self._result or {})

    def _on_load_finished(self, ok: bool):
        if ok:
            self._inject()
        else:
            print("SynapsePro: statistics settings web page failed to load")
            self._view.setHtml(
                "<html><body style='font-family:sans-serif;padding:24px'>"
                "<h3>Statistics Settings</h3>"
                "<p>The settings interface could not be rendered.</p></body></html>"
            )

    def _on_message(self, message: str):
        action, _sep, payload = message.partition(":")
        if action == "ready":
            self._inject()
        elif action == "cancel":
            self.reject()
        elif action == "save":
            try:
                data = json.loads(payload)
                stats_days = int(data.get("stats_time_range", 7))
                chart_days = int(data.get("stats_consistency_days", 30))
                self._result = {
                    "stats_time_range": stats_days if stats_days in (1, 7, 30) else 7,
                    "stats_consistency_days": chart_days if chart_days in (7, 30, 365) else 30,
                    "stats_show_consistency": bool(data.get("stats_show_consistency", True)),
                    "stats_show_efficiency": bool(data.get("stats_show_efficiency", True)),
                    "stats_show_retention": bool(data.get("stats_show_retention", True)),
                    "stats_show_new_cards": bool(data.get("stats_show_new_cards", True)),
                }
                self.accept()
            except Exception as exc:
                print(f"SynapsePro: invalid statistics settings payload: {exc}")

    def _inject(self):
        if self._injected:
            return
        self._injected = True
        night = False
        try:
            from aqt import mw
            night = bool(mw and mw.pm.night_mode())
        except Exception:
            pass
        colors = palette(night)
        payload = {
            "isDark": night,
            "accent": colors.get("blue", "#0071D3"),
            "translations": {source: _(source) for source in _UI_STRINGS},
            "config": {
                "stats_time_range": int(self.current_config.get("stats_time_range", 7) or 7),
                "stats_consistency_days": int(self.current_config.get("stats_consistency_days", 30) or 30),
                "stats_show_consistency": bool(self.current_config.get("stats_show_consistency", True)),
                "stats_show_efficiency": bool(self.current_config.get("stats_show_efficiency", True)),
                "stats_show_retention": bool(self.current_config.get("stats_show_retention", True)),
                "stats_show_new_cards": bool(self.current_config.get("stats_show_new_cards", True)),
            },
        }
        self._page.runJavaScript(
            "if(window.initStatisticsSettings){window.initStatisticsSettings("
            + json.dumps(payload)
            + ");}"
        )
