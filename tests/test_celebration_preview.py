"""Preview renderer uses synthetic data and never loads a user profile."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('celebration_preview', ROOT/'celebration_preview.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreviewTests(unittest.TestCase):
    def test_live_mode_and_claimed_reward(self):
        result = module.render_preview({'challenge': {'text': 'Test', 'xp': 100, 'claimed': True}}, live=True)
        self.assertIn('"live": true', result)
        self.assertIn('+100 XP claimed.', result)
        self.assertNotIn('Claim your +100', result)

    def test_popup_preferences(self):
        import ast
        tree = ast.parse((ROOT/'celebration_live.py').read_text())
        fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'select_events')
        ns = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'celebration_live.py', 'exec'), ns)
        events = {'rank': {}, 'level': {}, 'challenge': {}}
        select = ns['select_events']
        self.assertEqual(set(select(events, {})), {'rank', 'challenge'})
        self.assertEqual(select(events, {'gamification_popups_enabled': False}), {})
        self.assertEqual(set(select(events, {'gamification_popup_rank': False, 'gamification_popup_level': True})), {'level', 'challenge'})
        self.assertEqual(len(events), 3)

    def test_rendering_does_not_mutate_events_or_call_anki(self):
        import copy
        events = {'rank':{'old_image':'rang10.png','new_image':'rang11.png',
                         'old_name':'Fact Ferret','new_name':'Focus Falcon','level':50},
                  'challenge':{'text':'Review 50 cards today.', 'xp':195}}
        original = copy.deepcopy(events)
        result = module.render_preview(events)
        self.assertEqual(events, original)
        self.assertIn('rang10.png', result)
        self.assertIn('rang11.png', result)
        self.assertNotIn('pycmd(', result)
        self.assertIn('role="dialog"', result)

    def test_escape_values_validate_accent_and_static_images(self):
        result = module.render_preview({'rank':{'new_name':'<script>alert(1)</script>',
                                               'new_image':'rang11.gif','level':50}}, accent='red;}body{display:none}')
        self.assertNotIn('<script>alert(1)', result)
        self.assertIn('&lt;script&gt;', result)
        self.assertNotIn('rang11.gif', result)
        self.assertIn('--accent:#397cf6', result)

    def test_modes_and_reduced_motion(self):
        for events in ({'level':{'new':51}}, {'challenge':{'text':'Example', 'xp':100}}):
            result = module.render_preview(events, dark=True, reduced_motion=True)
            self.assertIn('"dark": true', result)
            self.assertIn('"reduced": true', result)
            self.assertIn('prefers-reduced-motion', result)


if __name__ == '__main__':
    unittest.main()
