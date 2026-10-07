"""Build browser fixtures from the real Python UI translation builders."""
import ast,importlib,json,sys,types
from pathlib import Path
root=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('translation_fixture');pkg.__path__=[str(root)];sys.modules[pkg.__name__]=pkg
loc=importlib.import_module(pkg.__name__+'.locales');web=importlib.import_module(pkg.__name__+'.web_i18n')
node=next(n for n in ast.parse((root/'notebook_sidebar.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_build_i18n_script')
env={'_':loc._,'_json_for_script':json.dumps}
exec(compile(ast.Module(body=[node],type_ignores=[]),'notebook-translations','exec'),env)
out={}
for lang in ['en','de','es','ko','pt','fr','vi','zh','hi','pl']:
 loc.USER_LANG=lang
 data={'ai':web.translations('ai'),'settings':web.translations('settings')}
 for tool in ['notebook','todo','pdf']:
  script=env['_build_i18n_script'](tool);data[tool]=json.loads(script.split('window.__SYNAPSE_I18N__=')[1].split(';</script>')[0])
 out[lang]=data
Path('/tmp/synapse-translation-payloads.json').write_text(json.dumps(out,ensure_ascii=False))
print('Built actual UI payloads for 10 languages')

# Onboarding has its own dictionary because selection precedes profile saving.
TERMS_TRANSLATIONS = importlib.import_module(pkg.__name__+'.onboarding_terms').TERMS_TRANSLATIONS
theme_sources = ('Ocean', 'Horizon', 'Forest', 'Dusty', 'Deluge', 'Orchid')
Path('/tmp/synapse-onboarding-payload.json').write_text(json.dumps({
 'terms': TERMS_TRANSLATIONS,
 'themes': {lang: [loc.translate_for_language(t, lang) for t in theme_sources] for lang in out},
 'errors': {lang: {t: loc.translate_for_language(t, lang) for t in ('Copy error', 'Show details')} for lang in out},
}, ensure_ascii=False))
