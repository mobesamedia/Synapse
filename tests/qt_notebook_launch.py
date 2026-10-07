"""Real WebEngine editor with isolated profile; normal save, retry and tool switch."""
import importlib,sys,tempfile,types,time,json,sqlite3,weakref
from pathlib import Path
from unittest.mock import patch
import aqt
from aqt.qt import QApplication,QMainWindow
from aqt.taskman import TaskManager
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
app=QApplication(['notebook-launch-test']);app.setQuitOnLastWindowClosed(False)
root=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('notebook_launch_fixture');pkg.__path__=[str(root)];pkg.addon_settings={};sys.modules[pkg.__name__]=pkg
class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self,level,message,line,source):
        if message.startswith('AUDIT:'):
            self.parent().bridge(message[6:])
class Web(QWebEngineView):
    def __init__(self,kind=None):
        super().__init__();self.setPage(Page(self));self.bridge=lambda cmd:None
    def set_bridge_command(self,callback,context):self.bridge=callback
    def setHtml(self,markup):
        markup=markup.replace('<head>','<head><script>window.pycmd=cmd=>console.log("AUDIT:"+cmd);</script>',1)
        super().setHtml(markup)
    def eval(self,script):self.page().runJavaScript(script)
    def evalWithCallback(self,script,cb):self.page().runJavaScript(script,cb)
    def cleanup(self):pass

def wait(fn):
    end=time.monotonic()+15
    while not fn():
        app.processEvents();time.sleep(.01)
        if time.monotonic()>end:raise AssertionError('Qt timeout')
def js(panel,script):
    results=[];panel.web.page().runJavaScript(script,results.append);wait(lambda:bool(results));return results[0]
with tempfile.TemporaryDirectory() as temp:
    mw=QMainWindow();mw.pm=types.SimpleNamespace(profileFolder=lambda:temp,night_mode=lambda:False);mw.col=None;mw.state='review';mw.weakref=lambda:weakref.proxy(mw);mw.taskman=TaskManager(mw);aqt.mw=mw
    module=importlib.import_module(pkg.__name__+'.notebook_sidebar');module.AnkiWebView=Web
    module.tooltip=lambda *a,**kw:None
    original=json.dumps({'pages':[{'id':'keep','title':'Important notes','icon':'📄','blocks':[{'type':'text','html':'Original content'}]}],'activePageId':'keep'})
    assert module.save_note(original)
    panel=module.NotebookPanel();panel.resize(400,700);panel.show()
    ensure=module._ensure_db_at
    with patch.object(module,'_ensure_db_at',side_effect=sqlite3.OperationalError('locked')):
        panel.load_content();wait(lambda:panel.web is not None)
        wait(lambda:js(panel,"document.querySelector('button[onclick*=retry]') !== null"))
        assert panel._load_failed
        # Bridge cannot store empty content while showing a load error.
        panel._on_bridge_cmd('notion_mini:save:[]')
    assert module.load_latest_note()==original
    js(panel,"document.querySelector('button[onclick*=retry]').click()")
    wait(lambda:panel._page_ready)
    assert not panel._load_failed
    assert 'Original content' in js(panel,'document.body.innerText')
    js(panel,"document.querySelector('#title').innerText='Edited title';document.querySelector('#title').dispatchEvent(new Event('input',{bubbles:true}))")
    panel._on_bridge_cmd('notion_mini:switch:todo')
    wait(lambda:panel.current_tool=='todo' and panel._page_ready)
    saved=json.loads(module.load_latest_note());assert saved['pages'][0]['title']=='Edited title',saved
    panel._on_bridge_cmd('notion_mini:switch:notebook');wait(lambda:panel.current_tool=='notebook' and panel._page_ready)
    assert 'Edited title' in js(panel,'document.body.innerText')
    done=[];panel.unload_content(done.append);wait(lambda:bool(done));assert done==[True]
    assert panel.web is None
    panel.close();panel.deleteLater();app.processEvents()
    print('PASS actual Qt notebook: read error, blocked empty save, retry button, restored notes, edit/save, tab roundtrip and close')
