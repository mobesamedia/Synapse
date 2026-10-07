# Dashboard demo

Developer console → Dashboard Demo → Apply demo and view dashboard.
Reopen the console and choose End dashboard demo to restore the normal display.
Closing the console alone keeps the demo running. Profile close/switch and application restart clear it.

Controls: level (1–100, rank derived from the existing rank thresholds), remaining XP (bounded by that level's XP requirement), streak, existing challenge and progress/claimed state, category and specific daily fact, three consistency patterns, efficiency, accuracy, retention and new-card percentage.

The demo temporarily displays the relevant widgets even if their visibility settings are off; it does not save those settings. The selected standard/minimal dashboard layout remains in use. Study-plan, deadline and deck list remain real. Studying still records real reviews normally; the demo only changes dashboard presentation.

Safety boundaries:
- State belongs to one collection object, lives only in module memory, and is returned by copy.
- DisplayGamification is an independent read-only adapter. No live manager is replaced or modified, and no GamificationManager constructor is invoked.
- Synthetic statistics are explicit renderer arguments, never stored in the real statistics cache. Chart counts bypass database lookup.
- Fact selection is an explicit renderer argument; it does not change the daily offset or saved category.
- Demo rendering does not consume real celebration events.
- No collection/configuration write API, scheduler operation, file persistence or network request is part of the demo implementation.

Tests: test_dashboard_demo.py covers state isolation and reset, bounds and curve presets. qt_dashboard_demo.py uses the actual renderers and dashboard hook with a collection that rejects all data access, verifies unchanged statistics cache, both layouts and the apply/end controls. qt_diagnostics.py protects existing lazy preview navigation.
