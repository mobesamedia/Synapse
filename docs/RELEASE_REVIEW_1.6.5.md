# Release-Prüfung Synapse 1.6.5

> **Nachtrag 28.10.2026:** Dieser Bericht dokumentiert den Stand **vor** der Korrektur. Die behobenen Befunde, aktuellen Testergebnisse und das gebaute Paket stehen in [RELEASE_FIXES_1.6.5.md](RELEASE_FIXES_1.6.5.md).

Prüfdatum: 27.10.2026. Ergebnis: **Den geprüften Stand noch nicht veröffentlichen.**

Es wurden zwei reproduzierbare Fälle gefunden, in denen Notebook-Inhalte aus dem aktuellen Dokument verschwinden. Einer davon ist eine Regression der neuen Historie, der andere besteht schon in 1.6.0. Zusätzlich ist die neue Versionssuche bei einer defekten SQLite-Datei nicht gegen Fehler abgesichert. Die erfolgreichen Standardtests reichen deshalb für eine Freigabe mit der Anforderung „keine Nutzerdaten verlieren“ noch nicht aus.

## Vergleichsbasis und Umfang

- GitHub: [mobesamedia/Synapse, main](https://github.com/mobesamedia/Synapse/commit/c01f68144b3f53b6978e57d63b74fc1399b67caa), Commit `c01f68144b3f53b6978e57d63b74fc1399b67caa`.
- Lokaler Ausgangscommit: `6afe28a3aa73aa94a5ca5466621d7c0f57f99b28`, Branch `update-1.6.0`.
- Beide Commits haben denselben Git-Dateibaum: `c0802aa009f00fb83233b8c6195f6c87e133b554`. GitHub liegt zwar zwei Commits weiter, der enthaltene Dateistand ist identisch. Die lokalen Änderungen sind damit tatsächlich die Änderungen gegenüber GitHub.
- Vor den für diese Prüfung ergänzten Dokumenten und Tests: 39 geänderte versionierte Dateien und 42 neue, noch nicht versionierte Dateien. Dazu gehören 17 Dateien unter `output/`; auch diese wurden beim Paketumfang berücksichtigt.
- Geprüft wurden Python, JavaScript, HTML/CSS, Speicherpfade, Versionskopien, Editor-Historie, Profilwechsel, Paketfilter, Versionsangaben und Übersetzungen. Alle Tests verwendeten synthetische Daten beziehungsweise temporäre Profile. Keine echte Nutzersammlung wurde geöffnet.
- Produktivcode wurde bei dieser Prüfung nicht korrigiert. Ergänzt wurden dieser Bericht, der Changelog-Entwurf, Testbelege und drei gezielte Regressionstestfälle. Von vorhandenen Browsertests erzeugte Änderungen an Dokumentations-Screenshots wurden auf ihre ursprünglichen Bytes zurückgesetzt.

Die vollständige Dateiliste mit SHA-256-Prüfsummen steht in [release-1.6.5/file-inventory.json](release-1.6.5/file-inventory.json). Die Bewertung gilt für genau diesen Stand; spätere Änderungen brauchen eine erneute Prüfung.

## Befunde nach Priorität

### R1 · P1 · Neue Regression: Historie überschreibt Seiten bei doppelten IDs

**Ort:** `web_notebook/index.html`, `captureNotebookCheckpoint()` und `navigateNotebook()`, insbesondere Zeilen 906–907 und 942–945.

Die Historie verwendet `Map(page.id → page)`. Enthalten Bestandsdaten zwei Seiten mit derselben ID, bleibt darin nur die letzte erhalten. Beim Anwenden einer Rückgängig-Aktion wird die Seitenliste aus dieser Map rekonstruiert. Dann können beide Listeneinträge den Inhalt der letzten Seite bekommen; der Inhalt der ersten Seite verschwindet aus dem gespeicherten Snapshot.

**Reproduktion:** Zwei Seiten mit `id: "same"`, aber verschiedenen Inhalten laden → eine neue Seite erstellen → Rückgängig. Danach enthält der aktuelle Stand zweimal den zweiten Seiteninhalt. Der erste Inhalt fehlt. Auf der GitHub-Version bleiben bei demselben Ablauf beide ursprünglichen Inhalte erhalten; deren älteres Undo verhält sich beim Erstellen anders, überschreibt diese Originale aber nicht.

**Voraussetzung:** Doppelte IDs in Bestandsdaten. Das ist ein Randfall, kein Fehler bei jedem Notebook. Der Loader akzeptiert diese Daten jedoch ungeprüft. Ältere Seitenerzeugung und weiterhin `createAndLinkPage()` verwenden `Date.now()` ohne Kollisionsprüfung; eindeutige IDs werden damit nicht durchgängig erzwungen. Die tatsächliche Verbreitung solcher Bestandsdaten ist unbekannt.

**Erforderliche Korrektur:** Bei nicht eindeutigen oder fehlenden IDs keine destruktive Historienrekonstruktion zulassen. Entweder alle Originalobjekte verlustfrei referenzieren oder vor einer ausdrücklich abgesicherten Umstellung eine vollständige, überprüfte Kopie behalten und Seitenverweise korrekt zuordnen. Keine stille Deduplizierung. Für sämtliche neu erzeugten Seiten UUIDs mit Kollisionsprüfung verwenden.

**Beleg:** `tests/review_165_notebook.cjs`, zweiter Fall; [evidence.json](release-1.6.5/evidence.json), Vergleich Alt/Neu.

### R2 · P1 · Bereits bestehend: Backspace im leeren Toggle-Titel entfernt gefüllten Inhalt

**Ort:** `web_notebook/index.html`, `createBlock('toggle')`, `title.onkeydown`, Zeilen 2007–2010.

Ist der Titel eines Toggle-Blocks leer, ersetzt Backspace den gesamten Toggle durch einen leeren Textblock. Ob `body` noch Text oder Bilder enthält, wird nicht geprüft. `triggerSave()` übernimmt anschließend diesen leeren Ersatz in den Notebook-Stand.

**Reproduktion:** Toggle mit leerem Titel und `body: "<b>IMPORTANT BODY CONTENT</b>"` laden → Titel fokussieren → Backspace → Snapshot lesen. Der Inhalt ist verschwunden. **Dieser Fehler wurde sowohl lokal als auch in der unveränderten GitHub-Version reproduziert.** Er ist keine durch 1.6.5 neu eingeführte Regression, widerspricht aber der geforderten Datensicherheit.

Historie oder Versionskopien können je nach Situation eine Wiederherstellung ermöglichen. Das ist keine Rechtfertigung dafür, den Inhalt bei einer normalen Tastenaktion zu entfernen, und bedeutet nicht, dass der Inhalt in jedem Fall physisch unwiederbringlich gelöscht ist.

**Erforderliche Korrektur:** Nur vollständig leere Toggles in einen leeren Absatz umwandeln. Bei gefülltem Body Titel und Inhalt erhalten oder verlustfrei in normale Blöcke überführen. Undo muss die vollständige Operation einschließlich Body und Metadaten abdecken.

**Beleg:** `tests/review_165_notebook.cjs`, erster Fall; identische Reproduktion auf Alt/Neu.

### R3 · P2 · Neue Wiederherstellungsfunktion bricht vor dem Lesen intakter Backups ab

**Ort:** `notebook_sidebar.py`, `_list_notebook_versions()`, Zeilen 1245–1253.

Das Öffnen/Lesen der SQLite-Datei steht vor der Schleife über die unabhängigen Vor-Update-Kopien. Bei einer beschädigten Datenbank wirft bereits die SQL-Abfrage eine Ausnahme; die gültigen JSON-Kopien werden gar nicht mehr gelesen. Eine exklusiv gesperrte Datenbank kann denselben Ablauf auslösen. Der Bridge-Callback macht daraus einen allgemeinen Versionsfehler.

**Reproduktion:** Zwei synthetische Snapshots speichern, damit eine Vor-Update-Kopie entsteht → nur die SQLite-Datei beschädigen → `_list_notebook_versions()` aufrufen. Ergebnis: `sqlite3.DatabaseError: file is not a database`, obwohl die JSON-Kopie intakt ist.

Das löscht die Kopie nicht. Es verhindert aber, dass diese Funktion sie ausliefert. Bei einem bereits fehlgeschlagenen initialen Notebook-Ladevorgang ist zudem eine unabhängige Wiederherstellungsoberfläche erforderlich, weil die normale Versionsansicht im Editor dann nicht verfügbar ist.

**Erforderliche Korrektur:** SQLite-Fehler separat behandeln, danach weiterhin beide Vor-Update-Dateien und Recovery lesen. Teilergebnisse anzeigen und die problematische Quelle kenntlich machen. Wiederherstellung und Export müssen auch von der Ladefehlerseite erreichbar sein.

**Beleg:** `tests/review_165_versions.py` schlägt mit dem beschriebenen Fehler fehl.

### R4 · Offener Freigabetest: Live-SoundCloud-Wiedergabe nicht bestätigt

Der vorhandene Integrationstest `tests/qt_soundcloud.py` scheitert in der installierten Umgebung wiederholt bei `upper Play starts real native audio`. Das offizielle Widget liefert Bereitschaft und Titelmetadaten; innerhalb des Testzeitfensters entsteht keine native Audio-Session mit fortschreitender Wiedergabe. Eine zusätzliche Abfrage im tatsächlichen SoundCloud-Frame liefert für den exakt vom Adapter geprüften Typ `audio/mp4; codecs="mp4a.40.2"` einen leeren Unterstützungswert. Der Frame behält zugleich die QtWebEngine-Browserkennung, die native Session bleibt leer und die Player-Oberfläche meldet keine Wiedergabe. Der beabsichtigte Adapterpfad wird in dieser Testumgebung also nicht erfolgreich aktiviert; die konkrete Ursache dafür ist offen.

Die URL-Tests, synthetischen Browser-Medientests und der echte Qt-Bridge-Test mit simulierten Audioprozessen bestehen. Das bestätigt Validierung, Befehle und Lebenszyklus, aber keine tatsächliche Audiowiedergabe. Der Live-Test erwartet ausdrücklich den nativen mpv-Pfad. Ob dessen Ausbleiben an Codec-Erkennung, Testannahmen, externem Dienst oder Produktcode liegt, wurde nicht abschließend geklärt. **Daraus folgt kein belegter allgemeiner SoundCloud-Ausfall bei allen Nutzern.** Die Behauptung „SoundCloud behoben“ ist für diesen Stand aber noch nicht freigeprüft.

Vor Freigabe die Wiedergabe mit und ohne AAC-Unterstützung prüfen; Play/Pause, Seek, Lautstärke, Playlist-Wechsel, automatischen nächsten Titel, Wechsel zu lokaler Musik und Profilende einschließen. Beide Wiedergabewege müssen im Test passend erkannt werden.

### R5 · P2 · Release-Paket enthält ungenutzte Entwurfsdateien

**Ort:** `scripts/package_addon.py`, `EXCLUDED_DIRS` und `release_files()`.

Der vorhandene Paketfilter würde 17 Dateien aus `output/imagegen/` mit insgesamt **21.621.438 Bytes** aufnehmen: Hintergrundentwürfe, Varianten und Prompt-Textdateien. Für diese Dateien wurde kein Runtime-Verweis gefunden. Das ergibt unnötigen Paketballast und veröffentlicht interne Arbeitsdateien. In diesen geprüften Dateien wurde kein Nutzerdatenverlust nachgewiesen.

**Erforderliche Korrektur:** `output/` aus dem Release ausschließen oder tatsächlich benötigte Assets gezielt an ihren Runtime-Ort übernehmen. Das endgültige ZIP per Dateiliste überprüfen. Runtime-Datenbanken sowie die neuen `*.pre-block-ui-v1.json` / `*.pre-hierarchy-v1.json` sind durch die bisherigen namensbasierten Ausschlüsse außerdem nicht ausdrücklich abgedeckt; im geprüften Ordner lagen solche Nutzerdatendateien nicht vor.

### R6 · Release-Vorbereitung noch nicht abgeschlossen

- `constants.py:10` und `manifest.json:5` nennen weiterhin **1.6.0**. `changelog.py` hat keinen 1.6.5-Eintrag. Das ist bei einem Entwurf erwartbar, muss aber vor Auslieferung konsistent geändert werden.
- Neue Runtime-Dateien sind noch unversioniert: `activity_chart.py`, `soundcloud_audio.py`, `soundcloud_native_audio.js`, `theme/user_files/none.css`, `theme/user_files/shared/scrollbars.css`. Sie müssen mitgeliefert werden. Insbesondere die neue relative Einbindung von `activity_chart.py` benötigt das Modul zwingend. Ein Commit nur der bereits versionierten Dateien wäre unvollständig.
- Es wurde kein Release veröffentlicht, kein Push ausgeführt und keine Versionsnummer vorzeitig umgestellt.

## Was an der Datensicherung bereits gut umgesetzt ist

- Neue Notebook-Sicherungen sind additiv. Keine SQL-Schemaänderung und kein Umschreiben bestehender Notizzeilen im untersuchten Diff.
- Vor dem normalen Kürzen auf 20 Snapshot-Zeilen werden zwei nicht rotierende Vor-Update-Kopien angelegt. Schreiben über temporäre Datei, Flush/fsync und atomaren Dateiaustausch.
- SQLite-Snapshots werden in Transaktionen gespeichert. Ungültiges JSON wird vor dem Speichern abgewiesen; bei SQLite-Problemen existiert ein atomarer Recovery-Pfad.
- Ein Lesefehler erzeugt eine Fehlerseite, deren leerer Inhalt nicht als Notebook gespeichert werden darf. Das wurde mit echter Qt-Bridge geprüft.
- Asynchrone Schreibvorgänge bleiben an den ursprünglichen Profilpfad gebunden. Der Abschluss eines Ansichtswechsels wartet auf das Speichern und prüft spätere Änderungen erneut.
- Unveränderte Blöcke, unbekannte Felder und unbekannte Blocktypen werden im Standardfall unverändert erhalten. Gefiltertes Bestands-HTML bleibt im gespeicherten Original erhalten; teilweise gefilterte Felder werden gegen Bearbeitung geschützt.
- Wiederherstellung aus Versionen und Vorlagen erzeugt eine unabhängige Kopie. Originalseiten werden dabei im getesteten Standardfall nicht ersetzt.
- Es wurden im Update keine neuen Löschoperationen an Anki-Karten oder der Anki-Sammlung festgestellt. Das ersetzt keine vollständige plattformübergreifende Laufzeitprüfung.

Diese Mechanismen senken das Risiko deutlich. Sie sind kein Nachweis, dass jeder Editorpfad verlustfrei ist; R1 und R2 zeigen die verbleibenden Lücken.

## Ausgeführte Prüfungen

Umgebung: macOS/ARM64, installiertes Anki 26.9.3, dessen Qt 6.11.0 und Python-3.13-Pakete; zusätzliche Python-Standardtests mit Python 3.12. Browser-Tests über Playwright und den installierten Google Chrome.

| Prüfung | Ergebnis | Einordnung |
| --- | --- | --- |
| Vorhandene Python-Unit-Tests | **155/155 erfolgreich** | Erster Sandbox-Lauf scheiterte nur bei Prozess-RSS; außerhalb der Sandbox bestand derselbe Test. |
| Python-Syntax aller lokalen Module | Erfolgreich | `compileall`; kein Import-/Anki-Kompatibilitätsnachweis allein dadurch. |
| Vorhandene Browser-Testdateien | **42/43 erfolgreich** | Übersetzungsfixtures erzeugt; fehlenden Playwright-Download durch vorhandenen Chrome ersetzt. |
| Übersetzungsaudit | **2049 auditierte Einträge, 0 fehlend, 0 Platzhalterfehler** | Der separate JSON-Katalog wächst von 1715 auf 1785 Schlüssel. Die Audit-Gesamtzahl umfasst weitere Quellen. |
| `qt_notebook_launch.py` | Erfolgreich | Ladefehler, geblocktes Leerspeichern, Wiederholung, echte Versions-Bridge, Kopien, Editor-/Medienaktionen, Speichern, Toolwechsel, Schließen. |
| `qt_roadmap_lifecycle.py` | Erfolgreich | Tutorial, Speichern, Tabwechsel, Hide/Show, Import/Export, Bilder, Icons, Themewechsel, Cleanup. |
| `qt_review_background.py` | Erfolgreich | Opt-in, Bilddarstellung, Cache, Intensität und Abschalten. |
| `qt_soundcloud_bridge.py` | Erfolgreich | Echte Qt-Objekte, simulierte Audioprozesse; keine Live-Audiobestätigung. |
| `qt_soundcloud.py` | **Fehlgeschlagen** | Wiederholt keine native Wiedergabe; Ursache offen, siehe R4. |
| Neue gezielte Notebook-Prüfung | **2/2 Fehler reproduziert** | Toggle-Verlust und ID-Kollisionsverlust, getrennt von den 43 bestehenden Browser-Dateien. |
| Neue gezielte Recovery-Prüfung | **Fehler reproduziert** | Gültige Kopie wird bei beschädigter SQLite-Datei nicht geliefert. |

Der eine fehlschlagende bestehende Browser-Test ist `web_glass_backdrop.cjs`: Die Settings-Vorschau liefert `backdrop-filter: none` statt `blur(16px)`. Der Fehler tritt sowohl lokal als auch in der unveränderten GitHub-Kopie auf. Deshalb ist er **keine nachgewiesene Regression dieses Updates**. Die erste Prüfung des tatsächlichen Wallpaper-Blurs im selben Test besteht; der Fehler betrifft den späteren Settings-Vorschau-Abschnitt. Testfixture und Vorschauzustand müssen abgeglichen werden, bevor daraus ein Produktdefekt behauptet wird.

Die übrigen Browser-Tests decken insbesondere Notebook-Sicherheit, Rohdaten-/Metadatenerhalt, Hierarchie, Historie, Drag-and-drop, Tabellen und Bilder, Vorlagen/Versionen, AI-Buttons, Hintergrundstile/Toolbars, Scrollbars, Deckübersicht und Map-Zoom ab. Einzelresultate stehen in [evidence.json](release-1.6.5/evidence.json).

## Änderungen gegenüber GitHub

Der veröffentlichbare Textentwurf steht in [CHANGELOG_1.6.5_DRAFT.md](CHANGELOG_1.6.5_DRAFT.md). Es werden nur Unterschiede zur Vergleichsbasis aufgeführt; bereits in 1.6.0 enthaltene Features wie die grundsätzliche FreeMap-Funktion, DeepSeek oder Timer Analytics werden nicht erneut als neue Features ausgegeben.

| Bereich | Lokale Änderung | Wesentliche Dateien |
| --- | --- | --- |
| Notebook-Blöcke | H3, neue Blockmenüs/Gutter, Einfügen, Duplizieren, Reihenfolge ändern, auf andere Seite verschieben; erweiterte Text-/Hintergrundfarben, Inline-Code und Formatierungen | `web_notebook/index.html`, `notebook_sidebar.py` |
| Notebook-Eingabe | Formatierung beim Teilen/Zusammenführen erhalten; differenzierter Umgang mit strukturellen und unbekannten Blöcken; Listen-/To-do-Verhalten; Klicks in Seitenränder und Fokusführung | `web_notebook/index.html` |
| Notebook-Navigation | Unterseiten, Hierarchie, Breadcrumbs, Verschachteln und Sortieren per Drag-and-drop, Seitenwahl mit Suche, chronologische Rückgängig-/Wiederholen-Historie | `web_notebook/index.html` |
| Tabellen/Bilder | Kopfzeile, Reihen/Spalten umordnen, Ausrichtung und Spaltenbreiten; Bilddateien hochladen, ausrichten, proportional skalieren und verschieben; Vorschau und Abbruch während Drag | `web_notebook/index.html` |
| Vorlagen/Versionen | Eigene Seitenvorlagen und Vorlage „Disease profile“; Inhaltsverzeichnis aus Überschriften; Versionsvorschau, Wiederherstellen als Kopie, zentraler Exportzugang | `web_notebook/index.html`, `notebook_sidebar.py` |
| Notebook-Sicherheit | Schutz vor HTML-/Markdown-Injection, Sicherheitshinweis, geschützte Darstellung gefilterter Bestandsinhalte und Erhalt ursprünglicher Daten | `web_notebook/index.html`, Übersetzungsdateien |
| Notebook-Sicherung | Zwei feste Vor-Update-Kopien vor Snapshot-Pruning; Auflistung gespeicherter Versionen und Recovery | `notebook_sidebar.py` |
| Hintergründe | Auswahl „None“, frei wählbare helle/dunkle Vollfarben; Erhalt des Dashboard-Layouts; getrennte Toolbar-Behandlung beim Lernen; Farbeingaben auch im nativen Fallback | `__init__.py`, `settings_dialog.py`, `web_settings_dialog.py`, `settings_web/settings.html`, `theme/user_files/none.css` |
| Scrollbars | Gemeinsames Stylesheet und sichtbare, gestaltete Scrollbars im Dashboard und der eigenen Deckübersicht | 16 bestehende Theme-CSS-Dateien, `theme/user_files/shared/scrollbars.css` |
| Charts | Gemeinsame geglättete Aktivitätskurve mit Flächenfüllung, Tooltip-Bereichen und Tagespunkt für Dashboard und Deckübersicht | `activity_chart.py`, `statistics_widget.py`, `deck_overview_view.py` |
| AI-Schnellaktionen | Eigene Buttons bearbeiten und Änderungen abbrechen; IDs, Shortcuts und Zusatzfelder bleiben erhalten; vorhandener Anlegeentwurf wird zurückgeholt | `chat_ui.html` |
| AI-Datenhinweis | Klarstellung: Schnellaktionen senden den Kartentext auch bei deaktiviertem Kontextschalter; der Schalter betrifft selbst eingegebene Fragen. Der Hinweis ändert das Backend-Verhalten nicht. | `chat_ui.html`, `web_i18n.py`, `web_translations.py` |
| MindMap/FreeMap | Trackpad-Pinch und native Qt-Zoomgesten an die Canvas weitergeben; Oberfläche nicht mitzoomen; Ansichten nach Fullscreen-Wechsel zentrieren; Navigationsicon angepasst | `mindmap_sidebar.py`, `index.html`, `web_roadmap/roadmap.js`, `web_roadmap/tool_nav.js`, `web_roadmap/tool_nav.css` |
| SoundCloud | Widget-lokaler AAC/HLS-Adapter mit getrenntem mpv-Prozess, Token-/Session-Prüfung, CDN-URL-Prüfung, Prozessbegrenzung und Pause/Cleanup; Lautstärke nach Widget-Neuladen wieder setzen | `soundcloud_audio.py`, `soundcloud_native_audio.js`, `background_music.py`, `soundcloud_player.html` |
| Sprachen/Tests | Neue UI-Texte in den vorhandenen zehn Sprachen; zusätzliche Python-/Browser-/Qt-Regressionstests und SoundCloud-Dokumentation | `translation_catalog.json`, `web_translations.py`, `web_i18n.py`, `tests/`, `docs/SOUNDCLOUD_PLAYBACK.md` |
| Arbeitsmaterial | 17 generierte Bild-/Prompt-Dateien, derzeit vom Paketfilter erfasst; kein freigeprüftes Produktfeature | `output/imagegen/` |

## Was vor der Freigabe noch nötig ist

1. R1 und R2 beheben; die beiden neuen Notebook-Regressionsfälle müssen erfolgreich sein. Zusätzlich reguläres Undo/Redo, Seitenwechsel und Schreiben nach Neustart erneut prüfen.
2. R3 beheben und Wiederherstellung auch bei initial nicht lesbarer Datenbank zugänglich machen. Intakte Kopien dürfen nicht wegen einer anderen defekten Quelle unsichtbar werden.
3. R4 mit nachvollziehbarem Live-Ergebnis abschließen oder den noch nicht freigeprüften Adapter aus dem Release nehmen. R5 beim tatsächlichen Release-ZIP korrigieren.
4. Version und Changelog konsistent vorbereiten; alle erforderlichen neuen Runtime-Dateien aufnehmen. Das fertige Paket in einer **Kopie** eines repräsentativen 1.6.0-Profils installieren.
5. Bei der Installation alte Notizformate, große Notebooks, Bilder, Tabellen, Unterseiten, geschützte HTML-Blöcke, Tasks, PDFs, Maps, AI-Einstellungen und Gamification prüfen. Anschließend neu starten und Inhalte erneut vergleichen. Abbruch/Schreibfehler, Datenbanksperren und Profilwechsel einbeziehen.
6. Windows und Linux sowie die deklarierte Mindestversion Anki 25.09.4 separat prüfen. Die hier erfolgreiche macOS-/Anki-26.9.3-Prüfung deckt diese Kombinationen nicht ab.
7. Vor der Verteilung eine vollständige externe Kopie des Testprofils inklusive `notebook.sqlite`, Recovery, `SynapsePro_Data` und relevanter Einstellungen anlegen und eine Wiederherstellung praktisch testen. Die Anki-Sammlung allein umfasst nicht automatisch jede externe Add-on-Datei.

Die neuen Tests lassen sich explizit mit `node tests/review_165_notebook.cjs` (Playwright erforderlich) und `python tests/review_165_versions.py` starten. Für den Altvergleich akzeptiert der Browser-Test `SYNAPSE_REVIEW_ROOT` auf eine entpackte GitHub-Version. Die drei ergänzten Fälle schlagen auf dem geprüften lokalen Stand absichtlich als Nachweis der offenen Fehler fehl; sie wurden nicht als erfolgreiche Tests gezählt.

Eine universelle Garantie völliger Bugfreiheit oder gegen Stromausfall/Hardwaredefekte ist aus einer Codeprüfung nicht ableitbar. Der aktuelle Ablehnungsgrund ist konkreter: Es liegen reproduzierte Inhaltsverluste und noch offene Freigabetests vor.
