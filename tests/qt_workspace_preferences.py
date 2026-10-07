"""Exercise both dedicated dialogs with a temporary profile and real Qt controls."""
import importlib, json, sys, tempfile, types
from pathlib import Path
from PyQt6 import QtCore, QtWidgets
app=QtWidgets.QApplication(['workspace-preferences-test'])
root=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('workspace_preferences_fixture');pkg.__path__=[str(root)];pkg.addon_settings={};sys.modules[pkg.__name__]=pkg
locales=types.ModuleType(pkg.__name__+'.locales');locales._=lambda s:s;locales.TRANSLATIONS={};locales.WORKSPACE_TRANSLATIONS={};sys.modules[locales.__name__]=locales
qt=types.ModuleType('aqt.qt')
for name in dir(QtWidgets):setattr(qt,name,getattr(QtWidgets,name))
sys.modules['aqt.qt']=qt
utils=types.ModuleType('aqt.utils');utils.showWarning=lambda *a,**k: (_ for _ in ()).throw(AssertionError(a));sys.modules['aqt.utils']=utils
with tempfile.TemporaryDirectory() as temp:
 aqt=types.ModuleType('aqt');aqt.mw=types.SimpleNamespace(pm=types.SimpleNamespace(profileFolder=lambda:temp,night_mode=lambda:False));sys.modules['aqt']=aqt
 prefs=importlib.import_module(pkg.__name__+'.workspace_preferences')
 for group in ('maps','notebook'):
  def interact():
   dialog=app.activeModalWidget();checks=dialog.findChildren(QtWidgets.QCheckBox);buttons=dialog.findChild(QtWidgets.QDialogButtonBox)
   for c in checks:c.setChecked(False)
   save=buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Save);assert not save.isEnabled()
   checks[-1].setChecked(True);assert save.isEnabled();save.click()
  QtCore.QTimer.singleShot(20,interact)
  assert prefs.show(None,group)
  result=prefs.enabled(group);assert sum(result.values())==1;assert result[prefs.GROUPS[group][-1]]
 saved=json.loads(prefs.path().read_text());assert len(saved)==5
 print('PASS dedicated map/notebook dialogs, require one visible tab, profile persistence, independent groups')
