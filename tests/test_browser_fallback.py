import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('browser_fallback', Path(__file__).resolve().parents[1]/'browser_fallback.py')
browser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)


class BrowserFallbackTests(unittest.TestCase):
    def test_only_google_failures_offer_recovery(self):
        self.assertFalse(browser.needs_search_help('https://www.synapse-pro.de/browser', False))
        self.assertFalse(browser.needs_search_help('https://duckduckgo.com/', False))
        self.assertFalse(browser.needs_search_help('https://www.google.com/search?q=captcha'))
        self.assertTrue(browser.needs_search_help('https://www.google.de/sorry/index'))
        self.assertTrue(browser.needs_search_help('https://www.google.co.uk/search?q=test', False))
        self.assertTrue(browser.needs_search_help('https://www.google.com/search?q=test', blocked=True))
        self.assertFalse(browser.needs_search_help('https://google.com.example.org/sorry/', False))
        self.assertFalse(browser.is_google_url('https://[broken'))

    def test_explicit_switch_preserves_query_only(self):
        self.assertEqual(browser.duckduckgo_url('https://www.google.com/search?q=Anki+%26+Lernen&token=private'), 'https://duckduckgo.com/?q=Anki+%26+Lernen')
        self.assertEqual(browser.duckduckgo_url('https://www.google.com/sorry/?continue=https%3A%2F%2Fwww.google.com%2Fsearch%3Fq%3DAnki'), 'https://duckduckgo.com/?q=Anki')
        self.assertEqual(browser.duckduckgo_url('https://www.google.com/sorry/?continue=https%3A%2F%2Fexample.org%2F%3Fq%3Dprivate'), 'https://duckduckgo.com/')

