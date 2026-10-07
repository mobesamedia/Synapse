# Deck Overview customization

Open Settings → Deck Overview, or use the gear next to the deck title. Changes
use the existing Save/Cancel transaction and refresh the open overview on save.
Preferences are global add-on settings, not individual deck options.

## Appearance and content

- Classic (default): original progress bars, three statistic tiles, original
  smiley artwork and size, and original action button colors.
- Focus: compact donut chart of remaining scheduler counts, a small new/learning/due legend, and Start Study. Zero remaining cards has a neutral ring and an explicit message.
- Overview: Classic plus a 14-day line chart below the statistics. Zero days are included; an empty period has a zero line and an explicit message.
- A small settings gear is positioned inside the white box, top right.
- Brainstorm Cloud is a single on/off setting, used by Classic and Overview.
- Period selects the retention window: 7 days, 30 days, or all time. The help
  text distinguishes this from the smiley's 30 days and the graph's 14 days.
- The schema preview, spacing option and individual content toggles were removed.
  Previously saved content switches are ignored; layouts define the content.
- Turning off Custom Deck Dashboard disables and dims all subordinate web
  settings. The native fallback also disables its subordinate controls.
- Smiley thresholds include a short expandable explanation with examples.

## Metrics

The old smiley used average Ease Factor, which could remain low despite recent
successful studying. The new indicator uses actual review answers from the past
30 days (`revlog.type=1`, positive ease). Again is unsuccessful; Hard, Good and
Easy are successful. Default boundaries include 85% for green and 70% for orange;
below 70% is red. Both boundaries are editable; green must exceed orange.
Fewer than 20 eligible answers shows the original medium smiley dimmed and marked as not yet rated. It describes
recall, not effort or ability.

Retention includes learning and review answers for the chosen period. No answers
shows a dash. Today's counts come from Anki's scheduler for the selected deck,
including children and daily limits. Distribution describes active card queues,
not learning completion. Mature cards have intervals of at least 21 days and
still need reviews. History counts positive-ease answers by local Anki day.
All queries are read-only; scheduling and review history are never changed.

## Verification

- `tests/test_deck_overview.py`: periods, scope, thresholds, no-data behavior,
  validation, fixed layouts, title escaping.
- `tests/qt_deck_overview.py`: real temporary Anki collection and scheduler,
  recall calculation, native fallback controls.
- `tests/web_deck_overview.cjs`: actual rendered overview, all three layouts,
  light/dark at 400/1000 px, detail actions, Brainstorm modes, master-toggle disabling,
  threshold validation and save payload.

Browser verification does not replace a final check in the installed Anki UI.
No installed add-on copy or user collection is modified by these tests.

## Deck interaction polish

Progress labels share the left edge of the tiles. Tiles have a flat surface and a subtle gray border matched to the detail hint.
Start Study uses the active primary color with white text. Hover remains flat. The smiley tile is 86 × 86 px, with a centered settings
icon in its separate top-right control.

Space on the overview background starts studying. Inputs and focused controls
retain their own keyboard behavior, and repeated held-key events are ignored.
Clicking the smiley exposes three manual choices and Automatic suggestion.
Choices are stored by deck ID in collection config `synapsepro_deck_smileys`,
separate from scheduling data. Automatic removes that deck's override. Stale
commands from another deck are ignored; failed saves show a retry message.
The computed recall statistics remain unchanged by a manual choice.

Browser tests cover alignment, square sizing, Space and selection commands.
The Qt/Anki test verifies per-deck isolation and persistence after reopening a
temporary collection. Space should also be checked in the user's installed Anki.

## Optional dots in the main Deck Browser

Settings has a global `deck_overview_indicators_all` switch (default off). When
on, all eligible visible decks get a dot. When off, individual opt-ins from the
smiley picker apply, stored in `synapsepro_deck_indicator_visibility`. Switching
the global option does not erase individual preferences. The picker shows its
checkbox as enabled/checked by the global setting but prevents editing it until
the global option is turned off, with an explanation.

A 6 px dot sits before the settings gear inside its existing table cell. Automatic dots require at least 20 positive-ease review answers in the last 30 days.
Manual smileys bypass that threshold, but still require global or per-deck visibility. The automatic color uses the configured
recall boundaries; a manual choice overrides color only. Deck descendants count
toward parent statistics consistently with the overview, but do not inherit an
individual visibility preference. Review answers are grouped in one database
query per browser render, even with the global setting enabled.

The Qt test uses the real Anki renderer to verify position, global/individual
selection, eligibility, colors and per-deck persistence. Browser tests cover the
new charts, settings save payload, narrow layouts and light/dark appearance.

## Compact layout refinement

Focus now contains the deck title, total card count, donut/legend and study
button inside one 350 px maximum-width card, with 20 px horizontal padding.
Its title keeps the neutral text color. Classic and Overview titles use the
active primary color above the card. Overview keeps its width but reduces
vertical padding, section gaps and the chart to 76 px height.

Browser checks verify Start Study is visible without scrolling at 1000×650 and
400×760 for all layouts in light and dark mode (normal view, details closed).

The gear anchor remains a direct child of its original cell. Inline flex on the
anchor and a nowrap cell prevent third-party block/flex styles from moving the
dot onto another line. The dot remains visible when Anki hides the gear until
hover. Repeated rendering removes old indicator markup before decorating again.
The smiley picker retains checkbox changes when reopened and reports the actual
recent review count when the 20-answer eligibility rule hides the dot.

Indicator layout reserves the same 6 px slot plus 9 px gap in every deck row
whenever dots are present. Rows without a dot get an invisible, accessibility-hidden
placeholder. Gear anchors use a fixed 20 × 20 px centered area; the 16 × 16 px
gear image has no inherited top padding. Browser geometry checks confirm matching
gear x coordinates and vertically centered dots/gears across mixed rows.
