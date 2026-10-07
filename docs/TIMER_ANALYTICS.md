# Timer

The preferred Qt WebEngine dialog has Settings, Statistics and Analytics tabs.
The segmented control follows the Music Player. Content requests its natural
height; the host preserves the width and limits height to the available screen
(up to 760 logical pixels). Large lists scroll inside the dialog. Keyboard tab
navigation supports arrows and Home/End. Unsaved settings survive tab changes;
Save/Cancel remain available when changes are pending, otherwise read-only tabs
show Close. The native fallback also provides all three tabs.

Analytics queries the existing Anki review log once, on the first visit to the
Analytics tab in each dialog. It runs in a collection-bound QueryOp worker, with
loading, empty and retry states. There are no study hooks, background timers,
periodic queries or modifications to review history. Only the expanded deck paths
are persisted in collection config (`synapsepro_timer_analytics_expanded`).

The range includes today and the previous 29 Anki study days, using the scheduler
cutoff, through the current time. Learning, review, relearning and filtered review
entries with positive answer time/rating are included; manual scheduling entries
are excluded. Existing capped answer times are summed in milliseconds. Cards in
filtered decks use their original deck ID. Otherwise grouping uses current deck
membership, and deleted cards or unknown decks cannot be attributed and are
excluded. This is explained in the UI.

Parent rows sum all descendants, with sibling rows sorted by duration descending.
The overall total sums only root rows, so expanding a parent never doubles time.
Deck names are rendered as text. Empty decks are omitted. Durations below one
minute show `<1 min`; other times display whole minutes.

Checks:
- `python3 -m unittest discover -s tests -p 'test_timer_analytics.py'`
- `node tests/web_timer.cjs` (Playwright; optional `SYNAPSE_TEST_CHROME`)
- `tests/qt_timer.py` under Anki's Python/runtime: actual WebEngine bridge,
  QueryOp, temporary collection, resizing, expansion persistence, save/cancel,
  and native fallback. It never opens a real user collection.
