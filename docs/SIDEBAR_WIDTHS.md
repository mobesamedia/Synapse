# Sidebar widths

Widths are remembered separately for each main sidebar group during the current Anki/profile session. Closing Anki or destroying a profile's docks resets them. No config or user-content files are written.

`sidebar_widths.py` attaches a dock-owned Qt event filter and a cancellable timer. It restores the explicit shared starting width of 400 logical pixels (`DEFAULT_SIDEBAR_WIDTH`), independent of content size hints, until the user drags the main-window dock separator. Only separator resizing between a main-window mouse press and release records a preference. Resizing the main window, opening another dock, programmatic resizes, and floating/embedded/fullscreen geometry do not replace it. Opening a dock restores its preference within the available main-window space; a temporarily clamped width is not saved over the preference.

Integrated features: Gamification, AI Assistant, Web Sidebar, Mindmap, Roadmap, Notebook, To-do, PDF. The launcher keeps its existing fixed layout. Mindmap/Roadmap share one width; Notebook/To-do/PDF share another. Switching internal tabs does not resize the dock. Tool selection follows the existing successful save/switch path; no save barriers or WebView lifetime handling are changed.

Qt can adjust actual widths to accommodate minimum sizes or other simultaneously visible docks in the same area. The per-feature preference remains unchanged.

Verification:
- `tests/qt_sidebar_widths.py`: real Qt dock-separator mouse events, 400 px starting size with different content size hints, internal tab switching without resizing, independent docks, window shrink/grow, main-window resize during held mouse press, automatic neighboring-dock layout changes, embedded/floating return, left-side docking, session reset and pending deletion.
- `tests/qt_roadmap_lifecycle.py`: existing real WebEngine navigation, save, hide/show, import/export and cleanup checks with a temporary profile.
- Python regression suite: 128 tests.
