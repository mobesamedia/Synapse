"""Polish selection, auto detection, and pre-profile onboarding translations."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import locales
from onboarding_terms import TERMS_TRANSLATIONS


class PolishLanguageTests(unittest.TestCase):
    def test_polish_and_anki_region_detection(self):
        with patch.object(locales, 'USER_LANG', 'pl'):
            self.assertEqual(locales._('Settings'), 'Ustawienia')
            self.assertEqual(locales._('Create cards'), 'Utwórz karty')
            self.assertEqual(locales._('Workspace settings'), 'Ustawienia obszaru')
        for code in ('pl', 'pl_PL', 'pl-PL'):
            module = types.ModuleType('anki.lang')
            module.current_lang = code
            with patch.dict(sys.modules, {'anki.lang': module}), patch.object(locales, 'USER_LANG', 'auto'):
                self.assertEqual(locales._current_lang(), 'pl')
                self.assertEqual(locales._('Cancel'), 'Anuluj')

    def test_explicit_translation_preserves_active_language(self):
        with patch.object(locales, 'USER_LANG', 'de'):
            self.assertEqual(locales.translate_for_language('Show details', 'pl'), 'Pokaż szczegóły')
            self.assertEqual(locales.USER_LANG, 'de')

    def test_real_onboarding_payload_includes_polish(self):
        tree = ast.parse((ROOT / 'onboarding_dialog.py').read_text())
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_on_load_finished')
        env = {'json': json, 'TERMS_TRANSLATIONS': TERMS_TRANSLATIONS,
               'translate_for_language': locales.translate_for_language}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), 'onboarding-payload', 'exec'), env)
        scripts = []
        dialog = types.SimpleNamespace(parent=lambda: None, _page=types.SimpleNamespace(runJavaScript=scripts.append))
        env['_on_load_finished'](dialog, True)
        payload = json.loads(scripts[0].split('window.initOnboarding(', 1)[1][:-2])
        self.assertEqual(len(payload['terms']), 10)
        self.assertEqual(payload['errors']['pl']['Copy error'], 'Kopiuj błąd')
        self.assertEqual(payload['themes']['pl'][2], 'Las')
        self.assertEqual(payload['terms']['pl']['html'].count('<h4>'), 8)
        self.assertNotIn('Terms of Service', payload['terms']['pl']['html'])

    def test_onboarding_accepts_polish_without_changing_machine_keys(self):
        tree = ast.parse((ROOT / '__init__.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_apply_onboarding_result')
        languages = next(n.value for n in ast.walk(fn) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'valid_langs' for t in n.targets))
        self.assertIn('pl', ast.literal_eval(languages))
        settings = ast.parse((ROOT / 'settings_dialog.py').read_text())
        self.assertTrue(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'addItem' and len(n.args) == 2 and isinstance(n.args[1], ast.Constant) and n.args[1].value == 'pl' for n in ast.walk(settings)))

    def test_polish_ai_response_uses_polish_instruction(self):
        tree = ast.parse((ROOT / 'ai_assistant.py').read_text())
        assignment = next(n for n in tree.body if isinstance(n, ast.AnnAssign) and n.target.id == 'LANG_SUFFIX')
        self.assertEqual(ast.literal_eval(assignment.value)['Polish'], 'in Polish')


if __name__ == '__main__':
    unittest.main()
