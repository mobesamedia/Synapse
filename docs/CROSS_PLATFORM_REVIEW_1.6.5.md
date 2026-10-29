# Windows-/Linux-Prüfung für Synapse 1.6.5

> **Aktueller Nachtrag:** Der hier dokumentierte Recovery-Blocker ist behoben. Neues Paket, Erklärung der additiven Metadaten und aktuelle Testbelege: [RECOVERY_FIX_1.6.5.md](RECOVERY_FIX_1.6.5.md). Die folgenden Angaben halten den damaligen Prüfstand fest.

Stand: **28.10.2026. Ergebnis: Das bisherige Paket noch nicht veröffentlichen.**

Die ergänzende Prüfung hat einen weiteren Speicherfehler reproduziert. Er betrifft eine ältere Recovery-Datei, die trotz erfolgreichem SQLite-Schreiben nicht entfernt oder aktualisiert werden kann. Dieser Fall ist unter Windows wegen der Dateifreigabe-Semantik besonders relevant. Bei entsprechenden Zugriffsfehlern kann derselbe Codepfad auch auf anderen Systemen auftreten.

## Was tatsächlich geprüft wurde

Die ausführbare Umgebung dieser Sitzung ist macOS/ARM64. Es wurden **keine nativen Windows- oder Linux-Instanzen** gestartet. Die Ergebnisse setzen sich aus Quellcodeprüfung, Paketprüfung, echten lokalen SQLite-Dateien und gezielter Simulation von Betriebssystemfehlern zusammen. Die reine Berechnung eines Windows-Dateipfads wurde ausdrücklich nicht als Windows-Dateizugriff gewertet.

Prüfgegenstand war das bereits erzeugte Paket `output/releases/Synapse-1.6.5.ankiaddon`, SHA-256:

`52601345e4545aa660d9b3c0d125de7b9420548882f847a2b0a6e2eae7f1cefb`

Alle enthaltenen Runtime-Dateien stimmen weiterhin bytegenau mit dem geprüften lokalen Quellstand überein. In dieser zusätzlichen Prüfung wurde **kein Produktivcode geändert und kein Ersatzpaket erstellt**. Ergänzt wurden Tests, dieser Bericht und ein Freigabehinweis neben dem vorhandenen Paket. Ein Test-Helfer liest Python-Quellen nun explizit als UTF-8, damit der portable Regressionstest nicht von einer Windows-Standardzeichencodierung abhängt.

## P1: Ältere Recovery-Datei verdrängt bestätigte neuere Änderungen

Betroffene Funktionen in `notebook_sidebar.py`:

- `_clear_snapshot_recovery()` versucht zuerst, die Recovery-Datei zu entfernen. Schlägt das fehl, versucht es, sie mit dem gerade gespeicherten Inhalt zu ersetzen. Das Fehlschlagen dieses zweiten Versuchs wird nicht an den Aufrufer weitergegeben.
- `_save_snapshot()` hat den neuen Stand zu diesem Zeitpunkt bereits in SQLite bestätigt und meldet deshalb trotzdem Erfolg.
- `_load_latest_snapshot()` bevorzugt bei jedem Laden eine gültige Recovery-Datei vor SQLite. Es erkennt nicht, dass diese Datei den älteren Stand enthält.

**Reproduzierter Ablauf mit synthetischen Notizen:**

1. Eine Notiz und eine ältere gültige Recovery-Datei anlegen.
2. Nur Löschen und Ersetzen dieser Recovery-Datei mit `PermissionError` scheitern lassen. SQLite und das übrige Verzeichnis bleiben nutzbar.
3. Eine neue Notizänderung speichern. Rückgabe: `True`, also „gespeichert“; SQLite enthält den neuen Inhalt.
4. Erneut laden. Ergebnis: Der ältere Recovery-Inhalt wird statt der neuen Änderung geliefert.
5. Nach Freigabe der simulierten Sperre 25 weitere Bearbeitungen dieses älteren Inhalts speichern. Ergebnis: Die zwischenzeitlich bestätigte neue Änderung ist in keiner über `_list_notebook_versions()` angebotenen Version mehr enthalten. Die Vor-Update-Kopien dieses Szenarios enthalten ebenfalls nur den älteren Stand.

Damit ist der Fehler mehr als eine vorübergehend falsche Anzeige. Zunächst existiert die neue Änderung noch in SQLite. Bei fortgesetzter Benutzung kann sie durch die normale Begrenzung der Snapshot-Historie verdrängt werden und ist dann über die implementierten Wiederherstellungswege nicht mehr verfügbar. Es wird keine Aussage über forensische Wiederherstellung gelöschter SQLite-Seiten getroffen.

**Voraussetzungen und Grenzen:** Der Test simuliert die fehlgeschlagenen Dateisystemoperationen; er erzeugt keine echte Windows-Dateisperre. Die Häufigkeit dieses Zusammentreffens auf Nutzerrechnern ist unbekannt. Microsoft dokumentiert jedoch, dass offene Handles ohne passende Löschfreigabe das Löschen verhindern können. Das ist ein reales Betriebssystemverhalten, das der Speicherpfad berücksichtigen muss. [Microsoft: DeleteFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-deletefilew)

Die drei beteiligten Recovery-/Ladefunktionen sind gegenüber dem lokalen 1.6.0-Ausgangscommit strukturell unverändert. Es handelt sich um einen **zusätzlich gefundenen bestehenden Fehler**, nicht um eine nachgewiesene Regression der zuletzt vorgenommenen Notebook-Korrekturen.

Vor Freigabe muss die Konsistenz zwischen SQLite, Recovery und Speicherbestätigung abgesichert werden: Ein bestätigter neuer Stand darf beim nächsten Laden nicht still durch einen älteren Stand ersetzt werden. Bloßes Unterdrücken der Ausnahme oder ein Vergleich unsicherer Dateizeitstempel reicht als Nachweis nicht aus. Die Originalquellen müssen erhalten bleiben; nicht eindeutig auflösbare Konflikte müssen sichtbar werden.

## Ergebnis der sieben ergänzten Testfälle

| Testfall | Ergebnis | Tatsächliche Aussage |
| --- | --- | --- |
| Unicode, Leerzeichen, `#` und `%` im Profilpfad; SQLite und schreibgeschützte Versionsabfrage | Erfolgreich | Echte lokale Dateien unter macOS; keine native Windows-/Linux-Zusage |
| Exklusive SQLite-Sperre mit Recovery und anschließendem erfolgreichem Speichern | Erfolgreich | Die ursprüngliche Datenbank bleibt erhalten; der Recovery-Pfad enthält die neue Änderung |
| Fehler beim Erstellen der Vor-Update-Kopie | Erfolgreich | Die 20 ursprünglichen Zeilen werden nicht gekürzt; neue Bearbeitung bleibt über Recovery erhalten |
| Gleichzeitiger Datenbank-/Recovery-Schreibfehler | Erfolgreich | Kein falscher Erfolg; ursprünglicher gespeicherter Stand bleibt lesbar |
| Gesperrte ältere Recovery-Datei nach erfolgreichem Datenbank-Commit | **Fehlgeschlagen** | Falscher Speichererfolg und Laden des älteren Inhalts; Freigabeblocker |
| Windows-URI mit Laufwerk, Umlauten und Sonderzeichen | Erfolgreich | Nur plattformspezifische Pfadberechnung, kein Windows-I/O |
| Paketdateinamen, exakte Groß-/Kleinschreibung und Quellstand | Erfolgreich | Keine Casefold-Kollisionen, reservierten Windows-Dateinamen, problematischen Endzeichen oder Backslashes; alle Paketbytes stimmen mit den Quellen überein |

Zusätzlich bestehen die vorhandenen Tests aus `test_launch_persistence.py` nach der expliziten UTF-8-Anpassung des Test-Helfers. Der neue Fehler ist ein zusätzlicher Testfall; die früher erfolgreichen 158 Python-Tests und 43 Browser-Dateien hatten diesen Fehler nicht abgedeckt.

Reproduktion:

```text
python tests/review_165_cross_platform.py -v
```

Der Test soll auf dem derzeitigen Stand mit genau dem beschriebenen Recovery-Befund fehlschlagen. Einzelresultate und die Fortsetzungs-Reproduktion stehen in [release-1.6.5/cross-platform-validation-2026-10-28.json](release-1.6.5/cross-platform-validation-2026-10-28.json).

## Weitere Plattformbefunde

- In den geprüften Runtime-Dateien für Notebook und SoundCloud wurden keine fest eingebauten macOS-Installationspfade gefunden.
- Sämtliche benannten relativen Python-Module der obersten Paketebene sind im Archiv mit exakter Groß-/Kleinschreibung vorhanden. Das reduziert das Risiko fehlender Imports auf einem typischerweise case-sensitiven Linux-Dateisystem.
- Der längste relative Archivpfad hat 57 Zeichen. Sehr lange absolute Profil-/Installationspfade bleiben ein gesonderter Windows-Randfall; eine native Prüfung der jeweiligen Pfadlängenkonfiguration wurde nicht durchgeführt.
- Der SoundCloud-Adapter nutzt Ankis mpv-Auflösung und eine Windows-spezifische, zufällige Pipe-Kennung. Die Kennung wurde bereits mit simuliertem Windows-Zweig geprüft; echte Windows-Pipe-Kommunikation, Audioausgabe und Linux-mpv-Verfügbarkeit wurden hier nicht getestet.
- Die Audioänderungen haben keine Notebook-Speicherpfade. Eine tatsächliche SoundCloud-Wiedergabe unter Windows/Linux sowie Qt-Fenster-/Profil-Lebenszyklen sind dennoch separat nativ abzunehmen.
- SQLite-Verbindungen des Hintergrundschreibers werden im jeweiligen Worker erzeugt und geschlossen. Die Pfade bleiben an das ursprüngliche Profil gebunden. Im untersuchten Code wird kein `synchronous=OFF` eingeschaltet.

Es wurde kein weiterer konkreter Windows-/Linux-spezifischer Inhaltsverlust durch die neuen Historien- oder Toggle-Schutzprüfungen gefunden. Das beseitigt weder den oben reproduzierten Fehler noch ersetzt es native Tests.

## Was für eine Freigabe noch fehlt

1. Den Recovery-Konsistenzfehler gezielt beheben und den neuen Regressionstest einschließlich Neustart und fortgesetzter Bearbeitung erfolgreich machen.
2. Die Speicherfehler zwischen allen relevanten Schreib-/Commit-/Bereinigungsschritten prüfen. Alte Kopien dürfen dabei nicht zur Vermeidung einer Fehlermeldung vorschnell gelöscht werden.
3. Das danach neu gebaute Paket mit einer Kopie einer bestehenden Datenbank unter echtem Windows und Linux testen: Bearbeiten, schließen, neu starten, Profil wechseln, Lade-/Schreibfehler auslösen und Inhalt vergleichen. SoundCloud separat prüfen.

Das bisherige Paket ist durch diesen Befund **nicht für die Veröffentlichung freigegeben**. Es wurden keine echten Nutzerprofile verändert und nichts auf GitHub oder AnkiWeb veröffentlicht.

Technische Referenzen: [Python: Betriebssystemoperationen und deren Fehler](https://docs.python.org/3.13/library/os.html), [pathlib: reine Pfade gegenüber echten Dateizugriffen](https://docs.python.org/3.13/library/pathlib.html). Für Netzwerk-Dateisysteme gelten zusätzliche, hier nicht praktisch geprüfte Einschränkungen bei Sperren und Schreibbestätigungen. [SQLite: Netzwerk-Dateisysteme](https://www.sqlite.org/useovernet.html)
