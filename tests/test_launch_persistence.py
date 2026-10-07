"""Regression checks for failed reads and final saves crossing a profile switch."""
import ast, json, os, sqlite3, tempfile, unittest, typing, types, html
from pathlib import Path
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[1]

def load_parts(filename, functions=(), methods=(), env=None):
    tree=ast.parse((ROOT/filename).read_text()); nodes=[]
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in functions: nodes.append(node)
        if isinstance(node,ast.ClassDef):
            nodes.extend(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name in methods)
    namespace={'Optional':typing.Optional,'Callable':typing.Callable,'json':json,'os':os,'sqlite3':sqlite3, 'html':html}
    namespace.update(env or {})
    exec(compile(ast.Module(body=nodes,type_ignores=[]),filename,'exec'),namespace)
    return namespace

class LaunchPersistenceTests(unittest.TestCase):
    def storage(self):
        return load_parts('notebook_sidebar.py', functions=('SnapshotLoadError','_ensure_db_at','_load_latest_snapshot','_save_snapshot','_valid_snapshot','_snapshot_recovery_path','_load_snapshot_recovery','_clear_snapshot_recovery','_write_snapshot_recovery'))

    def test_new_database_and_successful_roundtrip(self):
        ns=self.storage()
        with tempfile.TemporaryDirectory() as temp:
            path=temp+'/notes.sqlite'
            for table,body in [('notes','{"pages":[{"title":"Saved"}]}'),('todos','[{"text":"Task"}]'),('pdfs','{"pdfs":[]}')]:
                self.assertEqual(ns['_load_latest_snapshot'](table,'[]',path),'[]')
                self.assertTrue(ns['_save_snapshot'](table,body,path))
                self.assertEqual(ns['_load_latest_snapshot'](table,'[]',path),body)

    def test_legacy_notebook_formats_remain_readable(self):
        ns=self.storage()
        with tempfile.TemporaryDirectory() as temp:
            path=temp+'/notes.sqlite'
            for body in ('[{"type":"text","html":"Old note"}]', '{"title":"Old title","blocks":[{"type":"text","html":"Old note"}]}'):
                self.assertTrue(ns['_save_snapshot']('notes',body,path))
                self.assertEqual(ns['_load_latest_snapshot']('notes','[]',path),body)

    def test_failed_or_corrupt_read_never_becomes_empty(self):
        ns=self.storage()
        with tempfile.TemporaryDirectory() as temp:
            path=temp+'/notes.sqlite';original='{"pages":[{"title":"Keep me"}]}'
            ns['_save_snapshot']('notes',original,path)
            with patch.dict(ns,{'_ensure_db_at':Mock(side_effect=sqlite3.OperationalError('database is locked'))}):
                with self.assertRaises(ns['SnapshotLoadError']):ns['_load_latest_snapshot']('notes','[]',path)
            self.assertEqual(ns['_load_latest_snapshot']('notes','[]',path),original)
            with sqlite3.connect(path) as con:con.execute('UPDATE notes SET body=?',('broken JSON',))
            with self.assertRaises(ns['SnapshotLoadError']):ns['_load_latest_snapshot']('notes','[]',path)

    def test_error_page_can_retry_and_close_without_saving(self):
        error=type('SnapshotLoadError',(RuntimeError,),{})
        ns=load_parts('notebook_sidebar.py',methods=('_load_tool','_flush_current_state','_queue_tool_snapshot'),env={
            'SnapshotLoadError':error,'_':lambda s:s,'ADDON_NAME_FOR_BRIDGE':'notion_mini',
            '_inject_nav':lambda markup,*a,**k:markup,'_apply_night_mode':lambda s:s,'_inject_body_column':lambda s:s})
        panel=types.SimpleNamespace(web=types.SimpleNamespace(setHtml=Mock()),current_tool='notebook',is_in_fullscreen=False,is_embedded=False,_page_ready=True,_load_tool_content=Mock(side_effect=error()))
        ns['_load_tool'](panel,'notebook');self.assertTrue(panel._load_failed);self.assertFalse(panel._page_ready)
        self.assertIn('retry-load',panel.web.setHtml.call_args.args[0])
        done=Mock();ns['_flush_current_state'](panel,done);done.assert_called_once_with(True)
        saved=Mock();ns['_queue_tool_snapshot'](panel,'notebook','[]',saved);saved.assert_called_once_with(False)
        panel._load_tool_content.side_effect=None
        ns['_load_tool'](panel,'notebook');self.assertFalse(panel._load_failed)

    def test_notebook_delayed_flush_keeps_original_profile(self):
        callbacks=[];writes=[];current={'path':'A/notebook.sqlite'}
        ns=load_parts('notebook_sidebar.py',methods=('_flush_current_state','_queue_tool_snapshot'),env={
            'db_path':lambda:current['path'],'_background_writer':types.SimpleNamespace(submit=lambda *args:writes.append(args)),
            'QTimer':types.SimpleNamespace(singleShot=lambda *a:None),'MAX_FINAL_SAVE_ATTEMPTS':4})
        panel=types.SimpleNamespace(web=types.SimpleNamespace(evalWithCallback=lambda js,cb:callbacks.append(cb)),current_tool='notebook',_database_path=current['path'],_load_failed=False,_page_ready=True,_flush_in_progress=False,_unload_requested=False)
        panel._queue_tool_snapshot=types.MethodType(ns['_queue_tool_snapshot'],panel)
        done=Mock();ns['_flush_current_state'](panel,done)
        current['path']='B/notebook.sqlite';callbacks.pop(0)('{"pages":[]}')
        self.assertEqual(writes[0][2],'A/notebook.sqlite')
        writes[0][3](True);callbacks.pop(0)('{"pages":[]}');done.assert_called_once_with(True)

    def test_maps_delayed_flush_keeps_original_profile(self):
        callbacks=[];store=Mock();recovery=Mock(return_value=True)
        ns=load_parts('mindmap_sidebar.py',methods=('_persist_active','_roadmap_path'),env={'roadmap_store':types.SimpleNamespace(save=store),'_write_mindmap_recovery':recovery,'QTimer':types.SimpleNamespace(singleShot=lambda *a:None),'mw':types.SimpleNamespace(pm=types.SimpleNamespace(profileFolder=lambda:'B'))})
        panel=types.SimpleNamespace(web_view=types.SimpleNamespace(page=lambda:types.SimpleNamespace(runJavaScript=lambda script,cb=None:callbacks.append(cb) if cb else None)),_page_ready=True,current_tool='roadmap',_profile_folder='A',_page_generation=1,_roadmap_saved_revision=-1)
        panel._roadmap_path=types.MethodType(ns['_roadmap_path'],panel)
        ns['_persist_active'](panel,Mock());callbacks.pop(0)({'revision':1,'data':{'maps':[]}})
        self.assertEqual(store.call_args.args[0],os.path.join('A','SynapsePro_Data','roadmaps.sqlite3'))
        panel.current_tool='mindmap';ns['_persist_active'](panel,Mock());callbacks.pop(0)({'snapshot':'{}','savedAt':123,'saved':False})
        recovery.assert_called_once_with('{}',123,'A')


class LaunchTranslationTests(unittest.TestCase):
    def test_ai_errors_are_localized_without_losing_http_details(self):
        import sys, urllib.error, socket, io
        sys.path.insert(0,str(ROOT))
        import locales
        ns=load_parts('ai_assistant.py',functions=('_classify_error',),env={'urllib':__import__('urllib'),'socket':socket,'_':locales._})
        previous=locales.USER_LANG
        try:
            for language in ('de','es','ko','pt','fr','vi','zh','hi','pl'):
                locales.USER_LANG=language
                error=urllib.error.HTTPError('https://example.invalid',401,'Unauthorized',{},io.BytesIO(b''))
                text=ns['_classify_error'](error)
                self.assertIn('401',text)
                self.assertNotIn('Invalid API key',text)
                self.assertNotIn('Request timed out',ns['_classify_error'](TimeoutError()))
                self.assertNotIn('Model not found',ns['_classify_error'](urllib.error.HTTPError('https://example.invalid',404,'Not found',{},io.BytesIO(b''))))
                detail=ns['_classify_error'](urllib.error.HTTPError('https://example.invalid',400,'Bad request',{},io.BytesIO(b'provider detail')))
                self.assertIn('provider detail',detail)
        finally:locales.USER_LANG=previous

    def test_all_daily_facts_use_translated_keys(self):
        import sys
        sys.path.insert(0,str(ROOT))
        import locales
        facts=[]
        for node in ast.walk(ast.parse((ROOT/'daily_widgets.py').read_text())):
            if isinstance(node,ast.Dict):
                facts.extend(v.value for k,v in zip(node.keys,node.values) if isinstance(k,ast.Constant) and k.value=='text' and isinstance(v,ast.Constant) and isinstance(v.value,str))
        self.assertEqual(len(facts),100)
        previous=locales.USER_LANG
        try:
            for language in ('de','es','ko','pt','fr','vi','zh','hi','pl'):
                locales.USER_LANG=language
                for fact in facts:self.assertNotEqual(locales._(fact),fact,(language,fact))
        finally:locales.USER_LANG=previous

if __name__=='__main__':unittest.main()
