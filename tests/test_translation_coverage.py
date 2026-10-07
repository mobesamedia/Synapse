import importlib.util
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('translation_audit',ROOT/'scripts/audit_translations.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class TranslationCoverageTests(unittest.TestCase):
    def test_all_catalogs_and_native_literals_have_all_languages_and_placeholders(self):
        _,missing,broken=audit.audit()
        self.assertEqual(missing,[])
        self.assertEqual(broken,[])

    def test_partial_catalog_does_not_hide_other_languages(self):
        loc=audit.locales;old=loc.USER_LANG
        try:
            for lang in audit.LANGUAGES:
                loc.USER_LANG=lang
                self.assertNotEqual(loc._('Choose which celebrations appear on the dashboard. Changes are saved immediately.'),'Choose which celebrations appear on the dashboard. Changes are saved immediately.')
            loc.TRANSLATIONS['__test_partial']={'de':'Deutsch'}
            loc.WEB_TRANSLATIONS['__test_partial']={'fr':'Français'}
            loc.USER_LANG='fr';self.assertEqual(loc._('__test_partial'),'Français')
        finally:
            loc.TRANSLATIONS.pop('__test_partial',None);loc.WEB_TRANSLATIONS.pop('__test_partial',None);loc.USER_LANG=old

    def test_workspace_strings_available_before_loading_any_sidebar(self):
        loc=audit.locales;old=loc.USER_LANG
        try:
            for lang in audit.LANGUAGES:
                loc.USER_LANG=lang
                for source,translations in loc.WORKSPACE_TRANSLATIONS.items():
                    self.assertNotEqual(loc._(source),'',source)
                    self.assertTrue(translations.get(lang),(source,lang))
        finally:loc.USER_LANG=old
