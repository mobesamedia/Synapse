"""Release-review regression; private temporary SQLite and synthetic notes only.

Run explicitly: python tests/review_165_versions.py
"""
import json
from pathlib import Path
import tempfile
import unittest
import test_launch_persistence as persistence


class Review165Versions(unittest.TestCase):
    def test_valid_preupdate_copy_remains_readable_when_database_is_corrupt(self):
        ns = persistence.LaunchPersistenceTests().storage()
        ns = persistence.load_parts('notebook_sidebar.py', functions=('_list_notebook_versions',), env=ns)
        with tempfile.TemporaryDirectory() as temporary:
            database = str(Path(temporary) / 'notebook.sqlite')
            original = json.dumps({'pages': [{'id': 'A', 'title': 'Original', 'blocks': [{'type': 'text', 'html': 'PRESERVE THIS NOTE'}]}]})
            self.assertTrue(ns['_save_snapshot']('notes', original, database))
            self.assertTrue(ns['_save_snapshot']('notes', original, database))
            backup = Path(database + '.pre-block-ui-v1.json')
            self.assertTrue(backup.exists())
            before = backup.read_bytes()
            Path(database).write_bytes(b'corrupt database for release-review test')
            versions = ns['_list_notebook_versions'](database)
            self.assertIn(original, [version['body'] for version in versions])
            self.assertEqual(backup.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
