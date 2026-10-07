import ast
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('workspace_assets',ROOT/'workspace_assets.py')
assets=importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)

class WorkspaceTests(unittest.TestCase):
    def test_complete_translation_catalog(self):
        data=json.loads((ROOT/'workspace_translations.json').read_text())
        for key, values in data.items():
            for lang in ('de','es','ko','pt','fr','vi','zh','hi','pl'):
                self.assertTrue(values.get(lang),(key,lang))

    def test_image_references_are_bounded_and_cannot_escape_profile(self):
        valid='a'*64+'.jpg'
        self.assertEqual(assets.image_refs({'nodes':[{'image':valid},{'image':valid}]}),{valid})
        for doc in ({'nodes':[{'image':'../../a.png'}]}, {'nodes':[{'image':valid}]*41}, {'nodes':['invalid']}, {'objects':[{'image':'https://example.org/image.png'}]}):
            with self.assertRaises(ValueError):assets.image_refs(doc)

    def test_notebook_settings_button_uses_its_existing_bridge(self):
        tree=ast.parse((ROOT/'notebook_sidebar.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_build_nav_html')
        env={'workspace_preferences':type('Prefs',(),{'enabled':staticmethod(lambda group:dict.fromkeys(['notebook','todo','pdf'],True))}), '_':lambda x:x,'_NAV_ICONS':dict.fromkeys(['notebook','todo','pdf'],''),'_NAV_LABELS':dict(zip(['notebook','todo','pdf'],['Notebook','To-Do','PDF'])),'ADDON_NAME_FOR_BRIDGE':'synapse-notebook'}
        env.update(dict.fromkeys(['_WIN_ICON','_WIN_ICON_CLOSE','_FS_ICON','_FS_ICON_EXIT'],''))
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'notebook-nav','exec'),env)
        for tool in ('notebook','todo','pdf'):
            html=env['_build_nav_html'](tool)
            self.assertIn("pycmd('synapse-notebook:settings')",html)
            self.assertIn('aria-label="Settings"',html)
