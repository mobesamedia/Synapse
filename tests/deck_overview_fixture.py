"""Render the actual Overview hook without loading a user profile."""
import ast,importlib,json,sys,tempfile,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('overview_render_fixture');pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg
class Overview:pass
mw=types.SimpleNamespace(pm=types.SimpleNamespace(night_mode=lambda:False),col=types.SimpleNamespace(decks=types.SimpleNamespace(current=lambda:{'id':1,'name':'Medizin::Biochemie'})))
for name,attributes in {'aqt':{'mw':mw},'aqt.gui_hooks':{'webview_will_set_content':[],'webview_did_receive_js_message':[]},'aqt.overview':{'Overview':Overview},'aqt.utils':{'tooltip':lambda *a,**k:None}}.items():
 mod=types.ModuleType(name);mod.__dict__.update(attributes);sys.modules[name]=mod
colors={}
for n in ast.parse((ROOT/'theme.py').read_text()).body:
 if isinstance(n,ast.AnnAssign) and getattr(n.target,'id',None) in ('LIGHT','DARK'):colors[n.target.id]=ast.literal_eval(n.value)
theme=types.ModuleType(pkg.__name__+'.theme');theme.palette=lambda dark:colors['DARK' if dark else 'LIGHT'];theme.FONT_FAMILY='sans-serif';sys.modules[theme.__name__]=theme
locales=importlib.import_module(pkg.__name__+'.locales');locales.USER_LANG='de'
module=importlib.import_module(pkg.__name__+'.deck_overview');module.get_media_url=lambda filename:(ROOT/'media'/filename).as_uri()
options=module.overview_options
stats=dict(total=1234,hard=8,learned=240,review_p=65,learn_p=10,new_p=25,ret_p=91,indicator='green',indicator_p=90,indicator_reviews=100,diff_img='easy.png',today=(12,8,40),history=[])
out=Path(tempfile.mkdtemp(prefix='deck-overview-qa-'));files=[]
for layout in ('classic','focus','overview'):
 for dark in (False,True):
  cfg=options.normalize({'deck_overview_layout':layout});module.update_settings(cfg);mw.pm.night_mode=lambda:dark
  data=dict(stats);data['history']=[('2026-09-'+str(i+1).zfill(2),n) for i,n in enumerate([12,50,30,80,40,0,60,35,20,70,30,10,60,50])] if layout=='overview' else []
  module.get_stats=lambda did:data
  web=types.SimpleNamespace(body='');module.on_overview_render(web,Overview())
  assert 'custom-dashboard' in web.body
  p=out/(layout+('-dark' if dark else '-light')+'.html');p.write_text('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:'+colors['DARK' if dark else 'LIGHT']['bg']+'}</style><script>window.pycmd=x=>console.log("COMMAND:"+x)</script>'+web.body);files.append(str(p))
cases=[]
for mode in ('menu','hidden'):
 cfg=options.normalize({'deck_overview_brainstorm':mode,'deck_overview_show_indicator':False,'deck_overview_show_retention':False})
 module.update_settings(cfg);web=types.SimpleNamespace(body='');module.on_overview_render(web,Overview())
 p=out/(mode+'.html');p.write_text('<!doctype html><script>window.pycmd=x=>console.log("COMMAND:"+x)</script>'+web.body);cases.append(str(p))
print(json.dumps({'cases':cases,'files':files,'settings':options.payload({},locales._),'output':str(out)}))
