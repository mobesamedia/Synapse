"""Icon geometry is portable data, never arbitrary SVG markup."""
import copy,json,tempfile,unittest
from pathlib import Path
from workspace_icons import valid_definition,validate_document
import roadmap_store
from workspace_assets import export_bundle,import_bundle
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'web_roadmap/icons/catalog.js').read_text()
CATALOG=json.loads(text[text.index('=')+1:].rstrip(';\n'))

class Icons(unittest.TestCase):
 def test_all_bundled_icons_validate(self):
  self.assertEqual(len(CATALOG['icons']),208)
  for icon in CATALOG['icons']:
   self.assertTrue(valid_definition({'name':icon['name'],'nodes':icon['nodes']}),icon['id'])
  self.assertIn('ISC License',CATALOG['license'])
 def test_unsafe_svg_and_budgets_rejected(self):
  cases=[{'name':'bad','nodes':[['script',{}]]},
   {'name':'bad','nodes':[['path',{'d':'M0 0','onclick':'alert(1)'}]]},
   {'name':'bad','nodes':[['image',{'href':'https://example.org'}]]},
   {'name':'bad','nodes':[['path',{'d':'M0 0','fill':'url(https://example.org)'}]]},
   {'name':'bad','nodes':[['rect',{'width':'Infinity'}]]},
   {'name':'bad','nodes':[['path',{'d':'M0 0'}]]*65}]
  for value in cases:
   self.assertFalse(valid_definition(value))
   with self.assertRaises(ValueError):validate_document({'objects':[],'iconAssets':{'icon':value}})
  with self.assertRaises(ValueError):validate_document({'objects':[{'kind':'icon','icon':'missing'}]})
 def test_collection_save_and_export_import_without_library_lookup(self):
  icon=CATALOG['icons'][0]
  document={'id':'map','name':'Portable icons','view':{'x':0,'y':0,'scale':1},'iconAssets':{icon['id']:{'name':icon['name'],'nodes':icon['nodes']}},'iconLicense':CATALOG['license'],'objects':[{'id':'i','kind':'icon','icon':icon['id'],'x':10,'y':20,'w':96,'h':96,'rotation':12,'stroke':'#ff3355'}]}
  data={'version':1,'active':'map','maps':[document]}
  with tempfile.TemporaryDirectory() as folder:
   path=str(Path(folder)/'maps.sqlite3');roadmap_store.save(path,data)
   self.assertEqual(roadmap_store.load(path),data)
   bundle=json.loads(json.dumps(export_bundle(document,folder)))
   imported=import_bundle(bundle,folder)
   validate_document(imported)
   self.assertEqual(imported['iconAssets'],document['iconAssets'])
   self.assertEqual(imported['objects'][0]['stroke'],'#ff3355')
   bad=copy.deepcopy(data);bad['maps'][0]['iconAssets'][icon['id']]['nodes']=[['script',{}]]
   with self.assertRaises(ValueError):roadmap_store.save(path,bad)
   self.assertEqual(roadmap_store.load(path),data)
