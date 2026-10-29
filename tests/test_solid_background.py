import json,os,shutil,tempfile,unittest
from pathlib import Path
from test_launch_persistence import load_parts
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
class SolidBackgroundTests(unittest.TestCase):
    def test_persistent_toolbar_state_is_synchronized_for_both_views(self):
        top,bottom=[],[]
        mw=SimpleNamespace(toolbar=SimpleNamespace(web=SimpleNamespace(eval=top.append)),bottomWeb=SimpleNamespace(eval=bottom.append))
        ns=load_parts('__init__.py',functions=('_sync_toolbar_review_class',),env={'mw':mw,'addon_settings':{'active_theme':'none.css'}})
        for state,main,review in [('deckBrowser','true','false'),('overview','true','false'),('review','false','true'),('reset','false','false')]:
            ns['_sync_toolbar_review_class'](state)
            self.assertEqual(top[-1],bottom[-1])
            self.assertIn("toggle('synapse-main-background', "+main+")",top[-1])
            self.assertIn("toggle('reviewing', "+review+")",top[-1])

    def test_generation_changes_only_background_placeholders_and_validates_colors(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)/'theme/user_files';base.mkdir(parents=True);shutil.copy(ROOT/'theme/user_files/none.css',base/'none.css')
            cfg={'custom_bg_light':'#123456','custom_bg_dark':'#654321'}
            ns=load_parts('__init__.py',functions=('_is_valid_hex','write_custom_solid_css'),env={'_HEX_RE':None,'addon_path':temp,'addon_settings':cfg})
            ns['write_custom_solid_css']();actual=(base/'custom_solid.css').read_text();template=(base/'none.css').read_text()
            self.assertEqual(actual.split('\n',1)[1],template.replace('#f5f5f5','#123456').replace('#2c2c2c','#654321'))
            self.assertIn('@import url("medical_theme.css")',actual)
            cfg.update(custom_bg_light='bad; injected CSS',custom_bg_dark=None);ns['write_custom_solid_css']();actual=(base/'custom_solid.css').read_text();self.assertNotIn('injected',actual);self.assertIn('#f5f5f7',actual);self.assertIn('#1f1f21',actual)
if __name__=='__main__':unittest.main()
