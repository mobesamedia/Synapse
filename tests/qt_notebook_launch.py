"""Real WebEngine editor with isolated profile; normal save, retry and tool switch."""
import importlib,sys,tempfile,types,time,json,sqlite3,weakref
from pathlib import Path
from unittest.mock import patch
import aqt
from aqt.qt import QApplication,QMainWindow,QPoint,Qt
from PyQt6.QtTest import QTest
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
    # Model an existing 1.6.0 database: no new writer or update backup has run.
    module._ensure_db_at(module.db_path())
    with sqlite3.connect(module.db_path()) as legacy:
        legacy.execute('INSERT INTO notes(body,updated_at) VALUES (?,1)',(original,))
    assert not Path(module.db_path()+'.pre-block-ui-v1.json').exists()
    panel=module.NotebookPanel();panel.resize(400,700);panel.show()
    ensure=module._ensure_db_at
    with patch.object(module,'_ensure_db_at',side_effect=sqlite3.OperationalError('locked')):
        panel.load_content();wait(lambda:panel.web is not None)
        wait(lambda:js(panel,"document.querySelector('button[onclick*=retry]') !== null"))
        assert panel._load_failed
        # Bridge cannot store empty content while showing a load error.
        panel._on_bridge_cmd('notion_mini:save:[]')
    assert module.load_latest_note()==original
    # The load-error page can export a recovery copy through the real async
    # taskman/bridge, without loading an editor or modifying the source DB.
    from aqt.qt import QInputDialog
    source_path=Path(module.db_path());source_before=source_path.read_bytes()
    recovery_export=Path(temp)/'recovery-export.json'
    with patch.object(QInputDialog,'getItem',side_effect=lambda parent,title,label,choices,*args:(choices[0],True)), patch.object(module.QFileDialog,'getSaveFileName',return_value=(str(recovery_export),'JSON')):
        js(panel,"document.querySelector('button[onclick*=export-recovery]').click()")
        wait(lambda:recovery_export.exists())
        assert json.loads(recovery_export.read_text())==json.loads(original)
    assert source_path.read_bytes()==source_before
    assert panel._load_failed and not panel._page_ready
    js(panel,"document.querySelector('button[onclick*=retry]').click()")
    wait(lambda:panel._page_ready)
    assert not panel._load_failed
    assert 'Original content' in js(panel,'document.body.innerText')
    # Historical versions travel through the actual asynchronous Anki bridge.
    js(panel,"notebookShowVersions()")
    wait(lambda:js(panel,"document.querySelector('#notebook-dialog .nb-primary') !== null"))
    assert json.loads(js(panel,'window.__synapseSnapshotForUnload()'))['pages']==json.loads(original)['pages']
    js(panel,"document.querySelector('#notebook-dialog .nb-primary').click()")
    restored=json.loads(js(panel,'window.__synapseSnapshotForUnload()'))
    assert restored['pages'][0]==json.loads(original)['pages'][0]
    assert restored['pages'][1]['blocks']==json.loads(original)['pages'][0]['blocks']
    assert restored['pages'][1]['id']!='keep'
    js(panel,"navigateNotebook(-1)")
    assert json.loads(js(panel,'window.__synapseSnapshotForUnload()'))['pages']==json.loads(original)['pages']
    # Real mouse events in Qt: a pinned page must visibly enter a closed folder.
    js(panel, "appState.pages.push({id:'qt-drag',title:'Drag page',icon:'',pinned:true,blocks:[{type:'text',html:'Preserved drag content',extra:'keep'}]});appState.folders=[{id:'qt-folder',name:'Qt folder',open:false}];renderSidebar();toggleSidebar()")
    QTest.qWait(350)
    positions=js(panel, "[document.querySelector('[data-page-id=\"qt-drag\"]'),document.querySelector('[data-folder-id=\"qt-folder\"]')].map(el=>{const r=el.getBoundingClientRect();return [Math.round(r.left+50),Math.round(r.top+r.height/2)]})")
    target=panel.web.focusProxy() or panel.web
    start,end=positions
    QTest.mousePress(target,Qt.MouseButton.LeftButton,pos=QPoint(*start))
    for step in range(1,11):
        QTest.mouseMove(target,QPoint(round(start[0]+(end[0]-start[0])*step/10),round(start[1]+(end[1]-start[1])*step/10)),20)
    QTest.mouseRelease(target,Qt.MouseButton.LeftButton,pos=QPoint(*end))
    wait(lambda:js(panel,"appState.pages.find(page=>page.id==='qt-drag')?.folderId==='qt-folder'"))
    dragged=json.loads(js(panel,'window.__synapseSnapshotForUnload()'))
    assert dragged['pages'][1]['folderId']=='qt-folder',dragged
    assert dragged['pages'][1]['blocks']==[{'type':'text','html':'Preserved drag content','extra':'keep'}]
    assert dragged['folders'][0]['open'] is True
    assert js(panel,"document.querySelectorAll('[data-page-id=\"qt-drag\"]').length")==2
    js(panel,"navigateNotebook(-1)")
    assert 'folderId' not in json.loads(js(panel,'window.__synapseSnapshotForUnload()'))['pages'][1]
    js(panel,"loadContent("+json.dumps(original)+")")
    # Real Qt side-margin clicks must focus the line at that height, not the final block.
    js(panel,"editor.appendChild(createStoredBlock({type:'text',html:'Last line'}));triggerSave()")
    QTest.qWait(350)
    margin=js(panel,"(()=>{const r=editor.firstElementChild.getBoundingClientRect();return [Math.round(r.left-20),Math.round(r.top+r.height/2)]})()")
    QTest.mouseClick(panel.web.focusProxy() or panel.web,Qt.MouseButton.LeftButton,pos=QPoint(*margin))
    wait(lambda:js(panel,"document.activeElement===editor.firstElementChild"))
    assert json.loads(js(panel,'window.__synapseSnapshotForUnload()'))['pages'][0]['blocks'][0]==json.loads(original)['pages'][0]['blocks'][0]
    js(panel,"loadContent("+json.dumps(original)+")")
    # Opt-in table options and image manipulation in the actual embedded engine.
    png='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j9a8AAAAASUVORK5CYII='
    table_html='<tbody><tr><td contenteditable="true"><b>Keep bold</b></td><td contenteditable="true">Second</td></tr><tr><td contenteditable="true">Third</td><td contenteditable="true">Fourth</td></tr></tbody>'
    media_fixture={'pages':[{'id':'qt-media','title':'Media test','icon':'','blocks':[{'type':'table','html':table_html,'extra':'keep'},{'type':'text','html':'<img alt="old" src="data:image/png;base64,'+png+'" style="width:120px;height:80px">','extra':'keep'}]}],'activePageId':'qt-media'}
    js(panel,'loadContent('+json.dumps(json.dumps(media_fixture))+')')
    wait(lambda:js(panel,"editor.querySelector('img').complete"))
    js(panel,"notebookTableHeader(editor.querySelector('table'))")
    media_saved=json.loads(js(panel,'window.__synapseSnapshotForUnload()'))
    assert media_saved['pages'][0]['blocks'][0]['html']==table_html
    assert media_saved['pages'][0]['blocks'][0]['tableOptions']['headerRow'] is True
    js(panel,"navigateNotebook(-1);notebookSelectImage(editor.querySelector('img'))")
    grip=js(panel,"(()=>{const r=document.querySelector('.nb-image-size').getBoundingClientRect();return [Math.round(r.left+5),Math.round(r.top+5)]})()")
    target=panel.web.focusProxy() or panel.web
    QTest.mousePress(target,Qt.MouseButton.LeftButton,pos=QPoint(*grip))
    QTest.mouseMove(target,QPoint(grip[0]+50,grip[1]),50)
    QTest.mouseRelease(target,Qt.MouseButton.LeftButton,pos=QPoint(grip[0]+50,grip[1]))
    wait(lambda:js(panel,"editor.querySelector('img').getBoundingClientRect().width>120"))
    assert json.loads(js(panel,'window.__synapseSnapshotForUnload()'))['pages'][0]['blocks'][0]==media_fixture['pages'][0]['blocks'][0]
    js(panel,"navigateNotebook(-1)")
    assert json.loads(js(panel,'window.__synapseSnapshotForUnload()'))['pages']==media_fixture['pages']
    js(panel,"(async()=>{const bytes=Uint8Array.from(atob("+json.dumps(png)+"),c=>c.charCodeAt(0)),file=new File([bytes],'qt.png',{type:'image/png'});window.__qtUploaded=await notebookInsertImageFiles([file],{state:appState,pageId:appState.activePageId,anchor:editor.lastElementChild});})()")
    wait(lambda:js(panel,"window.__qtUploaded===true"))
    assert js(panel,"editor.querySelector('img[alt=\"qt.png\"]').getAttribute('src')")=='data:image/png;base64,'+png
    js(panel,"navigateNotebook(-1)")
    assert json.loads(js(panel,'window.__synapseSnapshotForUnload()'))['pages']==media_fixture['pages']
    js(panel,"loadContent("+json.dumps(original)+")")
    # New block controls run inside Anki's actual Chromium/Qt environment.
    unchanged = json.loads(js(panel, 'window.__synapseSnapshotForUnload()'))
    assert unchanged['pages'][0]['blocks'] == json.loads(original)['pages'][0]['blocks']
    js(panel, "notebookActionBlock=editor.firstElementChild;notebookOpenTypes(false);Array.from(notebookPopup.querySelectorAll('button')).find(b=>b.textContent===notebookTypeLabel('h3')).click()")
    assert json.loads(js(panel, 'window.__synapseSnapshotForUnload()'))['pages'][0]['blocks'][0]['type'] == 'h3'
    js(panel, "document.dispatchEvent(new KeyboardEvent('keydown',{key:'z',ctrlKey:true,bubbles:true}))")
    assert json.loads(js(panel, 'window.__synapseSnapshotForUnload()'))['pages'][0]['blocks'] == json.loads(original)['pages'][0]['blocks']
    js(panel, "editor.appendChild(createStoredBlock({type:'toggle',html:'Qt toggle',body:'Qt body',extra:'keep'}));triggerSave();reorderNotebookBlock(editor.firstElementChild,null)")
    reordered = json.loads(js(panel, 'window.__synapseSnapshotForUnload()'))['pages'][0]['blocks']
    assert reordered[0] == {'type':'toggle','html':'Qt toggle','body':'Qt body','extra':'keep'}
    assert reordered[1] == json.loads(original)['pages'][0]['blocks'][0]
    js(panel, "document.dispatchEvent(new KeyboardEvent('keydown',{key:'z',ctrlKey:true,bubbles:true}));editor.lastElementChild.remove();triggerSave()")
    js(panel, "appState.pages.push({id:'qt-child',title:'Qt child',icon:'',blocks:[{type:'text',html:'Qt child original'}]});setNotebookParent('qt-child','keep');loadPage('qt-child')")
    assert 'Important notes / Qt child' in js(panel, "document.getElementById('notebook-breadcrumbs').title")
    js(panel, "loadPage('keep');appState.pages=appState.pages.filter(p=>p.id!=='qt-child');renderSidebar()")
    assert json.loads(js(panel, 'window.__synapseSnapshotForUnload()'))['pages'][0]['blocks'] == json.loads(original)['pages'][0]['blocks']
    js(panel,"document.querySelector('#title').innerText='Edited title';document.querySelector('#title').dispatchEvent(new Event('input',{bubbles:true}))")
    panel._on_bridge_cmd('notion_mini:switch:todo')
    wait(lambda:panel.current_tool=='todo' and panel._page_ready)
    saved=json.loads(module.load_latest_note());assert saved['pages'][0]['title']=='Edited title',saved
    panel._on_bridge_cmd('notion_mini:switch:notebook');wait(lambda:panel.current_tool=='notebook' and panel._page_ready)
    assert 'Edited title' in js(panel,'document.body.innerText')
    # Full export flushes first and writes only a separate file.
    export_path=str(Path(temp)/'notebook-export.json')
    with patch.object(module.QFileDialog,'getSaveFileName',return_value=(export_path,'')):
        panel._on_bridge_cmd('notion_mini:export')
        wait(lambda:Path(export_path).exists())
    exported=json.loads(Path(export_path).read_text())
    assert exported['pages'][0]['title']=='Edited title'
    assert exported['pages'][0]['blocks']==json.loads(original)['pages'][0]['blocks']
    # A real worker/Qt save acknowledgement and WebView restart must never let
    # a locked, older recovery file override the newly confirmed title/content.
    assert module._write_snapshot_recovery('notes',original,module.db_path())
    recovery_path=module._snapshot_recovery_path('notes',module.db_path())
    recovery_before=Path(recovery_path).read_bytes()
    remove,replace=module.os.remove,module.os.replace
    def locked_remove(path,*args,**kwargs):
        if str(path)==recovery_path:raise PermissionError('synthetic Windows sharing violation')
        return remove(path,*args,**kwargs)
    def locked_replace(source,destination,*args,**kwargs):
        if str(destination)==recovery_path:raise PermissionError('synthetic Windows sharing violation')
        return replace(source,destination,*args,**kwargs)
    with patch.object(module.os,'remove',side_effect=locked_remove),patch.object(module.os,'replace',side_effect=locked_replace):
        js(panel,"titleEl.innerText='Confirmed with locked recovery';titleEl.dispatchEvent(new Event('input',{bubbles:true}))")
        wait(lambda:js(panel,"!saveDirty && document.getElementById('status').innerText===(window.__SYNAPSE_I18N__?.saved||'Saved')"))
        assert json.loads(module.load_latest_note())['pages'][0]['title']=='Confirmed with locked recovery'
        assert Path(recovery_path).read_bytes()==recovery_before
        restarted=[];panel.unload_content(restarted.append);wait(lambda:bool(restarted));assert restarted==[True]
        panel.load_content();wait(lambda:panel._page_ready)
        assert 'Confirmed with locked recovery' in js(panel,'document.body.innerText')
        assert json.loads(js(panel,'window.__synapseSnapshotForUnload()'))['pages'][0]['blocks']==json.loads(original)['pages'][0]['blocks']
        assert Path(recovery_path).read_bytes()==recovery_before
    done=[];panel.unload_content(done.append);wait(lambda:bool(done));assert done==[True]
    assert panel.web is None
    for suffix in ('pre-block-ui-v1','pre-hierarchy-v1'):
        backup=json.loads(Path(module.db_path()+'.'+suffix+'.json').read_text())
        assert any(row[1]==original for row in backup['snapshots'])
    panel.close();panel.deleteLater();app.processEvents()
    print('PASS actual Qt notebook: legacy upgrade, unchanged recovery export/source, failed-load protection, retry, versions, edit/save, tab roundtrip, locked recovery with real Saved acknowledgement and editor restart, original blocks and pre-update copies preserved')
