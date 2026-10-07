# Gamification settings

The hero opens Settings and How it works as sidebar-local HTML dialogs using the Friends sheet styling. Celebration controls retain their existing bridge commands and persistence. Dialogs support keyboard focus, Escape and focus return.

`GamificationManager.data.streak_rules` stores `reviews` (1–10000), `cards` (1–10000) and `allowCards` (boolean) in the existing collection config and profile JSON backup. Defaults remain one review per day, with card creation disabled. A qualifying day meets the review minimum OR, if enabled, the creation minimum. Real reviews have `ease > 0`; card counts use IDs/creation timestamps of existing cards (including imported cards). Deleted cards no longer qualify. Dates use historical local time followed by Anki's rollover offset. History is loaded in bounded 370-day windows.

Changes recalculate the current streak retroactively, without removing XP or earned achievements. Achievement badges retain their own review-based criteria. Existing daily XP timing is unchanged. Collection card-change hooks invalidate and refresh the sidebar's streak; day changes are checked on the next refresh. Settings are translated into German, with English fallback for other languages.

Verification:
- `python3 -m unittest discover -s tests -p 'test_*.py'`: 128 tests pass.
- `tests/web_gamification_settings.cjs`: Chrome, 300/360/900 px, light/dark, dialogs, focus, Escape, bridge messages, validation and celebration controls.
- `tests/web_achievements.cjs`: existing achievements and preview regression coverage, adapted to open the Settings dialog.
- `tests/qt_gamification_settings.py`: real Qt WebEngine console bridge, actual manager, temporary Anki collection, JSON backup and reload. No installed add-on or user collection is changed.
