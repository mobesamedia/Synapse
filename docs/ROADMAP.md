# Mindmap und Roadmap

Die Desktop-Version enthält eine gemeinsame Werkzeugleiste für **Mindmap** und
**Roadmap**, mit vergrößerter Ansicht im Anki-Fenster und Vollbild. Die bestehende
Mindmap bleibt unter ihrer bisherigen HTML-Adresse und verwendet weiterhin ihre
bisherige Speicherung. Notebook, To-Do und PDF besitzen ebenfalls einen eigenen Dialog zur Tab-Sichtbarkeit.

## Bedienung

- In der zweiten Leiste: Roadmap auswählen, neu erstellen und das Verwaltungsmenü öffnen.
- Im Menü: umbenennen, duplizieren, löschen sowie JSON importieren/exportieren.
- `+`: Formen anklicken oder auf die Fläche ziehen; außerdem freie Texte und Pfeile.
- Automatik (`A`, standardmäßig aktiv): Ziehen auf freier Fläche verschiebt die Ansicht;
  Formen und Pfeile lassen sich direkt auswählen und verschieben. Klick auf freie Fläche
  hebt die Auswahl auf. Umschalt ermöglicht einen Auswahlrahmen.
- Auswahlwerkzeug (`V`): verschieben; mit Umschalt mehrere Objekte auswählen oder
  einen Auswahlrahmen aufziehen. Vier Eckgriffe skalieren, der runde Griff darüber dreht.
  Umschalt rastet Drehungen in 15-Grad-Schritten ein und erhält beim Skalieren die Proportionen.
- Handwerkzeug (`H`) oder gehaltene Leertaste: Arbeitsfläche verschieben.
- Zoom über Mausrad oder `+`/`−`; Gesamtansicht passt den Zoom an, Zentrieren erhält ihn.
- Blaue Seitenpunkte erzeugen Pfeile. Beim Ziehen werden auch die Anschlusspunkte
  anderer Formen sichtbar. Die Endpunkte lassen sich später neu andocken oder frei platzieren.
- Schwebendes Menü: Form ersetzen, Text, Rand/Füllung und zuletzt verwendete Stile;
  weitere Aktionen für Ebenen, Kopieren, Duplizieren und Löschen.
- Doppelklick oder `T`: Text bearbeiten. Formatierung gilt für die Textauswahl;
  ohne Textauswahl stellt die Schriftgrößenangabe die bevorzugte Objektgröße ein.
- Pfeile haben vier Verlaufsarten, drei Spitzenformen bzw. keine Spitze, Farbe und
  Linienmuster. Beschriftungen lassen sich über das Stilmenü oder Doppelklick bearbeiten.
- Strg/Cmd+Z und Strg+Y bzw. Cmd+Umschalt+Z: Undo/Redo. Strg/Cmd+C/X/V: Objekte
  kopieren/ausschneiden/einfügen. Während Texteingabe gelten die normalen Textbefehle.
- Löschen einer verbundenen Form lässt den Pfeil an derselben Position frei enden.

## Speicherung und Lebenszyklus

Neue Datei zur Laufzeit: `<Anki-Profil>/SynapsePro_Data/roadmaps.sqlite3`.
Keine Übertragung an Supabase oder einen anderen Dienst; keine automatische Anki-Synchronisation.
Zum Übertragen auf einen anderen Rechner JSON exportieren und importieren.

Jede Roadmap ist ein JSON-Dokument mit stabilen Objekt-IDs und einer eigenen
SQLite-Zeile. Nur geänderte Dokumente werden geschrieben; Änderungen, Löschungen
und die aktive Auswahl werden in derselben Transaktion gespeichert. Die gesamte
Sammlung liegt derzeit als Daten im Arbeitsspeicher, dargestellt wird ausschließlich
die aktive Roadmap. Es gibt keine zweite dauerhaft parallel laufende Webansicht.

Speichern erfolgt nach einer kurzen Eingabepause und vor Werkzeugwechsel bzw.
Entladen. Die Python-Brücke bestätigt Schreibvorgänge. Fehler erhalten die offene
Ansicht; Laden ungültiger Daten führt nicht zum Überschreiben durch eine leere
Sammlung. Seiten-Generationen und Revisionsnummern verhindern, dass verspätete
Callbacks einen neueren Stand überschreiben. Automatisches Speichern beendet
keine laufende Texteingabe. Während des finalen Speicherns ist die Ansicht kurz gesperrt.

Die Mindmap-Wiederherstellung wird beim Zurückwechseln frisch eingelesen. Das ist
insbesondere wichtig, wenn deren Browser-Speicher voll war und nur die zusätzliche
Wiederherstellungsdatei geschrieben werden konnte.

SQLite schützt durch Transaktionen vor unvollständigen normalen Schreibvorgängen.
Das ersetzt keine externe Datensicherung. Nicht bestätigte letzte Eingaben können
bei einem abrupten Prozessabbruch verloren gehen. Export ist auch bei einer
fehlgeschlagenen normalen Speicherung verfügbar.

## Darstellung und Grenzen

- Formen, Texte und Verbindungen werden als Daten gespeichert; kein riesiges Canvas-Bild.
- SVG für die Darstellung; separater HTML-Eingabeeditor für formatierte Texte.
- Formen und Pfeile werden wiederverwendet, solange sich ihr Inhalt bzw. Verlauf
  nicht ändert. Ereignisse werden über Animationsframes gebündelt.
- Undo ist sitzungsbezogen, auf 50 Stände und ungefähr 8 Millionen JSON-Zeichen begrenzt
  (ein einzelner großer Stand bleibt möglich). Beim Dokumentwechsel beginnt die Historie neu.
- Objekt-Zwischenablage ist intern und funktioniert zwischen Roadmaps derselben geöffneten
  Editor-Sitzung. Es gibt kein systemweites Dateiformat für kopierte Diagrammobjekte.
- Text erhält einen konturabhängigen Innenbereich. Die Darstellungsgröße kann bis
  auf 8 px sinken; überlaufende Anzeige wird gekürzt. Originaltext und bevorzugte
  Schriftgrößen bleiben erhalten. Es gibt keinen zeilenweisen Textfluss entlang
  gekrümmter Konturen; Kreis, Raute und Dreieck nutzen sichere innere Textrechtecke.
- Pfeilverläufe berücksichtigen Anschlussrichtungen und weichen den gepolsterten
  Begrenzungsrahmen der Objekte aus. Drehungen werden konservativ als größere
  Begrenzungsrahmen behandelt. Bei überlappenden/eingeschlossenen Objekten kann
  eine kollisionsfreie Verbindung unmöglich sein.
- Nativer JSON-Import maximal 64 MB einschließlich Bilder; Browser-Vorschau ohne
  Bildimport maximal 20 MB. Beide Wege prüfen die Struktur und bereinigen Text-Markup.
- Ohne Anki-Host dient die HTML-Seite nur als Vorschau; dauerhaftes Sichern dort über Export.

## Prüfungen (25.09.2026)

- Python: 96 Tests bestanden, darunter 14 neue Tests für Roadmap-Speicherung und
  die asynchrone Host-Brücke (Transaktionen, Neustart, Fehler, Profiltrennung,
  veraltete Antworten und Werkzeugwechsel).
- `tests/web_roadmap.cjs`: reale Browserinteraktionen für Formen, Text, Autosave-Snapshot,
  Undo/Redo, interne Zwischenablage, angedockte Pfeile, vier Verläufe, Rotation,
  Größenänderung, mehrere Dokumente, schmale Ansicht und dunkles Design.
- `tests/web_roadmap_scale.cjs`: 100/500/1000 Formen mit jeweils fast ebenso vielen
  Pfeilen, bereinigter Import und Teilformatierung einschließlich Schriftgröße.
- `tests/web_mindmap_tutorial.cjs`: bestehende Mindmap-Prüfungen inklusive Tutorial
  und Isolation der Übungsdaten bestanden.
- Syntax: `python3 -m py_compile roadmap_store.py mindmap_sidebar.py` und `node --check`.

Lokale synthetische Chrome-Messung nach Wiederverwendung unveränderter Pfeile:

| Formen / Pfeile | JSON | Laden | Ein Zoom-Schritt |
|---|---:|---:|---:|
| 100 / 99 | 36 KB | 100 ms | 7 ms |
| 500 / 499 | 183 KB | 140 ms | 13 ms |
| 1000 / 999 | 368 KB | 241 ms | 9 ms |

Einzelmessungen auf diesem Mac, keine garantierten Grenzen für Ankis QtWebEngine.
Echte interaktive Abnahme unter Anki/macOS und Windows ist noch offen:
Erstellen → Text/Verbindungen ändern → Mindmap wechseln → zurück → Sidebar schließen
→ Profilneustart; außerdem Fenster/Vollbild und Export-/Importdialoge prüfen.
Die aktive Installation und echte Anki-Profile wurden für diese Arbeit nicht verändert.

## Korrektur: Reiter blockiert / Absturz beim Schließen (25.09.2026)

Nach einer Rückmeldung aus Anki wurde die native Qt-Anbindung zusätzlich geprüft.
Die vorherigen Chrome- und isolierten Python-Tests hatten diesen Fehler nicht erfasst:

- Die bisherigen `mindmap://`-Steueraufrufe erzeugten in Qt auch
  `loadFinished(False)`. Das setzte eine schon vollständig geladene Seite auf
  „nicht bereit“ und blockierte den Werkzeugwechsel. Nicht durch eine Nutzeraktion
  ausgelöste Aufrufe konnten zudem blockiert werden (unter anderem Autosave).
- Die Freigabe des Browserprofils war über einen Timer geplant, ohne die tatsächliche
  Zerstörung der zugehörigen Seite abzuwarten. Die vorliegenden macOS-Absturzberichte
  zeigten `QWebEngineView::hideEvent` beim Entfernen des Docks.
- Ein ausstehender Speichervorgang beim Ausblenden konnte eine inzwischen erneut
  geöffnete Webansicht nachträglich zerstören.

Steuerung und Autosave verwenden jetzt `QWebChannel` über `host_bridge.js`, ohne
Seitennavigation. Fehlgeschlagene Legacy-Steueraufrufe setzen den Bereitschaftsstatus
nicht zurück. Die Anwendung hält das Browserprofil bis zum `destroyed`-Signal der
Seite; das Entfernen der Sidebar erfolgt außerhalb des JavaScript-Ergebnis-Callbacks.
Schnelles Wiederöffnen erhält die vorhandene Webansicht. Echte Dokumentwechsel
setzen den Bereitschaftsstatus weiterhin explizit zurück.

Neue Prüfung: `tests/qt_roadmap_lifecycle.py` verwendet die tatsächlichen
QtWebEngine-Klassen und den tatsächlichen Projektcode, mit einer minimalen Anki-Hülle
und ausschließlich einem temporären Testprofil. Bestanden mit Qt 6.9 sowie mit den
Qt-6.11-Bibliotheken aus der installierten `/Applications/Anki.app`:

- Reiterwechsel mit echten Qt-Mausereignissen, ohne fehlgeschlagene Navigationen;
- Autosave ohne Nutzeraktion und ohne Seitennavigation;
- zehn schnelle Ausblenden-/Einblenden-Zyklen;
- dreimal vollständiges Schließen und Wiederöffnen mit erhaltenen Daten;
- geprüfte Zerstörungsreihenfolge: Seite vor Browserprofil;
- acht schnelle Klicks pro Wechsel während laufender Speicherung;
- dreimal Entfernen des sichtbaren Docks und erneutes Erstellen, ohne verbliebene
  eigene Browserprofile oder Warnung zur vorzeitigen Profilzerstörung.

Zusätzlich: 101 Python-Tests, bestehende Mindmap-/Tutorial-Browserprüfungen und
Syntaxprüfungen bestanden. Die laufende Anki-Instanz, aktive Add-on-Installation und
echte Nutzerprofile wurden dabei nicht verändert. Eine Abnahme in der vollständigen
Anki-Anwendung bleibt von diesem isolierten nativen Integrationstest zu unterscheiden.

## Gemeinsame Oberfläche (25.09.2026)

Mindmap und Roadmap verwenden `workspace_ui.css` und `workspace_ui.js` für dieselben
Buttonmaße, Positionen, dünnen SVG-Symbole, Dokumentauswahl und Menügestaltung.
Undo/Redo behalten die Mindmap-Pfeile. Zoom und Gesamtansicht stehen unten links,
Undo/Redo darüber und Zentrieren unten rechts. Roadmap-Werkzeuge bleiben oben links.
Der gepunktete Hintergrund nutzt dieselbe Berechnung für Zoom, Verschieben und Farbe.
Auch die Mindmap zeigt nun den Speicherstatus; fehlgeschlagene Schreibvorgänge werden
als „Nicht gespeichert“ bzw. mit der passenden Übersetzung angezeigt.

`tests/web_workspace_ui.cjs` prüft tatsächliche Buttonmaße bei 1100 und 390 Pixeln,
den Hintergrund in beiden Farbschemata, automatische und manuelle Interaktion,
Dokumentauswahl sowie erfolgreiche und fehlgeschlagene Mindmap-Speicherung.

## Bilder, Sprache, Formatierung und Reiter (25.09.2026)

- Die Roadmap verwendet jetzt dieselbe Spracheinstellung wie Mindmap und Notebook.
  `workspace_translations.json` enthält alle acht Übersetzungen zusätzlich zu Englisch.
  Namen und Inhalte bestehender Dokumente werden nicht automatisch übersetzt.
- Beide Ansichten folgen Ankis Dark Mode, auch wenn macOS einen anderen Modus nutzt.
  Ein laufender Farbwechsel aktualisiert die Ansicht ohne Reload und erhält Undo.
- Die Zahnräder öffnen eigene kleine Arbeitsbereich-Dialoge für Mindmap/Roadmap
  beziehungsweise Notebook/To-Do/PDF. Tabs lassen sich getrennt anzeigen.
  Mindestens einer bleibt verfügbar; Ausblenden löscht keine Dokumente.
- Mindmap: Rechtsklick auf einen Knoten bietet Fett, Kursiv, Schriftgröße, Textfarbe,
  voreingestellte helle Füllfarben sowie Bild hinzufügen/entfernen. Formatierung gilt
  für den gesamten Knotentext. Mit gesetzter heller Füllung bleibt die Schrift schwarz;
  Standard setzt die Formatierung zurück. Lernmodus verbirgt auch das Knotenbild.
- Roadmap: „+ → Bild hinzufügen“ erzeugt ein skalier- und drehbares Bildobjekt.
- Runde Anschlusspunkte erzeugen neue Pfeile; bestehende Enden werden über versetzte
  eckige Griffe bewegt. Auch bei ausgewähltem Pfeil bleiben die Anschlusspunkte seiner
  Formen zum Erzeugen weiterer Pfeile verfügbar. Ein freies Ende, das nach rechts
  gezogen wird, erhält einen nach rechts gerichteten letzten Abschnitt.
- Gerade und gebogene Verläufe bleiben erhalten, wenn sie frei sind. Bei Hindernissen
  wird eine ausweichende Verbindung gewählt. Die Berechnung wird pro Objektgeometrie
  zwischengespeichert und beim reinen Zoomen nicht wiederholt.

### Ablage und Grenzen für Bilder

Bilder liegen unter `<Anki-Profil>/SynapsePro_Data/workspace_images/`. Sie sind kein
Teil des Add-on-Codes und werden bei normalen Add-on-Updates nicht ersetzt. Im
Dokument, in der Browser-Speicherung und in Undo stehen nur kleine Bildverweise.
Dateinamen enthalten einen Inhalts-Hash; identische verarbeitete Bilder teilen sich
somit eine Datei. Neue Dateien und Exporte werden zunächst vollständig geschrieben
und anschließend atomar umbenannt.

- Eingabe: PNG, JPEG oder WebP, maximal 20 MB und 24 Megapixel pro Quelldatei.
- Ausgabe: höchstens 1.600 Pixel Kantenlänge und 1 MB; kleine Bilder werden nicht
  hochskaliert. Transparenz bleibt erhalten. Metadaten werden beim Neukodieren entfernt.
- Pro Dokument: maximal 40 Bilder und insgesamt 24 Megapixel über alle Bildobjekte.
  Letzteres entspricht bis zu etwa 96 MB reinen RGBA-Pixeln, zusätzlich zum Speicher
  von Qt/Chromium, Dokumenten und anderen Add-on-Funktionen. Eine Absturzfreiheit auf
  beliebiger Hardware wird dadurch nicht garantiert.
- Export enthält die verwendeten Bilder im JSON-Paket. Import prüft Namen, Hashes,
  Dateigrößen, Bildabmessungen und dekodierbare Bilddaten. Alte JSON-Dateien ohne
  Bilder bleiben importierbar. Vorschau im gewöhnlichen Browser bietet keine
  persistente Bildverwaltung; die Bildfunktion wird in Anki verwendet.
- Bilddateien werden beim Entfernen eines Objekts nicht automatisch gelöscht, damit
  Undo und Wiederherstellung keine fehlenden Bilder verursachen. Der gesamte Bildordner
  kann deshalb über längere Nutzung wachsen, auch wenn einzelne Dokumente begrenzt sind.

Mindmaps bleiben in `<Anki-Profil>/mindmap_web_data/` und werden zusätzlich nach
`<Anki-Profil>/mindmap_recovery.json` gespiegelt. Roadmaps liegen weiterhin in
`<Anki-Profil>/SynapsePro_Data/roadmaps.sqlite3`. Diese Ablage synchronisiert nicht
über AnkiWeb. Für Sicherungen vollständige JSON-Exporte inklusive Bildern oder eine
Sicherung der genannten Profildaten verwenden; eine reine Sammlungssicherung allein
ist keine Sicherung dieser Add-on-Dateien.

### Ergänzende Prüfungen

- `tests/test_workspace.py`: vollständiger Sprachkatalog, begrenzte Bildverweise,
  Notebook-Zahnrad in allen drei Ansichten.
- `tests/qt_workspace_assets.py`: echte Qt-Bildverarbeitung, Verkleinerung ohne
  Hochskalieren, Transparenz, Deduplizierung, Export/Import in ein anderes temporäres
  Profil sowie Ablehnung beschädigter Daten, ungültiger Pfade und überschrittener Limits.
- `tests/web_workspace_features.cjs`: alle neun Sprachen, Reiterauswahl, explizit heller
  Anki-Modus bei dunklem Systemmodus, Knotenformatierung, Füllung, Zoom und Bildbedienung.
- `tests/workspace_routing.cjs`: 16 Anschluss-/Zielkombinationen sowie eine versperrte
  Verbindung; `tests/web_roadmap_ports.cjs`: drei Pfeile aus demselben Anschluss,
  getrennte Griffe, unveränderte alte Endpunkte und korrekte Endrichtung.
- Der native Qt-Lebenszyklustest prüft nun zusätzlich beide vollständigen Bildwege,
  tatsächliche Bilddarstellung, Reiter deaktivieren/aktivieren und Live-Dark-Mode.
- Synthetischer Browserlauf mit 1.000 Formen und 999 Pfeilen: etwa 574 ms Laden,
  4 ms für den gemessenen Zoom-Schritt. Einzelmessung, keine Zusage für andere Geräte.

### Manuelle Abnahme in Anki

1. Deutsch/Englisch und eine weitere Sprache wählen; Roadmap-Palette, Stilmenüs,
   Speicheranzeige, Tooltips und Einstellungen prüfen.
2. Dark Mode bei geöffneter Mindmap und Roadmap umschalten, inklusive gegenüber
   macOS abweichender Einstellung. Texte und helle Knotenfüllungen müssen lesbar bleiben.
3. Mehrere Pfeile aus demselben runden Punkt ziehen. Danach ausschließlich über
   die eckigen Griffe vorhandene Enden versetzen.
4. Vom linken Anschluss nach rechts ziehen; weitere Boxen in den Weg stellen,
   anschließend verschieben und drehen. Überlappende Boxen zusätzlich ausprobieren.
5. Bilder in Roadmap und Mindmap hinzufügen; Roadmap-Bild skalieren/drehen/duplizieren,
   Knotenbild entfernen, jeweils Undo/Redo prüfen. Auch PNG-Transparenz testen.
6. In der Mindmap Fett/Kursiv, Größe, Textfarbe und alle hellen Füllungen ändern.
   Ansicht wechseln, Sidebar schließen und Anki neu starten; Darstellung muss erhalten bleiben.
7. Beide Dokumenttypen mit Bildern exportieren und erneut importieren, idealerweise
   zusätzlich in ein separates Testprofil. Bilder, Texte, Formatierung und Pfeile vergleichen.
8. Im Zahnrad jeweils einen Reiter deaktivieren und wieder aktivieren; Dokumente
   müssen erhalten bleiben. Das Zahnrad auch in Notebook, To-Do und PDF anklicken.
9. Zoom-Prozentwerte, Zentrieren, Gesamtansicht, Fensteransicht und Vollbild prüfen.
10. Vor einem Update einen Export anlegen, Add-on normal aktualisieren und danach
    Dokumente/Bilder öffnen. Die aktive Installation wurde für diese Entwicklung nicht verändert.


## Stabilitätskorrektur vom 26. September 2026

- Fenster-/Vollbild-Callbacks verdecken die Übersetzungsfunktion nicht mehr mit einem gleichnamigen Parameter. Regressionstest übergibt ausdrücklich ein Beschriftungsobjekt.
- Unerwartete JavaScript-Laufzeitfehler sperren weitere Speicherungen: Mindmap liefert keinen Recovery-Snapshot, Roadmap keinen Datenbank-Snapshot. Das Fenster bleibt zur Sicherung per Export offen. Roadmap pausiert zusätzlich die Bearbeitung. Dies schützt vor nachfolgenden Schreibvorgängen, garantiert aber keine Wiederherstellung bereits vor dem Fehler veränderter Daten. Nach einem Fehler exportieren, dann Anki neu öffnen; nicht auf eine weitere automatische Speicherung verlassen.
- Rückgängig und Wiederholen teilen sich höchstens 50 Einträge und 8 Millionen Zeichen serialisierten Text. Das entspricht bis zu etwa 16 MB UTF-16-Nutzdaten plus Laufzeit-Overhead; bei großen Maps stehen weniger Undo-Schritte zur Verfügung.
- Ein einmaliger Hinweis pro Dokument und Sitzung erscheint ab 2.000 Objekten, 18 Millionen Bildpixeln oder 2 Millionen Textzeichen. Dies ist eine Größenwarnung, kein RAM-Messgerät und keine Absturzvorhersage. Alle Dokumentmodelle einer Sammlung liegen weiter im Arbeitsspeicher; gerendert wird die aktive Map.
- Mindmap-Bilder wachsen mit dem vorhandenen Eckgriff des Knotens proportional mit. `imageDisplayWidth` speichert nur die Darstellungsbreite; Originalpixel und Bilddatei bleiben unverändert.
- Standard-Roadmap-Boxen folgen dem dunklen/hellen Erscheinungsbild. Eigene Füll-/Rand-/Textfarben bleiben erhalten. Ältere weiße Standardboxen ohne erkennbar eigene Farben werden als Standard behandelt; eine früher ausdrücklich gewählte identische Standardfarbe ist rückwirkend nicht unterscheidbar.
- Die Zahnräder öffnen eigene kleine Qt-Dialoge. Mindmap/Roadmap sowie Notebook/To-Do/PDF lassen sich unabhängig ausblenden. Mindestens ein Tab pro Gruppe bleibt sichtbar. Speicherung: `SynapsePro_Data/workspace_preferences.json` im Anki-Profil, atomar geschrieben. Die alten globalen Tab-Einstellungen werden beim ersten Einsatz als Vorgabe übernommen.

### Gezielter manueller Test

1. Aktualisierten Desktop-Ordner als Add-on installieren, Anki neu starten. Vorher beide Dokumentarten exportieren.
2. Mindmap und Roadmap mehrfach öffnen, vergrößern, Vollbild aktivieren/beenden und wechseln; keine Fehleranzeige.
3. Bildknoten am unteren rechten Eckgriff größer/kleiner ziehen; Undo/Redo, schließen/öffnen und Export/Import prüfen.
4. Roadmap mit Standardbox, farbiger Box und eigenem Textfarbton anlegen; Anki-Theme live umschalten. Standard wechselt, eigene Farben bleiben.
5. Beide Zahnräder prüfen, Tabs ausblenden und wieder einblenden; Inhalte müssen bestehen bleiben. Dialog darf nicht die allgemeinen Add-on-Einstellungen öffnen.
6. Große Testdokumente verwenden: Hinweis erst ab genannten Schwellen; normale Dokumente ohne Hinweis. Kein Belastungstest mit ungesicherten Originaldaten.

Die lokale SQLite-Transaktion der Roadmap ist kein unabhängiges Versionsbackup. Mindmap besitzt zusätzlich eine Recovery-Datei. Exportdateien sind deshalb weiterhin sinnvoll, ebenso eine Sicherung des gesamten Anki-Profilordners. Die Daten werden nicht automatisch über AnkiWeb synchronisiert.


## Anki-Verknüpfungen (26.09.2026)

- Mindmap: Rechtsklick auf einen Knoten → „Karte verknüpfen“.
- Roadmap: Form, Text- oder Bildobjekt auswählen → „Karte verknüpfen“ in der Objektleiste.
- Bei ausgewähltem Objekt außerhalb der Texteingabe öffnet Strg/⌘+K den Dialog.
- Der native Dialog bietet aktuelle Reviewer-Karte, Browser-Auswahl, Anki-Suche, Stapel- und Tag-Filter, reine Textvorschau der Notizfelder sowie Auswahl zwischen ganzer Notiz und einzelnen Karten. Die aktuelle Karte wird als Karten-Ziel vorausgewählt. Maximal 60 Treffer werden angezeigt; die Suche lässt sich weiter eingrenzen.
- Bis zu zwölf Verknüpfungen pro Objekt. „Hinzufügen“ sammelt Änderungen; „Speichern“ übernimmt sie, „Abbrechen“ verwirft sie. Doppelte Ziele werden nicht erneut hinzugefügt. Vorhandene Verknüpfungen lassen sich auswählen, ansehen und entfernen. „Speichern und öffnen“ übernimmt Änderungen und öffnet danach den Anki-Browser.
- Ein kleiner Anki-Button am Objekt öffnet ein einzelnes Ziel direkt. Bei mehreren Zielen öffnet er die Verwaltung. Die Mindmap blendet Links im Lernmodus aus. Textbearbeitung, Ziehen und Bildskalierung behalten ihre bisherige Funktion.
- Verknüpfungen lesen die Sammlung. Öffnen startet keine Wiederholung und verändert keine Lernstände. Vor dem Browser-Sprung werden bereits begonnene Browser-Eingaben über Ankis Editor gespeichert; ein Kartenlink wechselt gegebenenfalls in die Kartenansicht.
- `ankiLinks` speichert Art, Notiz-GUID, lokale IDs, Kartennummer/Vorlage und eine kurze Beschriftung. Kein vollständiger Notizinhalt und keine Kartenmedien werden kopiert. Export/Import sowie Undo/Redo nehmen die Referenzen mit.
- Zum Auflösen muss die GUID eindeutig in der aktuellen Sammlung existieren. Gleiche numerische IDs in einer anderen Sammlung reichen nicht. Geänderte IDs können über GUID und Kartenordinal/Vorlage aufgelöst werden. Fehlende oder mehrdeutige Ziele werden gemeldet, niemals anhand ähnlichen Texts geraten; die gespeicherte Verknüpfung bleibt erhalten. Das Exportieren einer Map exportiert nicht die verknüpften Anki-Karten: Diese müssen in der Ziel-Sammlung vorhanden sein.
- Abfragen laufen über Ankis serialisierte `QueryOp`-Hintergrundabfragen. Suche wartet 300 ms nach Eingabe; veraltete Antworten und Antworten nach geschlossenem Dialog werden ignoriert. Filter werden mit Ankis Suchausdrücken kombiniert, GUID-Auflösung verwendet gebundene SQL-Parameter.

### Pfeilbeschriftung

Pfeil auswählen → „Beschriftung“ direkt in der Werkzeugleiste oder den Pfeil doppelt anklicken. Die Beschriftung erscheint auf der Linie mit dunklem Hintergrund und heller Schrift; die Schriftgröße steht unter „Stil“. Leerer Text entfernt die Beschriftung. Doppelklick nutzt jetzt dieselbe Funktion auch bei aktiver SVG-Pointer-Erfassung; eine verdeckte Übersetzungsfunktion wurde korrigiert.

### Verknüpfungen testen

1. Aktuelle Reviewer-Karte direkt verknüpfen, Anki-Button anklicken und das genaue Browser-Ziel prüfen.
2. Im Browser mehrere Notizen auswählen; im Dialog deren Vorschau und einzelne Kartenvorlagen prüfen.
3. Mit Begriff, Stapel und Tag suchen; mehrere Links hinzufügen, Duplikate versuchen, speichern und Undo/Redo nutzen.
4. Dialogänderungen abbrechen: vorhandene Links müssen unverändert bleiben.
5. Beide Dokumentarten exportieren und importieren. Ohne passende Notizen wird ein fehlendes Ziel gemeldet; mit vorhandenen Notizen öffnet der Link das richtige Ziel.
6. Link entfernen: Anki-Karte und Notiz müssen erhalten bleiben. Mindmap-Lernmodus darf keine Links als Lösungshinweis anzeigen.
7. Pfeil doppelt anklicken, Text eintragen, über Werkzeugleiste ändern und mit leerem Text entfernen.

Automatisiert: 110 Python-Tests einschließlich GUID-Kollisionen, Mehrdeutigkeit, ungültigen IDs und Größenlimit; `tests/qt_workspace_links.py` prüft echte Sammlung und echte QueryOp-Threads; `tests/web_workspace_links.cjs` prüft beide Editoren einschließlich Undo/Redo, Import/Export und Pfeilbeschriftung.


## Korrektur und UI-Überarbeitung (26.09.2026)

Der bisherige JavaScript-Hostfilter ließ `anki-links:` und `anki-open:` nicht durch. Die Python-Funktion und der Dialog funktionierten isoliert, waren über echte UI-Klicks aber nicht erreichbar. Der Filter erlaubt jetzt ausschließlich diese beiden zusätzlichen Befehle mit begrenzter, kodierter Nutzlast. Abgelehnte Link-Anfragen setzen den lokalen Wartezustand zurück und zeigen eine Fehlermeldung. Der native Regressionstest lädt beide Original-HTML-Seiten, klickt den Button mit QtTest, verwendet den echten Hostfilter und WebChannel sowie die produktive Python-Verarbeitung und prüft das Ergebnis am Objekt. Die JavaScript-Befehlsfunktion wird dabei nicht ersetzt.

- Die Aktion heißt auf Englisch **Link Card**, auf Deutsch **Karte verknüpfen**; der Dialog ist entsprechend benannt. Unterstützung für ganze Notizen bleibt erhalten.
- Das Mindmap-Knotenmenü gruppiert Rand/Größe, Text, Füllung und Aktionen. Knotengröße und Schriftgröße stehen in Dropdowns. Fett/Kursiv zeigen den aktiven Zustand, Textfarbe und Pastellfarben sind zugänglich beschriftet. Formatierungen lassen das Menü offen; Escape oder ein Klick auf den Canvas schließt es. Bilder haben eine eigene Zeile mit Ersetzen/Entfernen.
- Pfeilbeschriftungen verwenden ein HTML-Dialogfeld im Workspace-Stil mit Light/Dark Mode, Vorschau, Textfeld und Schriftgrößenwahl. Speichern übernimmt Text und Größe zusammen als einen Undo-Schritt. Abbrechen und Escape verändern keine Daten. Es gibt keinen JavaScript-Prompt mehr für Pfeilbeschriftungen.
- Ausgewählte Pfeile zeigen einen **T**-Button neben dem Minusbutton. T, Doppelklick und der Toolbar-Button öffnen denselben Dialog. Beide SVG-Buttons sind auch per Tastatur erreichbar.

Zusätzliche Tests: `tests/workspace_host_bridge.cjs` prüft den tatsächlichen JavaScript-Filter einschließlich Unicode-Nutzlast und Warteschlange. `tests/web_workspace_polish.cjs` prüft Light/Dark Mode, 360 px breite Fenster, Menüformatierungen, Enter/Escape und Beschriftungs-Undo/Redo. Vorschauen liegen in `docs/node-menu-light.png`, `docs/node-menu-dark.png`, `docs/arrow-label-light.png` und `docs/arrow-label-dark.png`.


### Starter roadmap and shared sidebar widths

- A profile with no previously saved roadmap collection receives a localized, editable tutorial roadmap with example shapes, connected labeled arrows, and short instructions for formatting, images, Anki links, navigation and JSON backups.
- Initial framing leaves room for the floating bottom controls. The sample is an ordinary document: edits, undo, persistence, export and deletion use the existing paths.
- `roadmap_store.is_first_use()` checks the existing active-setting marker and stored maps. A saved empty collection or an existing document does not receive starter content. Read failures retain the host error barrier. The normal atomic save records initialization; no separate early flag can suppress a tutorial after a failed save.
- The Roadmap menu can add another tutorial to an existing collection without replacing its maps.
- Mindmap/Roadmap share their session width; Notebook/To-do/PDF share theirs. Internal tab selection does not request a resize. Other sidebars remain independent with the 400 px starting width.
- Verified with the grouped-width Qt test, the Roadmap Qt lifecycle test (first creation, real bridge save, deletion and later reopen), browser tutorial tests at 400/900 px in both themes, SQLite round-trip validation, and 129 Python tests. All test collections/profiles are temporary.

## Free Map interface (September 2026)

The visible tool name is now **Free Map**. Existing `roadmap` bridge actions,
IDs, directories, SQLite schema and import/export version remain unchanged so
older maps continue to open. Existing user document names are not renamed.
The map menu can create the richer Free Map tutorial as a separate editable map;
first-use seeding remains restricted to new stores. Existing tutorials are not
overwritten, because they may contain user edits.

The tutorial demonstrates a branching explanation alongside shape/text styling,
attached arrows, free notes, card links and navigation/export guidance. Its
objects use the normal document model and can be edited, undone or deleted.

Enlarge/Reduce state acknowledgements trigger a short, bounded ResizeObserver
that centers the final canvas geometry. Mindmap centers its root; Free Map uses
its existing Center View action. Neither changes the current zoom. Ordinary
window resizing or panning outside that transition retains its usual behavior.

The insertion palette has geometric previews and separate insertion actions.
Text editing uses a compact two-row panel with an alignment dropdown. Selection
ranges are retained while using formatting inputs; font size/color and active
format buttons follow the text selection. Text containers fill their available
width so paragraph alignment is visible. The insert menu draws above the object
inspector rather than behind it.

Validation: `tests/web_free_map_polish.cjs`, `tests/web_roadmap_tutorial.cjs`,
`tests/web_roadmap.cjs`, `tests/qt_roadmap_lifecycle.py`, and the workspace/store
Python tests. All use isolated browser contexts or temporary profiles.
