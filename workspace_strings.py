"""Canonical workspace strings, using the same language as the rest of SynapsePro."""
import json
from pathlib import Path
from .locales import _, TRANSLATIONS, WORKSPACE_TRANSLATIONS

CATALOG = WORKSPACE_TRANSLATIONS
for key, languages in CATALOG.items():
    TRANSLATIONS.setdefault(key, {}).update(languages)

def translations():
    return {key: _(key) for key in CATALOG}
