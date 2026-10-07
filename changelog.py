# -*- coding: utf-8 -*-
"""English changelog data rendered in the Settings dialog."""

CHANGELOG = [
    {
        "version": "1.6.0",
        "date": "October 2026",
        "items": [
            {
                "tag": "Highlight",
                "text": "FreeMap introduces a flexible canvas for diagrams, learning paths, and visual notes, with shapes, formatted text, images, icons, and customizable connections."
            },
            {
                "tag": "Highlight",
                "text": "The Custom Deck Overview now offers three layouts: Classic, a compact Focus layout with a donut chart, and Overview with a study-history graph."
            },
            {
                "tag": "Highlight",
                "text": "Timer Analytics shows recorded study time by deck over the past 30 days, with expandable subdecks and automatic sorting by study duration."
            },
            {
                "tag": "Highlight",
                "text": "The AI Assistant now displays mathematical formulas and includes a Copy button for answers."
            },
            {
                "tag": "New",
                "text": "The AI Assistant now supports DeepSeek API, including streamed answers and reasoning."
            },
            {
                "tag": "Highlight",
                "text": "The PDF Card Creator now supports Basic, reversed, and Cloze cards."
            },
            {
                "tag": "Highlight",
                "text": "Dark Mode has been unified across the main features, Settings, and pop-up menus for a more consistent appearance."
            },
            {
                "tag": "Highlight",
                "text": "Added Polish as the tenth interface language, including Settings and onboarding."
            },
            {
                "tag": "New",
                "text": "Added a local icon library to FreeMap, with categories, English search keywords, customizable colors, and icons included in exported maps."
            },
            {
                "tag": "New",
                "text": "Added a FreeMap tutorial that demonstrates the canvas and its editing tools."
            },
            {
                "tag": "New",
                "text": "MindMap and FreeMap objects can now link directly to Anki notes and cards."
            },
            {
                "tag": "New",
                "text": "Added configurable streak requirements, including a minimum number of reviews and optional qualification through card creation."
            },
            {
                "tag": "New",
                "text": "Added achievement badges for study milestones, with multiple progression tiers."
            },
            {
                "tag": "New",
                "text": "The Deck Overview recall indicator now supports adjustable thresholds and a manually selected smiley for each deck."
            },
            {
                "tag": "New",
                "text": "Optional colored indicators in the Deck Browser show a deck’s automatic or manually selected recall status. Indicators can be enabled globally or for individual decks."
            },
            {
                "tag": "New",
                "text": "The Deck Overview title can now use either the primary theme color or a custom color."
            },
            {
                "tag": "New",
                "text": "Custom Backgrounds can optionally appear behind learning cards, with separate intensity and blur settings."
            },
            {
                "tag": "New",
                "text": "Dashboard surfaces now support adjustable opacity and an optional Glass Effect, with a live preview."
            },
            {
                "tag": "New",
                "text": "Added a compact Deck Browser width option for users who prefer Anki’s narrower layout."
            },
            {
                "tag": "New",
                "text": "The Daily Fact widget can now display a random fact from all available categories."
            },
            {
                "tag": "New",
                "text": "The Dashboard can now show open tasks instead of daily facts."
            },
            {
                "tag": "New",
                "text": "Added recurring tasks and an optional cleanup setting for completed tasks."
            },
            {
                "tag": "New",
                "text": "The AI Assistant now includes layout settings for line spacing, message spacing, and text size."
            },
            {
                "tag": "New",
                "text": "Added optional current-card context for AI questions, with explicit controls over whether card content is included."
            },
            {
                "tag": "New",
                "text": "The developer console now includes a temporary Dashboard Demo and optional local diagnostics."
            },
            {
                "tag": "Improved",
                "text": "Sidebar widths are remembered separately for each main feature. Switching between related tabs, such as MindMap and FreeMap or Notebook, To-Do, and PDF, preserves the current width."
            },
            {
                "tag": "Improved",
                "text": "MindMap and FreeMap recenter after enlarging or reducing the workspace while preserving the selected zoom level."
            },
            {
                "tag": "Improved",
                "text": "Refined the MindMap and FreeMap editing menus, text formatting controls, connection tools, and narrow-window layouts."
            },
            {
                "tag": "Improved",
                "text": "Notebook and map visibility settings now open inside their workspace, matching the Gamification settings style."
            },
            {
                "tag": "Improved",
                "text": "The Gamification sidebar now includes compact Settings and Info buttons, a refined progress card, and a more balanced Dashboard widget layout."
            },
            {
                "tag": "Improved",
                "text": "Celebration pop-ups now follow the selected primary color. Their Settings button opens the relevant celebration controls directly."
            },
            {
                "tag": "Improved",
                "text": "Celebration-specific options are hidden when celebration pop-ups are disabled."
            },
            {
                "tag": "Improved",
                "text": "The Pomodoro feature is now named Timer, with separate Settings, Statistics, and Analytics tabs and a dialog that adapts to its content."
            },
            {
                "tag": "Improved",
                "text": "Refined the Deck Overview spacing, chart height, buttons, and information cards. Studying can now be started with the space bar."
            },
            {
                "tag": "Improved",
                "text": "Brainstorm Cloud can now be enabled or disabled in the Deck Overview settings."
            },
            {
                "tag": "Improved",
                "text": "Dashboard surface controls are now expandable, with a cleaner preview and clearer Settings organization."
            },
            {
                "tag": "Improved",
                "text": "Expanded translations across HTML interfaces, Settings, onboarding, Daily Facts, and user-facing messages."
            },
            {
                "tag": "Fix",
                "text": "Fixed unnecessary scrolling and positioning issues in the Custom Deck Overview."
            },
            {
                "tag": "Fix",
                "text": "Fixed Deck Browser indicator visibility and alignment alongside deck settings."
            },
            {
                "tag": "Fix",
                "text": "Fixed background-overlay gaps while studying and opaque centers in the Statistics widget’s circular indicators."
            },
            {
                "tag": "Fix",
                "text": "Improved grid visibility, tutorial text contrast, and workspace separation in Dark Mode."
            },
            {
                "tag": "Fix",
                "text": "Improved study XP accounting after sessions, including protection against duplicate credit and recovery after failed saves."
            },
            {
                "tag": "Fix",
                "text": "Failed Notebook data loads no longer create an editable empty replacement. Users can retry loading without overwriting existing content."
            },
            {
                "tag": "Fix",
                "text": "Delayed Notebook and map saves remain attached to their original Anki profile when switching profiles."
            },
            {
                "tag": "Fix",
                "text": "Fixed custom Deck Overview color selection in the native Settings fallback."
            },
            {
                "tag": "Fix",
                "text": "Fixed missing Daily Fact translations and untranslated AI and map messages."
            },
            {
                "tag": "Fix",
                "text": "Additional improvements to saving, recovery, imports, exports, keyboard interaction, and compatibility with older Notebook data."
            }
        ]
    },
    {
        "version": "1.5.0",
        "date": "August 2026",
        "items": [
            {
                "tag": "Highlight",
                "text": "A new Minimalist Dashboard offers a cleaner, more linear SynapsePro experience with fewer distractions.",
            },
            {
                "tag": "Highlight",
                "text": "Custom Backgrounds let you use your own optimized image across the Dashboard and toolbars, with controls for blur, overlay, position, and text contrast.",
            },
            {
                "tag": "Highlight",
                "text": "Dedicated Statistics Settings now let you choose separate time ranges and decide which insights appear in the responsive statistics widget.",
            },
            {
                "tag": "Improved",
                "text": "Study Plan and Daily Fact widgets can now be enabled or disabled independently.",
            },
            {
                "tag": "Improved",
                "text": "The PDF Viewer and card-creation workflow now include visible page numbers, manual page selection, easier deck selection, and direct links back to selected PDF pages during review.",
            },
            {
                "tag": "New",
                "text": "SynapsePro now remembers whether the launcher sidebar was open or closed and restores that state on the next start.",
            },
            {
                "tag": "Improved",
                "text": "The SynapsePro logo now follows the primary colour of custom themes while preserving its white details.",
            },
            {
                "tag": "New",
                "text": "Deck Browser counter colours can now be customized independently for New, Learn, and Due cards in Light and Dark mode.",
            },
            {
                "tag": "Improved",
                "text": "Added a subtle loading animation to the Mind Map workspace.",
            },
            {
                "tag": "Fix",
                "text": "Fixed issues affecting the Consistency graph, SoundCloud playback, and the Pomodoro and Music Player icons in the sidebar.",
            },
        ],
    },
    {
        "version": "1.4.0",
        "date": "July 2026",
        "items": [
            {
                "tag": "Highlight",
                "text": "Mind Map, Website Viewer, and Notebook can now be opened in full-screen workspaces, providing significantly more room than the sidebar view.",
            },
            {
                "tag": "Highlight",
                "text": "The PDF Viewer now opens at 100% zoom, supports text selection, and lets you open Anki's card editor to create cards directly while working with a PDF.",
            },
            {
                "tag": "Highlight",
                "text": "Selected content in Notebook notes can now be concealed and revealed, turning your notes into an active recall study tool.",
            },
            {
                "tag": "Highlight",
                "text": "Notebook now supports folders and links to subpages for clearer organization and navigation.",
            },
            {
                "tag": "Highlight",
                "text": "Settings have been completely redesigned with a clearer, more structured interface.",
            },
            {
                "tag": "Highlight",
                "text": "A new statistics graph on the Home Dashboard shows how many cards you have studied over time.",
            },
            {
                "tag": "Highlight",
                "text": "The Music Player has been completely redesigned and now includes SoundCloud support.",
            },
            {
                "tag": "Improved",
                "text": "The AI Assistant now includes an improved introduction and a clearer setup flow for Ollama.",
            },
            {
                "tag": "New",
                "text": "Gamification pop-ups have been added. Daily Challenges can now be completed only after their requirements are actually met, with progress shown directly in the Dashboard widget.",
            },
            {
                "tag": "New",
                "text": "Mind Map nodes can now be resized, and optional hints can be added for node recall.",
            },
            {
                "tag": "New",
                "text": "Study Plan timers can now be completed early when you finish a session ahead of schedule.",
            },
            {
                "tag": "New",
                "text": "The deck completion screen now includes a session summary and displays the XP earned during the session.",
            },
            {
                "tag": "Improved",
                "text": "Pomodoro Timer settings now use a redesigned interface.",
            },
            {
                "tag": "New",
                "text": "A Help Desk has been added to the AI Assistant.",
            },
            {
                "tag": "New",
                "text": "Notebook now includes a larger selection of built-in and custom emojis.",
            },
            {
                "tag": "Fix",
                "text": "General stability improvements, usability refinements, and bug fixes across the add-on.",
            },
        ],
    },
    {
        "version": "1.3.0",
        "date": "May 2026",
        "items": [
            {"tag": "New", "text": "Added Portuguese, Vietnamese, Chinese, and Hindi language support."},
            {"tag": "New", "text": "Added support for multiple deadlines, allowing several deadlines to be managed at the same time."},
            {"tag": "New", "text": "Added custom audio uploads to the Music Player."},
            {"tag": "New", "text": "Added collapsible, Notion-style toggle notes to Notebook."},
            {"tag": "New", "text": "Added a To-Do manager to Notebook for organizing tasks alongside notes."},
            {"tag": "New", "text": "Added a built-in PDF Viewer to Notebook."},
            {"tag": "New", "text": "Study mode can now focus on a selected grade range."},
            {"tag": "New", "text": "Added a Study Plan timeline showing upcoming days and their difficulty."},
            {"tag": "New", "text": "Added a quick-access button to the Reddit community in Settings."},
            {"tag": "Improved", "text": "Overhauled the AI Assistant with multiple API providers and local Ollama models."},
            {"tag": "Improved", "text": "Refined the onboarding experience for new users."},
            {"tag": "Improved", "text": "Enhanced Statistics with a cleaner layout and more detailed insights."},
            {"tag": "Improved", "text": "Improved the visual design of Mind Map."},
            {"tag": "Improved", "text": "Improved the progress bar in the Custom Deck Dashboard."},
            {"tag": "Improved", "text": "Refined the Website Viewer and the overall Settings layout."},
            {"tag": "Fix", "text": "Fixed the Statistics streak counter not tracking consecutive study days correctly."},
            {"tag": "Fix", "text": "Resolved several issues in Mind Map and Website Viewer."},
        ],
    },
    {
        "version": "1.2.0",
        "date": "April 2026",
        "items": [
            {"tag": "New", "text": "Added Spanish and German language support."},
            {"tag": "New", "text": "Introduced a theme system with six presets and a Custom Color Editor."},
            {"tag": "New", "text": "Added Pomodoro statistics with a new tab-based interface."},
            {"tag": "New", "text": "Introduced a new AI Assistant dialog structure with OpenRouter support."},
            {"tag": "New", "text": "Added a Deadline Bar with a remaining-days indicator."},
            {"tag": "Improved", "text": "Refined the interface throughout the add-on."},
            {"tag": "Fix", "text": "Resolved stability and usability issues, including improved logging, SVG fallbacks, and placeholder URLs."},
        ],
    },
    {
        "version": "1.1.0",
        "date": "March 2026",
        "items": [
            {"tag": "New", "text": "Added Brainstorm Cloud to the Deck Overview."},
            {"tag": "New", "text": "Added an option to hide the sidebar automatically while reviewing cards."},
            {"tag": "New", "text": "Added Countries and Languages to the Daily Facts categories."},
            {"tag": "New", "text": "Added pause and stop controls to the Study Plan timer."},
            {"tag": "New", "text": "Added Changelog and News shortcuts to Settings."},
            {"tag": "Improved", "text": "Refined the Home Dashboard spacing and visual styling."},
            {"tag": "Improved", "text": "Improved the onboarding flow."},
            {"tag": "Improved", "text": "Optimized image rendering and loading performance."},
            {"tag": "Improved", "text": "Refined button layout and styling in Website Viewer."},
            {"tag": "Fix", "text": "Resolved an issue that could occur when switching between Anki profiles."},
        ],
    },
    {
        "version": "1.0.0",
        "date": "February 2026",
        "items": [
            {"tag": "New", "text": "Official launch of SynapsePro, an all-in-one learning dashboard for Anki."},
        ],
    },
]
