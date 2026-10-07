"""Build the offline icon catalog from an official, pinned Lucide source archive.
Usage: python3 scripts/build_map_icons.py /path/to/lucide-<commit>.tar.gz
The archive is read as data only; no archive paths are extracted or executed.
"""
import json,sys,tarfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from workspace_icons import valid_definition
folder=ROOT/'web_roadmap'/'icons'
selection=json.loads((folder/'selection.json').read_text())
with tarfile.open(sys.argv[1]) as tar:
 root=tar.getnames()[0]
 def read(name):return tar.extractfile(root+'/'+name).read().decode('utf-8')
 license_text=read('LICENSE')
 records=[]
 for name,config in selection.items():
  svg=ET.fromstring(read('icons/'+name+'.svg'))
  assert svg.attrib.get('viewBox')=='0 0 24 24'
  definition={'name':config.get('name',name.replace('-',' ').title()),'nodes':[[child.tag.split('}')[-1],dict(child.attrib)] for child in svg]}
  assert valid_definition(definition),name
  metadata=json.loads(read('icons/'+name+'.json'))
  records.append({'id':'lucide-'+name,'name':definition['name'],'nodes':definition['nodes'],
      'categories':config['categories'],'tags':sorted(set(metadata.get('tags',[])+config['keywords']))})
 revision=root.removeprefix('lucide-')
 result={'source':'https://github.com/lucide-icons/lucide','revision':revision,'license':license_text,'icons':records}
 (folder/'catalog.js').write_text('/* Lucide SVG geometry, locally bundled. See LICENSE.txt and SOURCE.md. */\nwindow.FREE_MAP_ICON_CATALOG='+json.dumps(result,ensure_ascii=False,separators=(',',':'))+';\n')
 (folder/'LICENSE.txt').write_text(license_text)
 (folder/'SOURCE.md').write_text(f'# Local FreeMap icons\n\nSource: https://github.com/lucide-icons/lucide/tree/{revision}\n\n{len(records)} curated SVG icons. English category/tag metadata is supplemented\nby SynapsePro’s selection.json. No network requests at runtime.\n\nBuild: `python3 scripts/build_map_icons.py lucide-{revision}.tar.gz`\n\nSVG nodes are stored compactly in catalog.js and rendered as native SVG.\nOriginal ISC/MIT notices are in LICENSE.txt and in exported maps using icons.\n')
 print(len(records),'icons;', (folder/'catalog.js').stat().st_size,'catalog bytes')
