"""Real Qt console bridge and GamificationManager, temporary Anki collection only."""
import importlib,json,sys,tempfile,time,types
from pathlib import Path
import aqt
from aqt.qt import QApplication,QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from anki.collection import Collection
app=QApplication(['gamification-settings-test'])
root=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('gami_settings_fixture');pkg.__path__=[str(root)];pkg.addon_settings={};pkg.save_addon_settings=lambda:None;sys.modules[pkg.__name__]=pkg
for name,attrs in {'locales':{'_':lambda s:s},'constants':{'addon_package_name':'fixture'},'theme':{'palette':lambda night:{},'FONT_FAMILY':'sans-serif'},'web_i18n':{'translations':lambda surface:{}}}.items():
 mod=types.ModuleType(pkg.__name__+'.'+name);mod.__dict__.update(attrs);sys.modules[mod.__name__]=mod

def wait(check):
 end=time.monotonic()+15
 while not check():
  app.processEvents();time.sleep(.01)
  if time.monotonic()>end:raise AssertionError('timeout')
def js(code):
 result=[];page.runJavaScript(code,lambda value:result.append(value));wait(lambda:bool(result));return result[0]
with tempfile.TemporaryDirectory(prefix='gami-settings-') as tmp:
 col=Collection(str(Path(tmp)/'collection.anki2'))
 aqt.mw=types.SimpleNamespace(col=col,pm=types.SimpleNamespace(profileFolder=lambda:tmp,night_mode=lambda:False))
 gm=importlib.import_module(pkg.__name__+'.gamification');sidebar=importlib.import_module(pkg.__name__+'.sidebar')
 manager=gm.GamificationManager(None)
 note=col.new_note(col.models.by_name('Basic'));note.fields=['temporary test','answer'];col.add_note(note,col.decks.id('Default'))
 callbacks=[]
 holder=types.SimpleNamespace(manager=manager,update_display=lambda:callbacks.append('updated'))
 holder._addon_settings=lambda:(pkg.addon_settings,pkg.save_addon_settings)
 holder._set_popups_enabled=lambda *args:sidebar.GamificationSidebar._set_popups_enabled(holder,*args)
 ready=[]
 def receive(action):
  if action=='ready':ready.append(True)
  else:sidebar.GamificationSidebar._on_message(holder,action)
 view=QWebEngineView();page=sidebar._GamiPage(receive,view);view.setPage(page);view.resize(360,700)
 view.setUrl(QUrl.fromLocalFile(str(root/'gamification_web/sidebar.html')));view.show();wait(lambda:ready)
 js("initGamification({level:1,rankName:'Starter',xp:0,xpNeeded:100,streak:0,ranks:[],challenge:{}})")
 js("document.getElementById('gamificationSettings').click();document.getElementById('streakReviews').value='100';document.getElementById('streakAllowCards').click()")
 wait(lambda:bool(callbacks))
 assert manager.data['streak_rules']=={'reviews':100,'cards':1,'allowCards':True},manager.data
 assert manager.get_streak()==1
 assert col.conf[gm.CONFIG_KEY]['streak_rules']==manager.data['streak_rules']
 backup=json.loads((Path(tmp)/'SynapsePro_Data/gamification_data.json').read_text());assert backup['streak_rules']==manager.data['streak_rules']
 reloaded=gm.GamificationManager(None);assert reloaded.get_streak()==1
 js("document.getElementById('popupsToggle').click()")
 assert pkg.addon_settings['gamification_popups_enabled'] is False
 js("document.querySelector('#gamificationSettingsOverlay .gami-close').click();document.getElementById('gamificationInfo').click()")
 assert js("document.getElementById('gamificationInfoOverlay').open") is True
 view.close();page.deleteLater();app.processEvents();col.close()
 print('PASS real Qt HTML dialogs → console bridge → Python validation → temporary Anki collection + JSON backup + reload; celebration toggle')
