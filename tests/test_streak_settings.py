"""Real streak SQL and settings validation against an isolated review history."""
import ast
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import types
import unittest
import traceback

ROOT = Path(__file__).resolve().parents[1]
class StreakSettings(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript('CREATE TABLE revlog(id INTEGER PRIMARY KEY,ease INTEGER); CREATE TABLE cards(id INTEGER PRIMARY KEY);')
        self.today = (datetime.now()-timedelta(hours=4)).date()
        db = types.SimpleNamespace(all=lambda sql,*args:self.db.execute(sql,args).fetchall())
        tree=ast.parse((ROOT/'gamification.py').read_text())
        calc=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='calculate_streak_from_revlog')
        manager=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='GamificationManager')
        manager.body=[n for n in manager.body if isinstance(n,ast.FunctionDef) and n.name=='set_streak_rules']
        ns=dict(datetime=datetime,timedelta=timedelta,mw=types.SimpleNamespace(col=types.SimpleNamespace(db=db,conf={'rollover':4})),traceback=traceback)
        exec(compile(ast.Module(body=[calc,manager],type_ignores=[]),'gamification.py','exec'),ns)
        self.calc=ns['calculate_streak_from_revlog']; self.manager=ns['GamificationManager']()
    def add(self, days, count=1, table='revlog', hour=12, ease=3):
        timestamp=int((datetime.combine(self.today-timedelta(days=days),datetime.min.time())+timedelta(hours=hour)).timestamp()*1000)
        for i in range(count):
            self.db.execute('INSERT INTO '+table+' VALUES ('+('?,?' if table=='revlog' else '?')+')',(timestamp+i,ease) if table=='revlog' else (timestamp+i,))
    def test_default_and_threshold(self):
        for d in range(3): self.add(d,100 if d else 99)
        self.assertEqual(self.calc(),3)
        self.assertEqual(self.calc({'reviews':100}),2)
        self.add(0,1,hour=13);self.assertEqual(self.calc({'reviews':100}),3)
    def test_creation_alternative_and_deletion(self):
        self.add(0,2,'cards'); self.add(1,100);self.add(2,2,'cards')
        self.assertEqual(self.calc({'reviews':100}),1)
        self.assertEqual(self.calc({'reviews':100,'allowCards':True,'cards':2}),3)
        self.db.execute('DELETE FROM cards');self.assertEqual(self.calc({'reviews':100,'allowCards':True,'cards':2}),1)
    def test_missing_day_and_rescheduling(self):
        self.add(0,ease=0);self.add(2)
        self.assertEqual(self.calc(),0)
    def test_rollover(self):
        self.add(0,hour=3);self.add(2)
        self.assertEqual(self.calc(),2)
    def test_long_streak(self):
        for d in range(740):self.add(d)
        self.assertEqual(self.calc(),740)
    def test_validation_and_preserving_rewards(self):
        m=self.manager;m.data={'xp':123,'achievements':{'earned':{'streak':1}}};calls=[]
        m.refresh_streak_cache=lambda:calls.append('refresh');m.save_data=lambda:calls.append('save')
        for bad in ({},None,{'reviews':0,'cards':1,'allowCards':False},{'reviews':True,'cards':1,'allowCards':False},{'reviews':1,'cards':10001,'allowCards':False}):
            self.assertFalse(m.set_streak_rules(bad))
        self.assertEqual(calls,[])
        self.assertTrue(m.set_streak_rules({'reviews':100,'cards':3,'allowCards':True}))
        self.assertEqual(calls,['refresh','save']);self.assertEqual(m.data['xp'],123);self.assertEqual(m.data['achievements']['earned']['streak'],1)
if __name__=='__main__':unittest.main()
