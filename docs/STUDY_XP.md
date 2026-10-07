# Lern-XP: Abrechnung nach der Session

Lern-XP werden beim Verlassen des Reviewers und beim Profilstart abgeglichen.
Die zweimalige Session-Summary-Injektion ist ebenfalls ein sicherer Wiederholungs-
versuch. Sie zeigt den tatsächlich verbuchten Session-Anteil, keine Schätzung.
Das bestehende Layout bleibt unverändert.

Die Regeln bleiben 10 XP pro Minute, maximal 45 Sekunden je Bewertung, nur
revlog-Einträge mit ease > 0. Negative Zeiten zählen nicht. Bruchteile werden
zwischen Sessions weitergeführt. Levelkurve, Streak und Challenge-Belohnungen
bleiben unverändert.

`study_xp_ledger` speichert Startzeit und bereits vergütete ganze Lern-XP zusammen
mit XP/Level in derselben Collection-Konfiguration. Bei der ersten Abrechnung
beginnt der Zeitraum am alten `last_time_xp_check_day` inklusive Anki-Rollover:
Das ist der erste noch nicht abgeschlossene Lerntag. Frühere Tage werden nicht
nochmals vergütet. Einträge ab dieser Grenze werden aggregiert; dadurch sind auch
später eintreffende ältere Review-IDs innerhalb des Zeitraums berücksichtigt.
Es gibt keine zusätzliche Tabelle, keinen Netzwerkaufruf und keine Speicherung
nach jeder einzelnen Karte.

Nur die positive Differenz zum bezahlten Höchststand wird gutgeschrieben. Undo
zieht keine bereits vergebenen XP ab; bei Wiederherstellung derselben Lernzeit
werden sie nicht erneut vergeben. Nach einer Löschung von Reviews muss die
verbliebene Lernzeit erst wieder den vergüteten Höchststand überschreiten.

Bei fehlgeschlagener Abfrage oder Config-Speicherung bleiben XP und Abrechnungs-
stand unverändert. Der nächste Abgleich versucht es erneut. Das vorhandene
atomare JSON-Backup bleibt erhalten. Bereits durch ältere Versionen irrtümlich
abgeschlossene Zeiträume lassen sich nicht zuverlässig automatisch reparieren.
Ein Downgrade auf die alte Tagesabrechnung ist nicht vorgesehen. Konflikte bei
Collection-Synchronisation auf mehreren gleichzeitig aktiven Geräten werden
weiterhin durch Ankis bestehende Config-Synchronisation bestimmt; dies ist keine
neue geräteübergreifende Konfliktauflösung.

Prüfung: 82 Python-Tests bestanden, darunter 12 neue Regressionstests mit isolierter
SQLite-Revlog-Datenbank und den tatsächlichen Methoden. Geprüft wurden Neustart,
Doppelaufrufe, Tagesgrenze, Altbestände, Rundungsreste, Zeitbegrenzung, unmittelbarer
Levelaufstieg bei fünf fehlenden XP, Datenbank-/Speicherfehler, verspätete Reviews,
Undo und die tatsächlich gerenderte Session-Anzeige. Python-Syntaxprüfung bestanden.
Eine interaktive Anki-Abnahme unter Windows/macOS/Linux steht noch aus.
