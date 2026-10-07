"""First-use invitation tests without importing Anki or accessing real profiles."""
import ast
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'mindmap_sidebar.py'

class TutorialInvitationTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(SOURCE.read_text())
        claim = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_claim_tutorial_invitation')
        consider = next(n for c in tree.body if isinstance(c, ast.ClassDef) for n in c.body if isinstance(n, ast.FunctionDef) and n.name == '_consider_tutorial_invitation')
        self.ns = {'os': os, 'json': json}
        exec(compile(ast.Module(body=[claim, consider], type_ignores=[]), str(SOURCE), 'exec'), self.ns)

    def test_once_and_corrupt_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            claim = self.ns['_claim_tutorial_invitation']
            self.assertTrue(claim(folder))
            self.assertFalse(claim(folder))
            Path(folder, 'SynapsePro_Data', 'mindmap_tutorial.json').write_text('broken')
            self.assertFalse(claim(folder))

    def test_failed_write_does_not_offer_or_repeat(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(os, 'fsync', side_effect=OSError('synthetic failure')):
                self.assertFalse(self.ns['_claim_tutorial_invitation'](folder))
            self.assertFalse(self.ns['_claim_tutorial_invitation'](folder))
        self.assertFalse(self.ns['_claim_tutorial_invitation'](''))

    def test_existing_users_and_closed_views(self):
        for existing in (False, True):
            with self.subTest(existing=existing), tempfile.TemporaryDirectory() as folder:
                calls = []
                self.ns['mw'] = SimpleNamespace(pm=SimpleNamespace(profileFolder=lambda: folder))
                panel = SimpleNamespace(web_view=SimpleNamespace(page=lambda: SimpleNamespace(runJavaScript=calls.append)))
                consider = self.ns['_consider_tutorial_invitation']
                consider(panel, existing)
                consider(panel, False)  # Deleting maps later must not retrigger it.
                self.assertEqual(len(calls), 0 if existing else 1)
                panel.web_view = None
                consider(panel, False)

if __name__ == '__main__':
    unittest.main()
