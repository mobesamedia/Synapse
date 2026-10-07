# SynapsePro localization

UI languages: English (source), German, Spanish, Korean, Portuguese, French,
Vietnamese, Simplified Chinese, Hindi and Polish.

## Runtime catalogs

- `locales.py`: native UI translations and per-language lookup.
- `web_translations.py`: shared HTML UI sources.
- `translation_catalog.json`: translations for newer UI additions and the Polish
  extension of the existing native/HTML catalogs.
- `workspace_translations.json`: Notebook, MindMap and FreeMap vocabulary.
- `web_i18n.py`: exact sources sent to the Settings and AI HTML surfaces.
- Notebook/Todo/PDF and MindMap build their keyed payloads in their Python sidebar modules.

Lookup falls through **per language**, so a German-only entry cannot hide a French
translation from another catalog. Workspace strings are available before a sidebar
has been opened. New JSON resources must be included when packaging the add-on.

Only UI text is localized. User notes, card contents, deck/document names, saved
maps, URLs, provider/model names, commands, persistent identifiers and file formats
are not translated. The icon search vocabulary remains English, as designed.
Technical diagnostic reports and event identifiers use English for support exports;
the diagnostic controls and status messages follow the selected UI language.
The onboarding flow has not been redesigned. Polish is available in its language
selector, all seven screens, terms/privacy, theme names and error UI.
Polish Anki locales (`pl`, `pl_PL`, `pl-PL`) are also detected in Auto mode.

## Adding text

1. Wrap native text with `_('English source')` and add all nine translations.
2. Preserve formatting fields, cloze delimiters, markup, numbers and units.
3. Register new HTML sources in the correct payload, not just in a dictionary.
4. Store machine values with combo-box item data; never persist translated labels.
5. Use `translate_standard_buttons()` for add-on-owned Qt button boxes.
6. Rebuild a surface when changing its language; do not translate user-created content.

## Checks

- `python3 scripts/audit_translations.py`: 1,961 catalog entries, all nine target languages,
  no missing entries or formatting-placeholder mismatches at the end of this pass.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: includes catalog coverage,
  fallback precedence and workspace availability regressions.
- `python3 tests/translation_payloads.py`, then
  `node tests/web_translation_coverage.cjs`: real Python payloads in all ten
  languages on AI, Settings/About, Notebook, Todo and PDF/Cloze HTML surfaces.
- `tests/qt_translation_dates.py` in Anki's Python runtime: calendar, timeline,
  selected-language buttons and preserved user subject names in all ten languages.
- `tests/qt_dashboard_demo.py` and `tests/qt_diagnostics.py`: controls, stable
  internal values, recording and export behavior with isolated test data.

Browser tests require Playwright; Qt tests require Anki's Python environment.
Automated coverage checks cannot guarantee every translation's linguistic quality
or every possible combination of display size, font availability and user content.

- `tests/web_polish_onboarding.cjs`: full Polish onboarding in light/dark at the
  minimum window size, stable saved keys, language selectors and AI response language.
