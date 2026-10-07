"""Real Anki collection, real QueryOp worker and native Qt picker; temporary data only."""
import importlib,sys,tempfile,time,types,weakref,json
from pathlib import Path
import aqt
from aqt.qt import QApplication,QMainWindow,QTimer,QCoreApplication,QEvent,QUrl
from PyQt6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineScript
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtTest import QTest
from PyQt6.QtCore import QPoint,Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from aqt.taskman import TaskManager
from anki.collection import Collection
app=QApplication(['synapse-links-test']);app.setQuitOnLastWindowClosed(False)
ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('workspace_link_fixture');pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg
locales=types.ModuleType(pkg.__name__+'.locales');locales._=lambda s:s;locales.TRANSLATIONS={};locales.WORKSPACE_TRANSLATIONS={};locales.translate_standard_buttons=lambda *a,**kw:None;sys.modules[locales.__name__]=locales
links=importlib.import_module(pkg.__name__+'.workspace_links')
Dialog=importlib.import_module(pkg.__name__+'.workspace_link_dialog').LinkDialog

def wait(fn):
 end=time.monotonic()+15
 while not fn():
  app.processEvents();time.sleep(.01)
  if time.monotonic()>end:raise AssertionError('Timed out')

with tempfile.TemporaryDirectory(prefix='synapse-links-') as tmp:
 col=Collection(str(Path(tmp)/'collection.anki2'))
 mw=QMainWindow();mw.pm=types.SimpleNamespace(profileFolder=lambda:tmp);mw._profile_folder=tmp;mw.col=col;mw.weakref=lambda:weakref.proxy(mw);mw._increase_background_ops=lambda:None;mw._decrease_background_ops=lambda:None;mw.taskman=TaskManager(mw);aqt.mw=mw
 try:
  deck=col.decks.id('Biology')
  note=col.new_note(col.models.by_name('Basic'));note.fields=['Mitochondrion','ATP production'];note.tags=['biology'];col.add_note(note,deck)
  card=note.cards()[0];mw.state='review';mw.reviewer=types.SimpleNamespace(card=card)
  aqt.dialogs._dialogs['Browser'][1]=types.SimpleNamespace(selected_notes=lambda:[note.id])
  detail=links.describe(col,note.id);assert links.resolve(col,detail['note'])['nid']==note.id
  for i in range(62):
   other=col.new_note(col.models.by_name('Basic'));other.fields=['Other '+str(i),'Answer'];col.add_note(other,deck)
  from importlib import import_module
  bridge=import_module(pkg.__name__+'.workspace_link_bridge')
  calls=[];old_open=aqt.dialogs.open
  aqt.dialogs.open=lambda *args:types.SimpleNamespace(search_for=lambda query:calls.append(query))
  bridge.open_link(mw,detail['note']);wait(lambda:bool(calls));assert calls==['nid:'+str(note.id)]
  order=[];callbacks=[]
  table=types.SimpleNamespace(is_notes_mode=lambda:True,toggle_state=lambda mode,query:order.append(('mode',mode,query)))
  switch=types.SimpleNamespace(blockSignals=lambda value:False,setChecked=lambda value:order.append(('switch',value)))
  browser=types.SimpleNamespace(editor=types.SimpleNamespace(call_after_note_saved=lambda callback:callbacks.append(callback)),table=table,_switch=switch,search_for=lambda query:order.append(('search',query)))
  aqt.dialogs.open=lambda *args:browser
  bridge.open_link(mw,detail['cards'][0]['link']);wait(lambda:bool(callbacks));assert not order
  callbacks.pop()();assert order[-1]==('search','cid:'+str(card.id));assert order[0][0]=='mode'
  aqt.dialogs.open=old_open
  found=links.search(col,'Mitochondrion','Biology','biology');assert len(found['items'])==1
  assert links.search(col,'')['more'];assert len(links.search(col,'')['items'])==60
  dialog=Dialog(mw,[],'Mitochondrion');dialog.show();wait(lambda:not dialog.busy and dialog.results.count()==1)
  assert 'ATP production' in dialog.preview.toPlainText()
  dialog.current_btn.click();wait(lambda:not dialog.busy and dialog.target.currentData().get('kind')=='card')
  dialog.add.click();dialog.add.click();assert len(dialog.links)==1
  dialog.target.setCurrentIndex(0);dialog.add.click();assert len(dialog.links)==2
  dialog.browser_btn.click();wait(lambda:not dialog.busy and dialog.results.count()==1)
  app.processEvents();dialog.grab().save(str(ROOT/'docs/anki-link-picker.png'))
  dialog.linked.setCurrentRow(0);dialog.preview_link();wait(lambda:not dialog.busy)
  assert dialog.target.currentData()['kind']=='card'
  dialog.commit();assert len(dialog.result_links)==2
  roundtrip=json.loads(json.dumps({'nodes':[{'ankiLinks':dialog.result_links}]}))
  assert all(links.resolve(col,l) for l in roundtrip['nodes'][0]['ankiLinks'])
  # Actual HTML -> real host allowlist -> QWebChannel -> production Python handler
  # -> actual native picker -> production JS callback. Do not replace the JS command.
  constants=types.ModuleType(pkg.__name__+'.constants');constants.addon_path=str(ROOT);constants.MINDMAP_HTML_FILENAME='index.html';constants.MINDMAP_DOCK_OBJECT_NAME='test-mindmap';sys.modules[constants.__name__]=constants
  sidebar=importlib.import_module(pkg.__name__+'.mindmap_sidebar')
  view=QWebEngineView();view.resize(1100,800);profile=QWebEngineProfile(view);page=QWebEnginePage(profile,view);view.setPage(page)
  mw.web_view=view;mw.page=page;mw._page_generation=1;mw._unload_in_progress=False
  mw._handle_command=lambda command:sidebar.MindmapPanel._handle_command(mw,command) if command.startswith('anki-') else None
  channel=QWebChannel(page);host=sidebar.MindmapBridge(mw,page);channel.registerObject('mindmapHost',host);page.setWebChannel(channel)
  boot=QWebEngineScript();boot.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation);boot.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
  boot.setSourceCode("window.__SYNAPSE_MM_HOSTED__=true;window.__SYNAPSE_MM_DARK__=false;localStorage.setItem('mindmaps',JSON.stringify({test:{name:'Links',nodes:[{id:1,parent:null,text:'Mitochondrion',x:100,y:100}]}}));")
  page.scripts().insert(boot)
  def js(source):
   values=[];page.runJavaScript(source,lambda value:values.append(value));wait(lambda:bool(values));return values[0]
  def click(selector):
   rect=js("(()=>{const r=document.querySelector("+json.dumps(selector)+").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()")
   QTest.mouseClick(view.focusProxy(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(round(rect['x']),round(rect['y'])))
  for tool,file in [('mindmap','index.html'),('roadmap','web_roadmap/index.html')]:
   ready=[];view.loadFinished.connect(lambda ok:ready.append(ok));view.setUrl(QUrl.fromLocalFile(str(ROOT/file)));view.show();wait(lambda:bool(ready));wait(lambda:js('!!window.__workspaceDocument'))
   if tool=='mindmap':
    wait(lambda:js("!document.querySelector('#mindmap-loading-overlay') || getComputedStyle(document.querySelector('#mindmap-loading-overlay')).display==='none'"))
    js("document.querySelector('#node-1').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,clientX:550,clientY:350}));")
    selector='#context-menu [data-action=link-card]'
   else:
    js("document.querySelector('[data-shape=rect]').click()")
    selector='#object-toolbar button[title="Link Card"]'
   started=time.monotonic();failures=[];opened=[]
   def choose_in_modal():
    modal=app.activeModalWidget()
    if time.monotonic()-started>12:
     failures.append('Link Card did not open/finish its picker')
     if isinstance(modal,Dialog):modal.reject()
     return
    if isinstance(modal,Dialog):
     if not opened:opened.append(True);modal.query.setText('Mitochondrion');modal.request()
     if not modal.busy and modal.results.count()==1:modal.add.click();modal.commit();return
    QTimer.singleShot(30,choose_in_modal)
   QTimer.singleShot(30,choose_in_modal);click(selector)
   wait(lambda:bool(opened) or bool(failures));assert not failures,failures
   wait(lambda:js("document.querySelectorAll('.workspace-anki-link').length") == 1)
   document=js('window.__workspaceDocument()');assert (document.get('nodes') or document['objects'])[0]['ankiLinks'][0]['noteGuid']==note.guid
   # Follow the badge through the real channel as well, including pending-editor save.
   calls=[];aqt.dialogs.open=lambda *args:types.SimpleNamespace(search_for=lambda query:calls.append(query))
   click('.workspace-anki-link');wait(lambda:bool(calls));assert calls==['nid:'+str(note.id)];aqt.dialogs.open=old_open
   print('PASS real Link Card click and open through production Qt WebChannel: '+tool,flush=True)
  page.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);view.deleteLater();mw.web_view=None;QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
  # A rapid query change must never leave stale results selectable.
  d=Dialog(mw,dialog.result_links,'Other');d.show();d.query.setText('Mitochondrion');d.request();wait(lambda:not d.busy and d.results.count()==1)
  assert d.items[0]['nid']==note.id
  d.reject();assert d.result_links is None
  # Closing while a real worker query is pending is harmless.
  d=Dialog(mw,[],'Other');d.show();d.reject();wait(lambda:not d.busy)
  mw.taskman._collection_executor.shutdown(wait=True);app.processEvents()
  # Delete the target only in the temporary collection: missing references remain stored.
  col.remove_notes([note.id]);assert links.resolve(col,detail['note']) is None
  print('PASS real Anki search/deck/tag filters, bounded results, current card/browser selection, native picker, deduplication, cancel, stale queries, JSON round trip, missing target')
 finally:
  mw.taskman._collection_executor.shutdown(wait=True);mw.taskman._no_collection_executor.shutdown(wait=True);app.processEvents();col.close();mw.close();aqt.dialogs._dialogs['Browser'][1]=None
