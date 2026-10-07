import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]

class BackdropGateTests(unittest.TestCase):
    def test_image_layer_only_for_active_glass_dashboard(self):
        # Extract gate and remove its import to supply the actual pure clamp.
        import sys
        sys.path.insert(0,str(ROOT))
        from dashboard_appearance import surface_opacity
        node=next(n for n in ast.parse((ROOT/'custom_background.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_glass_active')
        node.body=[n for n in node.body if not isinstance(n,ast.ImportFrom)]
        settings={'dashboard_glass_enabled':True,'dashboard_surface_opacity':80,'custom_background_enabled':True}
        ns={'surface_opacity':surface_opacity,'mw':SimpleNamespace(state='deckBrowser'),'_settings':settings,'has_image':lambda:True}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'gate','exec'),ns)
        gate=ns['_glass_active'];self.assertTrue(gate())
        for state in ['review','overview']:
            ns['mw'].state=state;self.assertFalse(gate())
        ns['mw'].state='deckBrowser'
        for key,value in [('dashboard_surface_controls_expanded',False),('dashboard_glass_enabled',False),('dashboard_surface_opacity',100),('custom_background_enabled',False)]:
            previous=settings.get(key);settings[key]=value;self.assertFalse(gate());settings[key]=previous

    def test_master_switch_disables_all_surface_overrides(self):
        from dashboard_appearance import dashboard_surface_css
        self.assertEqual(dashboard_surface_css(40, True, 12, 75, enabled=False), '')
        active = dashboard_surface_css(40, True, 12, 75, enabled=True)
        self.assertIn('backdrop-filter:blur(12px)', active)
        self.assertIn('box-shadow:', active)
        self.assertIn('40%', active)

if __name__=='__main__':unittest.main()
