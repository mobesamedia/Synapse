"""Exercise actual renderers and developer controls without any writable collection."""
import importlib,json,sys,types
from pathlib import Path
import aqt
from aqt.qt import QApplication,QMainWindow,QDialog,QPushButton,QSpinBox
app=QApplication(['dashboard-demo-test'])
root=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('demo_fixture');pkg.__path__=[str(root)];sys.modules[pkg.__name__]=pkg
class ForbiddenCollection:
    def __getattr__(self,key):raise AssertionError("Demo accessed collection: "+key)
owner=ForbiddenCollection()
mw=QMainWindow();mw.col=owner;mw.pm=types.SimpleNamespace(night_mode=lambda:False)
mw.state='deckBrowser';calls=[];mw.deckBrowser=types.SimpleNamespace(refresh=lambda:calls.append('refresh'))
mw.addonManager=types.SimpleNamespace(addonFromModule=lambda _: root.name, addonsFolder=lambda: str(root.parent))
aqt.mw=mw
demo=importlib.import_module(pkg.__name__+'.dashboard_demo')
stats=importlib.import_module(pkg.__name__+'.statistics_widget')
facts=importlib.import_module(pkg.__name__+'.daily_widgets')
minimal=importlib.import_module(pkg.__name__+'.minimal_dashboard')
stats._statistics_cache['sentinel']=(1,{'real':True})
baseline=dict(stats._statistics_cache)
demo.start(owner,dict(demo.DEFAULTS,level=100))
values=demo.current(owner);manager=demo.DisplayGamification(values)
assert manager.get_rank_name()=='Anki<br>Admiral'
game=manager.render_widgets_html();assert 'Admiral' in game
data=demo.statistics(values);assert '<svg' in data['chart_html']
statistics=stats.render_statistics_widget_html(display_data=data)
fact=facts.generate_daily_widgets_html([],values['fact_theme'],show_study_plan=False,display_fact_index=0)
small=minimal.render_minimal_dashboard_sections(manager,None,None,statistics_override=data)
assert all(s for s in (game,statistics,fact,*small))
assert stats._statistics_cache==baseline
Path('/tmp/dashboard-demo-render.html').write_text('<style>body{font:14px Arial;background:#eee}</style>'+game+fact+statistics)
# Execute the actual dashboard hook with a real-manager sentinel. It must
# neither render nor consume achievement events on the real manager in demo.
import ast
tree=ast.parse((root/'__init__.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='render_all_deck_browser_widgets')
mw.gamification_manager=ForbiddenCollection()
scope=dict(__package__=pkg.__name__,mw=mw,DeckBrowser=object,DeckBrowserContent=object,
           addon_settings={'study_plan_widget_enabled':False,'deadline_bar_enabled':False},
           statistics_widget=stats,daily_widgets=facts,minimal_dashboard=minimal)
exec(compile(ast.Module(body=[fn],type_ignores=[]),'dashboard-hook','exec'),scope)
for compact in (False,True):
    scope['addon_settings']['minimal_dashboard_enabled']=compact
    content=types.SimpleNamespace(tree='<div>Real deck list</div>',stats='')
    scope['render_all_deck_browser_widgets'](None,content)
    assert 'Real deck list' in content.tree and '<svg' in content.stats
assert stats._statistics_cache==baseline
dialog=QDialog();panel=demo.build_panel(dialog)
dialog.resize(620,830)
from aqt.qt import QVBoxLayout
layout=QVBoxLayout(dialog);layout.addWidget(panel);dialog.show();app.processEvents()
dialog.grab().save('/tmp/dashboard-demo-console.png')
# Level and rank/XP controls update independently of live data.
spins=panel.findChildren(QSpinBox);spins[0].setValue(55)
buttons={b.text():b for b in panel.findChildren(QPushButton)}
buttons['Apply demo and view dashboard'].click()
assert demo.current(owner)['level']==55 and calls==['refresh']
buttons['End dashboard demo'].click()
assert demo.current(owner) is None and calls==['refresh','refresh']
assert stats._statistics_cache==baseline
print('PASS real renderers, automatic rank, compact dashboard, facts, controls, stop, zero collection access/cache writes')
