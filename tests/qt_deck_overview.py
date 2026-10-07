"""Real Anki scheduler and native fallback controls, temporary collection only."""
import importlib,sys,tempfile,types,time
from pathlib import Path
import aqt
from aqt.qt import QApplication,QDialog
from anki.collection import Collection
app=QApplication(['deck-overview-test'])
ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('deck_overview_fixture');pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg
options=importlib.import_module(pkg.__name__+'.deck_overview_options')
with tempfile.TemporaryDirectory(prefix='synapse-deck-overview-') as tmp:
 col=Collection(str(Path(tmp)/'collection.anki2'))
 try:
  did=col.decks.id('Overview Test');col.decks.select(did)
  for i in range(3):
   note=col.new_note(col.models.by_name('Basic'));note.fields=['Question '+str(i),'Answer'];col.add_note(note,did)
  col.sched.reset()
  stats=options.collect_stats(col,did,{'deck_overview_layout':'focus'})
  assert stats['today']==tuple(col.sched.counts()),stats
  assert stats['today'][0]==3,stats
  assert stats['ret_p'] is None and stats['indicator']=='neutral'
  card=col.find_cards('deck:"Overview Test"')[0];stamp=int((time.time()-86400)*1000)
  for i in range(20):col.db.execute('INSERT INTO revlog VALUES (?,?,?,?,?,?,?,?,?)',stamp+i,card,0,3 if i<18 else 1,20,10,2500,1000,1)
  stats=options.collect_stats(col,did,{})
  assert stats['indicator']=='green' and stats['indicator_p']==90,stats
  assert options.collect_stats(col,did,{'deck_overview_green':95})['indicator']=='orange'
  assert options.collect_stats(col,did,{'deck_overview_layout':'overview'})['history']
  from anki.lang import set_lang
  set_lang('en')
  from aqt.deckbrowser import DeckBrowser
  browser=DeckBrowser.__new__(DeckBrowser)
  browser._render_data=types.SimpleNamespace(current_deck_id=did)
  tree=browser._renderDeckTree(col.sched.deck_due_tree())
  dots=importlib.import_module(pkg.__name__+'.deck_browser_indicator')
  assert dots.render(tree,col,{},lambda s:s)==tree
  options.set_indicator_enabled(col,did,True)
  automatic=dots.render(tree,col,{},lambda s:s)
  assert automatic.count('class="sp-deck-indicator"')==1 and '#4caf6e' in automatic
  options.set_smiley_choice(col,did,'red')
  assert '#e05c5c' in dots.render(tree,col,{},lambda s:s)
  options.set_smiley_choice(col,did,'green')
  other=col.decks.id('Other Deck')
  assert options.smiley_choice(col,other)=='auto'
  options.set_smiley_choice(col,other,'green')
  options.set_indicator_enabled(col,did,False)
  tree=browser._renderDeckTree(col.sched.deck_due_tree())
  assert dots.render(tree,col,{},lambda s:s)==tree
  all_dots=dots.render(tree,col,{'deck_overview_indicators_all':True},lambda s:s)
  assert all_dots.count('class="sp-deck-indicator"')==2
  dot_cell=all_dots[all_dots.rfind('<td',0,all_dots.index('class="sp-deck-indicator"')):]
  assert dot_cell.index('class="sp-deck-indicator"') < dot_cell.index('class=gears') < dot_cell.index('</td>')
  assert dots.render(all_dots,col,{'deck_overview_indicators_all':True},lambda s:s).count('class="sp-deck-indicator"')==2
  options.set_indicator_enabled(col,other,True)
  assert dots.render(tree,col,{},lambda s:s).count('class="sp-deck-indicator"')==1
  options.set_smiley_choice(col,other,'auto')
  assert dots.render(tree,col,{},lambda s:s).count('class="sp-deck-indicator"')==0
  options.set_indicator_enabled(col,other,False)
  options.set_indicator_enabled(col,did,True)

  col.close();col=Collection(str(Path(tmp)/'collection.anki2'))
  assert options.smiley_choice(col,did)=='green'
  assert options.indicator_enabled(col,did)
  assert not options.indicator_enabled(col,other)
  options.set_smiley_choice(col,did,'red');assert options.smiley_choice(col,did)=='red'
  options.set_smiley_choice(col,did,'auto');assert options.smiley_choice(col,did)=='auto'
  aqt.mw=types.SimpleNamespace(col=col,pm=types.SimpleNamespace(night_mode=lambda:False))
  dialog_module=importlib.import_module(pkg.__name__+'.settings_dialog')
  dialog=dialog_module.SettingsDialog.__new__(dialog_module.SettingsDialog);QDialog.__init__(dialog)
  dialog.current_config={'deck_overview_layout':'focus','deck_overview_brainstorm':'hidden'};dialog.checkboxes={}
  col.decks.select(did)
  card_widget=dialog.create_deck_overview_card()
  from unittest.mock import patch
  color_button=dialog._deck_controls['deck_overview_title_color']
  with patch.object(dialog_module.QColorDialog,'getColor',return_value=dialog_module.QColor('#123456')):
   color_button.click()
  assert color_button.property('colorValue')=='#123456'
  assert color_button.text()=='#123456'
  assert not dialog.checkboxes['deck_overview_indicators_all'].isChecked()
  assert dialog._deck_controls['deck_overview_layout'].currentData()=='focus'
  assert not dialog.checkboxes['deck_overview_brainstorm'].isChecked()
  dialog._deck_controls['deck_overview_green'].setValue(60)
  assert dialog._deck_controls['deck_overview_orange'].value()==59
  dialog.checkboxes['deck_overview_enabled'].setChecked(False)
  assert not dialog._deck_options_frame.isEnabled()
  dialog.checkboxes['deck_overview_enabled'].setChecked(True)
  assert dialog._deck_options_frame.isEnabled()
  card_widget.deleteLater();dialog.deleteLater();app.processEvents()
  print('PASS real Anki scheduler counts, neutral/new deck, recent recall thresholds, history, native fallback controls')
 finally:col.close()
