# Git-Push-Prüfung – Synapse 1.6.5

Stand: 29.10.2026. Ergebnis: Der lokale Änderungsstand ist nach der beschriebenen Bereinigung aus Sicht dieser Prüfung zum Commit und Push geeignet. Es wurde nichts committed oder gepusht.

- GitHub Desktop zeigt das Repository Synapse auf Branch `update-1.6.0`. Fetch erfolgreich; HEAD und origin/update-1.6.0 sind gleichauf (0/0). Der Basis-Dateibaum stimmt mit origin/main überein.
- Alle 396 Dateien des geprüften 1.6.5-Pakets sind im Git-Kandidatenbestand und bytegleich mit den lokalen Quellen, einschließlich neuer Runtime-Module und Stylesheets. Paket SHA-256: `7038284cf20beb165c6b26fb3cca52189c2125d046e735408886845dc9a6d2ea`.
- Alle 118 Python-Quelldateien des Kandidatenbestands lassen sich syntaktisch kompilieren. Paket-CRC und `git diff --check` bestanden. Erneute Release-Sicherheitstests: 3/3; SoundCloud-URL-Prüfungen: 4/4.
- Lokaler Muster-Scan über sämtliche getrackten und nicht ignorierten neuen Dateien: keine echten Schlüssel, Tokens, privaten Schlüssel oder Zugangsdaten gefunden. Drei Treffer wurden manuell als Testwerte geprüft (`test-key` und eine absichtlich abgelehnte Test-URL). Keine Notebook-Datenbank oder Recovery-Inhalte im Commit-Bestand gefunden. Ein Muster-Scan garantiert nicht, jede denkbare Geheimnisform zu erkennen.
- Keine bereits getrackten Dateien gefunden, die von den aktuellen Ignore-Regeln erfasst werden. Keine ungesendeten älteren Commits auf dem aktuellen Branch.
- `.gitignore` ergänzt: output/, Add-on-Nutzerdaten, SQLite-Dateien und Journale, feste Vor-Update-Kopien, Recovery-Temporärdateien, lokale Umgebungsdateien, private Schlüsselformate und Tooling-Verzeichnisse. An 14 Beispielpfaden geprüft. Die Originaldateien bleiben lokal erhalten.
- Zwei neu erzeugte Prüfprotokolle anonymisiert: lokaler Benutzer-/Workspacepfad durch `<workspace>` ersetzt. Ihre JSON-Struktur bleibt gültig. Windows-Pfade im Testcode sind synthetische Testfälle.
- Nach der Bereinigung ausschließlich `.gitignore` und Dokumentation geändert; kein Produktcode und kein Notebook-Inhalt verändert. Paket-Neubau dafür nicht erforderlich.

Die vorherigen Laufzeitprüfungen (167 Python-Tests, 43 Browser-Testdateien, sieben Plattform-Fehlersimulationen, native Notebook-/SoundCloud-Tests unter macOS) sind in den bestehenden Release-Berichten dokumentiert. Native Windows-/Linux-Läufe wurden nicht durchgeführt. Der erfolgreiche eigene macOS-/Anki-Test des Nutzers ergänzt die Abnahme. Die Freigabe zum Push ist keine Garantie vollständiger Bugfreiheit und veröffentlicht für sich noch kein Anki-Update.

Für Veröffentlichung über den Hauptbranch: Änderungen vollständig committen, Branch pushen und anschließend in main übernehmen. Der vorhandene Branchname `update-1.6.0` ändert die in Manifest und Code hinterlegte Version 1.6.5 nicht. Eine Umbenennung wurde nicht vorgenommen.
