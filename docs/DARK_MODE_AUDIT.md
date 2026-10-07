# Dark-Mode-Audit – SynapsePro

Stand: 29. September 2026. Analyse des Desktop-Projekts, keine Änderung am laufenden Add-on oder an der installierten Anki-Kopie.

## Ergebnis

Die Inkonsistenz ist nachvollziehbar: SynapsePro besitzt bereits eine zentrale Python-Palette, verwendet daneben aber mehrere unabhängige HTML/CSS- und Qt-Paletten. Die richtige Grundlage ist der bestehende neutrale graue Stil von Dashboard und Launcher. Eine pauschale Verdunkelung oder das Ersetzen sämtlicher Grautöne durch dieselbe Farbe wäre keine sinnvolle Lösung.

Drei Dinge sollten vereinheitlicht werden: **Farben nach ihrer Funktion**, **die Übergabe dieser Farben an die Oberflächen** und **die Aktualisierung beim Theme-Wechsel**. Eine spätere dunklere Variante könnte dann dieselben semantischen Rollen neu belegen, statt jeden Bildschirm einzeln anzupassen. Eine solche Option wird mit diesem Audit weder eingebaut noch vorausgesetzt.

## Umfang und Aussagegrenzen

Quellcodeprüfung der zentralen Palette, Dashboard-/Deck-Overview-Renderer, Launcher, Feature-Sidebars, Webdialoge, gemeinsamer Workspace-Oberflächen, Musik-/Timer-Fenster, Celebration-Renderer, Onboarding sowie nativer Hilfs-, Verknüpfungs- und Konfigurationsdialoge. CSS-Fallbacks wurden, soweit vorhanden, gegen die Farb-Payloads aus Python geprüft. Besonders wichtig: Gamification und Musik erhalten zur Laufzeit andere Werte als manche ihrer CSS-Defaults.

Dies ist ein Architektur- und Farbaudit, kein vollständiger visueller Abnahmetest aller Zustände in Anki. Kontrastwerte unten sind aus opaken sRGB-Farbpaaren berechnet. Transparenz, tatsächliche Hintergründe, Betriebssystem-Widgets, externe Webseiten und sämtliche Zustandskombinationen benötigen bei der Umsetzung zusätzliche visuelle Prüfungen. Es wurden keine neuen Browser-/Qt-Tests ausgeführt, da kein Verhalten geändert wurde.

## 1. Die vorhandene Referenz

| Rolle heute | Wert | Quelle |
|---|---|---|
| Launcher und zentrale Kartenfläche | `#2C2C2C` | `theme.py:99`, `launcher_widget.py:568` |
| Deckliste / Papierfläche des Dashboard-Themes | `#303030` | `theme/user_files/medical_theme.css:25` |
| Vertiefte Arbeitsfläche | `#191919` | `theme.py:99` |
| Dezente Fläche / Track | `#303030` | `theme.py:99` |
| Hover / Auswahl | `#404040` | `theme.py:99` |
| Gedrückter Zustand | `#505050` | `theme.py:99` |
| Haupttext / Nebeninformation | `#E0E0E0` / `#AAAAAA` | `theme.py:99` |
| Sehr zurückgenommener Text | `#888888` | `theme.py:99` |
| Gemeinsame Workspace-/Browser-Leiste | `#2C2C2E`, Hover `#3A3A3C` | `website_sidebar.py:70`, `embedded_window.py:110`, `web_roadmap/workspace_ui.css` |

Auch die Referenz ist bewusst nicht einfarbig. Das Dashboard hat zusätzlich einen Theme-Verlauf; Bildhintergrund, Glas und Opazität verändern den wahrgenommenen Farbton. `#191919` ist deshalb **nicht** die allgemeine Dashboard-Kartenfarbe und sollte nicht als neuer Standard über alle Dialoge gelegt werden.

Empfehlung: `#2C2C2C` für normale Flächen und die bestehende neutrale Hierarchie als Ausgangspunkt festhalten. Karten, Canvas, Eingabefelder, erhöhte Dialoge und Hover dürfen unterscheidbar bleiben. Die geringe Abweichung `#2C2C2E` ist weniger dringlich als die deutlich anderen Farbwelten weiter unten.

## 2. Bestandsaufnahme nach Bereich

| Bereich | Ist-Zustand / Fundstelle | Bewertung |
|---|---|---|
| Dashboard, Statistik, Facts/Tasks, Gamification-Widgets | Python-Renderer nutzen `theme.palette`; Deckbrowser-CSS besitzt zusätzliche eigene Variablen. `statistics_widget.py`, `daily_widgets.py`, `gamification.py`, `minimal_dashboard.py`, `theme/user_files/medical_theme.css`. | Referenz erhalten; langfristig CSS und Python aus denselben Rollen speisen. |
| Deck Overview: Classic, Focus, Overview | `deck_overview.py:163` setzt Surface/Text aus Palette; `deck_overview_view.py` verwendet diese Variablen. Status- und Diagrammfarben sind teilweise eigene Werte. | Schon gut angebunden. Semantische Diagrammfarben separat behandeln. |
| Haupt-Sidebar / Launcher | `launcher_widget.py:568` verwendet Palette; eigener Theme-Hook mit Cleanup bei Zerstörung, Zeile 126. | Gute Ausgangsbasis. |
| AI Assistant | `chat_ui.html:22`: Hintergrund `#212121`, Fläche `#2F2F2F`, Text `#ECECEC`, Nebenfarbe `#8E8EA0`, Codefläche `#1A1A1A`. Qt-Seite separat `ai_assistant.py:1718`. | Eigenständige, teils violettgraue Palette; hoher Angleichungsbedarf. Chatblasen dürfen unterschiedliche Flächen behalten. |
| Gamification-Sidebar inkl. Settings/Friends | CSS-Defaults zunächst `#1C1C1E` / `#2A2A2C`; **wirksam überschrieben** durch `sidebar.py:434` und `gamification_web/sidebar.html:346`: `#191919` / `#2C2C2C`, Text/Tracks ebenfalls aus Palette. Friends/Settings verwenden überwiegend dieselben Variablen. | Bereits weitgehend zentralisiert. Nicht allein aufgrund der CSS-Defaults unnötig neu gestalten. Einzelne Status-/Accent-Fallbacks bleiben separat. |
| MindMap | `index.html`: Canvas `#191919`, Dialoge `#2C2C2C`, Eingaben `#404040`; zusätzliche Toolbar-/Menu-Regeln in `web_roadmap/workspace_ui.css`. | Farblich nah, technisch mehrfach definiert. Cascade und doppelte Dark-Regeln vereinfachen. |
| FreeMap | `web_roadmap/roadmap.css`: Canvas `#191919`, Surface `#292929`, Header `#252525`; gemeinsame Workspace-CSS ergänzt/überschreibt Teile. | Canvas passt, umgebende Flächen brauchen gemeinsame Rollen. Nicht jede CSS-Deklaration ist automatisch die sichtbare Endfarbe. |
| Notebook | `web_notebook/index.html`: Grund `#191919`, interne Sidebar `#202020`, Header `#252525`, Text teils weiß, Nebeninformation `#999`. | Eigene Hierarchie. Gemeinsame Navigations- und Dialogfarben angleichen; Dokumentfarben erhalten. |
| To-do / PDF | `web_notebook/todo.html:38`, `pdf_viewer.html:35`: Grund `#191919`, Header `#252525`, Text `#ECECEC`, Nebeninformation `#888`. | Nahe am Notebook, aber wiederum lokal definiert. PDF-Seiten sind Dokumentinhalt, keine UI-Fläche. |
| Web Browser | `website_sidebar.py:70`: eigene Toolbar-Palette `#2C2C2E`, Text `#E6E6E6`, Hover `#3A3A3C`. | Gute Nähe zur Workspace-Navigation, aber separate Quelle. Inhalte fremder Websites nicht pauschal umfärben. |
| Haupt-Settings / Appearance / Dashboard / eingebettete Deck-Settings | `settings_web/settings.html:20`: Hintergrund `#1C1C1E`, Sidebar `#222224`, Gruppen `#2A2A2C`, Felder `#3A3A3C`, Text `#F5F5F7`. | Deutlich eigene Palette. Sehr sichtbarer Kandidat für erste Angleichung. Layout kann unverändert bleiben. |
| Statistik-Settings | `settings_web/statistics.html:9`, `statistics_settings_dialog.py:69`: Palette ähnlich Haupt-Settings; Qt-Seitenhintergrund ebenfalls separat. | Zusammen mit Haupt-Settings migrieren. |
| Timer: Settings / Statistics / Analytics | `settings_web/pomodoro.html`: Apple-artige Palette wie Settings (`#1C1C1E`, `#2A2A2C`, `#3A3A3C`). `pomodoro.py:740` liefert den Dark-Status aus Modulvariable. | Flächen und Theme-Erkennung angleichen; Tabs/Diagramme beibehalten. |
| Focus Music | `background_music.py:838` liefert zentrale bg/card/text/muted/track-Werte; `music_player.html` übernimmt diese per `applyColors`. | Bereits gutes Muster für andere Webdialoge. Lokale CSS-Fallbacks und Randwerte vereinheitlichen. SoundCloud-Inhalt bleibt extern. |
| Celebration-Pop-ups | `celebration_preview.py:69`: blaugrauer Grund `#171B23`, Surface `#252A35`, Rahmen `#414754`. Live-Renderer verwendet diesen gemeinsamen Renderer. | Auffälliger Fremdkörper trotz bereits nutzerabhängiger Primärfarbe. Neutrale Flächen zuerst angleichen. |
| Onboarding | `onboarding/onboarding.html:491`: `#1F2329`, `#282E38`, `#242A33`, blaugraue Texte; `onboarding_dialog.py:139` setzt passende, aber eigene Qt-Farbe. | Eigene kühle Farbwelt. UI neutralisieren; Theme-Vorschaubilder und bewusste Illustrationen nicht verändern. |
| Native Konfiguration / Theme-Editor / Fallback-Settings | `configuration.py:42`, `theme_editor_dialog.py:39`, `settings_dialog.py:42`: nutzen Palette, ermitteln Nachtmodus aber beim Modulimport. | Weniger ein Farbproblem als ein Aktualisierungsproblem. Fallback-Oberflächen bei Migration mitnehmen. |
| Link Card / Hilfe / Diagnose / Entwicklerkonsole | `workspace_link_dialog.py`, `help_dialog.py`, `diagnostics_ui.py`, `developer_console.py`: überwiegend native Qt-/Anki-Widgets; Vorschauen zusätzlich separate Webrenderer. | Anki-Vererbung erhalten, keine globale Qt-Umfärbung. Entwickler-Vorschauen müssen dieselben Tokens bekommen wie die reale Oberfläche. |
| Eingebettete Fensterköpfe / Fehlermeldungen | `embedded_window.py:110` eigene Toolbarwerte; inline Error-Banner u. a. in Notebook-Dateien. | Auch Nebenpfade einbeziehen, sonst bleiben sichtbare Ausnahmen. |

## 3. Konkrete Probleme und Prioritäten

### Hoch: mehrere Quellen für dieselbe Farbfunktion

Ein Dialoghintergrund bedeutet derzeit je nach Modul etwas anderes. Das betrifft nicht nur Helligkeit, sondern Farbtemperatur und Textkontrast. Zentrale `theme.py`-Werte allein ändern reicht nicht: Ein Teil der Weboberflächen erhält nur Accent und Dark-Boolean, andere erhalten die ganze Palette, wieder andere deklarieren eigene Variablen.

**Maßnahme:** einen gemeinsamen Satz semantischer UI-Rollen bereitstellen und in Python/QSS sowie HTML/CSS übersetzen. Bestehende Modulvariablen zunächst an diese Rollen anbinden, statt Layout und Verhalten neu zu schreiben.

### Hoch: wenig lesbare Hinweise im AI Assistant

`chat_ui.html:25` definiert `--text-faint:#4A4A5A`; verwendet u. a. für `.start-hint` (Zeile 157), `.chip-indicator` (324) und weiteren kleinen Text (358).

Berechneter Kontrast auf `#212121`: **1,85:1**. Das ist für lesbare Hinweise deutlich zu schwach. Auch `#8E8EA0` auf `#2F2F2F` erreicht nur **4,16:1**; dies ist bei normalem kleinen Text unter dem üblichen 4,5:1-Ziel. Der tatsächlich anliegende Hintergrund ist je Element zu prüfen.

Die vorhandene Referenz funktioniert besser: `#E0E0E0` auf `#2C2C2C` ergibt **10,58:1**, `#AAAAAA` ergibt **6,01:1**. Aber auch zentrale Tokens dürfen nicht beliebig kombiniert werden: `#888888` auf `#404040` erreicht nur **2,92:1**. Ein deaktiviertes Element darf zurückhaltend sein; ein hilfreicher Erklärungstext muss lesbar bleiben.

### Hoch: Theme-Lifecycle ist nicht einheitlich

`__init__.py:938` aktualisiert ausdrücklich Workspace, AI und Hintergründe. Launcher hat seinen eigenen Hook. Musik und Browser haben eigene Refresh-Funktionen und Aufrufe beim Speichern von Einstellungen; das ist nicht derselbe Pfad wie der zentrale Anki-Themewechsel.

Mehrere Module halten `is_night_mode` seit dem Import fest. Besonders konkret: `pomodoro.py:740` verwendet diese Variable im Web-Payload. Bei Statistik/Facts betrifft sie noch einzelne Accent-Berechnungen. Ein Neustarthinweis existiert bereits; das ist keine einheitliche Live-Aktualisierung.

**Bewertung:** belegtes strukturelles Risiko für veraltete Farben, keine Behauptung, dass jedes dieser Fenster bei jedem Wechsel sichtbar falsch ist. Für Notebook kommen AnkiWebView-Hooks hinzu; deren Verhalten muss im integrierten Test geprüft werden.

**Maßnahme:** aktuellen Anki-Zustand beim Erzeugen eines Payloads lesen; bestehende Fenster über einen gemeinsamen, sauber abmeldbaren Update-Pfad versorgen. Kein Seitenreload, wenn dadurch Textentwürfe, Auswahl, Map-Undo oder Timerzustand verloren gehen könnten.

### Mittel: First Paint und Host-Hintergrund

Qt-WebEngine-Seitenhintergrund, initiale CSS-Werte und spätere JS-Payload können unterschiedlich sein. AI, Onboarding und Statistik-Settings setzen ihre Qt-Farben jeweils separat. Beim späteren Angleichen müssen alle drei Ebenen berücksichtigt werden, sonst sind kurz falsche Flächen oder Ränder möglich. Das ist ein Prüfpunkt, kein in diesem Audit reproduzierter Flash-Bug.

### Mittel: Rahmen, Zustände und Farbeffekte

Rahmen reichen von `#303030` / `#555555` bis zu weißen Alpha-Linien. Auswahl ist teils neutrales Grau, teils ein fester Farbstich; Nebeninformation reicht von reinem Grau bis zu blau/violett. Auch Fokus, Hover, Disabled, Dropdown, Tooltip und Scrollbar müssen Rollen erhalten. Nicht jede Statusfarbe durch die Primärfarbe ersetzen: Erfolg, Warnung, Fehler und Kartenkategorien tragen eigene Bedeutung.

## 4. Empfohlene Zielstruktur

Eine gemeinsame Theme-Auflösung in der bestehenden Theme-Schicht, keine zweite konkurrierende Dark-Mode-Engine:

- **Flächen:** Fenster, Karte, vertiefter Canvas, Navigation, Eingabe, erhöhtes Pop-up.
- **Text:** Haupttext, Nebeninformation, lesbarer Hinweis, deaktiviert, Text auf Accent.
- **Interaktion:** Hover, Pressed, Auswahl, Fokusrahmen, schwacher/starker Rahmen.
- **Semantik:** Accent, Erfolg, Warnung, Fehler; Diagrammfarben separat.
- **Effekte:** Overlay, Schatten, Glas-/Opazitätsparameter separat von neutralen Grundfarben.

Python erzeugt aus diesen Rollen QSS und ein kleines Web-Payload/CSS-Variablenset. Der frühe Dokumentzustand und spätere Updates verwenden dieselben Werte. Bestehende Variablennamen können vorübergehend als Alias bleiben. Canvas-Hintergrund darf weiterhin dunkler sein als die Launcher-Fläche; Gleichheit entsteht durch gleiche Rollen, nicht durch dieselbe Farbe überall.

Eine spätere optionale dunklere Palette wäre lediglich eine andere Rollenbelegung. Sie sollte nicht durch Hex-Ersetzungen, invertierende Filter oder globale Eingriffe in fremde WebEngine-Seiten entstehen.

## 5. Sinnvolle Umsetzung in Etappen

1. **Referenz festhalten und Theme-Übergabe vereinheitlichen.** Dashboard/Launcher visuell unverändert sichern; Rollen ergänzen; aktuelle Theme-Erkennung und sichere Update-Anbindung vorbereiten.
2. **Settings, Statistik-Settings, Timer, AI und Celebration angleichen.** Größter sichtbarer Nutzen, ohne Funktions- oder Layoutumbau. Kontrastarme Hinweise gleich korrigieren.
3. **Workspace-Familie vereinheitlichen.** MindMap/FreeMap/Notebook/To-do/PDF/Browser-Leisten, Kontextmenüs, Dialoge und Host-Hintergründe gemeinsam behandeln.
4. **Nebenflächen und Fallbacks abschließen.** Onboarding, native Konfiguration, Entwickler-Vorschauen, Fehlerbanner und eingebettete Fensterköpfe.

Abnahme je Etappe: Light/Dark nebeneinander; Anki-Themewechsel bei geöffnetem Fenster; 400-px-Sidebar und vergrößerte Ansicht; Hover/Fokus/Disabled/Dropdown; Hintergrund ohne Bild und mit Bild/Opazität/Glas. Bei Editoren zusätzlich ungespeicherter Text, Auswahl, Undo und Zoom; beim Timer laufende Session, bei Musik laufende Wiedergabe. Erst Webansichten prüfen, danach tatsächliche Qt-/Anki-Integration.

## 6. Bewusst erhalten

Nutzerfarben in Maps, SVG-Icons und Notizen, Bilder, Karten-Templates und PDF-Inhalte sind Inhalt und keine Theme-Tokens. Externe Webseiten und SoundCloud können nicht zuverlässig mit der eigenen UI-Palette erzwungen werden. Native Anki-Dialoge sollten ihre Systemintegration behalten. Die bestehenden Nutzerpräferenzen für Primärfarbe, Hintergrund, Transparenz und Glas bleiben unabhängig.

**Empfehlung:** Den gewünschten grauen Dark Mode bewahren und seine Farbsprache systematisieren. Die Grundlagen sind teilweise schon vorhanden; erforderlich ist vor allem, alle eigenen Oberflächen konsequent daran anzuschließen.

## Umsetzungsstand: eigenständige Menüs und Pop-ups

Die bestätigte Timer-Palette wurde auf Haupt-Settings (inklusive ihrer eingebetteten
Unterdialoge), Statistik-Settings, Focus Music/Track-Import, Celebration-Pop-ups,
Onboarding und native Einstellungs-/Lernplan-/Theme-Editor-Dialoge übertragen.
`theme.dialog_palette()` kapselt die neutralen Python-Werte und erhält die
nutzergewählte Akzentfarbe. `theme.palette()` für Dashboard und Hauptfunktionen
bleibt unverändert. Die Webdialoge verwenden entsprechende lokale CSS-Tokens.

Basis `#2C2C2C`, Inhaltsflächen `#252525`, Bedienelemente `#414141`, Haupttext Weiß.
Inaktive Tabs verwenden `#7E7E7E`; hilfreiche kleine Beschriftungen `#B0B0B0`.
Light Mode, Statusfarben, Inhalte und Theme-Vorschaubilder bleiben erhalten.
Die Hauptansichten und deren funktionsinterne Editor-/Sidebar-Menüs sind noch
nicht migriert. Native Anki-Systemdialoge und externe SoundCloud-Inhalte bleiben
unter Kontrolle von Anki bzw. des Anbieters.

### Erstes Hauptfeature: AI Assistant

Die AI-Oberfläche verwendet jetzt dieselbe neutrale Grundpalette einschließlich
Chatblasen, Eingaben und interner Menüs. Qt-Seitenhintergründe beim Öffnen und
Theme-Refresh wurden ebenfalls angepasst. Kleine Hinweise sind bewusst heller
als das inaktive Grau. Die dekorativen Hintergrundlichter sind im Dark Mode
zurückgenommen; Light Mode und Primärfarbe bleiben erhalten.
Browserprüfung bei 360/400/800 px, jeweils Light/Dark, einschließlich Settings,
Chip-Manager und synthetischer Streaming-Antwort mit Copy-Button durchgeführt.
Die übrigen Hauptfeatures sind weiterhin unverändert.

### Notebook / To-do / PDF Viewer

Die drei Notebook-Ansichten verwenden nun die neutrale Grundfläche `#2C2C2C`,
Navigation und Karten `#252525`, Eingaben/Hover `#414141`, weißen Text und
lesbare Nebenbeschriftungen. Gemeinsame Navigation, Notebook-Formatierungs- und
Blockwerkzeuge sowie Menübuttons wurden mitgenommen. PDF-Canvas-Umgebung und
Ladeoverlay sind dunkelneutral; die PDF-Seiten selbst bleiben unverändert weiß.
Nutzerformatierungen, Dokumentdaten und Speicherlogik wurden nicht geändert.
Browserprüfung: Light/Dark bei 400/800 px, Aufgabenanlage, Formatierungsleisten,
PDF-Seitenfarbe und JavaScript-Fehler. Keine integrierte Qt-/PDF-Rendering-Abnahme
in diesem Schritt; die Änderungen betreffen CSS und die injizierte Navigation.

### MindMap / FreeMap / Gamification

Die noch offenen Hauptansichten übernehmen jetzt ebenfalls die bestätigte
Palette: Arbeitsflächen `#2C2C2C`, dunkle Karten/Werkzeugleisten `#252525`,
Bedienelemente und Hover `#414141`, weiße Haupttexte, helle Nebeninformationen.
Gemeinsame Map-Menüs, Icon-Picker, Gamification-/Friends-Dialoge und die bisher
helle Cheers-Fläche wurden berücksichtigt. Workspace-Settings verwenden die
Dialogpalette. Dashboard und Launcher bleiben unverändert. Nutzerdefinierte
Map-Inhalte, Farbfüllungen und SVGs werden nicht umgefärbt.

Prüfung: 146 Python-Tests; Gamification-Dialogtests in Light/Dark und bei
300/360/900 px; FreeMap-Icon-Tests inklusive Undo, Copy und Export; gerenderte
MindMap-/FreeMap-/Gamification-Ansichten samt tatsächlichen CSS-Flächenfarben.
Keine vollständige Live-Anki-Abnahme aller Fenster in diesem Schritt.
