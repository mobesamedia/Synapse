"""Portable release review, with simulated OS failures; no real Anki profile.

Run: python tests/review_165_cross_platform.py -v
Passing these simulations is not equivalent to running native Windows/Linux Qt.
"""
import errno
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import test_launch_persistence as persistence

ROOT = Path(__file__).resolve().parents[1]


def note(text):
    return json.dumps({'pages': [{'id': 'A', 'title': 'Jörg 学习', 'blocks': [
        {'type': 'text', 'html': text, 'extra': {'preserve': True}},
    ]}], 'activePageId': 'A'}, ensure_ascii=False, separators=(',', ':'))


class CrossPlatformStorageReview(unittest.TestCase):
    def storage(self):
        return persistence.load_parts('notebook_sidebar.py', functions=('_list_notebook_versions',),
                                      env=persistence.LaunchPersistenceTests().storage())

    def test_unicode_spaces_hash_and_percent_paths_roundtrip_and_readonly_versions(self):
        ns = self.storage()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'Jörg 学习 #100% space'
            folder.mkdir()
            database = str(folder / 'notebook.sqlite')
            original = note('<b>Original</b> ÄÖÜ 中文 😀')
            latest = note('New content')
            self.assertTrue(ns['_save_snapshot']('notes', original, database))
            self.assertTrue(ns['_save_snapshot']('notes', latest, database))
            self.assertEqual(ns['_load_latest_snapshot']('notes', '[]', database), latest)
            before = Path(database).read_bytes()
            versions = ns['_list_notebook_versions'](database)
            self.assertIn(original, [item['body'] for item in versions])
            self.assertIn(latest, [item['body'] for item in versions])
            self.assertEqual(Path(database).read_bytes(), before)

    def test_exclusive_sqlite_lock_uses_recovery_and_preserves_original(self):
        ns = self.storage()
        with tempfile.TemporaryDirectory() as temp:
            database = str(Path(temp) / 'notebook.sqlite')
            original, latest = note('Original'), note('Latest during lock')
            self.assertTrue(ns['_save_snapshot']('notes', original, database))
            con = sqlite3.connect(database)
            try:
                con.execute('BEGIN EXCLUSIVE')
                self.assertTrue(ns['_save_snapshot']('notes', latest, database, sqlite_timeout=0))
                # Recovery is durable, but an exclusive DB lock prevents checking
                # whether its identity was superseded. Never guess on reload.
                self.assertEqual(ns['_read_snapshot_recovery']('notes', database)[0], latest)
                with self.assertRaises(ns['SnapshotLoadError']):
                    ns['_load_latest_snapshot']('notes', '[]', database)
            finally:
                con.rollback()
                con.close()
            with sqlite3.connect(database) as check:
                self.assertEqual(check.execute('SELECT body FROM notes ORDER BY id DESC LIMIT 1').fetchone()[0], original)
            self.assertTrue(ns['_save_snapshot']('notes', latest, database))
            self.assertEqual(ns['_load_latest_snapshot']('notes', '[]', database), latest)

    def test_preupdate_copy_failure_does_not_prune_originals(self):
        ns = self.storage()
        with tempfile.TemporaryDirectory() as temp:
            database = str(Path(temp) / 'notebook.sqlite')
            ns['_ensure_db_at'](database)
            originals = [note('Original ' + str(index)) for index in range(20)]
            with sqlite3.connect(database) as con:
                con.executemany('INSERT INTO notes(body,updated_at) VALUES (?,1)', [(body,) for body in originals])
            real_open = open
            def locked_backup(path, *args, **kwargs):
                if '.pre-block-ui-v1.json.tmp' in os.fspath(path):
                    raise PermissionError(errno.EACCES, 'simulated backup lock')
                return real_open(path, *args, **kwargs)
            latest = note('New edit')
            with patch('builtins.open', side_effect=locked_backup):
                self.assertTrue(ns['_save_snapshot']('notes', latest, database))
            with sqlite3.connect(database) as con:
                self.assertEqual([row[0] for row in con.execute('SELECT body FROM notes ORDER BY id')], originals)
            self.assertEqual(ns['_load_latest_snapshot']('notes', '[]', database), latest)

    def test_database_and_recovery_write_failures_are_not_acknowledged(self):
        ns = self.storage()
        with tempfile.TemporaryDirectory() as temp:
            database = str(Path(temp) / 'notebook.sqlite')
            original = note('Original')
            self.assertTrue(ns['_save_snapshot']('notes', original, database))
            with patch.dict(ns, {'_ensure_db_at': lambda *a, **kw: (_ for _ in ()).throw(OSError(errno.ENOSPC, 'simulated full disk'))}), patch.object(os, 'replace', side_effect=PermissionError(errno.EACCES, 'simulated replacement failure')):
                self.assertFalse(ns['_save_snapshot']('notes', note('Unwritten edit'), database))
            self.assertEqual(ns['_load_latest_snapshot']('notes', '[]', database), original)

    def test_locked_recovery_never_masks_a_new_acknowledged_sqlite_save(self):
        ns = self.storage()
        with tempfile.TemporaryDirectory() as temp:
            database = str(Path(temp) / 'notebook.sqlite')
            original, latest = note('OLDER RECOVERY'), note('NEW CONFIRMED EDIT')
            self.assertTrue(ns['_save_snapshot']('notes', original, database))
            self.assertTrue(ns['_write_snapshot_recovery']('notes', original, database))
            recovery = ns['_snapshot_recovery_path']('notes', database)
            real_remove, real_replace = os.remove, os.replace
            def remove(path, *args, **kwargs):
                if os.fspath(path) == recovery:
                    raise PermissionError(errno.EACCES, 'simulated Windows sharing violation')
                return real_remove(path, *args, **kwargs)
            def replace(src, dst, *args, **kwargs):
                if os.fspath(dst) == recovery:
                    raise PermissionError(errno.EACCES, 'simulated Windows sharing violation')
                return real_replace(src, dst, *args, **kwargs)
            with patch.object(os, 'remove', side_effect=remove), patch.object(os, 'replace', side_effect=replace):
                acknowledged = ns['_save_snapshot']('notes', latest, database)
            with sqlite3.connect(database) as con:
                self.assertEqual(con.execute('SELECT body FROM notes ORDER BY id DESC LIMIT 1').fetchone()[0], latest)
            loaded = ns['_load_latest_snapshot']('notes', '[]', database)
            self.assertFalse(acknowledged and json.loads(loaded) != json.loads(latest),
                             'Save reported success, but restart loads stale recovery instead of the committed edit')

    def test_windows_uri_encoding_without_claiming_windows_io(self):
        uri = PureWindowsPath(r'C:\Users\Jörg 学习 #100%\Anki2\notebook.sqlite').as_uri()
        self.assertTrue(uri.startswith('file:///C:/Users/'))
        self.assertIn('%23', uri)
        self.assertIn('%25', uri)
        self.assertNotIn(' ', uri)
        self.assertTrue(uri.endswith('/Anki2/notebook.sqlite'))

    def test_archive_paths_are_portable_and_match_reviewed_sources(self):
        archive = ROOT / 'output/releases/Synapse-1.6.5.ankiaddon'
        reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{prefix}{i}' for prefix in ('COM', 'LPT') for i in range(1, 10)}
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            self.assertEqual(len(names), len(set(name.casefold() for name in names)))
            for name in names:
                self.assertNotIn('\\', name)
                self.assertFalse(name.startswith('/'))
                for part in name.split('/'):
                    self.assertEqual(part, part.rstrip(' .'))
                    self.assertNotIn(part.split('.')[0].upper(), reserved)
                    self.assertNotIn(part, ('.', '..'))
                self.assertEqual(hashlib.sha256(z.read(name)).digest(), hashlib.sha256((ROOT / name).read_bytes()).digest())


if __name__ == '__main__':
    unittest.main()
