import ast
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class WorkspaceSettingsSaveTests(unittest.TestCase):
    def test_profile_groups_and_invalid_payloads(self):
        tree = ast.parse((ROOT / 'workspace_preferences.py').read_text())
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('save', 'save_command')]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'preferences.json'
            env = {'json': json, 'GROUPS': {'maps': ('mindmap', 'roadmap'), 'notebook': ('notebook', 'todo', 'pdf')}, 'path': lambda: target, 'atomic_write': lambda p, b: p.write_bytes(b)}
            exec(compile(ast.Module(body=funcs, type_ignores=[]), 'prefs', 'exec'), env)
            env['save']('maps', {'mindmap': True, 'roadmap': False})
            env['save']('notebook', {'notebook': False, 'todo': True, 'pdf': True})
            expected = target.read_bytes()
            for bad in ({'mindmap': False, 'roadmap': False}, {'mindmap': 1, 'roadmap': True}, {'mindmap': True}, {'mindmap': True, 'roadmap': True, 'other': True}):
                with self.assertRaises(ValueError): env['save']('maps', bad)
                self.assertEqual(target.read_bytes(), expected)
            self.assertEqual(json.loads(expected)['todo'], True)
            with self.assertRaises(ValueError): env['save_command']('maps', 'settings-save:' + 'x' * 2001)
