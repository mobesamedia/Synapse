"""Display-only demo state has no collection/configuration API dependency."""
import importlib.util
from pathlib import Path
import unittest
from datetime import date
spec=importlib.util.spec_from_file_location('dashboard_demo',Path(__file__).resolve().parents[1]/'dashboard_demo.py')
demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)

class DashboardDemoTests(unittest.TestCase):
    def tearDown(self): demo.stop()
    def test_isolation_and_profile_switch(self):
        class ForbiddenCollection:
            def __getattr__(self,key): raise AssertionError("No collection access: "+key)
        owner=ForbiddenCollection()
        values=dict(demo.DEFAULTS,level=100)
        demo.start(owner,values);values['level']=2
        display=demo.current(owner);self.assertEqual(display['level'],100)
        display['level']=3;self.assertEqual(demo.current(owner)['level'],100)
        self.assertIsNone(demo.current(ForbiddenCollection()))
        self.assertIsNone(demo.current(owner))
    def test_stop_and_reapply(self):
        owner=object()
        demo.start(owner,dict(level=55));demo.start(owner,dict(level=70))
        self.assertEqual(demo.current(owner)['level'],70)
        demo.stop();self.assertIsNone(demo.current(owner))
        with self.assertRaises(ValueError): demo.start(None,{})
    def test_bounds_and_graphs(self):
        owner=object();demo.start(owner,dict(level=500,retention=-1,consistency='unknown'))
        state=demo.current(owner)
        self.assertEqual((state['level'],state['retention'],state['consistency']),(100,0,'varied'))
        for days in (7,30,365):
            profiles=[demo.counts(key,days,date(2026,1,31)) for key in ('varied','paused','steady')]
            self.assertTrue(all(len(p)==days for p in profiles))
            self.assertTrue(all(v>=0 for p in profiles for v in p.values()))
            self.assertEqual(list(profiles[1].values())[-1],0)
            self.assertEqual(len({tuple(p.values()) for p in profiles}),3)
