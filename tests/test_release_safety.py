"""Release safety checks; synthetic snapshots and private temporary files only."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import test_launch_persistence as persistence

ROOT = Path(__file__).resolve().parents[1]


class RecoverySafetyTests(unittest.TestCase):
    def storage(self):
        return persistence.load_parts('notebook_sidebar.py', functions=('_list_notebook_versions',),
                                      env=persistence.LaunchPersistenceTests().storage())

    def test_independent_sources_survive_database_damage_and_missing_table(self):
        ns = self.storage()
        for damage in ('corrupt', 'missing-table', 'missing-file'):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as temp:
                database = str(Path(temp) / 'notebook.sqlite')
                body = json.dumps({'pages': [{'id': 'A', 'blocks': [{'type': 'text', 'html': 'Original'}]}]})
                ns['_save_snapshot']('notes', body, database)
                ns['_save_snapshot']('notes', body, database)
                backup = Path(database + '.pre-block-ui-v1.json')
                before = backup.read_bytes()
                if damage == 'corrupt':
                    Path(database).write_bytes(b'broken sqlite for test')
                elif damage == 'missing-table':
                    with sqlite3.connect(database) as con:
                        con.execute('DROP TABLE notes')
                else:
                    Path(database).unlink()
                versions = ns['_list_notebook_versions'](database)
                self.assertIn(body, [version['body'] for version in versions])
                self.assertEqual(backup.read_bytes(), before)
                if damage == 'missing-file':
                    self.assertFalse(Path(database).exists())

    def test_recovery_export_cancellation_existing_file_and_profile_switch(self):
        for scenario in ('save', 'cancel', 'existing-file', 'profile-switch'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'copy.json'
                body = '{"pages":[{"id":"A","blocks":[{"type":"text","html":"Original"}]}]}'
                if scenario == 'existing-file':
                    path.write_text('DO NOT OVERWRITE')
                current = {'path': str(Path(temp) / 'notebook.sqlite')}
                panel = types.SimpleNamespace(_database_path=current['path'])
                item = Mock(return_value=('1 · Versions', scenario != 'cancel'))
                dialogs = types.ModuleType('aqt.qt')
                dialogs.QInputDialog = types.SimpleNamespace(getItem=item)
                finished = []
                ns = persistence.load_parts('notebook_sidebar.py', methods=('_export_notebook_recovery',), env={
                    '_': lambda text: text, 'db_path': lambda: current['path'],
                    'mw': types.SimpleNamespace(taskman=types.SimpleNamespace(run_in_background=lambda work, done: finished.append((work, done)))),
                    '_list_notebook_versions': lambda _: [{'body': body, 'source': 'saved'}],
                    'QFileDialog': types.SimpleNamespace(getSaveFileName=Mock(return_value=(str(path), 'JSON'))),
                    'tooltip': Mock(), 'showInfo': Mock(),
                })
                with patch.dict(sys.modules, {'aqt.qt': dialogs}):
                    ns['_export_notebook_recovery'](panel)
                work, done = finished[0]
                versions = work()
                if scenario == 'profile-switch':
                    current['path'] = 'another-profile'
                done(types.SimpleNamespace(result=lambda: versions))
                if scenario == 'save':
                    self.assertEqual(path.read_text(), body)
                elif scenario == 'existing-file':
                    self.assertEqual(path.read_text(), 'DO NOT OVERWRITE')
                    ns['showInfo'].assert_called_once()
                else:
                    self.assertFalse(path.exists())
                    if scenario == 'profile-switch':
                        item.assert_not_called()


class PackageSafetyTests(unittest.TestCase):
    def test_excludes_drafts_and_recovery_files_but_keeps_runtime(self):
        spec = importlib.util.spec_from_file_location('review_packager', ROOT / 'scripts/package_addon.py')
        packager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(packager)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            keep = ('__init__.py', 'soundcloud_audio.py', 'soundcloud_native_audio.js',
                    'activity_chart.py', 'theme/user_files/shared/scrollbars.css', 'theme/user_files/none.css')
            exclude = ('output/draft.png', 'output/prompts.txt', 'notebook.sqlite', 'notebook.sqlite-wal',
                       'notes.db', 'notebook.sqlite.pre-block-ui-v1.json',
                       'notebook.sqlite.pre-hierarchy-v1.json.tmp', 'synapsepro_notes_recovery.json')
            for name in keep + exclude:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('synthetic')
            self.assertEqual({str(relative) for _, relative in packager.release_files(root)}, set(keep))


if __name__ == '__main__':
    unittest.main()
