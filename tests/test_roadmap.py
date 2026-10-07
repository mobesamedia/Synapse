"""Roadmap persistence tests using only temporary databases."""
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('roadmap_store', Path(__file__).resolve().parents[1] / 'roadmap_store.py')
store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store)


def sample():
    return {'version': 1, 'active': 'map', 'maps': [{'id': 'map', 'name': 'Roadmap', 'objects': [
        {'id': 'box', 'kind': 'shape', 'x': 5, 'y': 7, 'w': 150, 'h': 80, 'rotation': 35, 'html': '<b>Text</b>'},
        {'id': 'arrow', 'kind': 'arrow', 'a': {'node': 'box', 'side': 'right'}, 'b': {'x': 500, 'y': 600}}
    ]}]}


class RoadmapStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'roadmaps.sqlite3')

    def test_tutorial_only_before_first_save(self):
        self.assertTrue(store.is_first_use(self.path))
        store.save(self.path, sample())
        self.assertFalse(store.is_first_use(self.path))
        store.save(self.path, {'version': 1, 'active': None, 'maps': []})
        self.assertFalse(store.is_first_use(self.path))

    def test_empty_and_restart(self):
        self.assertEqual(store.load(self.path), {'version': 1, 'active': None, 'maps': []})
        data = sample()
        store.save(self.path, data)
        self.assertEqual(store.load(self.path), data)
        store.save(self.path, data)
        self.assertEqual(store.load(self.path), data)

    def test_multiple_maps_selection_and_delete(self):
        data = sample()
        data['maps'].append({'id': 'two', 'name': 'Zweite', 'objects': []})
        data['active'] = 'two'
        store.save(self.path, data)
        self.assertEqual(store.load(self.path), data)
        data['maps'] = data['maps'][1:]
        store.save(self.path, data)
        self.assertEqual(store.load(self.path), data)

    def test_invalid_data_preserves_committed_copy(self):
        store.save(self.path, sample())
        for mutation in ('duplicate', 'nan', 'connection', 'active', 'dimensions'):
            data = sample()
            if mutation == 'duplicate': data['maps'][0]['objects'].append(data['maps'][0]['objects'][0].copy())
            if mutation == 'nan': data['maps'][0]['objects'][0]['x'] = float('nan')
            if mutation == 'connection': data['maps'][0]['objects'][1]['a']['node'] = 'missing'
            if mutation == 'active': data['active'] = 'missing'
            if mutation == 'dimensions': data['maps'][0]['objects'][0]['w'] = -1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): store.save(self.path, data)
            self.assertEqual(store.load(self.path), sample())

    def test_transaction_rollback(self):
        store.save(self.path, sample())
        con = sqlite3.connect(self.path)
        con.execute("CREATE TRIGGER reject_update BEFORE INSERT ON settings BEGIN SELECT RAISE(ABORT, 'synthetic write error'); END")
        con.commit()
        con.close()
        changed = sample()
        changed['maps'][0]['name'] = 'Must roll back'
        with self.assertRaises(sqlite3.DatabaseError): store.save(self.path, changed)
        self.assertEqual(store.load(self.path), sample())

    def test_corrupt_database_fails_without_replacing_data(self):
        Path(self.path).write_bytes(b'not a database')
        with self.assertRaises(sqlite3.DatabaseError): store.load(self.path)
        self.assertEqual(Path(self.path).read_bytes(), b'not a database')

    def test_profile_isolation(self):
        other = str(Path(self.temp.name) / 'other' / 'roadmaps.sqlite3')
        store.save(self.path, sample())
        self.assertEqual(store.load(other)['maps'], [])
        self.assertEqual(store.load(self.path), sample())

    def test_unchanged_document_not_rewritten(self):
        store.save(self.path, sample())
        con = sqlite3.connect(self.path)
        con.execute("CREATE TRIGGER reject_document BEFORE INSERT ON roadmaps BEGIN SELECT RAISE(ABORT, 'unchanged document rewritten'); END")
        con.commit()
        con.close()
        store.save(self.path, sample())


# Exercise the actual asynchronous host methods without starting Anki.
import ast
from types import SimpleNamespace
from unittest.mock import Mock


class RoadmapBridgeTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / 'mindmap_sidebar.py'
        tree = ast.parse(source.read_text())
        panel = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'MindmapPanel')
        methods = [n for n in panel.body if isinstance(n, ast.FunctionDef) and n.name in ('_persist_active', 'switch_tool', '_prepare_roadmap_boot', '_on_load_finished', '_complete_unload')]
        self.timers = []
        self.store = SimpleNamespace(save=Mock())
        self.ns = {'json': json, 'roadmap_store': self.store,
                   'workspace_io': SimpleNamespace(enabled_tools=lambda: {'mindmap':True,'roadmap':True}),
                   'QTimer': SimpleNamespace(singleShot=lambda ms, fn: self.timers.append(fn)),
                   'QUrl': SimpleNamespace(fromLocalFile=lambda p: p), '_write_mindmap_recovery': Mock(return_value=True)}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(source), 'exec'), self.ns)
        self.callbacks = []
        self.scripts = []
        def run(script, callback=None):
            self.scripts.append(script)
            if callback: self.callbacks.append(callback)
        web = SimpleNamespace(page=lambda: SimpleNamespace(runJavaScript=run), setEnabled=Mock(), setUrl=Mock())
        self.panel = SimpleNamespace(web_view=web, _page_ready=True, current_tool='roadmap',
                                     _page_generation=1, _roadmap_saved_revision=-1, _profile_folder='profile-A',
                                     _roadmap_path=lambda: 'synthetic.sqlite3', _switching=False, _unload_in_progress=False,
                                     _prepare_roadmap_boot=Mock(), _tool_path=lambda: 'index.html')
        self.panel._persist_active = lambda done: self.ns['_persist_active'](self.panel, done)

    def test_save_ack_and_timeout_only_once(self):
        done = Mock()
        self.panel._persist_active(done)
        self.callbacks.pop()({'revision': 3, 'data': sample()})
        self.store.save.assert_called_once()
        self.timers.pop()()
        done.assert_called_once_with(True)
        self.assertIn('__roadmapSaved(true,3)', self.scripts[-1])

    def test_older_callback_does_not_overwrite_newer_save(self):
        self.panel._persist_active(Mock())
        self.panel._persist_active(Mock())
        self.callbacks[1]({'revision': 8, 'data': sample()})
        self.callbacks[0]({'revision': 7, 'data': sample()})
        self.store.save.assert_called_once()
        self.assertEqual(self.panel._roadmap_saved_revision, 8)

    def test_late_callback_from_previous_page_is_ignored(self):
        done = Mock()
        self.panel._persist_active(done)
        self.panel._page_generation += 1
        self.callbacks.pop()({'revision': 9, 'data': sample()})
        self.store.save.assert_not_called()
        done.assert_called_once_with(False)

    def test_failed_save_cancels_switch(self):
        self.store.save.side_effect = OSError('synthetic disk failure')
        self.ns['switch_tool'](self.panel, 'mindmap')
        self.callbacks.pop()({'revision': 2, 'data': sample()})
        self.assertEqual(self.panel.current_tool, 'roadmap')
        self.panel.web_view.setUrl.assert_not_called()
        self.panel.web_view.setEnabled.assert_called_with(True)
        self.assertFalse(self.panel._switching)

    def test_successful_switch_waits_for_save(self):
        self.ns['switch_tool'](self.panel, 'mindmap')
        self.panel.web_view.setUrl.assert_not_called()
        self.callbacks.pop()({'revision': 2, 'data': sample()})
        self.assertEqual(self.panel.current_tool, 'mindmap')
        self.panel.web_view.setUrl.assert_called_once_with('index.html')
        self.assertFalse(self.panel._page_ready)

    def test_mindmap_uses_existing_recovery(self):
        self.panel.current_tool = 'mindmap'
        done = Mock()
        self.panel._persist_active(done)
        self.callbacks.pop()({'snapshot': '{}', 'savedAt': 123, 'saved': False})
        self.ns['_write_mindmap_recovery'].assert_called_once_with('{}', 123, 'profile-A')
        self.store.save.assert_not_called()
        done.assert_called_once_with(True)

    def test_return_to_mindmap_refreshes_recovery_boot_data(self):
        class Script:
            InjectionPoint = SimpleNamespace(DocumentCreation=1)
            ScriptWorldId = SimpleNamespace(MainWorld=1)
            def setName(self, name): self._name = name
            def name(self): return self._name
            def setInjectionPoint(self, value): pass
            def setWorldId(self, value): pass
            def setRunsOnSubFrames(self, value): pass
            def setSourceCode(self, source): self.source = source
        scripts = []
        collection = SimpleNamespace(toList=lambda: list(scripts), remove=scripts.remove, insert=scripts.append)
        self.panel.page = SimpleNamespace(scripts=lambda: collection)
        self.panel.current_tool = 'mindmap'
        self.ns['QWebEngineScript'] = Script
        recovery = Mock(side_effect=[{'saved_at': 1}, {'saved_at': 2}])
        self.ns['_load_mindmap_recovery'] = recovery
        prepare = self.ns['_prepare_roadmap_boot']
        prepare(self.panel)
        prepare(self.panel)
        self.assertEqual(len(scripts), 1)
        self.assertIn('"saved_at": 2', scripts[0].source)
        self.assertEqual(self.panel._page_generation, 3)


    def test_rejected_control_navigation_keeps_document_ready(self):
        self.panel._inject_i18n = Mock()
        self.ns['_on_load_finished'](self.panel, False)
        self.assertTrue(self.panel._page_ready)
        self.panel._inject_i18n.assert_not_called()
        self.panel._page_ready = False
        self.ns['_on_load_finished'](self.panel, False)
        self.assertFalse(self.panel._page_ready)

    def test_teardown_waits_until_after_javascript_callback(self):
        self.panel._unload_in_progress = True
        self.panel._unload_for_hide = False
        self.panel._destroy_web_view = Mock()
        self.panel._finish_unload_callbacks = Mock()
        self.ns['_complete_unload'](self.panel, self.panel.web_view, True)
        self.panel._destroy_web_view.assert_not_called()
        self.panel._finish_unload_callbacks.assert_not_called()
        self.timers.pop()()
        self.panel._destroy_web_view.assert_called_once_with(self.panel.web_view)
        self.panel._finish_unload_callbacks.assert_called_once_with(True)

    def test_reopening_during_hide_save_preserves_web_view(self):
        self.panel._unload_in_progress = True
        self.panel._unload_for_hide = True
        self.panel.parent_dock = SimpleNamespace(isVisible=lambda: True)
        self.panel._destroy_web_view = Mock()
        self.panel._finish_unload_callbacks = Mock()
        self.ns['_complete_unload'](self.panel, self.panel.web_view, True)
        self.timers.pop()()
        self.panel._destroy_web_view.assert_not_called()
        self.panel.web_view.setEnabled.assert_called_once_with(True)
        self.assertFalse(self.panel._unload_in_progress)

    def test_failed_unload_retains_live_page(self):
        self.panel._unload_in_progress = True
        self.panel._unload_for_hide = False
        self.panel._destroy_web_view = Mock()
        self.panel._finish_unload_callbacks = Mock()
        self.ns['_complete_unload'](self.panel, self.panel.web_view, False)
        self.timers.pop()()
        self.panel._destroy_web_view.assert_not_called()
        self.panel._finish_unload_callbacks.assert_called_once_with(False)

    def test_switch_while_unloading_is_ignored(self):
        self.panel._unload_in_progress = True
        self.ns['switch_tool'](self.panel, 'mindmap')
        self.assertFalse(self.callbacks)
        self.assertFalse(self.panel._switching)


if __name__ == '__main__':
    unittest.main()
