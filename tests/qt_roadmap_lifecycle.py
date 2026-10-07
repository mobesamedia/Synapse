"""Real QtWebEngine integration; synthetic profile, no running Anki or user data.

Run with Anki's installed Python/PyQt environment. This deliberately loads the
actual Desktop module behind a minimal aqt stub, not a mocked WebEngine.
"""
import importlib
import json
import sys
import tempfile
import time
import types
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets, QtTest
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile

ROOT = Path(__file__).resolve().parents[1]
app = QtWidgets.QApplication(['roadmap-lifecycle-test'])
app.setQuitOnLastWindowClosed(False)
qt_messages = []
def log_qt(kind, context, message):
    qt_messages.append(message)
    if 'WebEnginePage' in message: print(message, flush=True)
QtCore.qInstallMessageHandler(log_qt)
tmp = tempfile.TemporaryDirectory(prefix='synapse-roadmap-qt-')
mw = QtWidgets.QMainWindow()
mw.resize(1000, 760)
central=QtWidgets.QWidget()
mw.setCentralWidget(central)
mw.mainLayout=QtWidgets.QVBoxLayout(central)
mw.pm = types.SimpleNamespace(profileFolder=lambda: tmp.name, night_mode=lambda: False)
aqt = types.ModuleType('aqt')
aqt.mw = mw
qt = types.ModuleType('aqt.qt')
for module in (QtCore, QtGui, QtWidgets):
    for name in dir(module):
        if not name.startswith('_'): setattr(qt, name, getattr(module, name))
sys.modules['aqt'] = aqt
sys.modules['aqt.qt'] = qt
package = types.ModuleType('roadmap_qt_fixture')
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
constants = types.ModuleType(package.__name__ + '.constants')
constants.addon_path = str(ROOT)
constants.MINDMAP_HTML_FILENAME = 'index.html'
constants.MINDMAP_DOCK_OBJECT_NAME = 'test-mindmap'
sys.modules[constants.__name__] = constants
locales = types.ModuleType(package.__name__ + '.locales')
locales._ = lambda s: s
locales.TRANSLATIONS = {}; locales.WORKSPACE_TRANSLATIONS = {}
sys.modules[locales.__name__] = locales
module = importlib.import_module(package.__name__ + '.mindmap_sidebar')
# No first-use tutorial obscuring the synthetic map.
module._claim_tutorial_invitation = lambda folder: False


def spin(seconds=0.1):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        time.sleep(.005)


def wait(predicate, seconds=10):
    end = time.monotonic() + seconds
    while not predicate():
        assert time.monotonic() < end, 'Qt operation timed out'
        spin(.02)


def js(panel, source):
    replies = []
    panel.web_view.page().runJavaScript(source, replies.append)
    wait(lambda: bool(replies))
    return replies[0]


def click_tab(panel, index, repeats=1):
    rect = js(panel, f"(() => {{const r=document.querySelectorAll('#workspace-nav .tool')[{index}].getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})()")
    for _ in range(repeats):
        QtTest.QTest.mouseClick(panel.web_view.focusProxy(), QtCore.Qt.MouseButton.LeftButton,
                               pos=QtCore.QPoint(round(rect['x']), round(rect['y'])))


try:
    module.setup_mindmap_dock()
    dock = module.mindmap_dock
    panel = dock.widget()
    mw.show()
    dock.show()
    wait(lambda: panel.web_view is not None and panel._page_ready)
    spin(.6)
    load_results = []
    panel.web_view.loadFinished.connect(load_results.append)
    click_tab(panel, 1)
    spin(1)
    assert panel.current_tool == 'roadmap' and panel._page_ready, 'Roadmap tab did not load'
    assert js(panel, 'window.__roadmapSnapshot && window.__roadmapSnapshot()')
    # First hosted opening seeds a normal map and persists through the real bridge.
    initial = js(panel, 'window.__roadmapSnapshot().data')
    assert len(initial['maps'][0]['objects']) >= 20, initial
    zoom_before = js(panel, '__roadmapSnapshot().data.maps[0].view.scale')
    for enlarge in (True, False):
        js(panel, "document.querySelector('#workspace-window').click()")
        wait(lambda: panel.is_embedded == enlarge)
        spin(.85)
        automatic = js(panel, '__roadmapSnapshot().data.maps[0].view')
        js(panel, "document.querySelector('#center').click()")
        assert automatic == js(panel, '__roadmapSnapshot().data.maps[0].view')
        assert automatic['scale'] == zoom_before
    print('PASS actual embedded-window resize centers Free Map with unchanged zoom', flush=True)
    wait(lambda: len(module.roadmap_store.load(panel._roadmap_path())['maps']) == 1)
    assert not module.roadmap_store.is_first_use(panel._roadmap_path())
    js(panel, "window.confirm=()=>true;document.querySelector('[data-doc=delete]').click()")
    wait(lambda: module.roadmap_store.load(panel._roadmap_path())['maps'][0]['objects'] == [])
    print('PASS first-use tutorial saved by real Qt bridge and deletable without resurrection', flush=True)
    for n in range(4):
        target = 'mindmap' if n % 2 == 0 else 'roadmap'
        index = 0 if target == 'mindmap' else 1
        click_tab(panel, index)
        wait(lambda: panel.current_tool == target and panel._page_ready)
        spin(.6)
    assert all(load_results), load_results
    print('PASS real Qt tab clicks without failed navigations', flush=True)

    # Autosave must work without a user gesture and without navigating away.
    js(panel, "document.querySelector('[data-shape=rect]').click()")
    wait(lambda: len(module.roadmap_store.load(panel._roadmap_path())['maps'][0]['objects']) == 1)
    assert js(panel, "document.querySelector('#save-status').textContent") == 'Saved'
    assert all(load_results), load_results
    print('PASS Qt channel autosave without navigation/user gesture', flush=True)

    for _ in range(10):
        existing = panel.web_view
        dock.hide()
        dock.show()
        spin(.15)
        assert panel.web_view is existing and panel._page_ready
    spin(.5)
    print('PASS 10 rapid hide/show cycles preserve the open page', flush=True)

    for _ in range(3):
        destroyed = []
        panel.page.destroyed.connect(lambda: destroyed.append('page'))
        panel.profile.destroyed.connect(lambda: destroyed.append('profile'))
        dock.hide()
        wait(lambda: panel.web_view is None)
        wait(lambda: destroyed == ['page', 'profile'])
        dock.show()
        wait(lambda: panel.web_view is not None and panel._page_ready)
        spin(.3)
        assert len(js(panel, 'window.__roadmapSnapshot().data')['maps'][0]['objects']) == 1
        assert len(panel.web_container.findChildren(QWebEngineView)) == 1
    print('PASS close/reopen retains data; page is destroyed before profile', flush=True)

    # Repeated attempts while one save/switch is pending are coalesced safely.
    for index, target in [(0, 'mindmap'), (1, 'roadmap')]:
        click_tab(panel, index, repeats=8)
        wait(lambda: panel.current_tool == target and panel._page_ready)
        spin(.6)
    print('PASS repeated clicks during a pending switch', flush=True)

    # Native file dialogs are replaced only in this synthetic profile.
    from unittest.mock import patch
    picture = Path(tmp.name) / 'picture.png'
    bitmap = QtGui.QImage(120, 80, QtGui.QImage.Format.Format_RGB32)
    bitmap.fill(QtGui.QColor('#74b89a'))
    assert bitmap.save(str(picture))
    with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', return_value=(str(picture), '')):
        js(panel, "document.querySelector('#add-image').click()")
        wait(lambda: js(panel, "document.querySelectorAll('#objects image').length") == 1)
    js(panel, "document.querySelector('#add-icon').click()")
    wait(lambda: js(panel, "!!document.querySelector('#icon-picker[open]')"))
    js(panel, "document.querySelector('[data-icon=lucide-heart-pulse]').click()")
    wait(lambda: js(panel, "__workspaceDocument().objects.filter(o=>o.kind==='icon').length") == 1)
    js(panel, "const c=document.querySelector('#object-toolbar input[type=color]');c.value='#cc3355';c.dispatchEvent(new Event('change'))")
    export_file = Path(tmp.name) / 'roadmap-images.json'
    with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(export_file), '')):
        js(panel, "window.__synapseMindmapCommand('roadmap-export')")
        wait(export_file.exists)
    exported = json.loads(export_file.read_text())
    assert len(exported['maps'][0]['assets']) == 1
    assert len(exported['maps'][0]['iconAssets']) == 1
    assert next(o for o in exported['maps'][0]['objects'] if o['kind']=='icon')['stroke'] == '#cc3355'
    assert 'ISC License' in exported['maps'][0]['iconLicense']
    assert len(list((Path(tmp.name)/'SynapsePro_Data'/'workspace_images').iterdir())) == 1
    with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', return_value=(str(export_file), '')):
        js(panel, "window.__synapseMindmapCommand('workspace-import')")
        wait(lambda: js(panel, "document.querySelector('#map-select').options.length") == 2)
    assert js(panel, "document.querySelectorAll('#objects image').length") == 1
    assert js(panel, "__workspaceDocument().objects.find(o=>o.kind==='icon').stroke") == '#cc3355'
    assert js(panel, "Object.keys(__workspaceDocument().iconAssets).length") == 1
    print('PASS native icon insertion, recolor and self-contained SVG export/import', flush=True)
    click_tab(panel, 0)
    wait(lambda: panel.current_tool == 'mindmap' and panel._page_ready)
    spin(.3)
    js(panel, 'window.__workspaceImported('+json.dumps({'name':'Image test','nodes':[{'id':1,'text':'Image topic','parent':None,'x':100,'y':100,'bold':True,'fill':'#e4f5e9'}]})+')')
    with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', return_value=(str(picture), '')):
        js(panel, "document.querySelector('#node-1').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,clientX:250,clientY:250}));Array.from(document.querySelectorAll('#context-menu button')).find(b=>b.textContent==='Add image').click()")
        wait(lambda: js(panel, "document.querySelectorAll('.node-image').length") == 1)
        wait(lambda: js(panel, "document.querySelector('.node-image').naturalWidth") == 120)
    mindmap_file = Path(tmp.name) / 'mindmap-images.json'
    with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(mindmap_file), '')):
        js(panel, "window.__synapseMindmapCommand('workspace-export')")
        wait(mindmap_file.exists)
    exported = json.loads(mindmap_file.read_text())
    assert len(exported['assets']) == 1 and exported['nodes'][0]['bold'] is True
    with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', return_value=(str(mindmap_file), '')):
        js(panel, "window.__synapseMindmapCommand('workspace-import')")
        spin(.4)
    assert js(panel, "window.__workspaceDocument().nodes[0].image") == exported['nodes'][0]['image']
    print('PASS native image selection, actual Qt image rendering, both file export/import paths, deduplication and Mindmap formatting round trip', flush=True)
    # Disabling a tab reloads only after saving, without deleting either document set.
    package.addon_settings = {'workspace_mindmap_tab': False, 'workspace_roadmap_tab': True}
    module.refresh_workspace_settings()
    wait(lambda: panel.current_tool == 'roadmap' and panel._page_ready)
    spin(.3)
    assert js(panel, "document.querySelectorAll('#workspace-nav .tool').length") == 1
    package.addon_settings = {'workspace_mindmap_tab': True, 'workspace_roadmap_tab': True}
    module.refresh_workspace_settings()
    spin(.8)
    assert js(panel, "document.querySelectorAll('#workspace-nav .tool').length") == 2
    print('PASS disabling and re-enabling a tab preserves documents and switches away from the disabled tool', flush=True)
    old_view = panel.web_view
    mw.pm.night_mode = lambda: True
    module.refresh_workspace_theme()
    assert js(panel, "document.documentElement.classList.contains('dark')") is True
    mw.pm.night_mode = lambda: False
    module.refresh_workspace_theme()
    assert js(panel, "document.documentElement.classList.contains('dark')") is False
    assert panel.web_view is old_view
    print('PASS live Anki dark/light changes without reloading the editor', flush=True)

    for cycle in range(3):
        module.cleanup_mindmap_sidebar()
        wait(lambda: module.mindmap_dock is None)
        spin(.3)
        assert not any(p.storageName() == 'mindmap_persistent_profile_v3' for p in app.findChildren(QWebEngineProfile))
        if cycle < 2:
            module.setup_mindmap_dock()
            dock = module.mindmap_dock
            panel = dock.widget()
            dock.show()
            wait(lambda: panel.web_view is not None and panel._page_ready)
            spin(.3)
    assert not any('WebEnginePage still not deleted' in m for m in qt_messages), qt_messages
    print('PASS repeated visible-dock cleanup without premature profile destruction', flush=True)

finally:
    # Keep parent window alive until queued WebEngine destruction has completed.
    if module.mindmap_dock is not None:
        module.cleanup_mindmap_sidebar()
        spin(.8)
    mw.hide()
    spin(.3)
    tmp.cleanup()
