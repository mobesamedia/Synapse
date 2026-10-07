"""Read-only overview metrics, threshold validation and optional content."""
import importlib.util
from pathlib import Path
import sqlite3,types,unittest
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
options=load('deck_overview_options');view=load('deck_overview_view')
class OverviewTests(unittest.TestCase):
 def setUp(self):
  self.sql=sqlite3.connect(':memory:');self.addCleanup(self.sql.close)
  self.sql.executescript('CREATE TABLE cards(id integer,did integer,lapses integer,ivl integer,queue integer);CREATE TABLE revlog(id integer,cid integer,ease integer,type integer);')
  self.sql.executemany('INSERT INTO cards VALUES (?,?,?,?,?)',[(1,1,0,30,2),(2,2,9,4,1),(3,1,0,0,0),(4,3,0,30,2),(5,1,0,0,-1)])
  db=types.SimpleNamespace(first=lambda q,*p:self.sql.execute(q,p).fetchone(),all=lambda q,*p:self.sql.execute(q,p).fetchall())
  self.col=types.SimpleNamespace(db=db,decks=types.SimpleNamespace(deck_and_child_ids=lambda d:[1,2]),sched=types.SimpleNamespace(counts=lambda:(12,4,32)),conf={'rollover':4})
  self.now=1800000000
 def reviews(self,count,success,days=1,kind=1,cid=1):
  base=int((self.now-days*86400)*1000)
  self.sql.executemany('INSERT INTO revlog VALUES (?,?,?,?)',[(base+i,cid,3 if i<success else 1,kind) for i in range(count)])
 def test_actual_recent_answers_replace_ease(self):
  self.reviews(100,90);self.reviews(100,0,days=50);self.reviews(100,0,kind=0);self.reviews(100,0,cid=4)
  stats=options.collect_stats(self.col,1,{},self.now)
  self.assertEqual(stats['indicator'],'green');self.assertEqual(stats['indicator_p'],90)
  self.assertEqual(stats['ret_p'],45);self.assertEqual(stats['total'],4);self.assertEqual(stats['hard'],1)
  self.assertIsNone(stats['today']);self.assertEqual(stats['learned'],1)
 def test_neutral_and_exact_boundaries(self):
  cfg=options.normalize({})
  self.assertEqual(options.indicator(19,19,cfg),'neutral')
  for ok,state in [(17,'green'),(14,'orange'),(13,'red')]:self.assertEqual(options.indicator(ok,20,cfg),state)
  self.reviews(19,19);self.assertEqual(options.collect_stats(self.col,1,{},self.now)['indicator'],'neutral')
 def test_no_data_is_not_failure(self):
  stats=options.collect_stats(self.col,1,{},self.now)
  self.assertIsNone(stats['ret_p']);self.assertEqual(stats['indicator'],'neutral')
 def test_history_scope_and_period(self):
  self.reviews(20,20,days=2);self.reviews(20,0,days=10);self.reviews(20,0,days=40)
  cfg={'deck_overview_retention_days':7,'deck_overview_layout':'overview'}
  stats=options.collect_stats(self.col,1,cfg,self.now)
  self.assertEqual(stats['ret_p'],100);self.assertEqual(sum(n for _,n in stats['history']),40);self.assertEqual(len(stats['history']),14)
 def test_normalization(self):
  cfg=options.normalize({'deck_overview_green':20,'deck_overview_orange':90,'deck_overview_layout':'bad','deck_overview_show_today':'false'})
  self.assertEqual(cfg['deck_overview_orange'],19);self.assertEqual(cfg['deck_overview_layout'],'classic')
 def test_title_color_validation(self):
  self.assertEqual(options.normalize({'deck_overview_title_color':'#12aBcF'})['deck_overview_title_color'],'#12aBcF')
  for invalid in ('red','</style>',None,'#123456;display:none'):
   self.assertEqual(options.normalize({'deck_overview_title_color':invalid})['deck_overview_title_color'],'#577B9A')
  self.assertEqual(options.normalize({})['deck_overview_title_color_mode'],'primary')
 def test_fixed_layouts(self):
  for layout in ('classic','focus','overview'):
   cfg=options.normalize({'deck_overview_layout':layout,'deck_overview_brainstorm':False,'deck_overview_show_retention':False})
   stats=options.collect_stats(self.col,1,cfg,self.now)
   rendered=view.render_dashboard('<script>unsafe</script>',stats,cfg,lambda s:s,lambda s:s)
   self.assertNotIn('<script>',rendered);self.assertNotIn('id="brainstorm-btn"',rendered);self.assertIn('start_study',rendered)
   self.assertEqual('class="today-counts"' in rendered,layout=='focus')
   self.assertEqual('data-info="retention"' in rendered,layout!='focus')
   self.assertEqual('class="history-panel"' in rendered,layout=='overview')
   if layout=='focus':self.assertEqual(stats['today'],(12,4,32))
 def test_empty_charts(self):
  stats=options.collect_stats(self.col,1,{'deck_overview_layout':'overview'},self.now)
  rendered=view.render_dashboard('Deck',stats,options.normalize({'deck_overview_layout':'overview'}),lambda s:s,lambda s:s)
  self.assertIn('No reviews in the last 14 days',rendered)
  self.assertIn('class="history-line"',rendered)
  stats['today']=(0,0,0)
  rendered=view.render_dashboard('Deck',stats,options.normalize({'deck_overview_layout':'focus'}),lambda s:s,lambda s:s)
  self.assertIn('No cards waiting right now',rendered)
  self.assertNotIn('nan',rendered.lower())
 def test_old_cloud_preferences_migrate(self):
  self.assertTrue(options.normalize({'deck_overview_brainstorm':'menu'})['deck_overview_brainstorm'])
  self.assertFalse(options.normalize({'deck_overview_brainstorm':'hidden'})['deck_overview_brainstorm'])
  fields=options.payload({},lambda s:s)['fields']
  self.assertIn('deck_overview_title_color',{field['key'] for field in fields})
if __name__=='__main__':unittest.main()
