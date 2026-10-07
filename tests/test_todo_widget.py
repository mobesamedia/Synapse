"""Synthetic task preview tests. Never opens an Anki profile."""
import ast
import html
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]

def extract(file, name, ns):
    tree = ast.parse((ROOT / file).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), file, 'exec'), ns)
    return ns[name]

def render(data):
    module = types.ModuleType('preview.notebook_sidebar')
    module.load_todo_preview_snapshot = lambda: json.dumps(data)
    with patch.dict(sys.modules, {'preview': types.ModuleType('preview'), 'preview.notebook_sidebar': module}):
        return extract('daily_widgets.py', 'generate_todo_widget', {'__package__':'preview', 'html':html, 'json':json, 'date':__import__('datetime').date, '_':lambda t:t})()

class PreviewTests(unittest.TestCase):
    def test_limits_and_escapes(self):
        data = [{'text':'<img src=x onerror=alert(1)>', 'done':False}] + [{'text':f'Task {i}', 'done':False} for i in range(8)] + [{'text':'Finished', 'done':True}]
        result = render(data)
        self.assertIn('&lt;img', result)
        self.assertNotIn('<img src=x', result)
        self.assertNotIn('Finished', result)
        self.assertNotIn('Task 7', result)
        self.assertIn('>9</span>', result)
        self.assertEqual(result.count('class="sp-task-label"'), 8)
    def test_empty_and_invalid(self):
        self.assertIn('All done.', render([]))
        self.assertIn('Open Tasks to view your list.', render(None))
    def test_dashboard_bridge_routes_real_prefix(self):
        from typing import Union
        class DeckBrowser: pass
        calls=[]
        module=types.ModuleType('preview.notebook_sidebar')
        module.toggle_todo_sidebar=lambda:calls.append('open')
        module.complete_dashboard_task=lambda task:calls.append(task)
        ns={'__package__':'preview','Union':Union,'DeckBrowser':DeckBrowser,'Reviewer':type('Reviewer',(),{}),
            'CMD_RESET_DATA':'reset','CMD_CLAIM_CHALLENGE':'claim',
            'QTimer':types.SimpleNamespace(singleShot=lambda delay,fn:fn())}
        handler=extract('__init__.py','webview_did_receive_js_message',ns)
        with patch.dict(sys.modules,{'preview':types.ModuleType('preview'),'preview.notebook_sidebar':module}):
            self.assertEqual(handler(False,'pycmd:synapsepro:todo_viewer',DeckBrowser()),(True,None))
            self.assertEqual(handler(False,'pycmd:synapsepro:todo_complete:test%20id',DeckBrowser()),(True,None))
            self.assertFalse(handler(False,'pycmd:synapsepro:todo_viewer',object()))
        self.assertEqual(calls,['open','test id'])

    def test_open_uses_existing_tool_switch(self):
        class Panel:
            web = None
            current_tool = 'notebook'
            fullscreen_window = None
            def load_content(self):
                self.web = object()
            def _on_bridge_cmd(self, command):
                self.command = command
        panel = Panel()
        dock = types.SimpleNamespace(widget=lambda:panel, show=lambda:None, raise_=lambda:None)
        fn = extract('notebook_sidebar.py','open_todo_sidebar', {'_ensure_dock':lambda:dock,'NotebookPanel':Panel,'ADDON_NAME_FOR_BRIDGE':'test','_sync_notebook_launcher':lambda:None})
        fn()
        self.assertEqual(panel.current_tool,'todo')
        self.assertEqual(panel.command,'test:switch:todo')
        panel.current_tool='notebook'
        fn()
        self.assertEqual(panel.current_tool,'notebook')  # Existing live data must go through the safe switch.
        self.assertEqual(panel.command,'test:switch:todo')

    def test_manager_toggle(self):
        class Panel:
            current_tool='todo'
            is_in_fullscreen=False
            is_embedded=False
            fullscreen_window=None
        panel=Panel()
        calls=[]
        dock=types.SimpleNamespace(widget=lambda:panel,isVisible=lambda:True,hide=lambda:calls.append('hide'))
        fn=extract('notebook_sidebar.py','toggle_todo_sidebar',{'_dock':dock,'NotebookPanel':Panel,'_sync_notebook_launcher':lambda:calls.append('sync'),'open_todo_sidebar':lambda:calls.append('open')})
        fn()
        self.assertEqual(calls,['hide','sync'])
        calls.clear()
        panel.current_tool='notebook'
        fn()
        self.assertEqual(calls,['open'])

    def completion_context(self):
        class Panel: pass
        tasks=[{'id':'one','text':'Original','done':False,'custom':42},{'id':'two','text':'Keep','done':False}]
        saved=[];deferred=[];warnings=[];refresh=[]
        def save(table,body,**kwargs):
            saved.append(json.loads(body));tasks[:]=json.loads(body);return True
        ns={'_dock':None,'NotebookPanel':Panel,'mw':types.SimpleNamespace(pm=object()),'db_path':lambda:'/profile/a',
            '_background_writer':types.SimpleNamespace(is_idle=lambda:True),'json':json,
            'load_todo_preview_snapshot':lambda:json.dumps(tasks),'_save_snapshot':save,'_normalize_todo_body':lambda body:body,
            '_refresh_dashboard_tasks':lambda:refresh.append(True),'tooltip':warnings.append,'_':lambda s:s,
            'QTimer':types.SimpleNamespace(singleShot=lambda ms,fn:deferred.append(fn))}
        fn=extract('notebook_sidebar.py','complete_dashboard_task',ns)
        return fn,ns,tasks,saved,deferred,warnings,refresh

    def test_closed_manager_completion_preserves_data(self):
        fn,ns,tasks,saved,deferred,warnings,refresh=self.completion_context()
        fn('one');fn('one')
        self.assertEqual(len(saved),1)
        self.assertEqual(tasks,[{'id':'one','text':'Original','done':True,'custom':42,'completed_on':__import__('datetime').date.today().isoformat()},{'id':'two','text':'Keep','done':False}])
        self.assertEqual(warnings,[])
        self.assertIsNone(ns['_dock'])

    def test_waits_for_writer_and_cancels_on_profile_switch(self):
        fn,ns,tasks,saved,deferred,warnings,refresh=self.completion_context()
        ns['_background_writer'].is_idle=lambda:False
        fn('one');self.assertEqual(saved,[])
        tasks[0]['text']='Latest pending edit'
        ns['_background_writer'].is_idle=lambda:True
        deferred.pop()()
        self.assertEqual(saved[0][0]['text'],'Latest pending edit')
        ns['_background_writer'].is_idle=lambda:False
        fn('two');ns['db_path']=lambda:'/profile/b';deferred.pop()()
        self.assertFalse(tasks[1]['done'])

    def test_live_editor_is_source_of_truth(self):
        fn,ns,tasks,saved,deferred,warnings,refresh=self.completion_context()
        panel=ns['NotebookPanel']();panel.web=object();panel.current_tool='todo';panel._page_ready=True;panel._flush_in_progress=False
        consumed=[];panel._consume_dashboard_completions=lambda:consumed.extend(panel._dashboard_completions)
        ns['_dock']=types.SimpleNamespace(widget=lambda:panel)
        fn('one');self.assertEqual(consumed,['one']);self.assertEqual(saved,[])
        panel._flush_in_progress=True;fn('two');self.assertEqual(len(deferred),1)

    def test_failed_save_does_not_report_success(self):
        fn,ns,tasks,saved,deferred,warnings,refresh=self.completion_context()
        ns['_save_snapshot']=lambda *a,**kw:False
        fn('one')
        self.assertEqual(refresh,[]);self.assertEqual(len(warnings),1)
        self.assertFalse(tasks[0]['done'])

    def test_read_only_and_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder)/'tasks.db')
            ns={'os':os,'sqlite3':sqlite3,'db_path':lambda:path,'_load_snapshot_recovery':lambda *a:None,'_normalize_todo_body':lambda body:body}
            read = extract('notebook_sidebar.py','load_todo_preview_snapshot',ns)
            self.assertEqual(read(),'[]')
            self.assertFalse(os.path.exists(path))
            with sqlite3.connect(path) as con:
                con.execute('CREATE TABLE todos(id INTEGER PRIMARY KEY, body TEXT, updated_at INTEGER)')
                con.execute('INSERT INTO todos VALUES(1,?,10)', ('[{"text":"Keep"}]',))
            before=Path(path).read_bytes()
            self.assertEqual(json.loads(read())[0]['text'],'Keep')
            self.assertEqual(Path(path).read_bytes(),before)
            ns['_load_snapshot_recovery']=lambda *a:'[{"text":"Recovered"}]'
            self.assertIn('Recovered',read())
            ns['_load_snapshot_recovery']=lambda *a:None
            con=sqlite3.connect(path)
            try:
                con.execute('BEGIN EXCLUSIVE')
                self.assertEqual(read(),'null')
            finally: con.close()

if __name__=='__main__':
    unittest.main()
