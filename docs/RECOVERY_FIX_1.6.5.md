# Synapse 1.6.5 – Recovery-Konsistenz behoben und Paket neu gebaut

> **Paketstand 29.10.2026:** Der Changelog wurde vervollständigt und das Paket erneut gebaut. Die unten dokumentierte Prüfsumme gehört zum damaligen Testpaket. Alle Produktdateien außer `changelog.py` sind im aktuellen Paket bytegleich. Aktuelle Prüfsumme und Prüfung: [changelog-package-validation-2026-10-29.json](release-1.6.5/changelog-package-validation-2026-10-29.json).

Stand: **28.10.2026**. Der zuvor reproduzierte Recovery-Freigabeblocker ist behoben und erneut geprüft. Das neue Paket ersetzt den gesperrten Kandidaten; es wurde nichts veröffentlicht oder in ein echtes Nutzerprofil installiert.

**Paket:** [Synapse-1.6.5.ankiaddon](../output/releases/Synapse-1.6.5.ankiaddon)

- Größe: **35.168.288 Bytes**, 396 enthaltene Dateien.
- SHA-256: `4d97a19787d3998b20b5cdee29bf11ecbab35cd768cb40e401a03a58ab1f95ae`
- Der alte, gesperrte Kandidat wurde unter `output/releases/archive/Synapse-1.6.5-before-recovery-fix.ankiaddon` unverändert aufbewahrt. **Diesen alten Kandidaten nicht verwenden.**

## Was die Korrektur macht

Neue Recovery-Dateien erhalten zusätzlich zum bisherigen Format eine zufällige `recovery_id`. Damit unterscheidet sich auch eine neue, absichtliche Wiederherstellung desselben Inhalts von einer früher abgelösten Recovery-Version. Bisherige Recovery-Dateien ohne diese Kennung bleiben lesbar; sie werden beim Lesen nicht umgeschrieben.

Wenn SQLite einen neuen Snapshot speichert, wird die Identität der dadurch abgelösten Recovery-Datei **in derselben Transaktion** festgehalten. Dazu dient eine zusätzliche kleine Tabelle `snapshot_recovery_retired`. Sie enthält Tabellenbezeichnungen und SHA-256-Fingerabdrücke, keine weiteren Kopien der Notizinhalte. Ihre Anlage und der neue Snapshot werden gemeinsam bestätigt oder gemeinsam zurückgerollt.

Die vorhandenen Tabellen für Notizen, Aufgaben und PDFs werden nicht umgebaut und bestehende Inhaltszeilen nicht nachträglich umgeschrieben. Die normale Snapshot-Aufbewahrung bleibt bei 20 Zeilen; die festen Vor-Update-Kopien bleiben erhalten.

Das anschließende Entfernen der alten Recovery-Datei ist nur noch ein Aufräumversuch. Ist sie unter Windows gesperrt, darf sie unverändert liegen bleiben. Beim nächsten Laden erkennt SQLite anhand des Fingerabdrucks, dass genau diese Recovery-Version bereits abgelöst wurde, und der bestätigte neuere Stand wird verwendet. Eine neuere unabhängige Recovery-Datei wird beim Aufräumen nicht entfernt. Es gibt keinen Vergleich von Datei-Zeitstempeln und kein Erraten des jüngeren Inhalts.

Wenn Datenbank oder Recovery nicht ausreichend lesbar sind, wird nicht still eine möglicherweise ältere Quelle geöffnet. Der Editor zeigt die bestehende Ladefehlerseite; die Quelldateien bleiben erhalten und der unabhängige Recovery-Export bleibt verfügbar, soweit die jeweilige Quelle lesbar ist. Eine exklusive Datenbanksperre kann deshalb vorübergehend eine Fehlermeldung verursachen, bis die Quelle wieder überprüfbar ist. Das ist eine beabsichtigte Absicherung gegen falsches Laden.

Bei einem echten Prozessabbruch kann SQLite ein offenes Rollback-Journal hinterlassen. Die Prüfung liest normalerweise über eine schreibgeschützte Verbindung. Nur wenn SQLite zur eigenen Journal-Wiederherstellung Schreibzugriff benötigt, wird eine Verbindung zur **bereits existierenden** Datenbank mit `mode=rw` versucht. SQLite führt die Wiederherstellung selbst durch. Die Anwendung löscht keine Journaldatei und schreibt keine Notizdaten manuell zurück. Kann SQLite die Quelle nicht sicher öffnen, bleibt der Editor auf der Fehlerseite.

## Gezielte Fehler- und Absturzprüfungen

Die neun neuen Tests in `tests/test_recovery_consistency.py` sind Teil der vollständigen Python-Suite. Sie umfassen mehrere Unterfälle:

- Dauerhaft gesperrte alte Recovery-Datei; 31 erfolgreiche Speichervorgänge mit jeweils frisch erzeugtem Loader; der bestätigte neue Inhalt bleibt erhalten, während die gesperrte Datei bytegleich bleibt.
- Normale Kürzung auf 20 SQLite-Snapshots, ohne dass eine alte Recovery wieder Vorrang erhält. Die Vor-Update-Kopien enthalten weiterhin den ursprünglichen Inhalt.
- Neue Recovery desselben Inhalts: Ihre neue Identität wird nicht fälschlich als bereits abgelöst behandelt.
- Alte Array-, Single-Page- und Multi-Page-Formate ohne Recovery-ID; im normalen Lesevorgang bleiben die Datenbank und Recovery-Datei bytegleich.
- Unlesbare Recovery, nicht prüfbarer Datenbankpfad und gesperrte Datenbank: sichtbarer Ladefehler, keine Ersetzung durch einen geratenen Stand; unabhängige Versionsquellen bleiben exportierbar.
- Fehlende Datenbank mit vorhandener gültiger Recovery: Laden ohne Erstellen einer neuen Datenbank.
- Neuere Recovery zwischen Speichern und Aufräumen: Die neue Datei wird nicht entfernt oder überschrieben.
- Getrennte Identitäten für Notebook, Aufgaben und PDFs.
- **Echte abrupt beendete Python-Kindprozesse** direkt vor dem Commit, vor dem Commit mit einer großen Notiz von etwa 4 MiB und direkt nach dem Commit vor der Bereinigung. Beim erneuten Öffnen wird der jeweils konsistente Stand geladen. Die abgebrochene neue Transaktion verdrängt keine zuvor bestätigte Recovery; eine bestätigte neue Transaktion lässt sich nicht durch die alte Datei überdecken.
- Simulierter Commit-Fehler mit funktionierendem Recovery-Pfad beziehungsweise ebenfalls gesperrter Recovery-Datei. Im ersten Fall wird die neue Recovery verwendet; im zweiten wird kein Erfolg gemeldet. Die ursprünglichen SQLite-Zeilen und die vorherige Recovery bleiben erhalten. Die nicht bestätigte Ablösung wird zurückgerollt.

Die Tests arbeiten ausschließlich mit synthetischen Inhalten in temporären Verzeichnissen. Die Prozessabbrüche beenden nur eigens gestartete Testprozesse, niemals Anki oder einen Nutzerprozess.

## Abschlussprüfung

| Prüfung | Ergebnis |
| --- | --- |
| Vollständige Python-Suite einschließlich der neun neuen Recovery-Tests | **167/167 erfolgreich** |
| Browser-Testdateien | **43/43 erfolgreich** |
| Zusätzliche Windows-/Linux-bezogene Fehler- und Pfadtests | **7/7 erfolgreich**, einschließlich des zuvor fehlgeschlagenen Recovery-Falls |
| Zusätzlicher Versions-Export-Test bei beschädigter Datenbank | Erfolgreich |
| Echte Anki-/Qt-Notebook-Prüfung aus dem neuen Paket | Erfolgreich: bestehende synthetische Datenbank, Ladefehler/Export, echte „Gespeichert“-Bestätigung bei gesperrter Altdatei, Schließen/Öffnen, Originalblöcke und Vor-Update-Kopien erhalten |
| SoundCloud-Live-Test aus dem neuen Paket | Erfolgreich: beide Play-Buttons, Fortschritt, Pause, Seek, Lautstärke, Playlists, Neuladen, Ausblenden, Moduswechsel und unveränderte gespeicherte Testdaten |
| Übersetzungen | 2049 auditierte Einträge; keine fehlenden Übersetzungen oder Platzhalterfehler |
| Paketintegrität, Version und Übereinstimmung mit Quellen | Erfolgreich |

Gegenüber dem vorherigen Paket haben sich ausschließlich `notebook_sidebar.py` und `changelog.py` geändert. Die SoundCloud-Implementierung, Themes und übrigen Produktdateien bleiben bytegleich. Version 1.6.5 und 25 Changelog-Einträge sind enthalten. Tests, Berichte, Bildentwürfe, Datenbanken und Recovery-Dateien sind weiterhin vom Paket ausgeschlossen. Von den Browser-Tests erzeugte Dokumentationsbilder wurden auf ihre vorherigen Bytes zurückgesetzt.

Prüfbelege, Paketdatei-Prüfsummen und vollständige Testausgaben: [recovery-fix-validation-2026-10-28.json](release-1.6.5/recovery-fix-validation-2026-10-28.json).

## Reichweite und Verwendung

Die echte native Ausführung erfolgte unter **macOS/ARM64 mit Anki 26.9.3**. Windows-Dateisperren und weitere Speicherfehler wurden gezielt simuliert. **Es wurden weiterhin keine nativen Windows- oder Linux-Läufe durchgeführt.** Die erfolgreichen Simulationen sind keine Behauptung einer vollständigen nativen Plattformfreigabe.

Die Tabellenablösung ist additiv und wird erst bei einem entsprechenden Speichervorgang benötigt. Ältere Add-on-Versionen kennen diese Zusatzinformation nicht; ein Downgrade oder gleichzeitiger Zugriff verschiedener Add-on-Versionen auf dasselbe Profil ist nicht als sichere Rückkehrstrategie geprüft. Für eine Rückkehr den vollständigen gesicherten Profilstand verwenden, nicht nur einzelne Speicherdateien mischen.

Es wurden keine echten Notebook-Inhalte oder Nutzerprofile geöffnet, geändert oder migriert. Eine vollständige externe Profilkopie vor dem produktiven Update bleibt erforderlich. Das Paket ist lokal vorbereitet; Installation zum eigenen Abnahmetest und Veröffentlichung wurden nicht automatisch durchgeführt. Eine universelle Garantie gegen sämtliche Bugs, externe Dateiveränderungen oder Hardwaredefekte wird nicht behauptet.
