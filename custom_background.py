# -*- coding: utf-8 -*-
"""Fast, profile-local custom background rendering for SynapsePro.

The image is decoded once and painted by one native QWidget behind Anki's
top/main/bottom web views. Chromium only receives transparent backgrounds;
it never decodes or composites a second copy of the image.
"""

from __future__ import annotations

import base64
import os
from typing import Optional

from aqt import mw
from aqt.qt import (
    QColor, QEvent, QFileDialog, QGraphicsBlurEffect, QGraphicsPixmapItem,
    QGraphicsScene, QImageReader, QPainter, QPixmap, QRectF, QSize, Qt, QTimer,
    QWidget,
)
from aqt.utils import showWarning

from .locales import _

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_SOURCE_EDGE = 10_000
MAX_STORED_WIDTH = 3840
MAX_STORED_HEIGHT = 2160
ACTIVE_STATES = {"deckBrowser", "overview"}

_layer: Optional["BackgroundLayer"] = None
_settings = {}


def _storage_dir() -> str:
    profile = mw.pm.profileFolder() if mw and getattr(mw, "pm", None) else ""
    return os.path.join(profile, "SynapsePro_Data", "custom_background")


def image_path() -> str:
    return os.path.join(_storage_dir(), "background.jpg")


def _preview_path() -> str:
    return os.path.join(_storage_dir(), "preview.jpg")


def pending_image_path() -> str:
    return os.path.join(_storage_dir(), "pending.jpg")


def _preview_for(path: str) -> str:
    return _preview_path() if path == image_path() else path + ".preview.jpg"


def has_image() -> bool:
    try:
        return os.path.isfile(image_path()) and os.path.getsize(image_path()) > 0
    except OSError:
        return False


def preview_data_uri() -> str:
    return data_uri_for(image_path())


def data_uri_for(path: str) -> str:
    try:
        if not path or not os.path.isfile(path):
            return ""
        candidate = _preview_for(path)
        preview = candidate if os.path.isfile(candidate) else path
        with open(preview, "rb") as handle:
            return "data:image/jpeg;base64," + base64.b64encode(handle.read()).decode("ascii")
    except Exception:
        return ""


def would_upscale_strongly(path: Optional[str] = None) -> bool:
    """Return whether cover rendering needs substantial enlargement.

    The check uses the current window's physical pixel size, so a portrait or
    low-resolution image is judged against the display it will actually fill.
    It is advisory only and never rejects an otherwise valid image.
    """
    candidate = path or image_path()
    try:
        reader = QImageReader(candidate)
        reader.setAutoTransform(True)
        size = reader.size()
        parent = mw.centralWidget() if mw else None
        if size.width() < 1 or size.height() < 1 or parent is None:
            return False
        dpr = max(1.0, float(parent.devicePixelRatioF()))
        target_w = max(1.0, parent.width() * dpr)
        target_h = max(1.0, parent.height() * dpr)
        cover_scale = max(target_w / size.width(), target_h / size.height())
        return cover_scale > 1.35
    except Exception:
        return False


def import_image(parent=None, target_path: Optional[str] = None) -> bool:
    """Ask for an image, then validate and store an optimized local JPEG."""
    filename, _filter = QFileDialog.getOpenFileName(
        parent,
        _("Choose Background Image"),
        "",
        _("Images (*.jpg *.jpeg *.png *.webp)"),
    )
    if not filename:
        return False
    return import_image_file(filename, parent=parent, target_path=target_path)


def import_image_file(
    filename: str,
    parent=None,
    target_path: Optional[str] = None,
) -> bool:
    """Validate and optimize a known local image path.

    Used by both the native file picker and bundled Starter Wallpapers, so
    examples receive exactly the same safety and performance checks as user
    images.
    """
    target = target_path or image_path()
    try:
        size_bytes = os.path.getsize(filename)
        if size_bytes <= 0 or size_bytes > MAX_FILE_BYTES:
            raise ValueError(_("The image must be smaller than 20 MB."))

        reader = QImageReader(filename)
        reader.setAutoTransform(True)
        can_read = reader.canRead()
        image_format = bytes(reader.format()).decode("ascii", "ignore").lower()
        if not can_read or image_format not in ("jpg", "jpeg", "png", "webp"):
            raise ValueError(_("Please choose a valid PNG, JPEG or WebP image."))
        try:
            if reader.supportsAnimation() and reader.imageCount() != 1:
                raise ValueError(_("Animated images are not supported."))
        except AttributeError:
            pass
        source_size = reader.size()
        width, height = source_size.width(), source_size.height()
        if width < 1 or height < 1:
            raise ValueError(_("The image dimensions could not be read."))
        if (width > MAX_SOURCE_EDGE or height > MAX_SOURCE_EDGE
                or width * height > MAX_PIXELS):
            raise ValueError(_("The image is too large. Use an image below 40 megapixels."))

        scale = min(1.0, MAX_STORED_WIDTH / width, MAX_STORED_HEIGHT / height)
        if scale < 1.0:
            reader.setScaledSize(QSize(max(1, int(width * scale)), max(1, int(height * scale))))
        image = reader.read()
        if image.isNull():
            raise ValueError(_("The image could not be decoded."))

        os.makedirs(_storage_dir(), exist_ok=True)
        temporary = target + ".tmp.jpg"
        if not image.save(temporary, "JPEG", 88):
            raise ValueError(_("The optimized background could not be saved."))
        os.replace(temporary, target)
        preview = image.scaled(
            QSize(720, 405), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        preview.save(_preview_for(target), "JPEG", 78)
        return True
    except Exception as exc:
        try:
            temporary = target + ".tmp.jpg"
            if os.path.exists(temporary):
                os.remove(temporary)
        except OSError:
            pass
        showWarning(str(exc), parent=parent)
        return False


def remove_image() -> None:
    try:
        for path in (image_path(), _preview_path()):
            if os.path.exists(path):
                os.remove(path)
    except OSError as exc:
        print(f"SynapsePro: could not remove custom background: {exc}")


def discard_pending() -> None:
    for path in (pending_image_path(), _preview_for(pending_image_path())):
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def commit_pending() -> bool:
    pending = pending_image_path()
    if not os.path.isfile(pending):
        return False
    os.replace(pending, image_path())
    pending_preview = _preview_for(pending)
    if os.path.isfile(pending_preview):
        os.replace(pending_preview, _preview_path())
    return True


def _blur_pixmap(source: QPixmap, radius: int) -> QPixmap:
    """Create one cached blurred pixmap; never blur during paint events."""
    if source.isNull() or radius <= 0:
        return source
    # Blur a bounded working image. This one-time GPU/Qt operation stays fast
    # even when the imported source came from a 4K display.
    working = source
    if max(source.width(), source.height()) > 2560:
        working = source.scaled(
            QSize(2560, 2560), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(working)
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(float(radius))
    effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    pad = max(2, radius * 2)
    output = QPixmap(working.width() + pad * 2, working.height() + pad * 2)
    output.fill(Qt.GlobalColor.transparent)
    painter = QPainter(output)
    scene.render(
        painter,
        QRectF(0, 0, output.width(), output.height()),
        QRectF(-pad, -pad, output.width(), output.height()),
    )
    painter.end()
    return output.copy(pad, pad, working.width(), working.height())


class BackgroundLayer(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self._overlay = 0
        self._position = "center"
        self._cache_key = None
        self.setObjectName("SynapseCustomBackgroundLayer")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        parent.installEventFilter(self)
        self.setGeometry(parent.rect())
        self.lower()
        self.hide()

    def eventFilter(self, watched, event):
        if watched is self.parentWidget() and event.type() in (
            QEvent.Type.Resize, QEvent.Type.Show,
        ):
            self.setGeometry(watched.rect())
            self.lower()
        return False

    def load(self, blur_radius: int, overlay: int, position: str = "center") -> None:
        blur_radius = max(0, min(30, int(blur_radius)))
        try:
            key = (image_path(), os.path.getmtime(image_path()), blur_radius)
        except OSError:
            key = None
        if key != self._cache_key:
            source = QPixmap(image_path()) if has_image() else QPixmap()
            self._pixmap = _blur_pixmap(source, blur_radius)
            self._cache_key = key
        self._overlay = max(0, min(70, int(overlay)))
        self._position = position if position in ("top", "center", "bottom") else "center"
        self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        target = self.rect()
        source = self._pixmap.rect()
        scale = max(target.width() / source.width(), target.height() / source.height())
        visible_w = target.width() / scale
        visible_h = target.height() / scale
        sx = (source.width() - visible_w) / 2.0
        if self._position == "top":
            sy = 0.0
        elif self._position == "bottom":
            sy = source.height() - visible_h
        else:
            sy = (source.height() - visible_h) / 2.0
        painter.drawPixmap(QRectF(target), self._pixmap, QRectF(sx, sy, visible_w, visible_h))
        if self._overlay:
            painter.fillRect(target, QColor(0, 0, 0, round(255 * self._overlay / 100)))
        painter.end()


def setup(settings: dict) -> None:
    global _layer, _settings
    _settings = dict(settings or {})
    if not mw:
        return
    parent = mw.centralWidget()
    if parent is None:
        return
    if _layer is None:
        _layer = BackgroundLayer(parent)
    if _settings.get("custom_background_enabled", False) and has_image():
        _layer.load(
            int(_settings.get("custom_background_blur", 0) or 0),
            int(_settings.get("custom_background_overlay", 0) or 0),
            str(_settings.get("custom_background_position", "center") or "center"),
        )
    sync_state(getattr(mw, "state", ""))


def canvas_script(active: bool, include_body: bool = True) -> str:
    """Return JS that makes the document canvas deterministically transparent.

    Inline ``!important`` properties are intentional here. Dark colour themes
    can load after add-on styles and use equally specific selectors on html;
    an inline property removes that stylesheet-order race on every platform.
    """
    enabled = "true" if active else "false"
    body_expr = "document.body" if include_body else "null"
    return (
        "(function(){var on=" + enabled + ",nodes=[document.documentElement,"
        + body_expr + "];for(var i=0;i<nodes.length;i++){var n=nodes[i];if(!n)continue;"
        "n.classList.toggle(i===0?'synapse-custom-background-root':"
        "'synapse-custom-background',on);"
        "if(on){n.style.setProperty('background','transparent','important');"
        "n.style.setProperty('background-color','transparent','important');"
        "n.style.setProperty('background-image','none','important');}else{"
        "n.style.removeProperty('background');n.style.removeProperty('background-color');"
        "n.style.removeProperty('background-image');}}})();"
    )


def _set_page_transparency(active: bool) -> None:
    color = QColor(0, 0, 0, 0) if active else QColor(
        "#2c2c2c" if mw and mw.pm.night_mode() else "#f5f5f5"
    )
    views = (
        getattr(getattr(mw, "toolbar", None), "web", None),
        getattr(mw, "web", None), getattr(mw, "bottomWeb", None),
    )
    js = canvas_script(active)
    for view in views:
        try:
            if view is not None and view.page() is not None:
                view.page().setBackgroundColor(color)
                view.eval(js)
        except Exception:
            pass


def sync_state(state: str) -> None:
    enabled = bool(_settings.get("custom_background_enabled", False))
    active = bool(enabled and has_image() and state in ACTIVE_STATES)
    if _layer is not None:
        _layer.setVisible(active)
        if active:
            _layer.lower()
    _set_page_transparency(active)
    # Anki can replace a WebEngine document shortly after its state hook. The
    # delayed pass evaluates the *current* state, so a rapid jump into Review
    # can never accidentally restore the dashboard background.
    def resync_document() -> None:
        current = getattr(mw, "state", "") if mw else ""
        current_active = bool(
            _settings.get("custom_background_enabled", False)
            and has_image() and current in ACTIVE_STATES
        )
        _set_page_transparency(current_active)
    try:
        QTimer.singleShot(0, resync_document)
        QTimer.singleShot(100, resync_document)
    except Exception:
        pass


def inject_style(web_content, active: bool) -> None:
    """Override only page canvases; retain SynapsePro widget/theme styling."""
    if active:
        # Applied while the head is parsed, before body classes or the first
        # visible frame. This avoids Chromium briefly painting its black/default
        # canvas while Anki swaps between dashboard documents.
        web_content.head = (
            "<script>" + canvas_script(True, include_body=False) + "</script>"
            + web_content.head
        )
    web_content.head += """
<style id="synapse-custom-background-style">
html.synapse-custom-background-root,
html.synapse-custom-background-root body,
html.synapse-custom-background-root body.deckbrowser,
html.synapse-custom-background-root body.overview,
html.synapse-custom-background-root body:has(#custom-dashboard),
html:has(body.synapse-custom-background),
body.synapse-custom-background {
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
}
/* The colour themes target the custom overview through #custom-dashboard.
   That ID makes their rule more specific than the generic canvas reset above,
   so explicitly beat it without changing any of the overview cards. */
html:has(body.synapse-custom-background):has(#custom-dashboard),
html:has(body.synapse-custom-background.overview),
body.synapse-custom-background:has(#custom-dashboard),
body.synapse-custom-background.overview,
body.synapse-custom-background #overview-wrapper {
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
  background-attachment: initial !important;
}
body.synapse-custom-background.top-toolbar .header,
body.synapse-custom-background.top-toolbar #header,
body.synapse-custom-background.top-toolbar .toolbar,
body.synapse-custom-background.top-toolbar .left-tray,
body.synapse-custom-background.top-toolbar .right-tray,
body.synapse-custom-background.top-toolbar center,
body.synapse-custom-background.top-toolbar table,
body.synapse-custom-background.bottom-toolbar #outer,
body.synapse-custom-background.bottom-toolbar #header,
body.synapse-custom-background.bottom-toolbar #inner,
body.synapse-custom-background.bottom-toolbar #innertable,
body.synapse-custom-background.bottom-toolbar center,
body.synapse-custom-background.bottom-toolbar table {
  background: transparent !important;
  background-color: transparent !important;
  box-shadow: none !important;
  border-color: transparent !important;
}
/* One stable solid toolbar surface instead of one coloured tile per button.
   backdrop-filter is deliberately avoided: it creates separate GPU layers
   and renders differently across Qt's macOS, Windows and Linux backends. */
body.synapse-custom-background.top-toolbar .header .toolbar,
body.synapse-custom-background.top-toolbar #header .toolbar,
html:has(body.synapse-custom-background.top-toolbar) .header:has(a#decks) .toolbar,
html:has(body.synapse-custom-background.top-toolbar) #header:has(a#decks) .toolbar {
  background: #ffffff !important;
  border: 1px solid rgba(20, 24, 32, 0.12) !important;
  border-top: 0 !important;
  border-radius: 0 0 10px 10px !important;
  box-shadow: 0 1px 4px rgba(18, 24, 32, 0.16) !important;
  overflow: hidden !important;
}
body.nightMode.synapse-custom-background.top-toolbar .header .toolbar,
body.nightMode.synapse-custom-background.top-toolbar #header .toolbar,
html:has(body.nightMode.synapse-custom-background.top-toolbar) .header:has(a#decks) .toolbar,
html:has(body.nightMode.synapse-custom-background.top-toolbar) #header:has(a#decks) .toolbar {
  background: #2c2c2e !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.34) !important;
}
body.synapse-custom-background.top-toolbar a.hitem,
html:has(body.synapse-custom-background.top-toolbar) .header:has(a#decks) a.hitem,
html:has(body.synapse-custom-background.top-toolbar) #header:has(a#decks) a.hitem {
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
  border-color: transparent !important;
  box-shadow: none !important;
}
body.synapse-custom-background.top-toolbar a.hitem:hover,
html:has(body.synapse-custom-background.top-toolbar) .header:has(a#decks) a.hitem:hover,
html:has(body.synapse-custom-background.top-toolbar) #header:has(a#decks) a.hitem:hover {
  background: rgba(120, 128, 142, 0.12) !important;
}
body.nightMode.synapse-custom-background.top-toolbar a.hitem:hover,
html:has(body.nightMode.synapse-custom-background.top-toolbar) .header:has(a#decks) a.hitem:hover,
html:has(body.nightMode.synapse-custom-background.top-toolbar) #header:has(a#decks) a.hitem:hover {
  background: rgba(255, 255, 255, 0.10) !important;
}
</style>
"""
    studied_mode = str(
        _settings.get("custom_background_studied_text", "dark") or "dark"
    ).lower()
    if studied_mode == "light":
        studied_color = "#ffffff"
        studied_shadow = "0 1px 3px rgba(0,0,0,0.58)"
    else:
        studied_color = "#1d1d1f"
        studied_shadow = "0 1px 2px rgba(255,255,255,0.32)"
    web_content.head += (
        '<style id="synapse-custom-background-text-style">'
        'body.synapse-custom-background.deckbrowser #studiedToday{'
        f'color:{studied_color} !important;text-shadow:{studied_shadow} !important;'
        '}</style>'
    )
    if active:
        web_content.body = (
            "<script>" + canvas_script(True) + "</script>"
            + web_content.body
        )


def on_internal_page_styled(web) -> None:
    """Keep Anki's TypeScript congratulations page on the normal canvas."""
    try:
        page = os.path.basename(web.page().url().path()).lower()
        if page in ("congrats", "congrats.html"):
            if _layer is not None:
                _layer.hide()
            _set_page_transparency(False)
    except Exception:
        pass


def cleanup() -> None:
    global _layer, _settings
    _set_page_transparency(False)
    if _layer is not None:
        try:
            parent = _layer.parentWidget()
            if parent is not None:
                parent.removeEventFilter(_layer)
            _layer.deleteLater()
        except RuntimeError:
            pass
    _layer = None
    _settings = {}
