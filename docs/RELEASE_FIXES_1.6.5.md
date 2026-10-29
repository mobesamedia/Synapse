# Synapse 1.6.5 – Korrekturen und Abschlussprüfung

> **Aktueller Nachtrag:** Der hier dokumentierte Recovery-Blocker ist behoben. Neues Paket, Erklärung der additiven Metadaten und aktuelle Testbelege: [RECOVERY_FIX_1.6.5.md](RECOVERY_FIX_1.6.5.md). Die folgenden Angaben halten den damaligen Prüfstand fest.

> **Aktueller Freigabestand: NICHT VERÖFFENTLICHEN.** Die anschließende Windows-/Linux-Prüfung hat einen weiteren bestehenden Recovery-Konsistenzfehler reproduziert. Dieser Bericht hält die zuvor erfolgreichen Korrekturen fest; die aktuelle Entscheidung und zusätzlichen Testbelege stehen in [CROSS_PLATFORM_REVIEW_1.6.5.md](CROSS_PLATFORM_REVIEW_1.6.5.md).

Stand: **28.10.2026**. Die bestätigten Notebook-Fehler sind lokal behoben. SoundCloud funktioniert im vollständigen Live-Test wieder. Ein geprüftes Installationspaket wurde vorbereitet; es wurde nichts veröffentlicht und keine installierte Benutzer-Version automatisch ersetzt.

Paket: [Synapse-1.6.5.ankiaddon](../output/releases/Synapse-1.6.5.ankiaddon), 35.167.113 Bytes, 396 enthaltene Dateien.

SHA-256: `52601345e4545aa660d9b3c0d125de7b9420548882f847a2b0a6e2eae7f1cefb`.

## Notebook: Bestandsdaten bleiben unverändert

- Vor jedem Erfassen und Anwenden der neuen Historie werden die Seiten-IDs auf Eindeutigkeit geprüft. Bei doppelten, leeren oder ungeeigneten IDs bleibt die neue Historie deaktiviert. Die gespeicherten Seiten und ihre Verweise werden **nicht** automatisch umnummeriert, zusammengeführt oder gelöscht.
- Bei doppelten IDs kann auch ein Löschklick nicht mehr mehrere Originalseiten mit derselben ID entfernen. Eine solche mehrdeutige Löschaktion wird nicht ausgeführt.
- Neu angelegte Seiten, per Seitenlink erzeugte Seiten sowie Vorlagen-/Versionskopien prüfen ihre neue ID auf Kollisionen mit vorhandenen Seiten.
- Backspace in einem leeren Toggle-Titel lässt einen gefüllten Body unangetastet. Das gilt auch für Bilder, reine Leerzeichen, unsichtbares beziehungsweise gefiltertes Original-HTML und Zusatzfelder.
- Ein vollständig leerer Toggle kann weiterhin in einen normalen Absatz umgewandelt werden. Die Operation erhält seine Zusatzfelder und kann rückgängig gemacht werden.

Diese Änderungen greifen an den betroffenen Editoraktionen ein. Es gibt keine neue automatische Migration und keine Änderung des Datenbankschemas.

## Wiederherstellung und Export

- Fehler beim Lesen der SQLite-Datei brechen das Lesen unabhängiger Vor-Update- und Recovery-Dateien nicht mehr ab. Auch eine beschädigte, fehlende oder unvollständige Datenbank verhindert die Auflistung intakter Kopien nicht mehr.
- Die Notebook-Ladefehlerseite bietet einen Export vorhandener Versionen an. Lesen und Versionsauswahl erfolgen unabhängig vom nicht geladenen Editor.
- Der Export erzeugt eine **neue** JSON-Datei. Bestehende Dateien, die Datenbank und Sicherungsquellen können durch diese Aktion nicht überschrieben werden. Abbruch und Profilwechsel lassen die Quellen unverändert.
- Ein echter Qt-Test vergleicht die Quelldatenbank vor und nach diesem Export bytegenau. Sie bleibt unverändert; die Fehlerseite speichert keine leeren Editorinhalte.

## SoundCloud: konkrete Ursache und Korrektur

In der geprüften neueren Qt-Version wurde das zuvor nur an der Host-Seite registrierte Adapter-Script nicht im separaten Renderer des eingebetteten SoundCloud-Frames ausgeführt. Die lokale Host-Seite lud, Titelmetadaten waren verfügbar, aber der native AAC/HLS-Adapter startete nicht.

Das Script wird jetzt am **dedizierten Musikprofil** registriert. Es beendet sich weiterhin sofort außerhalb von `w.soundcloud.com/player/`. Andere Anki-WebViews verwenden dieses Musikprofil nicht. Die Script-Registrierung wird beim Zerstören der zugehörigen SoundCloud-Seite entfernt; dazu gibt es einen eigenen Qt-Test.

Die Änderung löscht weder Cookies noch Sender, lokale Titel oder Anki-Daten. Der separate mpv-Prozess bleibt von Ankis normaler Karten-Audiowiedergabe getrennt. Der ausschließlich im Integrationstest verwendete Listener für den orangenen Play-Button wurde ebenfalls auf dieselbe Frame-Injektion umgestellt.

**Live bestätigt:** oberer und orangener Play-Button, echter Wiedergabefortschritt, Pause, Spulen, Lautstärke, nächster/vorheriger Titel, Stationswechsel, Lautstärkeerhalt, automatisches Weiterschalten am Titelende, Neuladen, Ausblenden/Anzeigen, Wechsel zur lokalen Musik und unveränderte gespeicherte synthetische Daten.

Der vollständige Live-Test bestand sowohl im Arbeitsverzeichnis als auch mit dem Code aus dem gebauten Paket. Die einzige spätere Paketänderung war die zusätzliche Notebook-ID-/Löschsicherung; die SoundCloud-Dateien und sämtliche anderen Paketdateien wurden dabei bytegenau als unverändert verifiziert.

## Paket und Changelog

- `output/` mit den rund 21,6 MB Bildentwürfen und Prompt-Dateien wird nicht mit ausgeliefert. Die Arbeitsdateien selbst wurden nicht gelöscht.
- Profilordner, SQLite-/DB-Dateien, SQLite-Nebendateien, Vor-Update-Kopien sowie Backup-/Recovery-Dateien einschließlich ihrer temporären Schreibdateien werden ausgeschlossen.
- Die benötigten neuen Runtime-Dateien sind enthalten: `activity_chart.py`, `soundcloud_audio.py`, `soundcloud_native_audio.js`, `none.css` und `shared/scrollbars.css`.
- `constants.py`, `manifest.json` und `changelog.py` sind auf **1.6.5** abgestimmt. Das Changelog enthält 24 Einträge einschließlich der bestätigten Korrekturen. Der ergänzte deutsche/englische Text steht in [CHANGELOG_1.6.5_DRAFT.md](CHANGELOG_1.6.5_DRAFT.md).
- Das endgültige ZIP wurde auf Integrität und vollständige Übereinstimmung aller enthaltenen Dateien mit dem lokalen Quellstand geprüft. Keine Entwicklungstests, Berichte oder generierten Entwürfe sind enthalten.

## Prüfergebnisse

| Prüfung | Ergebnis |
| --- | --- |
| Vollständige Python-Suite | **158/158 erfolgreich** |
| Bestehende Browser-Testdateien | **43/43 erfolgreich** |
| Zusätzliche Notebook-Datenerhalt-Regressionen | Erfolgreich; auch Bilder, geschütztes HTML, Leerzeichen, Metadaten, leere Toggles mit Undo und mehrdeutige Löschaktionen |
| Zusätzlicher Recovery-Test bei beschädigter Datenbank | Erfolgreich |
| Übersetzungen | 2049 auditierte Einträge; keine fehlenden Übersetzungen oder Platzhalterfehler |
| Echte Qt-Notebook-Bridge | Erfolgreich; Ladefehler, Export, Ansichtswechsel, Speichern und Schließen |
| Notebook aus endgültigem Paket mit synthetischer Bestandsdatenbank | Erfolgreich; Originalinhalt und beide Vor-Update-Kopien erhalten, Datenbank beim Recovery-Export unverändert |
| SoundCloud-Bridge und Script-Lebenszyklus | Erfolgreich; Token-/Session-Prüfung, Prozessbegrenzung, Cleanup und Entfernen des Profil-Scripts |
| SoundCloud mit offiziellem Live-Widget | Vollständiger Test erfolgreich, auch aus dem gebauten Paket |
| ZIP-Integrität, enthaltene Dateien, Versionen und Python-Syntax | Erfolgreich |

Der zuvor fehlschlagende Glaseffekt-Test hatte seinen bereits aktivierten Master-Schalter durch einen unbedingten Klick selbst ausgeschaltet. Der Test aktiviert ihn jetzt nur bei Bedarf. Dafür wurde kein Produktverhalten geändert.

Nach der abschließenden kleinen ID-/Löschsicherung wurden die gezielten Datenerhalt-Tests, der umfangreiche Notebook-Upgrade-Browsertest und der echte Qt-Test aus dem endgültigen Paket erneut ausgeführt. Die vollständige Browser-Suite wurde davor bereits erfolgreich geprüft. Testgenerierte Dokumentationsbilder wurden auf ihre vorherigen Bytes zurückgesetzt.

Maschinenlesbare Belege und Paket-Dateiprüfsummen stehen in [release-1.6.5/fix-validation-2026-10-28.json](release-1.6.5/fix-validation-2026-10-28.json). Der ursprüngliche Bericht vom 27.10. bleibt als Vorher-Zustand erhalten.

## Reichweite der Aussage

Geprüfte native Umgebung: **macOS/ARM64 mit Anki 26.9.3** und dessen Qt-/Python-Paketen. Windows, Linux und die deklarierte Mindestversion Anki 25.09.4 wurden nicht separat ausgeführt. Der Live-Erfolg von SoundCloud gilt für den Dienststand zum Prüfzeitpunkt; spätere Änderungen des externen Dienstes bleiben möglich.

Keine echten Notebook-Daten, Nutzerprofile oder Sammlungen wurden für die Tests geöffnet oder verändert. Die getestete Update-Datenbank war eine synthetische bestehende Datenbank. Eine allgemeine Garantie gegen sämtliche Bugs oder Hardware-/Dateisystemausfälle ist daraus nicht ableitbar.

Zum eigenen Abnahmetest das Paket in Anki installieren und Anki vollständig neu starten. Vor einem produktiven Update eine vollständige externe Kopie des bisherigen Profils einschließlich Add-on-Daten behalten. Das Paket wurde vorbereitet, aber nicht in das reale Benutzerprofil eingespielt oder auf GitHub/AnkiWeb veröffentlicht.
