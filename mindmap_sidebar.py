
import json
import os
import shutil
import time
import traceback
from typing import Callable, Optional

# --- Local Imports ---
from . import constants

# --- PyQt Imports ---
QWidget, QDockWidget, QVBoxLayout, QHBoxLayout, QLabel = object, object, object, object, object
QUrl, Qt, QPushButton, QIcon, QTimer = object, object, object, object, object
QWebEngineView, QWebEnginePage, QWebEngineProfile, QWebEngineSettings, QWebEngineScript = object, object, object, object, object
QObject, QWebChannel = object, object
pyqtSlot = lambda *args: (lambda method: method)

try:
    from aqt.qt import (QWidget, QDockWidget, QVBoxLayout, QHBoxLayout, QLabel,
                        QPushButton, QUrl, Qt, QTimer, QIcon, QColor, QCoreApplication)
    from PyQt6.QtCore import QObject, pyqtSlot
    from PyQt6.QtWebChannel import QWebChannel
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings, QWebEngineScript
except ImportError:
    pass

# --- Anki Imports ---
if QWidget is not object:
    try:
        from aqt import mw
    except ImportError: mw = None
else: mw = None

# --- Translation ---
try:
    from .locales import _
except ImportError:
    def _(text): return text  # type: ignore

from . import embedded_window
from . import roadmap_store, workspace_io

# --- Globale Referenz ---
mindmap_dock: Optional[QDockWidget] = None
MINDMAP_RECOVERY_FILENAME = "mindmap_recovery.json"


def _claim_tutorial_invitation(profile_folder: str) -> bool:
    """At most one automatic invitation per profile; fail closed on I/O errors.

    Exclusive creation also prevents two views from offering simultaneously.
    Even a partial marker suppresses future automatic invitations.
    """
    if not profile_folder:
        return False
    try:
        folder = os.path.join(profile_folder, "SynapsePro_Data")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "mindmap_tutorial.json"), "x", encoding="utf-8") as handle:
            json.dump({"version": 1, "invitation_handled": True}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        return True
    except FileExistsError:
        return False
    except Exception as exc:
        print(f"Mindmap tutorial invitation could not be recorded: {exc}")
        return False


def _mindmap_recovery_path(profile_folder=None) -> str:
    if profile_folder is not None:
        return os.path.join(profile_folder, MINDMAP_RECOVERY_FILENAME)
    if mw and mw.pm and mw.pm.profileFolder():
        return os.path.join(mw.pm.profileFolder(), MINDMAP_RECOVERY_FILENAME)
    return os.path.join(constants.addon_path, MINDMAP_RECOVERY_FILENAME)


def _write_mindmap_recovery(snapshot: str, saved_at: int, profile_folder=None) -> bool:
    """Atomically mirror the latest map collection outside QtWebEngine storage."""
    path = _mindmap_recovery_path(profile_folder)
    tmp_path = f"{path}.tmp"
    try:
        mindmaps = json.loads(snapshot)
        if not isinstance(mindmaps, dict):
            raise ValueError("mind map recovery snapshot is not an object")
        payload = {
            "version": 1,
            "saved_at": int(saved_at),
            "mindmaps": mindmaps,
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        return True
    except Exception as exc:
        print(f"Mindmap recovery save failed: {exc}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False


def _load_mindmap_recovery(profile_folder=None) -> Optional[dict]:
    try:
        with open(_mindmap_recovery_path(profile_folder), "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("saved_at"), int)
            and isinstance(payload.get("mindmaps"), dict)
        ):
            return payload
    except FileNotFoundError:
        pass
    except Exception as exc:
        print(f"Mindmap recovery load failed: {exc}")
    return None

# --- Vollbildfenster ---
class MindmapFullscreenWindow(QWidget):
    def __init__(self, panel_instance, web_view, parent=None, windowed=False):
        super().__init__(parent)
        self.panel = panel_instance
        self.web_view = web_view
        self.windowed = windowed
        self.setWindowTitle(
            _("MindMap") if windowed else _("MindMap - Fullscreen")
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)

    def closeEvent(self, event):
        self.panel.exit_fullscreen(self.web_view)
        event.accept()

# --- i18n helper ───────────────────────────────────────────────────────────────
def _build_mindmap_i18n() -> dict:
    """Return the translation dict for the current addon language."""
    return {
        'tutorial': _('Tutorial'),
        'fit_map': _('Show entire map'),
        'tour_step': _('Step {current} of {total}'),
        'tour_style': _('Right click a node and choose a different color or size.'),
        'tour_edit': _('Click the main topic and change its text.'),
        'tour_child': _('Drag the small blue dot on the main topic into an empty area to create a child node.'),
        'tour_navigate': _('Drag the empty canvas to move the view. Use the mouse wheel or the zoom buttons to zoom.'),
        'tour_fit': _('Click Show entire map to bring every node into view. Node positions stay unchanged.'),
        'tour_learn': _('Open the highlighted menu and choose Start Learning. Try revealing a hidden answer.'),
        'tour_done': _('Done. Continue when you are ready.'),
        'tour_finish': _('Finish tutorial'),
        'tour_next': _('Next'),
        'tour_back': _('Back'),
        'tour_skip': _('Skip step'),
        'tour_practice': _('Practice · changes are not saved'),
        'tour_topic': _('My learning topic'),
        'tour_example': _('An example'),
        'tour_exit': _('Exit tutorial'),
        'tour_busy': _('Finish the current editing or learning mode before opening the tutorial.'),
        'tour_invite': _('Discover Mindmaps'),
        'tour_intro_summary': _('Connect ideas visually and test your knowledge with hidden answers.'),
        'tour_intro_steps': _('Six short steps'),
        'tour_intro_create': _('Create and connect nodes'),
        'tour_intro_style': _('Adjust colors and sizes'),
        'tour_intro_navigate': _('Navigate your map and try learning mode'),
        'tour_intro_safe_title': _('Practice with sample data'),
        'tour_intro_safe': _('Your own maps stay untouched. Practice changes are not saved.'),
        'tour_intro_exit': _('You can exit at any time and restart from the menu.'),
        'tour_invite_body': _('Connect ideas visually and test your knowledge with hidden answers. In six short steps, you will create and style nodes, navigate your map and try learning mode. You will use sample data. Your own maps stay untouched and practice changes are not saved. You can exit at any time and restart from the menu.'),
        'tour_start': _('Start tutorial'),
        'tour_not_now': _('Not now'),

        "app_title":        _("MindMap"),
        "new_map":          _("New"),
        "menu_title":       _("Menu"),
        "start_learning":   _("Start Learning"),
        "create_with_ai":   _("Create with AI"),
        "import_map":       _("Import"),
        "export_map":       _("Export"),
        "delete_map":       _("Delete Map"),
        "information":      _("Information"),
        "fullscreen_enter": _("Fullscreen"),
        "fullscreen_exit":  _("Exit Fullscreen"),
        "window_open":      _("New Window"),
        "window_exit":      _("Close Window"),
        "center_view":      _("Center View"),
        "reveal":           _("Reveal"),
        "didnt_know":       _("Didn't know"),
        "i_knew_it":        _("I knew it!"),
        "stop_learning":    _("Stop"),
        "learning_setup":   _("Learning Setup"),
        "scope":            _("Scope"),
        "entire_map":       _("Entire Map"),
        "select_nodes":     _("Select Nodes"),
        "order":            _("Order"),
        "top_down":         _("Top-Down"),
        "random_order":     _("Random"),
        "wrong_penalty":    _("Wrong Answer Penalty"),
        "skip":             _("Skip"),
        "retry_soon":       _("Retry Soon"),
        "revisit_later":    _("Revisit Later"),
        "cancel":           _("Cancel"),
        "start":            _("Start"),
        "tap_to_select":    _("Tap nodes to select:"),
        "footer_hint":      _("Right-click on a node for options. Drag the blue dot to create new nodes."),
        "edit_hints":       _("Edit Hints"),
        "save_status_saved": _("Saved"),
        "save_status_pending": _("Saving..."),
        "save_status_error": _("Save failed"),
        "save":             _("Save"),
        "selected_count":   _("{count} selected"),
        "enter_here":       _("Enter here..."),
        "confirm":          _("Confirm"),
        "undo":             _("Undo (Ctrl+Z)"),
        "redo":             _("Redo (Ctrl+Y)"),
        "error_title":      _("MindMap error"),
        "error_show":       _("Show details"),
        "error_hide":       _("Hide details"),
        "error_copy":       _("Copy error"),
        "error_copied":     _("Copied!"),
        "error_dismiss":    _("Dismiss"),
        "error_unexpected": _("Unexpected error"),
        "error_unexpected_async": _("Unexpected error (async)"),
        "error_safe":       _("Please keep this window open and export your changes. Send the error details to help.synapse.pro@gmail.com."),
        "error_no_stack":   _("(no stack trace available)"),
        "info_basic":       _("Basic Controls"),
        "info_pan":         _("Pan View: Click and drag on the empty background."),
        "info_zoom":        _("Zoom View: Use the mouse wheel or the +/- buttons."),
        "info_move":        _("Move Node: Click and drag any node."),
        "info_child":       _("Create Child Node: Click and drag the blue dot on a node."),
        "info_undo":        _("Undo/Redo: Use the arrows at the top right or Ctrl+Z / Ctrl+Y."),
        "info_edit":        _("Edit Text: Double-click the text inside a node."),
        "info_features":    _("Features"),
        "info_manage":      _("New Map / Delete Map: Manage your mind maps."),
        "info_ai":          _("Create with AI: Generate a mind map from a topic using AI."),
        "info_learn":       _("Start Learning: Review mode with active recall."),
        "info_title":       _("MindMap Information"),
        "ai_step1":        _("Step 1: Customize and Copy the Prompt"),
        "copy_prompt":      _("Copy Prompt"),
        "ai_step2":        _("Step 2: Paste the AI-Generated JSON"),
        "paste_json":      _("Paste JSON here..."),
        "import_mindmap":  _("Import MindMap"),
        "import_save_failed": _("The current mind map could not be saved. Import was cancelled to protect your changes."),
        "import_paste_first": _("Please paste your mind map JSON first."),
        "invalid_json":    _("Invalid JSON: {error}. Make sure you copied the complete JSON object."),
        "invalid_map":     _("This JSON is not a valid mind map: {error}"),
        "import_store_failed": _("The mind map is valid but could not be saved (storage full?)."),
        "import_load_failed": _("Import failed while loading the map: {error}"),
        "import_repaired": _("Mind map imported. Some data was repaired automatically: {details}"),
        "unnamed_map":     _("Unnamed Map"),
        "create_title":    _("Create New MindMap"),
        "enter_name":      _("Please enter a name."),
        "create":          _("Create"),
        "central_topic":   _("Central Topic"),
        "import_json":     _("Import from JSON"),
        "paste_map_json":  _("Paste your mind map JSON data below."),
        "export_json":     _("Export to JSON"),
        "copy_json":       _("Copy the JSON data below."),
        "copy_clipboard":  _("Copy to Clipboard"),
        "nothing_export":  _("Nothing to export: the current mind map was not found in storage."),
        "color":           _("Color"),
        "size":            _("Size"),
        "small":           _("Small"),
        "medium":          _("Medium"),
        "large":           _("Large"),
        "delete_map_confirm": _("Delete this map?"),
        "resize":          _("Resize"),
        "hint_placeholder": _("Hint…"),
        "new_node":        _("New Node"),
        "delete_node_confirm": _("Delete node?"),
        "review_missed":   _("Reviewing missed cards…"),
        "learning_done":   _("Done! Great work!"),
        "recall_prompt":   _("Recall the highlighted node · {remaining} remaining"),
        "recall_correct":  _("Did you recall it correctly?"),
        "storage_read_failed": _("Storage read failed"),
        "storage_corrupt": _("Stored mind map data was corrupted and has been backed up. Starting fresh."),
        "storage_full": _("Could not save: browser storage is full. Export your maps as backup and delete unused maps."),
        "save_failed": _("Could not save mind maps: {error}"),
        "recovery_invalid": _("Recovery data is invalid"),
        "recovery_restored": _("A newer mind map recovery copy was restored."),
        "recovery_memory": _("Your recovery copy is open in memory. Free browser storage or export it before closing."),
        "corrupt_removed_count": _("{count} corrupted mind map(s) were removed so the tool works again. A backup was kept in storage."),
        "repaired_count": _("{count} mind map(s) had invalid data and were repaired automatically."),
        "startup_check": _("Startup check"),
        "loading_map": _("Loading mind map"),
        "corrupt_map_removed": _("This mind map was corrupted and has been removed. A backup was kept in storage."),
        "initialization": _("Initialization"),
        "ai_prompt_intro": _("You are an expert assistant that creates mind maps in a specific JSON format."),
        "ai_prompt_json_only": _("The output must be one valid JSON object and nothing else. Do not add explanations."),
        "ai_prompt_structure": _("Use this JSON structure:"),
        "ai_sample_name": _("Name of the MindMap"),
        "ai_sample_central": _("Central Topic"),
        "ai_sample_branch": _("Main Branch"),
        "ai_sample_subpoint": _("Sub-point"),
        "ai_prompt_generate": _("Generate the mind map JSON now."),
        "tutorial_name": _("MindMap Tutorial"),
        "tutorial_welcome": _("Welcome to the MindMap Tool!"),
        "tutorial_center": _("Center View: Use the Center View button to focus on the root node."),
        "tutorial_manage_nodes": _("Managing Nodes"),
        "tutorial_delete_node": _("Delete Node: Hover over a node and use the minus button."),
        "tutorial_customize": _("Customize Nodes (right-click)"),
        "tutorial_color": _("Change Color: Right-click a node and choose a color."),
        "tutorial_size": _("Change Size: Right-click and choose Small, Medium, or Large."),
        "tutorial_special": _("Special Features"),
        "tutorial_ai_1": _("1. Select Create with AI in the menu."),
        "tutorial_ai_2": _("2. Copy the prompt and paste it into an AI service."),
        "tutorial_ai_3": _("3. Copy the AI's JSON response and paste it back into the tool."),
        "tutorial_recall": _("Turns your map into an active-recall session."),
        "tutorial_hidden": _("Child nodes are hidden so you can recall them."),
        "tutorial_rate": _("Rate your answer to reinforce your memory."),
        "tutorial_data": _("Data & Maps"),
        "tutorial_switch": _("Use the list at the top left to switch between maps."),
        "tutorial_collection": _("New Map and Delete Map manage your collection."),
        "tutorial_backup": _("Import / Export (backup)"),
        "tutorial_export": _("Export saves your map as JSON for backup."),
        "tutorial_import": _("Import loads a map from a JSON file."),
    }


class MindmapBridge(QObject):
    """Control messages without navigating/unloading the HTML document."""

    def __init__(self, panel, page):
        super().__init__(page)
        self._panel = panel
        self._page = page

    @pyqtSlot(str)
    def send(self, command):
        panel, page = self._panel, self._page
        def dispatch():
            if panel.page is page and panel.web_view is not None:
                panel._handle_command(command)
        QTimer.singleShot(0, dispatch)


# --- Custom WebPage: intercepts mindmap://fullscreen navigation ---
class MindmapWebPage(QWebEnginePage):
    """Intercepts mindmap:// navigation requests and routes them to the panel."""

    def __init__(self, panel: "MindmapPanel", profile, parent=None):
        super().__init__(profile, parent)
        self._panel = panel
        self._channel = QWebChannel(self)
        self._bridge = MindmapBridge(panel, self)
        self._channel.registerObject("mindmapHost", self._bridge)
        self.setWebChannel(self._channel)

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        if QUrl is not object and url.scheme() == "mindmap":
            # Compatibility for existing pages; new controls use QWebChannel.
            if is_main_frame:
                command = url.host()
                if command == "switch":
                    command += ":" + url.query()
                elif command == "tutorial-init":
                    command += ":" + ("1" if url.query() == "existing=1" else "0")
                self._bridge.send(command)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


# --- Main panel class ---
class MindmapPanel(QWidget):
    def __init__(self, parent_dock: QDockWidget):
        super().__init__()
        self.parent_dock = parent_dock
        self._profile_folder = mw.pm.profileFolder()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.web_container = QWidget()
        self.web_layout = QVBoxLayout(self.web_container)
        self.web_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.web_container, 1)

        self.web_view: Optional[QWebEngineView] = None
        self.fullscreen_window = None
        self.is_in_fullscreen = False
        self.is_embedded = False  # True when embedded in the Anki main window
        self.current_tool = "mindmap" if workspace_io.enabled_tools()["mindmap"] else "roadmap"
        self._switching = False
        self._roadmap_saving = False
        self._page_generation = 0
        self._roadmap_saved_revision = -1
        self._windowed = False

        self.is_initialized = False
        self._page_ready = False
        self._unload_in_progress = False
        self._unload_for_hide = False
        self._unload_callbacks: list[Callable[[bool], None]] = []

    def load_content(self):
        """Erstellt den Webview und lädt die Mindmap (RAM Verbrauch steigt)."""
        if self.web_view: return

        if QWebEngineView is object:
            self.web_layout.addWidget(QLabel(_("Error: QtWebEngine not available.")))
            return

        self.web_view = QWebEngineView()
        
        if QWebEngineProfile is not object:
            old_storage = os.path.join(constants.addon_path, "web_storage")
            new_storage = old_storage
            if mw and mw.pm and mw.pm.profileFolder():
                new_storage = os.path.join(self._profile_folder, "mindmap_web_data")

            if new_storage != old_storage and os.path.exists(old_storage) and not os.path.exists(new_storage):
                try:
                    shutil.copytree(old_storage, new_storage)
                    print("Mindmap: Data migrated to profile folder.")
                except Exception as e: print(f"Mindmap Migration Warning: {e}")

            os.makedirs(new_storage, exist_ok=True)
            
            # The application owns the profile until the page is actually
            # destroyed. A queued deleteLater on the view is not proof that
            # Qt has finished destroying its page.
            self.profile = QWebEngineProfile(
                "mindmap_persistent_profile_v3", QCoreApplication.instance()
            )
            self.profile.setPersistentStoragePath(new_storage)
            self.page = MindmapWebPage(self, self.profile, self.web_view)
            self.web_view.setPage(self.page)

            # The default tutorial and startup diagnostics are created before
            # loadFinished. Inject translations at DocumentCreation so even
            # those first-run contents use the selected add-on language.
            try:
                boot_i18n = json.dumps(_build_mindmap_i18n(), ensure_ascii=False).replace("</", "<\\/")
                boot_dark = bool(mw and mw.pm.night_mode())
                boot_accent = None
                boot_pressed = None
                try:
                    from .theme import palette
                    boot_palette = palette(boot_dark)
                    boot_accent = boot_palette.get("blue_accent") or boot_palette.get("blue")
                    boot_pressed = boot_palette.get("blue_pressed") or boot_accent
                except Exception:
                    # The post-load theme injection below remains as a fallback.
                    pass
                script = QWebEngineScript()
                script.setName("synapse-mindmap-i18n")
                script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
                script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
                script.setRunsOnSubFrames(False)
                script.setSourceCode(
                    workspace_io.boot_script() + "window.__SYNAPSE_MM_HOSTED__=true;"
                    f"window.__SYNAPSE_MM_I18N__={boot_i18n};"
                    f"window.__SYNAPSE_MM_DARK__={json.dumps(boot_dark)};"
                    f"window.__SYNAPSE_MM_ACCENT__={json.dumps(boot_accent)};"
                    f"window.__SYNAPSE_MM_ACCENT_PRESSED__={json.dumps(boot_pressed)};"
                )
                self.page.scripts().insert(script)
            except Exception as exc:
                print(f"Mindmap: early translation injection failed: {exc}")

        if QWebEngineSettings is not object:
            try:
                s = self.web_view.settings()
                s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
                if hasattr(QWebEngineSettings.WebAttribute, 'AllowFileAccessFromFileUrls'):
                    s.setAttribute(QWebEngineSettings.WebAttribute.AllowFileAccessFromFileUrls, True)
            except Exception: pass

        # Match the page background to the theme BEFORE anything paints —
        # otherwise the view flashes white in dark mode while loading.
        try:
            from .theme import palette
            dark = bool(mw and mw.pm.night_mode())
            self.web_view.page().setBackgroundColor(
                QColor("#2c2c2c") if dark else QColor("#f8f9fa"))
        except Exception:
            pass

        web_ref = self.web_view
        self.web_view.loadFinished.connect(
            lambda ok: self._on_load_finished(ok) if self.web_view is web_ref else None
        )

        self._prepare_roadmap_boot()
        html_path = self._tool_path()
        if os.path.exists(html_path):
            self.web_view.setUrl(QUrl.fromLocalFile(html_path))
        else:
            self.web_view.setHtml(f"<h3>Error: {constants.MINDMAP_HTML_FILENAME} not found.</h3>")

        self.web_layout.addWidget(self.web_view)
        self.is_initialized = True

    def _consider_tutorial_invitation(self, existing_maps: bool) -> None:
        if not self.web_view or not mw or not mw.pm:
            return
        # Record the decision for existing users too; removing their maps later
        # must not make a first-use invitation unexpectedly reappear.
        if _claim_tutorial_invitation(mw.pm.profileFolder()) and not existing_maps:
            self.web_view.page().runJavaScript(
                "if(window.__synapseOfferTutorial) window.__synapseOfferTutorial();"
            )

    def _on_load_finished(self, ok: bool) -> None:
        # Rejected mindmap:// control messages also emit loadFinished(False)
        # in Qt. They do not unload the already usable document. Real document
        # loads explicitly clear _page_ready before setUrl().
        if not ok or not self.web_view:
            return
        self._page_ready = True
        self._inject_i18n()
        self._inject_theme_accent()
        self._set_html_toggle(self.web_view, self.is_in_fullscreen)
        self._set_html_toggle(self.web_view, self.is_embedded, windowed=True)

    def _handle_command(self, command):
        if mw.pm.profileFolder() != self._profile_folder:
            return
        if command.startswith(("anki-links:", "anki-open:")):
            from . import workspace_link_bridge
            QTimer.singleShot(0, lambda: workspace_link_bridge.action(self, command))
            return
        if command in ("image-add", "workspace-import", "workspace-export", "roadmap-export"):
            QTimer.singleShot(0, lambda: workspace_io.action(self, command))
            return
        if command == "settings":
            from .workspace_preferences import popup_script
            self.web_view.page().runJavaScript(popup_script('maps'))
            return
        if command.startswith("settings-save:"):
            from .workspace_preferences import save_command, popup_error
            def saved(ok):
                if not ok:
                    self.web_view.page().runJavaScript(popup_error(_('Could not save the current map. Please try again.')))
                    return
                try:
                    save_command('maps', command)
                    refresh_workspace_settings()
                except Exception as error:
                    self.web_view.page().runJavaScript(popup_error(error))
            self._persist_active(saved)
            return
        if command in ("switch:mindmap", "switch:roadmap"):
            self.switch_tool(command.split(":", 1)[1])
        elif command in ("tutorial-init:0", "tutorial-init:1"):
            self._consider_tutorial_invitation(command.endswith(":1"))
        else:
            action = {
                "roadmap-save": self.save_roadmap,
                "roadmap-export": self.export_roadmap,
                "fullscreen": self.enter_fullscreen,
                "exitfullscreen": self.close_fullscreen,
                "window": self.enter_window,
                "exitwindow": self.exit_window,
            }.get(command)
            if action is not None:
                action()

    def _roadmap_path(self):
        folder = self._profile_folder
        return os.path.join(folder, "SynapsePro_Data", "roadmaps.sqlite3")

    def _tool_path(self):
        return os.path.join(constants.addon_path, "web_roadmap", "index.html") if self.current_tool == "roadmap" else os.path.join(constants.addon_path, constants.MINDMAP_HTML_FILENAME)

    def _prepare_roadmap_boot(self):
        enabled = workspace_io.enabled_tools()
        if not enabled.get(self.current_tool, True):
            self.current_tool = next(key for key, value in enabled.items() if value)
        tracker = getattr(getattr(self, "parent_dock", None), "_synapse_width", None)
        if tracker is not None:
            tracker.select(self.current_tool)
        self._page_generation += 1
        self._roadmap_saved_revision = -1
        scripts = self.page.scripts()
        for script in scripts.toList():
            if script.name() in ("synapse-roadmap-data", "synapse-mindmap-recovery-current"):
                scripts.remove(script)
        if self.current_tool != "roadmap":
            # Refresh on every return, including when LocalStorage was full and
            # the latest switch could persist only the profile recovery copy.
            script = QWebEngineScript()
            script.setName("synapse-mindmap-recovery-current")
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(False)
            script.setSourceCode("window.__SYNAPSE_MM_RECOVERY__=" + json.dumps(_load_mindmap_recovery(self._profile_folder), ensure_ascii=True) + ";")
            scripts.insert(script)
            return
        try:
            data = roadmap_store.load(self._roadmap_path())
            first_use = not data["maps"] and roadmap_store.is_first_use(self._roadmap_path())
            error = None
        except Exception:
            data = None
            first_use = False
            error = _("Could not load your data. Nothing has been overwritten. Please try again.")
        script = QWebEngineScript()
        script.setName("synapse-roadmap-data")
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(False)
        script.setSourceCode("window.__ROADMAP_FIRST_RUN__=" + json.dumps(first_use) + ";window.__ROADMAP_HOSTED__=true;window.__ROADMAP_DATA__=" + json.dumps(data, ensure_ascii=True) + ";window.__ROADMAP_ERROR__=" + json.dumps(error) + ";")
        scripts.insert(script)

    def _persist_active(self, done):
        web = self.web_view
        if not web or not self._page_ready:
            done(not self._page_ready)
            return
        is_roadmap = self.current_tool == "roadmap"
        generation = self._page_generation
        finished = False
        def complete(ok):
            nonlocal finished
            if finished:
                return
            finished = True
            done(ok)
        def receive(result):
            if finished or self.web_view is not web or generation != self._page_generation:
                complete(False)
                return
            try:
                if not isinstance(result, dict):
                    complete(False)
                    return
                if is_roadmap:
                    revision = int(result.get("revision", 0))
                    if revision >= self._roadmap_saved_revision:
                        roadmap_store.save(self._roadmap_path(), result["data"])
                        self._roadmap_saved_revision = revision
                    web.page().runJavaScript("window.__roadmapSaved && window.__roadmapSaved(true," + json.dumps(result.get("revision")) + ");")
                    complete(True)
                else:
                    recovery = _write_mindmap_recovery(result["snapshot"], int(result["savedAt"]), self._profile_folder)
                    complete(result.get("saved") is True or recovery)
            except Exception:
                if is_roadmap:
                    web.page().runJavaScript("window.__roadmapSaved && window.__roadmapSaved(false);")
                complete(False)
        method = "__roadmapSnapshot" if is_roadmap else "__synapseFlushMindmap"
        try:
            web.page().runJavaScript("window." + method + " ? window." + method + "() : null", receive)
            QTimer.singleShot(5000, lambda: complete(False))
        except Exception:
            complete(False)

    def export_roadmap(self):
        if self.current_tool != "roadmap" or not self.web_view:
            return
        def receive(result):
            if not isinstance(result, dict):
                return
            try:
                data = roadmap_store.validate(result["data"])
                active = next(m for m in data["maps"] if m["id"] == data["active"])
                from aqt.qt import QFileDialog
                path, _filter = QFileDialog.getSaveFileName(self, _("Export"), "FreeMap.json", "JSON (*.json)")
                if not path:
                    return
                payload = {"version": 1, "active": active["id"], "maps": [active]}
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, ensure_ascii=False, indent=2)
            except Exception:
                if self.web_view:
                    self.web_view.page().runJavaScript("alert(" + json.dumps(_("Export failed. Please try again.")) + ");")
        self.web_view.page().runJavaScript("window.__roadmapSnapshot && window.__roadmapSnapshot()", receive)

    def save_roadmap(self):
        if self.current_tool != "roadmap" or self._roadmap_saving or self._switching:
            return
        self._roadmap_saving = True
        def done(ok):
            self._roadmap_saving = False
        self._persist_active(done)

    def switch_tool(self, target):
        if target not in ("mindmap", "roadmap") or not workspace_io.enabled_tools().get(target) or target == self.current_tool or self._switching or self._unload_in_progress or not self._page_ready:
            return
        self._switching = True
        # Freeze input while the final snapshot crosses the asynchronous bridge.
        self.web_view.setEnabled(False)
        def done(ok):
            self._switching = False
            if not self.web_view:
                return
            self.web_view.setEnabled(True)
            if not ok:
                self.web_view.page().runJavaScript("alert('Speichern fehlgeschlagen. Die aktuelle Ansicht bleibt geöffnet.');")
                return
            self.current_tool = target
            self._page_ready = False
            self._prepare_roadmap_boot()
            self.web_view.setUrl(QUrl.fromLocalFile(self._tool_path()))
        self._persist_active(done)

    def _destroy_web_view(self, web_ref) -> None:
        if self.web_view is not web_ref:
            return
        self.web_layout.removeWidget(web_ref)
        # Delete the profile only after Qt emits the page's destroyed signal.
        # Its application parent also keeps the Python wrapper from releasing
        # the native profile while deleteLater is still waiting in the queue.
        profile_ref = self.profile
        page_ref = self.page
        if profile_ref is not None:
            page_ref.destroyed.connect(profile_ref.deleteLater)
        web_ref.hide()
        web_ref.deleteLater()
        self.web_view = None
        self.profile = None
        self.page = None
        self.is_initialized = False
        self._page_ready = False
        self._page_generation += 1

    def _complete_unload(self, web_ref, durable: bool) -> None:
        def finish_outside_js_callback():
            # A quick hide/show must not destroy the view that was just reopened.
            reopened = self._unload_for_hide and (
                self.parent_dock.isVisible() or self.is_in_fullscreen or self.is_embedded
            )
            if self.web_view is web_ref:
                if durable and not reopened:
                    self._destroy_web_view(web_ref)
                else:
                    web_ref.setEnabled(True)
            self._unload_in_progress = False
            self._finish_unload_callbacks(durable)
        # Removing a dock or destroying WebEngine objects inside a JavaScript
        # result callback can re-enter Qt's hideEvent on a partially torn-down view.
        QTimer.singleShot(0, finish_outside_js_callback)

    def unload_content(
        self, on_complete: Optional[Callable[[bool], None]] = None,
        *, only_if_hidden: bool = False,
    ) -> None:
        """Persist LocalStorage plus a disk recovery copy before freeing RAM."""
        if on_complete:
            self._unload_callbacks.append(on_complete)
        if not self.web_view:
            self._finish_unload_callbacks(True)
            return
        if self._unload_in_progress:
            if not only_if_hidden:
                self._unload_for_hide = False
            return
        self._unload_for_hide = only_if_hidden

        if self.current_tool == "roadmap":
            self._unload_in_progress = True
            web_ref = self.web_view
            web_ref.setEnabled(False)
            def finished(ok):
                self._complete_unload(web_ref, ok)
            self._persist_active(finished)
            return
        self._unload_in_progress = True
        web_ref = self.web_view
        page_was_ready = self._page_ready
        completed = False

        def finish(durable: bool) -> None:
            nonlocal completed
            if completed:
                return
            completed = True
            self._complete_unload(web_ref, durable)

        def receive_snapshot(result) -> None:
            if self.web_view is not web_ref:
                finish(True)
                return
            if result is None:
                finish(not page_was_ready)
                return
            if not isinstance(result, dict):
                finish(False)
                return

            snapshot = result.get("snapshot")
            local_saved = result.get("saved") is True
            try:
                saved_at = int(result.get("savedAt") or int(time.time() * 1000))
            except (TypeError, ValueError):
                saved_at = int(time.time() * 1000)
            recovery_saved = (
                isinstance(snapshot, str)
                and _write_mindmap_recovery(snapshot, saved_at, self._profile_folder)
            )
            finish(local_saved or recovery_saved)

        js = (
            "(typeof window.__synapseFlushMindmap === 'function')"
            " ? window.__synapseFlushMindmap() : null"
        )
        try:
            web_ref.page().runJavaScript(js, receive_snapshot)
            # A renderer failure must not discard the live page. Timeout only
            # unlocks the panel and deliberately keeps the WebView in memory.
            QTimer.singleShot(5000, lambda: finish(False))
        except Exception as exc:
            print(f"Mindmap final save request failed: {exc}")
            finish(False)

    def _finish_unload_callbacks(self, saved: bool) -> None:
        callbacks = self._unload_callbacks
        self._unload_callbacks = []
        for callback in callbacks:
            try:
                callback(saved)
            except Exception as exc:
                print(f"Mindmap unload callback failed: {exc}")

    def _inject_i18n(self):
        """Inject the translation dict and call applyMindmapI18n() in the page."""
        if not self.web_view:
            return
        try:
            import json
            strings = _build_mindmap_i18n()
            dark = bool(mw and mw.pm.night_mode())
            js = (
                workspace_io.boot_script() + f"window.__SYNAPSE_MM_I18N__ = {json.dumps(strings, ensure_ascii=False)};"
                f"document.documentElement.classList.toggle('dark', {json.dumps(dark)});"
                f"if(window.applyMindmapI18n) applyMindmapI18n();if(window.applyWorkspaceI18n) applyWorkspaceI18n();"
            )
            self.web_view.page().runJavaScript(js)
        except Exception:
            pass

    def _inject_theme_accent(self):
        """Apply the add-on's colour theme to the page.

        Overrides the hardcoded ``--primary-color`` CSS variable so the root
        node (and selection rings, drag handles …) use the accent colour of
        whichever theme the user picked instead of the default blue.
        """
        if not self.web_view:
            return
        try:
            from .theme import palette
            c = palette(bool(mw and mw.pm.night_mode()))
            accent = c.get("blue_accent") or c.get("blue")
            pressed = c.get("blue_pressed") or accent
            js = ""
            if accent:
                js += (
                    "document.documentElement.style.setProperty('--primary-color', %s);"
                    "document.documentElement.style.setProperty('--primary-color-dark', %s);"
                ) % (json.dumps(accent), json.dumps(pressed))
            js += (
                "if(window.__synapseMarkMindmapThemeReady) "
                "window.__synapseMarkMindmapThemeReady();"
            )
            self.web_view.page().runJavaScript(js)
        except Exception:
            # Never leave the loading cover stuck just because a custom palette
            # could not be read. The HTML still has safe light/dark defaults.
            try:
                self.web_view.page().runJavaScript(
                    "if(window.__synapseMarkMindmapThemeReady) "
                    "window.__synapseMarkMindmapThemeReady();"
                )
            except Exception:
                pass

    def enter_fullscreen(self):
        if not self.web_view: return
        if self.is_in_fullscreen or self.is_embedded: return
        self.is_in_fullscreen = True

        self.web_layout.removeWidget(self.web_view)
        self.web_view.setParent(None)
        self.parent_dock.hide()

        self.fullscreen_window = MindmapFullscreenWindow(self, self.web_view)
        self.fullscreen_window.showFullScreen()

        self._set_html_toggle(self.web_view, True, windowed=False)

    def close_fullscreen(self):
        """Called from the HTML fullscreen button while in fullscreen."""
        if self.fullscreen_window:
            self.fullscreen_window.close()  # triggers exit_fullscreen via closeEvent

    def exit_fullscreen(self, web_view_ref):
        self.is_in_fullscreen = False
        self.fullscreen_window = None

        self.web_layout.addWidget(web_view_ref)
        self.parent_dock.show()

        self._set_html_toggle(web_view_ref, False, windowed=False)

    # ── Embedded view (inside the Anki main window) ──
    def enter_window(self):
        if not self.web_view: return
        if self.is_in_fullscreen or self.is_embedded: return

        # IMPORTANT: set the flag *before* hiding the dock. Hiding the dock
        # fires visibilityChanged, whose handler would otherwise destroy the
        # web view (RAM saving) via unload_content(). The flag suppresses that
        # teardown so the borrowed web view survives to be embedded.
        self.is_embedded = True
        self.web_layout.removeWidget(self.web_view)
        self.web_view.setParent(None)
        self.parent_dock.hide()

        ok = embedded_window.embed(self.web_view, self.exit_window, _("MindMap"),
                                   show_header=False)
        if not ok:
            self.is_embedded = False
            self.web_layout.addWidget(self.web_view)
            self.parent_dock.show()
            return
        self._set_html_toggle(self.web_view, True, windowed=True)

    def exit_window(self):
        if not self.is_embedded:
            return
        self.is_embedded = False
        wv = self.web_view
        if wv is not None:
            self.web_layout.addWidget(wv)  # reparents out of the container
        embedded_window.restore()
        self.parent_dock.show()
        self.parent_dock.raise_()
        if wv is not None:
            self._set_html_toggle(wv, False, windowed=True)

    def _set_html_toggle(self, web_view_ref, active, windowed=False):
        """Update the fullscreen or window button state inside the page."""
        try:
            import json
            strings = _build_mindmap_i18n()
            t_json = json.dumps(strings, ensure_ascii=False)
            flag = "true" if active else "false"
            fn = "__synapseSetWindow" if windowed else "__synapseSetFullscreen"
            web_view_ref.page().runJavaScript(
                f"if(window.{fn}) {fn}({flag}, {t_json});"
            )
        except Exception:
            pass

    def on_visibility_changed(self, visible):
        """RAM-Management Logik"""
        if visible:
            self.load_content()
        else:
            if not self.is_in_fullscreen and not self.is_embedded:
                self.unload_content(only_if_hidden=True)

# --- Setup & Toggle ---

def setup_mindmap_dock():
    global mindmap_dock
    if not mw or QDockWidget is object or mindmap_dock: return

    try:
        mindmap_dock = QDockWidget("MindMap", mw)
        mindmap_dock.setObjectName(constants.MINDMAP_DOCK_OBJECT_NAME)
        if Qt: mindmap_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)

        title_bar = QWidget()
        title_bar.setFixedHeight(0)
        mindmap_dock.setTitleBarWidget(title_bar)

        panel = MindmapPanel(mindmap_dock)
        mindmap_dock.setWidget(panel)
        
        mindmap_dock.visibilityChanged.connect(panel.on_visibility_changed)

        from .sidebar_widths import attach
        attach(mw, mindmap_dock, panel.current_tool,
               lambda: panel.is_in_fullscreen or panel.is_embedded)
        if Qt: mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, mindmap_dock)
        mindmap_dock.setVisible(False)

    except Exception as e:
        print(f"MindmapSidebar Setup Error: {e}")
        traceback.print_exc()

def toggle_mindmap_dock():
    if mindmap_dock is None:
        setup_mindmap_dock()
    
    if mindmap_dock:
        if mindmap_dock.isVisible():
            mindmap_dock.hide()
        else:
            mindmap_dock.show()
            mindmap_dock.raise_()

def cleanup_mindmap_sidebar():
    global mindmap_dock
    if not mindmap_dock:
        return

    dock_ref = mindmap_dock
    mindmap_dock = None
    panel = dock_ref.widget()

    def dispose(saved: bool) -> None:
        global mindmap_dock
        if not saved:
            # Do not deliberately destroy the only live copy when both
            # LocalStorage and the recovery-file write failed.
            return
        try:
            mw.removeDockWidget(dock_ref)
        except Exception:
            pass
        dock_ref.deleteLater()
        if mindmap_dock is dock_ref:
            mindmap_dock = None

    if isinstance(panel, MindmapPanel):
        if panel.fullscreen_window:
            panel.fullscreen_window.close()
        if panel.is_embedded:
            panel.exit_window()
        panel.unload_content(dispose)
    else:
        dispose(True)


def refresh_workspace_settings():
    """Persist before rebuilding tabs/language; defer navigation out of JS callbacks."""
    if not mindmap_dock:
        return
    panel = mindmap_dock.widget()
    if not panel or not panel.web_view or not panel._page_ready:
        return
    def saved(ok):
        if not ok:
            return
        def reload_page():
            if not panel.web_view:
                return
            scripts = panel.page.scripts()
            for script in scripts.toList():
                if script.name() == 'synapse-workspace-settings':
                    scripts.remove(script)
            script = QWebEngineScript()
            script.setName('synapse-workspace-settings')
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(False)
            script.setSourceCode(workspace_io.boot_script() +
                'window.__SYNAPSE_MM_I18N__=' + json.dumps(_build_mindmap_i18n()) + ';' +
                'window.__SYNAPSE_MM_DARK__=' + json.dumps(bool(mw.pm.night_mode())) + ';')
            scripts.insert(script)
            panel._page_ready = False
            panel._prepare_roadmap_boot()
            panel.web_view.setUrl(QUrl.fromLocalFile(panel._tool_path()))
        QTimer.singleShot(0, reload_page)
    panel._persist_active(saved)


def refresh_workspace_theme():
    """Apply Anki's appearance to either editor without reloading or losing undo."""
    if not mindmap_dock:
        return
    panel = mindmap_dock.widget()
    if not panel or not panel.web_view:
        return
    dark = json.dumps(bool(mw and mw.pm.night_mode()))
    panel.web_view.page().runJavaScript(
        'window.__SYNAPSE_MM_DARK__='+dark+';document.documentElement.classList.toggle("dark",'+dark+');')
    panel._inject_theme_accent()
    # Keep early-paint values correct on the next tab switch too.
    import re
    scripts = panel.page.scripts()
    for script in scripts.toList():
        if script.name() in ('synapse-mindmap-i18n','synapse-workspace-settings'):
            source = re.sub(r'window\.__SYNAPSE_MM_DARK__\s*=\s*(?:true|false);', 'window.__SYNAPSE_MM_DARK__='+dark+';', script.sourceCode())
            scripts.remove(script)
            script.setSourceCode(source)
            scripts.insert(script)
