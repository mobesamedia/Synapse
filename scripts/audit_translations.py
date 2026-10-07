"""Offline UI catalog audit. Run: python3 scripts/audit_translations.py."""
import ast
import json
import sys
from collections import Counter
from pathlib import Path
from string import Formatter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import locales
LANGUAGES=('de','es','ko','pt','fr','vi','zh','hi','pl')

def catalogs():
    merged={}
    # Per-language fallback order used by locales._().
    for source in (locales.SUPPLEMENTAL_TRANSLATIONS,locales.WEB_TRANSLATIONS,locales.TRANSLATIONS):
        for key,values in source.items():
            merged.setdefault(key,{}).update({k:v for k,v in values.items() if v})
    for key,values in json.loads((ROOT/'workspace_translations.json').read_text()).items():
        merged.setdefault(key,{}).update(values)
    return merged

def sources():
    out=set(catalogs())
    for file in ROOT.glob('*.py'):
        if file.name in ('locales.py','web_translations.py','onboarding_terms.py'):continue
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('_','tr') and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
                out.add(node.args[0].value)
    for node in ast.walk(ast.parse((ROOT/'daily_widgets.py').read_text())):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == 'text' and isinstance(value, ast.Constant) and isinstance(value.value, str):
                    out.add(value.value)
    return out

def fields(text):
    try:return Counter((field,spec,conversion) for _,field,spec,conversion in Formatter().parse(text) if field is not None)
    except ValueError:return None

def audit():
    catalog=catalogs();missing=[];broken=[]
    for source in sorted(sources()):
        for lang in LANGUAGES:
            value=catalog.get(source,{}).get(lang)
            if not value:missing.append((source,lang));continue
            original=fields(source)
            if original and original!=fields(value):broken.append((source,lang,value))
    return catalog,missing,broken

if __name__=='__main__':
    catalog,missing,broken=audit()
    print(f'{len(catalog)} catalog entries; {len(missing)} missing translations; {len(broken)} placeholder mismatches')
    for issue in missing+broken:print(issue)
    sys.exit(bool(missing or broken))
