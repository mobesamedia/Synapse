"""Real Qt integration with temporary data and a synthetic page; no Anki launch."""
import importlib
import json
import sys
import tempfile
import time
import types
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

app = QtWidgets.QApplication(['diagnostics-test'])
app.setQuitOnLastWindowClosed(False)
mw = QtWidgets.QMainWindow()
root = tempfile.TemporaryDirectory(prefix='synapse-diag-qt-')
mw.pm = types.SimpleNamespace(profileFolder=lambda: root.name)
mw.app = app
anki = types.ModuleType('anki'); anki.version = 'test'
aqt = types.ModuleType('aqt'); aqt.mw = mw
qt = types.ModuleType('aqt.qt')
for module in (QtCore, QtGui, QtWidgets):
    for name in dir(module):
        if not name.startswith('_'): setattr(qt, name, getattr(module, name))
sys.modules.update({'aqt': aqt, 'aqt.qt': qt, 'anki': anki})
package = types.ModuleType('diag_fixture'); package.__path__ = [str(Path(__file__).resolve().parents[1])]
sys.modules[package.__name__] = package
browser = types.ModuleType('diag_fixture.website_sidebar')
view = QWebEngineView(mw); browser.sidebar_webview = view
sys.modules[browser.__name__] = browser
package.website_sidebar = browser
diag = importlib.import_module('diag_fixture.diagnostics')
ui = importlib.import_module('diag_fixture.diagnostics_ui')
importlib.import_module('diag_fixture.locales').USER_LANG = 'de'

def spin(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        time.sleep(.01)

window = QtWidgets.QDialog(mw)
panel = ui.build_panel(window)
layout = QtWidgets.QVBoxLayout(window); layout.addWidget(panel)
window.resize(820, 850); window.show()
buttons = {b.text(): b for b in panel.findChildren(QtWidgets.QPushButton)}
buttons['Aufnahme starten'].click()
spin(1)
assert diag._recorder.snapshot()['state'] == 'recording', diag._recorder.snapshot()
view.setHtml('<html><body>synthetic page</body></html>')
spin(.5)
# Reattaching must not duplicate load/termination connections.
diag.attach_webview(view); diag.attach_webview(view)
view.renderProcessTerminated.emit(QWebEnginePage.RenderProcessTerminationStatus.CrashedTerminationStatus, 139)
buttons['Auffälligkeit markieren'].click()
window.close(); window.deleteLater()
spin(.5)
assert diag._recorder.thread.is_alive(), 'closing console stopped recording'
view.deleteLater(); browser.sidebar_webview = None
spin(.3)
assert not diag._recorder.renderers, 'destroyed renderer registration retained'
diag.stop(); spin(.8)
assert diag._recorder.snapshot()['state'] == 'stopped'
assert diag._recorder.snapshot()['renderer_terminations'] == 1
window = QtWidgets.QDialog(mw)
layout = QtWidgets.QVBoxLayout(window); panel = ui.build_panel(window); layout.addWidget(panel)
window.resize(820, 850); window.show(); spin(.2)
text = panel.findChild(QtWidgets.QPlainTextEdit).toPlainText()
assert '139' in text and 'Recording ended' in text, text
# Exercise actual UI export without interactive file chooser.
archive = Path(root.name) / 'export.zip'
QtWidgets.QFileDialog.getSaveFileName = lambda *a, **k: (str(archive), 'ZIP (*.zip)')
for button in panel.findChildren(QtWidgets.QPushButton):
    if 'ZIP' in button.text(): button.click()
spin(2.2)
assert archive.exists()
import zipfile
with zipfile.ZipFile(archive) as z:
    assert 'report.txt' in z.namelist() and 'summary.json' in z.namelist()
    assert json.loads(z.read('summary.json'))['renderer_terminations'] == 1
window.grab().save('/private/tmp/synapse-diagnostics.png')
window.close(); window.deleteLater(); spin(.1)
# Exercise the real developer console wrapper and lazy preview creation.
for short, attrs in {
    'locales': {'_': lambda value: value},
    'gamification': {'RANKS': [{'level': i, 'name': str(i), 'image': 'none.png'} for i in range(12)]},
    'dashboard_demo': {'build_panel': lambda parent: QtWidgets.QWidget(parent)},
    'celebration_preview': {'render_preview': lambda *a, **k: '<html><body>preview</body></html>'},
    'theme': {'palette': lambda dark: {}},
    'sidebar': {'_is_night': lambda: False},
}.items():
    mod = types.ModuleType('diag_fixture.' + short)
    for key, val in attrs.items(): setattr(mod, key, val)
    sys.modules[mod.__name__] = mod
console = importlib.import_module('diag_fixture.developer_console')
console.enabled = True
checks = []
def inspect_console():
    dialog = app.activeModalWidget()
    try:
        assert dialog is not None
        assert not dialog.findChildren(QWebEngineView), 'diagnostics opened an unnecessary WebEngine view'
        tabs = dialog.findChild(QtWidgets.QTabWidget)
        tabs.setCurrentIndex(next(i for i in range(tabs.count()) if tabs.tabText(i)=='Previews'))
        assert len(dialog.findChildren(QWebEngineView)) == 1
        checks.append(True)
    finally:
        if dialog: dialog.reject()
QtCore.QTimer.singleShot(200, inspect_console)
console.open_console(mw)
spin(.2)
assert checks == [True]
print('PASS: real Qt signals, duplicate attachment, close/reopen, destruction, ZIP export and lazy console previews')
root.cleanup()
