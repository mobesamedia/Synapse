import sqlite3
import unittest
from types import SimpleNamespace
from timer_analytics import collect_analytics, save_expanded


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript('CREATE TABLE cards(id INTEGER, did INTEGER, odid INTEGER); CREATE TABLE revlog(id INTEGER, cid INTEGER, time INTEGER, type INTEGER, ease INTEGER);')
        self.config = {}
        self.now = 1800000000
        self.col = SimpleNamespace(
            db=SimpleNamespace(all=lambda sql,*args:self.db.execute(sql,args).fetchall()),
            decks=SimpleNamespace(all_names_and_ids=lambda:[SimpleNamespace(id=i,name=n) for i,n in [(1,'Study'),(2,'Study::Anatomy'),(3,'Study::Anatomy::Bones'),(4,'Study::Biology'),(5,'Other')]]),
            sched=SimpleNamespace(day_cutoff=self.now+3600),
            get_config=lambda k,d:self.config.get(k,d),set_config=lambda k,v:self.config.update({k:v}))
    def tearDown(self):self.db.close()
    def add(self,cid,did,duration,age=0,kind=1,ease=3,odid=0):
        self.db.execute('INSERT INTO cards VALUES(?,?,?)',(cid,did,odid))
        self.db.execute('INSERT INTO revlog VALUES(?,?,?,?,?)',(int((self.now-age)*1000),cid,duration,kind,ease))
    def test_hierarchy_sort_filtered_and_no_double_count(self):
        self.add(1,2,60000);self.add(2,3,120000,kind=0);self.add(3,4,30000,kind=2);self.add(4,99,10000,kind=3,odid=2);self.add(5,5,40000)
        result=collect_analytics(self.col,self.now)
        self.assertEqual(result['milliseconds'],260000)
        self.assertEqual(result['answers'],5)
        study=result['decks'][0]
        self.assertEqual(study['milliseconds'],220000)
        self.assertEqual(study['children'][0]['name'],'Anatomy')
        self.assertEqual(study['children'][0]['ownMilliseconds'],70000)
    def test_excludes_old_future_manual_deleted_zero_and_unknown(self):
        self.add(1,2,10000,age=31*86400);self.add(2,2,10000,kind=4);self.add(3,2,10000,ease=0);self.add(4,2,0);self.add(5,2,10000,age=-10);self.add(6,999,10000)
        self.db.execute('INSERT INTO revlog VALUES(?,?,?,?,?)',(self.now*1000,99999,10000,1,3))
        self.assertEqual(collect_analytics(self.col,self.now)['decks'],[])
    def test_study_day_boundary_and_expansion(self):
        start=self.now+3600-30*86400
        self.add(1,3,1000,age=self.now-start)
        self.add(2,3,5000,age=self.now-start+1)
        save_expanded(self.col,['Study','Study','Study::Anatomy','missing',None])
        result=collect_analytics(self.col,self.now)
        self.assertEqual(result['milliseconds'],1000)
        self.assertEqual(result['expanded'],['Study','Study::Anatomy'])
