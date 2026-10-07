"""Regression checks with synthetic data; does not import Anki or read profiles."""
import ast, pathlib, tempfile, json, os, typing, types, unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
def functions(file,names,ns):
 tree=ast.parse((ROOT/file).read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 assert len(nodes)==len(names)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),file,'exec'),ns)
 return ns
class Col:
 def __init__(self,data):self.data=data.copy();self.removed=[]
 def get_config(self,k,default=None):return self.data.get(k,default)
 def remove_config(self,k):self.removed.append(k);self.data.pop(k,None)
class Checks(unittest.TestCase):
 def test_sidebar_popup_preferences_save_shared_keys(self):
  tree=ast.parse((ROOT/'sidebar.py').read_text())
  node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_set_popups_enabled')
  ns={'ADDON_NAME':'test'}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'sidebar.py','exec'),ns)
  settings={'gamification_popup_rank':False,'unrelated':'keep'};saved=[];refresh=[]
  subject=types.SimpleNamespace(_addon_settings=lambda:(settings,lambda:saved.append(settings.copy())),update_display=lambda:refresh.append(True))
  ns['_set_popups_enabled'](subject,True,'level')
  self.assertTrue(settings['gamification_popup_level'])
  ns['_set_popups_enabled'](subject,False)
  self.assertFalse(settings['gamification_popups_enabled'])
  self.assertFalse(settings['gamification_popup_rank'])
  self.assertTrue(settings['gamification_popup_level'])
  self.assertEqual(settings['unrelated'],'keep')
  ns['_set_popups_enabled'](subject,True,'unrelated')
  self.assertEqual(len(saved),2);self.assertEqual(len(refresh),2)
 def test_website_migration(self):
  for failure in (False,True):
   with self.subTest(failure=failure),tempfile.TemporaryDirectory() as d:
    path=d+'/website.json';col=Col({'sites':'[{"name":"Example","url":"https://example.org"}]','url':'https://example.org'})
    ns=functions('website_sidebar.py',{'_load_website_state','_save_website_state'},{'os':os,'json':json,'Dict':typing.Dict,'_website_state_path':lambda:path,'mw':types.SimpleNamespace(col=col),'constants':types.SimpleNamespace(CONFIG_KEY_CUSTOM_SITES='sites',CONFIG_KEY_LAST_OPENED_URL='url')})
    with patch.object(os,'replace',side_effect=OSError('synthetic write failure')) if failure else patch.object(os,'replace',wraps=os.replace):
     result=ns['_load_website_state']()
    self.assertEqual(result['last_url'],'https://example.org')
    if failure:
     self.assertEqual(col.removed,[]);self.assertFalse(os.path.exists(path))
     # Subsequent retry must migrate the original data.
     ns['_load_website_state']();self.assertEqual(set(col.removed),{'sites','url'})
    else:self.assertEqual(set(col.removed),{'sites','url'})
    self.assertEqual(json.loads(pathlib.Path(path).read_text()),result)
 def test_secret_migration(self):
  for failure in (False,True):
   with self.subTest(failure=failure),tempfile.TemporaryDirectory() as d:
    path=d+'/keys.json';col=Col({'key':'synthetic-test-value'})
    ns=functions('ai_assistant.py',{'_save_secret_map','_secret_get'},{'os':os,'json':json,'Dict':typing.Dict,'Any':typing.Any,'_secret_path':lambda:path,'_load_secret_map':lambda:{},'_anki_ok':True,'mw':types.SimpleNamespace(col=col)})
    with patch.object(os,'replace',side_effect=OSError('synthetic write failure')) if failure else patch.object(os,'replace',wraps=os.replace):
     self.assertEqual(ns['_secret_get']('key'),'synthetic-test-value')
    self.assertEqual(col.removed,[] if failure else ['key'])
 def test_readback_failure_keeps_legacy(self):
  col=Col({'key':'synthetic-test-value'})
  ns=functions('ai_assistant.py',{'_secret_get'},{'Any':typing.Any,'_load_secret_map':lambda:{},'_anki_ok':True,'mw':types.SimpleNamespace(col=col),'_save_secret_map':lambda x:False})
  self.assertEqual(ns['_secret_get']('key'),'synthetic-test-value');self.assertEqual(col.removed,[])
 def test_website_show_does_not_navigate_existing_page(self):
  class Dock:
   visible=False
   def isVisible(self):return self.visible
   def show(self):self.visible=True
   def hide(self):self.visible=False
   def raise_(self):pass
  for url in ('about:blank','https://example.org/search?q=test'):
   with self.subTest(url=url):
    dock=Dock();loads=[]
    view=types.SimpleNamespace(url=lambda:types.SimpleNamespace(toString=lambda:url))
    ns=functions('website_sidebar.py',{'toggle_website_dock'},{'_qt_available':True,'sidebar_dock':dock,'sidebar_webview':view,'QDockWidget':Dock,'rebuild_custom_buttons_ui':lambda:None,'load_last_opened_url':lambda:'https://example.org','load_url_in_webview':lambda v,u:loads.append(u)})
    ns['BROWSER_HOME_URL']='https://www.synapse-pro.de/browser'
    ns['toggle_website_dock']();self.assertEqual(loads,['https://www.synapse-pro.de/browser'] if url=='about:blank' else [])
    ns['toggle_website_dock']();self.assertFalse(dock.visible)
 def test_search_deferred_profile_switch(self):
  callbacks=[];calls=[];col=object();mw=types.SimpleNamespace(col=col)
  ns=functions('website_sidebar.py',{'search_in_sidebar'},{'mw':mw,'QTimer':types.SimpleNamespace(singleShot=lambda delay,cb:callbacks.append(cb)),'_execute_search_in_sidebar':calls.append})
  ns['search_in_sidebar']('test');self.assertEqual(calls,[])
  mw.col=object();callbacks.pop()();self.assertEqual(calls,[])
  ns['search_in_sidebar']('test');callbacks.pop()();self.assertEqual(calls,['test'])
 def test_external_search_encoding(self):
  import urllib.parse
  urls=[];callbacks=[]
  ns=functions('website_sidebar.py',{'search_in_browser'},{'urllib':__import__('urllib'),'QTimer':types.SimpleNamespace(singleShot=lambda delay,cb:callbacks.append(cb)),'_open_browser_url':urls.append})
  ns['search_in_browser']('Herz & Gefäße + 2');self.assertEqual(urls,[]);callbacks.pop()()
  self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(urls[0]).query),{'q':['Herz & Gefäße + 2']})
 def test_captcha_browser_destination(self):
  import urllib.parse
  for url,expected in [
   ('https://www.google.com/sorry/index?continue=https%3A%2F%2Fwww.google.com%2Fsearch%3Fq%3Dtest','https://www.google.com/search?q=test'),
   ('https://www.google.com/sorry/index?continue=javascript%3Aalert(1)','https://www.google.com/sorry/index?continue=javascript%3Aalert(1)'),
   ('https://example.org','https://example.org')]:
   with self.subTest(url=url):
    urls=[];ns=functions('website_sidebar.py',{'open_current_in_browser'},{'urllib':__import__('urllib'),'sidebar_webview':types.SimpleNamespace(url=lambda:types.SimpleNamespace(toString=lambda:url)),'_open_browser_url':urls.append})
    ns['open_current_in_browser']();self.assertEqual(urls,[expected])
if __name__=='__main__':unittest.main()
