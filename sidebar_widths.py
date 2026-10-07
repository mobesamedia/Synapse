"""Session-only widths for SynapsePro tools; no content or profile-file writes.

Qt's dock area can reuse the width of a different hidden dock. Restore each
feature's own splitter choice on show/tool change, using a 400 px starting width
until the user actually drags the main-window dock separator. Main-window
resizes, floating windows and embedded/fullscreen tools do not teach widths.
"""
from aqt.qt import QObject, QEvent, QTimer, Qt


DEFAULT_SIDEBAR_WIDTH = 400


def width_group(feature):
    if feature in ("mindmap", "roadmap"):
        return "maps"
    if feature in ("notebook", "todo", "pdf"):
        return "notebook"
    return feature


class SidebarWidth(QObject):
    def __init__(self, window, dock, feature, suspended=None):
        super().__init__(dock)
        self.window = window
        self.dock = dock
        self.feature = width_group(feature)
        self.suspended = suspended or (lambda: False)
        self.widths = {}
        self.drag_size = None
        self.drag_feature = None
        self.drag_changed = False
        self.restoring = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.restore)
        dock.installEventFilter(self)
        window.installEventFilter(self)
        dock.topLevelChanged.connect(lambda _floating: self.schedule())

    def active(self):
        return (self.dock.isVisible() and not self.dock.isFloating()
                and not self.suspended()
                and self.window.dockWidgetArea(self.dock) in (
                    Qt.DockWidgetArea.LeftDockWidgetArea,
                    Qt.DockWidgetArea.RightDockWidgetArea))

    def schedule(self):
        self.timer.start(0)

    def select(self, feature):
        feature = width_group(feature)
        if feature == self.feature:
            return
        self.feature = feature
        self.drag_size = None
        self.schedule()

    def restore(self):
        if not self.active():
            return
        requested = self.widths.get(self.feature, DEFAULT_SIDEBAR_WIDTH)
        center = self.window.centralWidget()
        center_min = max(160, center.minimumWidth(), center.minimumSizeHint().width()) if center else 160
        available = max(self.dock.minimumWidth(), self.window.contentsRect().width() - center_min - 12)
        self.restoring = True
        try:
            self.window.resizeDocks([self.dock], [min(requested, available)], Qt.Orientation.Horizontal)
        finally:
            self.restoring = False

    def eventFilter(self, watched, event):
        kind = event.type()
        if watched is self.window:
            if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self.drag_size = self.window.size()
                self.drag_feature = self.feature
                self.drag_changed = False
            elif kind == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if (self.drag_changed and self.drag_size == self.window.size()
                        and self.drag_feature == self.feature and self.active()):
                    self.widths[self.feature] = self.dock.width()
                self.drag_size = None
                self.drag_changed = False
        elif watched is self.dock:
            if kind == QEvent.Type.Show:
                self.schedule()
            elif kind == QEvent.Type.Hide:
                self.timer.stop()
                self.drag_size = None
                self.drag_changed = False
            elif (kind == QEvent.Type.Resize and self.drag_size is not None
                  and not self.restoring and self.active()
                  and event.oldSize().width() != event.size().width()):
                self.drag_changed = True
        return False


def attach(window, dock, feature, suspended=None):
    """Attach once, after setting content and before the first show."""
    tracker = getattr(dock, '_synapse_width', None)
    if tracker is None:
        tracker = SidebarWidth(window, dock, feature, suspended)
        dock._synapse_width = tracker
    return tracker


def select(dock, feature):
    tracker = getattr(dock, '_synapse_width', None)
    if tracker is not None:
        tracker.select(feature)
