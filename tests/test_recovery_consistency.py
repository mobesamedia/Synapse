"""Recovery/SQLite consistency under locks, interrupted commits and restarts.

All files are synthetic and live in private temporary directories. Process-exit
tests intentionally terminate child Python processes, never Anki or a profile.
"""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import test_launch_persistence as persistence

ROOT = Path(__file__).resolve().parents[1]


def note(text):
    return json.dumps({'pages': [{'id': 'A', 'blocks': [
        {'type': 'text', 'html': text, 'unknown': {'preserve': True}}
    ]}], 'unknownRoot': 'preserve'}, ensure_ascii=False, separators=(',', ':'))


class RecoveryConsistencyTests(unittest.TestCase):
    def storage(self):
        return persistence.load_parts('notebook_sidebar.py', functions=('_list_notebook_versions',),
                                      env=persistence.LaunchPersistenceTests().storage())

    def locked_recovery(self, path):
        remove, replace = os.remove, os.replace
        def locked_remove(target, *args, **kwargs):
            if os.fspath(target) == path:
                raise PermissionError('simulated sharing violation')
            return remove(target, *args, **kwargs)
        def locked_replace(source, target, *args, **kwargs):
            if os.fspath(target) == path:
                raise PermissionError('simulated sharing violation')
            return replace(source, target, *args, **kwargs)
        return patch.object(os, 'remove', side_effect=locked_remove), patch.object(os, 'replace', side_effect=locked_replace)

    def test_locked_recovery_restart_and_30_further_saves_preserve_confirmed_content(self):
        ns = self.storage()
        with tempfile.TemporaryDirectory() as temp:
            database = str(Path(temp) / 'notebook.sqlite')
            old = note('Older original')
            self.assertTrue(ns['_save_snapshot']('notes', old, database))
            self.assertTrue(ns['_write_snapshot_recovery']('notes', old, database))
            recovery = ns['_snapshot_recovery_path']('notes', database)
            original_bytes = Path(recovery).read_bytes()
            remove, replace = self.locked_recovery(recovery)
            with remove, replace:
                for revision in range(31):
                    latest = note('NEW CONFIRMED CONTENT · 学习 ' + str(revision))
                    self.assertTrue(ns['_save_snapshot']('notes', latest, database))
                    fresh = self.storage()
                    self.assertEqual(fresh['_load_latest_snapshot']('notes', '[]', database), latest)
                    self.assertEqual(Path(recovery).read_bytes(), original_bytes)
                with sqlite3.connect(database) as con:
                    self.assertEqual(con.execute('SELECT count(*) FROM notes').fetchone()[0], 20)
                    self.assertEqual(con.execute('SELECT count(*) FROM snapshot_recovery_retired').fetchone()[0], 1)
            for suffix in ('pre-block-ui-v1', 'pre-hierarchy-v1'):
                backup = json.loads(Path(database + '.' + suffix + '.json').read_text(encoding='utf-8'))
                self.assertIn(old, [row[1] for row in backup['snapshots']])
            self.assertIn(old, [item['body'] for item in ns['_list_notebook_versions'](database)])

    def test_new_recovery_of_identical_content_is_not_mistaken_for_retired_copy(self):
        ns = self.storage()
        with tempfile.TemporaryDirectory() as temp:
            database = str(Path(temp) / 'notebook.sqlite')
            old, newer = note('Same content, intentionally restored'), note('Intermediate')
            ns['_save_snapshot']('notes', old, database)
            ns['_write_snapshot_recovery']('notes', old, database)
            path = ns['_snapshot_recovery_path']('notes', database)
            first_identity = ns['_read_snapshot_recovery']('notes', database)[1]
            remove, replace = self.locked_recovery(path)
            with remove, replace:
                self.assertTrue(ns['_save_snapshot']('notes', newer, database))
            self.assertIsNone(ns['_load_snapshot_recovery']('notes', database))
            self.assertTrue(ns['_write_snapshot_recovery']('notes', old, database))
            self.assertNotEqual(ns['_read_snapshot_recovery']('notes', database)[1], first_identity)
            self.assertEqual(self.storage()['_load_latest_snapshot']('notes', '[]', database), old)

    def test_legacy_recovery_and_database_are_not_changed_by_reading(self):
        ns = self.storage()
        for original in ('[{"type":"text","html":"Legacy array","extra":123}]',
                         '{"blocks":[{"type":"text","html":"Legacy object"}],"extra":true}',
                         note('Legacy multi-page')):
            with self.subTest(original=original), tempfile.TemporaryDirectory() as temp:
                database = str(Path(temp) / 'notebook.sqlite')
                ns['_save_snapshot']('notes', note('Database original'), database)
                path = Path(ns['_snapshot_recovery_path']('notes', database))
                path.write_text(json.dumps({'version': 1, 'table': 'notes', 'body': json.loads(original)}, ensure_ascii=False), encoding='utf-8')
                before = (Path(database).read_bytes(), path.read_bytes())
                self.assertEqual(json.loads(ns['_load_latest_snapshot']('notes', '[]', database)), json.loads(original))
                self.assertEqual((Path(database).read_bytes(), path.read_bytes()), before)
                remove, replace = self.locked_recovery(str(path))
                with remove, replace:
                    self.assertTrue(ns['_save_snapshot']('notes', note('New explicit edit'), database))
                self.assertEqual(path.read_bytes(), before[1])
                self.assertEqual(ns['_load_latest_snapshot']('notes', '[]', database), note('New explicit edit'))

    def test_unreadable_database_or_recovery_fails_closed_and_keeps_sources(self):
        ns = self.storage()
        with tempfile.TemporaryDirectory() as temp:
            database = str(Path(temp) / 'notebook.sqlite')
            ns['_save_snapshot']('notes', note('Original'), database)
            ns['_write_snapshot_recovery']('notes', note('Pending recovery'), database)
            recovery = Path(ns['_snapshot_recovery_path']('notes', database))
            before = (Path(database).read_bytes(), recovery.read_bytes())
            with patch.object(sqlite3, 'connect', side_effect=sqlite3.OperationalError('locked')):
                with self.assertRaises(ns['SnapshotLoadError']):
                    ns['_load_latest_snapshot']('notes', '[]', database)
                versions = ns['_list_notebook_versions'](database)
                self.assertIn(note('Pending recovery'), [item['body'] for item in versions])
            real_stat = os.stat
            def denied_stat(path, *args, **kwargs):
                if os.fspath(path) == database:
                    raise PermissionError('denied database stat')
                return real_stat(path, *args, **kwargs)
            with patch.object(os, 'stat', side_effect=denied_stat):
                with self.assertRaises(ns['SnapshotLoadError']):
                    ns['_load_latest_snapshot']('notes', '[]', database)
            real_open = open
            def denied_open(path, *args, **kwargs):
                if os.fspath(path) == str(recovery):
                    raise PermissionError('denied recovery read')
                return real_open(path, *args, **kwargs)
            with patch('builtins.open', side_effect=denied_open):
                with self.assertRaises(ns['SnapshotLoadError']):
                    ns['_load_latest_snapshot']('notes', '[]', database)
            self.assertEqual((Path(database).read_bytes(), recovery.read_bytes()), before)

    def test_missing_database_retains_pending_recovery_without_creating_database(self):
        ns = self.storage()
        with tempfile.TemporaryDirectory() as temp:
            database = str(Path(temp) / 'notebook.sqlite')
            body = note('Recovery only')
            ns['_write_snapshot_recovery']('notes', body, database)
            self.assertEqual(ns['_load_latest_snapshot']('notes', '[]', database), body)
            self.assertFalse(Path(database).exists())

    def test_cleanup_does_not_remove_or_overwrite_a_newer_recovery_identity(self):
        ns = self.storage()
        with tempfile.TemporaryDirectory() as temp:
            database = str(Path(temp) / 'notebook.sqlite')
            ns['_write_snapshot_recovery']('notes', note('Old'), database)
            old_identity = ns['_read_snapshot_recovery']('notes', database)[1]
            ns['_write_snapshot_recovery']('notes', note('New independent recovery'), database)
            path = Path(ns['_snapshot_recovery_path']('notes', database))
            before = path.read_bytes()
            ns['_clear_snapshot_recovery']('notes', note('Committed earlier'), database, old_identity)
            self.assertEqual(path.read_bytes(), before)

    def test_retirement_is_table_specific_for_notebook_todos_and_pdfs(self):
        ns = self.storage()
        cases = [('notes', note('Old'), note('New')),
                 ('todos', '[{"text":"Old","extra":true}]', '[{"text":"New","extra":true}]'),
                 ('pdfs', '{"pdfs":[{"path":"Old.pdf","extra":true}]}', '{"pdfs":[{"path":"New.pdf","extra":true}]}')]
        with tempfile.TemporaryDirectory() as temp:
            database = str(Path(temp) / 'notebook.sqlite')
            for table, old, new in cases:
                ns['_save_snapshot'](table, old, database)
                ns['_write_snapshot_recovery'](table, old, database)
                remove, replace = self.locked_recovery(ns['_snapshot_recovery_path'](table, database))
                with remove, replace:
                    self.assertTrue(ns['_save_snapshot'](table, new, database))
                self.assertEqual(ns['_load_latest_snapshot'](table, '[]', database), new)

    def test_real_process_exit_before_or_after_commit_keeps_consistent_sources(self):
        for point, expected_exit in (('before-commit', 71), ('before-commit-large', 71), ('after-commit', 72)):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as temp:
                ns = self.storage()
                database = str(Path(temp) / 'notebook.sqlite')
                original, pending, latest = note('Original SQLite'), note('Last acknowledged recovery'), note('New edit')
                if point == 'before-commit-large':
                    latest = note('Large uncommitted edit ' + 'x' * (4 * 1024 * 1024))
                ns['_save_snapshot']('notes', original, database)
                ns['_write_snapshot_recovery']('notes', pending, database)
                recovery = Path(ns['_snapshot_recovery_path']('notes', database))
                before = recovery.read_bytes()
                script = '''
import sys,os,sqlite3
sys.path.insert(0,sys.argv[1])
import test_launch_persistence as p
ns=p.LaunchPersistenceTests().storage()
database,body_file,point=sys.argv[2:]
with open(body_file,encoding='utf-8') as handle:body=handle.read()
if point=='after-commit':
    ns['_clear_snapshot_recovery']=lambda *a,**kw:os._exit(72)
else:
    connect=sqlite3.connect
    calls=[0]
    class ExitBeforeCommit:
        def __init__(self,con):self.con=con
        def __getattr__(self,key):return getattr(self.con,key)
        def __enter__(self):return self
        def __exit__(self,*args):os._exit(71)
    def wrapped(*a,**kw):
        con=connect(*a,**kw);calls[0]+=1
        return ExitBeforeCommit(con) if calls[0]==2 else con
    sqlite3.connect=wrapped
ns['_save_snapshot']('notes',body,database)
raise AssertionError('exit point was not reached')
'''
                payload = Path(temp) / 'child-payload.json'
                payload.write_text(latest, encoding='utf-8')
                result = subprocess.run([sys.executable, '-c', script, str(ROOT / 'tests'), database, str(payload), point],
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, expected_exit, result.stdout + result.stderr)
                fresh = self.storage()
                self.assertEqual(fresh['_load_latest_snapshot']('notes', '[]', database),
                                 latest if point == 'after-commit' else pending)
                self.assertEqual(recovery.read_bytes(), before)
                with sqlite3.connect(database) as con:
                    retired = con.execute("SELECT 1 FROM sqlite_master WHERE name='snapshot_recovery_retired'").fetchone()
                    self.assertEqual(bool(retired), point == 'after-commit')
                    if point.startswith('before-commit'):
                        self.assertEqual(con.execute('SELECT body FROM notes').fetchall(), [(original,)])

    def test_commit_failure_rolls_back_retirement_and_uses_fresh_recovery_or_reports_failure(self):
        for recovery_locked in (False, True):
            with self.subTest(recovery_locked=recovery_locked), tempfile.TemporaryDirectory() as temp:
                ns = self.storage()
                database = str(Path(temp) / 'notebook.sqlite')
                original, pending, latest = note('Original DB'), note('Pending previous edit'), note('New edit')
                ns['_save_snapshot']('notes', original, database)
                ns['_write_snapshot_recovery']('notes', pending, database)
                recovery = ns['_snapshot_recovery_path']('notes', database)
                before = Path(recovery).read_bytes()
                connect = sqlite3.connect
                calls = [0]
                class FailCommit:
                    def __init__(self, con): self.con = con
                    def __getattr__(self, key): return getattr(self.con, key)
                    def __enter__(self): return self
                    def __exit__(self, *args):
                        self.con.rollback()
                        raise sqlite3.OperationalError('simulated commit failure')
                def wrapped(*args, **kwargs):
                    con = connect(*args, **kwargs)
                    calls[0] += 1
                    return FailCommit(con) if calls[0] == 2 else con
                remove, replace = self.locked_recovery(recovery)
                with patch.object(sqlite3, 'connect', side_effect=wrapped):
                    if recovery_locked:
                        with remove, replace:
                            acknowledged = ns['_save_snapshot']('notes', latest, database)
                    else:
                        acknowledged = ns['_save_snapshot']('notes', latest, database)
                self.assertEqual(acknowledged, not recovery_locked)
                with connect(database) as con:
                    self.assertEqual(con.execute('SELECT body FROM notes').fetchall(), [(original,)])
                    self.assertIsNone(con.execute("SELECT 1 FROM sqlite_master WHERE name='snapshot_recovery_retired'").fetchone())
                self.assertEqual(ns['_load_latest_snapshot']('notes', '[]', database), pending if recovery_locked else latest)
                if recovery_locked:
                    self.assertEqual(Path(recovery).read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
