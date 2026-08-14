# -*- coding: utf-8 -*-
import os
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

try:
    from .locales import _
except ImportError:
    def _(text):  # type: ignore
        return text

class ThemeChangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Restart Required"))
        self.setMinimumWidth(360)

        layout = QVBoxLayout()

        # --- Bild Logik (OBEN) ---
        addon_path = os.path.dirname(__file__)
        image_path = os.path.join(addon_path, "media", "mode.png")

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                if pixmap.width() > 350:
                    scaled_pixmap = pixmap.scaledToWidth(
                        350,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    image_label.setPixmap(scaled_pixmap)
                else:
                    image_label.setPixmap(pixmap)

        layout.addWidget(image_label)

        layout.addSpacing(10)

        # --- Text Logik (UNTEN) ---
        label = QLabel(_(
            "<b>Theme Change Detected</b><br><br>"
            "You have switched between Light and Dark mode.<br>"
            "To ensure all SynapsePro UI elements and styles are applied correctly, "
            "please restart Anki."
        ))
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        
        layout.addWidget(label)

        self.dont_show_again_checkbox = QCheckBox(_("Don't show this message again"))
        layout.addWidget(
            self.dont_show_again_checkbox,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )

        layout.addSpacing(10)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        buttons.setCenterButtons(True) 
        layout.addWidget(buttons)
        
        self.setLayout(layout)

    def dont_show_again(self) -> bool:
        return bool(self.dont_show_again_checkbox.isChecked())

def show_restart_warning():
    """Show the dialog and return whether future warnings should be hidden."""
    if mw:
        d = ThemeChangeDialog(mw)
        d.exec()
        return d.dont_show_again()
    return False
