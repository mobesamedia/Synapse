import importlib.util
import sqlite3
import unittest
from pathlib import Path
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('workspace_links',Path(__file__).resolve().parents[1]/'workspace_links.py')
links=importlib.util.module_from_spec(spec);spec.loader.exec_module(links)

class DB:
    def __init__(self):
        self.db=sqlite3.connect(':memory:');self.db.executescript('create table notes(id integer,guid text);create table cards(id integer,nid integer,ord integer);')
    def all(self,sql,*args):return self.db.execute(sql,args).fetchall()

class LinkTests(unittest.TestCase):
    def setUp(self):
        self.db=DB();self.col=SimpleNamespace(db=self.db,get_card=lambda cid:SimpleNamespace(template=lambda:{'name':'Card 1'}))
        self.note={'version':1,'kind':'note','noteGuid':'guid-one','noteId':'123','label':'Topic'}
        self.card=dict(self.note,kind='card',cardId='456',cardOrd=0,template='Card 1')
    def test_portable_note_uses_guid_not_colliding_local_id(self):
        self.db.all('insert into notes values(123,?)','wrong-note');self.assertIsNone(links.resolve(self.col,self.note))
        self.db.all('insert into notes values(789,?)','guid-one');self.assertEqual(links.resolve(self.col,self.note)['search'],'nid:789')
    def test_card_fallback_and_missing_card(self):
        self.db.all('insert into notes values(789,?)','guid-one');self.db.all('insert into cards values(999,789,0)')
        self.assertEqual(links.resolve(self.col,self.card)['search'],'cid:999')
        self.assertIsNone(links.resolve(self.col,dict(self.card,cardOrd=1)))
        self.assertIsNone(links.resolve(self.col,dict(self.card,template='Other template')))
    def test_ambiguous_guid_is_not_guessed(self):
        self.db.all('insert into notes values(123,?)','guid-one');self.db.all('insert into notes values(789,?)','guid-one')
        self.assertIsNone(links.resolve(self.col,self.note))
    def test_malicious_guid_stays_a_bound_sql_parameter(self):
        self.db.all('insert into notes values(123,?)','guid-one')
        self.assertIsNone(links.resolve(self.col,dict(self.note,noteGuid="' OR 1=1 --")))
    def test_validation_deduplication_and_limits(self):
        self.assertEqual(len(links.clean_links([self.note,self.note,self.card])),2)
        for item in [dict(self.note,noteId='1 OR 1=1'),dict(self.note,noteGuid=''),dict(self.card,cardOrd=True),dict(self.card,cardId='../x')]:
            with self.assertRaises(ValueError):links.clean_link(item)
        with self.assertRaises(ValueError):links.clean_links([self.note]*13)
    def test_preview_is_plain_text(self):
        self.assertEqual(links.plain('<script>bad()</script><b>Topic</b><img src=x>'),'Topic[image]')
