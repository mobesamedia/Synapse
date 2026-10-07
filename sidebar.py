# -*- coding: utf-8 -*-
"""Gamification sidebar — HTML/WebView UI.

The sidebar is rendered by ``gamification_web/sidebar.html`` inside a
QWebEngineView. Python builds a JSON payload (level, rank, streak, daily
challenge, all ranks …) and injects it via ``initGamification()``; the page
reports clicks back over a console.log bridge (``SYNAPSEPRO_GAMI:<action>``),
mirroring the pattern used by ``web_settings_dialog.py``.

Public API (used by __init__.py):
    GamificationSidebar(manager, parent)  – QDockWidget
    .update_display()                     – re-inject fresh data
    .refresh_style()                      – re-apply theme after settings change
"""

import json
import os
import traceback
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from aqt import mw
from aqt.qt import Qt, QDockWidget, QLabel, QUrl, QWidget
from aqt.utils import tooltip

try:
    from .gamification import ADDON_NAME
except ImportError:
    ADDON_NAME = "GamificationSidebar"

try:
    from .locales import _
except ImportError:
    def _(text):  # type: ignore
        return text

try:
    from .web_i18n import translations as _web_translations
except ImportError:
    def _web_translations(_surface):  # type: ignore
        return {}

try:
    from .theme import dialog_palette as _palette
except ImportError:
    def _palette(night):  # type: ignore
        return {}

if TYPE_CHECKING:
    from .gamification import GamificationManager

# ── Qt 6 WebEngine imports ─────────────────────────────────────────────────────
try:
    from PyQt6.QtGui import QColor
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
except ImportError:
    QWebEngineView = QWebEnginePage = QWebEngineSettings = None  # type: ignore
    QColor = None  # type: ignore

_BRIDGE_PREFIX = "SYNAPSEPRO_GAMI:"

_HTML_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "gamification_web", "sidebar.html")


def _is_night() -> bool:
    try:
        return bool(mw and hasattr(mw, "pm") and mw.pm.night_mode())
    except Exception:
        return False


def _file_url(path: Optional[str]) -> str:
    """Absolute file:// URL for *path*, or '' if it doesn't exist."""
    if path and os.path.exists(path):
        return QUrl.fromLocalFile(path).toString()
    return ""


def _last_frame_png(gif_path: Optional[str]) -> Optional[str]:
    """Extract the GIF's LAST frame as a cached PNG via QMovie.

    The page freezes the badge animation on this image. It has exactly the
    same dimensions and content as the final GIF frame, so the swap is
    invisible (the shipped rank PNGs are cropped differently, and canvas
    drawImage() only ever yields the FIRST frame per the HTML spec).
    """
    if not gif_path or not os.path.exists(gif_path):
        return None
    cache_dir = os.path.join(os.path.dirname(_HTML_PATH), "cache")
    out = os.path.join(
        cache_dir, os.path.basename(gif_path).rsplit(".", 1)[0] + "_last.png")
    try:
        if (os.path.exists(out)
                and os.path.getmtime(out) >= os.path.getmtime(gif_path)):
            return out
        from aqt.qt import QMovie
        os.makedirs(cache_dir, exist_ok=True)
        mv = QMovie(gif_path)
        n = mv.frameCount()
        if n <= 0:
            # Some decoders report 0 — step through one loop to count.
            n = 0
            while mv.jumpToNextFrame():
                cur = mv.currentFrameNumber()
                if cur <= n and n > 0:
                    break  # wrapped around to the start
                n = cur
            n += 1
        mv.jumpToFrame(max(0, n - 1))
        pix = mv.currentPixmap()
        if pix.isNull() or not pix.save(out, "PNG"):
            return None
        return out
    except Exception as e:
        print(f"{ADDON_NAME}: last-frame extraction failed: {e}")
        return None


_gif_duration_cache: Dict[str, int] = {}


def _gif_duration_ms(path: Optional[str]) -> int:
    """Total duration of one GIF loop in milliseconds (0 if unknown).

    Parsed directly from the GIF block structure (sum of all Graphic Control
    Extension delays) so the page can freeze the badge on its static frame
    after exactly one playthrough.
    """
    if not path or not os.path.exists(path):
        return 0
    if path in _gif_duration_cache:
        return _gif_duration_cache[path]
    total = 0
    try:
        with open(path, "rb") as f:
            data = f.read()
        if data[:6] not in (b"GIF87a", b"GIF89a"):
            return 0
        pos = 6
        packed = data[pos + 4]
        pos += 7
        if packed & 0x80:  # global color table
            pos += 3 * (2 ** ((packed & 7) + 1))
        while pos < len(data):
            block = data[pos]; pos += 1
            if block == 0x3B:  # trailer
                break
            if block == 0x21:  # extension
                label = data[pos]; pos += 1
                if label == 0xF9 and data[pos] >= 4:
                    delay = data[pos + 2] | (data[pos + 3] << 8)  # 1/100 s
                    total += (delay if delay > 1 else 10) * 10
                while True:  # skip sub-blocks
                    size = data[pos]; pos += 1
                    if size == 0:
                        break
                    pos += size
            elif block == 0x2C:  # image descriptor
                lct = data[pos + 8]; pos += 9
                if lct & 0x80:  # local color table
                    pos += 3 * (2 ** ((lct & 7) + 1))
                pos += 1  # LZW minimum code size
                while True:  # skip image data sub-blocks
                    size = data[pos]; pos += 1
                    if size == 0:
                        break
                    pos += size
            else:
                break
        total = max(400, min(total, 20000)) if total else 0
    except Exception:
        total = 0
    _gif_duration_cache[path] = total
    return total


if QWebEnginePage is not None:

    class _GamiPage(QWebEnginePage):  # type: ignore[misc]
        """Console-message bridge: JS logs 'SYNAPSEPRO_GAMI:<action>'."""

        def __init__(self, callback, *args):
            super().__init__(*args)
            self._callback = callback

        def acceptNavigationRequest(self, url, navigation_type, is_main_frame):  # noqa: N802
            # This privileged bridge belongs only to the bundled sidebar.
            return bool(is_main_frame and url.isLocalFile()
                        and os.path.realpath(url.toLocalFile()) == os.path.realpath(_HTML_PATH))

        def javaScriptConsoleMessage(self, level, message, line, source_id):  # noqa: N802
            if isinstance(message, str) and message.startswith(_BRIDGE_PREFIX):
                try:
                    self._callback(message[len(_BRIDGE_PREFIX):])
                except Exception as e:
                    print(f"{ADDON_NAME}: bridge error: {e}")


class GamificationSidebar(QDockWidget):
    def __init__(self, manager: 'GamificationManager', parent: Optional[QWidget] = None):
        super().__init__("", parent)
        self.manager = manager
        self.setObjectName("GamificationSidebar")
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.setMinimumWidth(300)
        self.setTitleBarWidget(QWidget())

        self._loaded = False

        if QWebEngineView is None or not os.path.exists(_HTML_PATH):
            fallback = QLabel(_("Error: QtWebEngine not available."))
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setWidget(fallback)
            self._view = None
            self._page = None
            return

        self._view = QWebEngineView(self)
        self._page = _GamiPage(self._on_message, self._view)
        self._view.setPage(self._page)

        # Match the page background to the theme BEFORE anything paints —
        # otherwise the view flashes white in dark mode while loading.
        self._apply_view_background()

        # Allow the local page to display the rank images from ../media/.
        try:
            s = self._view.settings()
            s.setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        except Exception:
            pass

        self._view.loadFinished.connect(self._on_load_finished)
        self._view.setUrl(QUrl.fromLocalFile(_HTML_PATH))
        self.setWidget(self._view)

    # ── public API ────────────────────────────────────────────────────────────
    def update_display(self) -> None:
        """Re-inject fresh gamification data into the page."""
        self._inject()

    def refresh_style(self) -> None:
        """Re-apply the current colour theme after a settings change."""
        self._apply_view_background()
        self._inject()

    def showEvent(self, event) -> None:  # noqa: N802
        """Replay the badge animation once whenever the sidebar is opened."""
        super().showEvent(event)
        self._inject()
        if self._page and self._loaded:
            try:
                self._page.runJavaScript("window.replayBadge && replayBadge();")
            except Exception:
                pass

    # ── internals ─────────────────────────────────────────────────────────────
    def _apply_view_background(self) -> None:
        if not self._page or QColor is None:
            return
        try:
            c = _palette(_is_night())
            self._page.setBackgroundColor(
                QColor(c.get("bg", "#1c1c1e" if _is_night() else "#f5f5f7")))
        except Exception:
            pass

    def _on_load_finished(self, ok: bool) -> None:
        if ok:
            self._loaded = True
            self._inject()

    def _on_message(self, action: str) -> None:
        if action == "ready":
            # DOM is ready — inject even before loadFinished fires.
            self._loaded = True
            self._inject()
        elif action == "complete":
            self._on_complete_challenge()
        elif action.startswith("popups:"):
            self._set_popups_enabled(action.split(":", 1)[1] == "1")
        elif action.startswith("popupType:"):
            parts = action.split(":")
            if len(parts) == 3 and parts[1] in ("rank", "level", "challenge") and parts[2] in ("0", "1"):
                self._set_popups_enabled(parts[2] == "1", parts[1])
        elif action.startswith("streakRules:"):
            try:
                if len(action) <= 256 and self.manager:
                    if self.manager.set_streak_rules(json.loads(action.split(":", 1)[1])):
                        self.update_display()
            except (ValueError, TypeError):
                pass
        elif action.startswith("achievementSeen:"):
            badge_id = action.split(":", 1)[1]
            if self.manager and self.manager.mark_achievement_seen(badge_id):
                self.update_display()
        elif action.startswith("favoriteAchievement:"):
            badge_id = action.split(":", 1)[1]
            if self.manager and self.manager.toggle_favorite_achievement(badge_id):
                self.update_display()
        elif action.startswith("err:"):
            print(f"{ADDON_NAME}: JS error: {action[4:]}")

    def _inject(self) -> None:
        if not self._loaded or not self._page:
            return
        try:
            payload = json.dumps(self._build_payload())
            self._page.runJavaScript(
                f"window.initGamification && initGamification({payload});")
        except Exception as e:
            print(f"{ADDON_NAME}: inject failed: {e}")
            traceback.print_exc()


    @staticmethod
    def _addon_settings():
        """The package-level settings dict + save function (or (None, None))."""
        try:
            import sys
            pkg = sys.modules.get(__package__ or "")
            settings = getattr(pkg, "addon_settings", None)
            save = getattr(pkg, "save_addon_settings", None)
            if isinstance(settings, dict):
                return settings, save
        except Exception:
            pass
        return None, None

    def _popups_enabled(self) -> bool:
        settings, _save = self._addon_settings()
        if settings is None:
            return True
        return bool(settings.get("gamification_popups_enabled", True))

    def _set_popups_enabled(self, enabled: bool, event_type=None) -> None:
        """Toggle the celebration popups (checkbox in this sidebar)."""
        try:
            settings, save = self._addon_settings()
            if settings is not None:
                if event_type is not None and event_type not in ("rank", "level", "challenge"):
                    return
                key = "gamification_popup_" + event_type if event_type else "gamification_popups_enabled"
                settings[key] = bool(enabled)
                if callable(save):
                    save()
                self.update_display()
        except Exception as e:
            print(f"{ADDON_NAME}: popup toggle failed: {e}")

    def _on_complete_challenge(self) -> None:
        if not self.manager:
            tooltip(_("Error: Gamification Manager not available."))
            return
        if self.manager.is_challenge_completed_today():
            tooltip(_("Challenge already completed today!"))
            self.update_display()
            return
        # on_complete_challenge() re-validates the goal before awarding XP.
        try:
            self.manager.on_complete_challenge()
        except Exception as e:
            print(f"{ADDON_NAME}: Error calling on_complete_challenge: {e}")
            tooltip(_("An error occurred."))
        self.update_display()

    # ── payload ───────────────────────────────────────────────────────────────
    def _build_payload(self) -> Dict[str, Any]:
        night = _is_night()
        c = _palette(night)
        popup_settings, _save = self._addon_settings()
        popup_settings = popup_settings or {}

        payload: Dict[str, Any] = {
            "isDark": night,
            "errors": _web_translations("errors"),
            "colors": {
                "accent":       c.get("blue"),
                "accentBright": c.get("blue_accent"),
                "bg":           c.get("bg"),
                "card":         c.get("surface"),
                "border":       c.get("grey_light"),
                "text":         c.get("text"),
                "muted":        c.get("text_muted"),
                "track":        c.get("grey_light"),
                "statsControlBg": c.get("grey_mid" if night else "grey_light"),
                "statsControlColor": c.get("text_muted"),
                # NOTE: green intentionally not themed from the palette — the
                # page uses its own muted, Apple-style green (text-only).
            },
            "labels": {
                "title":       _("Synapse Gamification"),
                "level":       _("Level {}"),
                "nextGoal":    _("Next Goal"),
                "onlyXp":      _("Only {} XP left"),
                "maxRank":     _("Maximum Rank Achieved!"),
                "congrats":    _("Congratulations!"),
                "streak":      _("Current Streak"),
                "dayStreak":   _("{} Day"),
                "daysStreak":  _("{} Days"),
                "challenge":   _("Daily Challenge"),
                "completed":   _("Completed"),
                "claim":       _("Claim +{} XP"),
                "notYet":      _("Challenge not completed yet ({}/{})."),
                "allRanks":    _("All Ranks"),
                "lvlPlus":     _("Lvl {}+: {}"),
                "locked":      _("(Locked)"),
                "how":         _("How it works"),
                "xpNeededTip": _("Needed for next level: {}"),
                "popups":      _("Celebration popups"),
                "popupsHint":  _("Choose which celebrations appear on the dashboard. Changes are saved immediately."),
                "popupRank": _("Rank up"), "popupLevel": _("Level up"),
                "popupChallenge": _("Daily Challenge"),
            },
            "streakRules": (self.manager.data.get("streak_rules", {}) if self.manager else {}),
            "streakLabels": {key: _(value) for key, value in {
                "settings": "Settings", "close": "Close", "title": "Streak sensitivity",
                "reviews": "Minimum reviews per day", "allowCards": "Creating cards can also count",
                "cards": "Minimum new cards per day",
                "hint": "A day counts when either enabled goal is reached. Anki’s day boundary applies. Changes recalculate your current streak, including past days; earned XP and badges stay yours.",
                "creationHint": "Uses creation dates of cards still in your collection, including imported cards. Deleted cards no longer count.",
                "info": "Your streak counts consecutive qualifying Anki days. Today remains open until the next day begins. Choose your daily criteria in Settings. Achievement badges keep their own study criteria.",
            }.items()},
            "popupsEnabled": self._popups_enabled(),
            "popupTypes": {key: bool(popup_settings.get("gamification_popup_" + key, key != "level"))
                           for key in ("rank", "level", "challenge")},
            "achievementLabels": {
                "title": _("Achievements"), "hint": _("Select a badge to see your progress."),
                "locked": _("Not earned yet"), "close": _("Close"),
                "value": _("Recorded progress: {}"), "next": _("Next stage: {}"),
                "remaining": _("Still needed: {}"), "complete": _("All stages earned"),
                "permanent": _("This achievement is yours to keep."),
                "nextGoal": _("Your next badge"),
                "goalOne": _("One more {} to reach {}."),
                "goalMany": _("{} more {} to reach {}."),
                "new": _("New"),
                "earnedOn": _("Earned on {}"),
                "chooseFavorite": _("Choose as favorite badge"),
                "favorite": _("Favorite badge"),
            },
            "guideHtml": self._guide_html(),
        }

        m = self.manager
        if not m:
            payload.update({
                "level": "?", "rankName": "?", "badge": "",
                "xp": 0, "xpNeeded": None, "remainingXp": None, "progressPct": 0,
                "streak": 0, "streakXp": 0,
                "challenge": {"text": _("Loading..."), "cur": 0, "target": 0,
                              "completed": False, "achieved": False, "xpReward": 0},
                "nextGoal": None, "ranks": [],
            })
            return payload

        level = m.get_level()
        rank_info = m.get_current_rank_info()
        rank_name = _(rank_info.get("name", _("Unknown Rank"))).replace("<br>", " ")
        badge_gif_path = m.get_rank_image_path(rank_info.get("image"))
        badge_url = _file_url(badge_gif_path)
        # Still image the page freezes on after one GIF playthrough:
        # the extracted last frame (pixel-identical), falling back to the
        # shipped static PNG if extraction is unavailable.
        badge_png_path = _last_frame_png(badge_gif_path)
        if not badge_png_path and badge_gif_path:
            badge_png_path = badge_gif_path.replace(".gif", ".png")
        badge_static_url = _file_url(badge_png_path)

        xp_current = m.data.get("xp", 0)
        needed = m.get_xp_for_level(level)
        needed_val = None if needed == float("inf") else int(needed)
        remaining = m.get_remaining_xp()
        remaining_val = int(remaining) if isinstance(remaining, int) else None

        streak = m.get_streak()

        challenge_text, _unused = m.get_current_challenge()
        chall_cur, chall_target = m.get_challenge_progress()
        completed = m.is_challenge_completed_today()

        all_ranks: List[Dict[str, Any]] = m.get_all_ranks()

        # Next rank goal (XP still needed until the next rank's level)
        next_goal = None
        for rank in all_ranks:
            if rank["level"] > level:
                xp_to_finish_level = needed - xp_current if needed_val is not None else 0
                xp_intermediate = sum(
                    m.get_xp_for_level(i) for i in range(level + 1, rank["level"]))
                next_goal = {
                    "xp": int(xp_to_finish_level + xp_intermediate),
                    "name": _(rank["name"]).replace("<br>", " "),
                }
                break

        ranks_payload = []
        for rank in all_ranks:
            rank_level = rank.get("level", 999)
            gif_path = m.get_rank_image_path(rank.get("image"))
            # Static PNG for the grid (animated GIFs stay reserved for the hero badge)
            img_path = gif_path.replace(".gif", ".png") if gif_path else None
            if not (img_path and os.path.exists(img_path)):
                img_path = gif_path
            ranks_payload.append({
                "name": _(rank.get("name", "?")).replace("<br>", " "),
                "level": rank_level,
                "img": _file_url(img_path),
                "unlocked": level >= rank_level,
                "current": rank_level == rank_info.get("level"),
            })

        payload.update({
            "level": level,
            "rankName": rank_name,
            "badge": badge_url,
            "badgeStatic": badge_static_url,
            "badgeDurationMs": _gif_duration_ms(badge_gif_path),
            "xp": int(xp_current),
            "xpNeeded": needed_val,
            "remainingXp": remaining_val,
            "progressPct": m.get_progress_percentage(),
            "streak": streak,
            "streakXp": streak * 20,
            "challenge": {
                "text": challenge_text,
                "cur": chall_cur,
                "target": chall_target,
                "completed": completed,
                "achieved": chall_cur >= chall_target,
                "xpReward": m.get_daily_challenge_xp(),
            },
            "nextGoal": next_goal,
            "ranks": ranks_payload,
            "achievements": m.get_achievements(),
        })
        return payload

    def _guide_html(self) -> str:
        tpl = _(
            "<p>Earn XP, level up, and climb the ranks while studying!</p>"
            "<p><b>How to Earn XP</b></p>"
            "<ul>"
            "<li><b>Study Time:</b> 10 XP per minute.</li>"
            "<li><b>Daily Challenge:</b> Bonus XP based on level.</li>"
            "<li><b>Streak:</b> 20 XP × current streak day.</li>"
            "</ul>"
            "<p><b>Leveling &amp; Ranks</b></p>"
            "<ul>"
            "<li>Max Level: 100.</li>"
            "<li>New Rank every 5 levels.</li>"
            "</ul>"
            "<p class=\"tip\">Tip: Consistency is key!</p>"
        )
        return tpl
