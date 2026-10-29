"""Pre-update notebook copies use only temporary databases and synthetic notes."""
import json, os, sqlite3, tempfile, unittest
from unittest.mock import patch
import test_launch_persistence as persistence
from pathlib import Path

class NotebookBackupTests(unittest.TestCase):
    def test_pre_update_copy_is_preserved_after_history_pruning(self):
        ns = persistence.LaunchPersistenceTests().storage()
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, 'notebook.sqlite')
            original = '{"pages":[{"id":"A","blocks":[{"type":"text","html":"Original notes"}]}]}'
            ns['_ensure_db_at'](path)
            with sqlite3.connect(path) as con:
                con.execute('INSERT INTO notes(body, updated_at) VALUES (?, 1)', (original,))
            for revision in range(25):
                self.assertTrue(ns['_save_snapshot']('notes', json.dumps({'pages':[{'title':str(revision)}]}), path))
            with open(path + '.pre-block-ui-v1.json', encoding='utf-8') as handle:
                backup = json.load(handle)
            self.assertEqual(backup['snapshots'][0][1], original)
            with open(path + '.pre-hierarchy-v1.json', encoding='utf-8') as handle:
                hierarchy_backup = json.load(handle)
            self.assertEqual(hierarchy_backup['snapshots'][0][1], original)
            hierarchy_before = Path(path + '.pre-hierarchy-v1.json').read_bytes()
            with sqlite3.connect(path) as con:
                self.assertEqual(con.execute('SELECT count(*) FROM notes').fetchone()[0], 20)
            before = Path(path + '.pre-block-ui-v1.json').read_bytes()
            ns['_save_snapshot']('notes', '{"pages":[]}', path)
            self.assertEqual(Path(path + '.pre-block-ui-v1.json').read_bytes(), before)
            self.assertEqual(Path(path + '.pre-hierarchy-v1.json').read_bytes(), hierarchy_before)

    def test_version_listing_is_read_only_and_includes_pruned_originals(self):
        ns = persistence.LaunchPersistenceTests().storage()
        ns = persistence.load_parts('notebook_sidebar.py', functions=('_list_notebook_versions',), env=ns)
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, 'versions.sqlite')
            self.assertEqual(ns['_list_notebook_versions'](path), [])
            self.assertFalse(os.path.exists(path))
            original = '{"pages":[{"id":"A","title":"Old note","blocks":[{"type":"text","html":"<b>Original</b>","extra":"keep"}]}],"extra":"keep"}'
            ns['_save_snapshot']('notes', original, path)
            for revision in range(25):
                ns['_save_snapshot']('notes', json.dumps({'pages':[{'id':'A','title':str(revision),'blocks':[]}]}), path)
            paths = [Path(path), Path(path + '.pre-block-ui-v1.json'), Path(path + '.pre-hierarchy-v1.json')]
            before = [item.read_bytes() for item in paths]
            versions = ns['_list_notebook_versions'](path)
            self.assertIn(original, [version['body'] for version in versions])
            self.assertTrue(any(version['source']=='pre-update' and version['body']==original for version in versions))
            self.assertEqual(len({version['body'] for version in versions}), len(versions))
            self.assertEqual([item.read_bytes() for item in paths], before)
            # A malformed side backup does not hide the valid database or another backup.
            paths[1].write_text('invalid backup', encoding='utf-8')
            self.assertIn(original, [version['body'] for version in ns['_list_notebook_versions'](path)])

    def test_copy_includes_existing_recovery_and_invalid_saves_do_not_touch_it(self):
        ns = persistence.LaunchPersistenceTests().storage()
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, 'notebook.sqlite')
            original = '{"pages":[{"title":"Recovered original"}]}'
            self.assertTrue(ns['_write_snapshot_recovery']('notes', original, path))
            self.assertFalse(ns['_save_snapshot']('notes', 'broken JSON', path))
            self.assertFalse(os.path.exists(path + '.pre-block-ui-v1.json'))
            self.assertTrue(ns['_save_snapshot']('notes', '{"pages":[]}', path))
            with open(path + '.pre-block-ui-v1.json', encoding='utf-8') as handle:
                self.assertEqual(json.loads(json.load(handle)['recovery']), json.loads(original))

if __name__ == '__main__': unittest.main()
