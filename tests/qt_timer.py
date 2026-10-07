"""Timer WebEngine bridge, actual QueryOp and temporary Anki collection."""
import importlib,json,sys,tempfile,time,types,weakref
from pathlib import Path
import aqt
from aqt.qt import QApplication,QMainWindow
from aqt.taskman import TaskManager
from anki.collection import Collection
from anki.lang import set_lang
set_lang('en')
app=QApplication(['synapse-timer-test']);app.setQuitOnLastWindowClosed(False)
ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('timer_fixture');pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg

def wait(fn):
 end=time.monotonic()+15
 while not fn():
  app.processEvents();time.sleep(.01)
  if time.monotonic()>end:raise AssertionError('Timed out')

with tempfile.TemporaryDirectory(prefix='synapse-timer-') as tmp:
 col=Collection(str(Path(tmp)/'collection.anki2'))
 mw=QMainWindow();mw.app=app;mw.col=col;mw.pm=types.SimpleNamespace(night_mode=lambda:False);mw.weakref=lambda:weakref.proxy(mw);mw._increase_background_ops=lambda:None;mw._decrease_background_ops=lambda:None;mw.taskman=TaskManager(mw);aqt.mw=mw
 try:
  pomo=importlib.import_module(pkg.__name__+'.pomodoro')
  pomo.tooltip=lambda *_args,**_kwargs:None  # host notification, unrelated to the dialog
  analytics=importlib.import_module(pkg.__name__+'.timer_analytics')
  did=col.decks.id('Study::Anatomy::Bones')
  note=col.new_note(col.models.by_name('Basic'));note.fields=['Question','Answer'];col.add_note(note,did);card=note.cards()[0]
  col.db.execute('INSERT INTO revlog VALUES (?,?,?,?,?,?,?,?,?)',int(time.time()*1000)-1000,card.id,-1,3,1,1,2500,60000,1)
  d=pomo.PomodoroWebDialog(mw);d.show()
  def js(code):
   out=[];d._page.runJavaScript(code,out.append);wait(lambda:len(out)>0);return out[0]
  wait(lambda:js("typeof selectTab")=='function')
  wait(lambda:js("document.getElementById('work').value")=='25')
  wait(lambda:d.height()<600)
  initial=d.height();js("selectTab('statistics')");wait(lambda:d.height()!=initial)
  js("selectTab('analytics')");wait(lambda:js('analyticsData !== null'))
  assert js('analyticsData.milliseconds')==60000
  assert js('analyticsData.decks[0].name')=='Study'
  js("document.querySelector('#analyticsBody button').click()")
  wait(lambda:col.get_config(analytics.EXPANDED_KEY,[])==['Study'])
  js("selectTab('settings');document.getElementById('work').value='37';selectTab('analytics')")
  assert js("document.getElementById('work').value")=='37'
  d.reject()
  d2=pomo.PomodoroWebDialog(mw);d2.show();d=d2
  wait(lambda:js("document.getElementById('work') && document.getElementById('work').value")=='25')
  js("selectTab('analytics')");wait(lambda:js('analyticsData !== null'))
  assert js('analyticsData.expanded')==['Study']
  js("selectTab('settings');document.getElementById('work').value='37';document.getElementById('saveBtn').click()")
  wait(lambda:not d.isVisible())
  assert col.get_config(pomo.constants.CONFIG_KEY_POMODORO)['work_minutes']==37
  native=pomo.PomodoroConfigDialog(mw);native.show();native._tabs.setCurrentIndex(2)
  wait(lambda:native._native_analytics_loaded)
  assert native._analytics_tree.topLevelItem(0).text(0)=='Study'
  assert native._analytics_tree.topLevelItem(0).isExpanded()
  native.reject()
  print('PASS real Qt bridge, adaptive height, QueryOp analytics, expansion persistence, cancel/save settings, native fallback')
 finally:
  mw.taskman._collection_executor.shutdown(wait=True);mw.taskman._no_collection_executor.shutdown(wait=True);app.processEvents();col.close();mw.close()
