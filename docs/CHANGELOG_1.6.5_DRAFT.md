# Synapse 1.6.5 – vollständiger Changelog

Stand: **29.10.2026**. Änderungen gegenüber der zuvor geprüften GitHub-Basis (1.6.0). Dieser Text beschreibt die Änderungen für Nutzer; technische Testbelege stehen in [RECOVERY_FIX_1.6.5.md](RECOVERY_FIX_1.6.5.md).

## Deutscher Veröffentlichungstext

### Notebook: neue Funktionen

- Erweiterte Blockmenüs: Blöcke einfügen, duplizieren, umordnen und auf eine andere Seite verschieben.
- Überschriften der dritten Ebene (H3).
- Text- und Hintergrundfarben, Durchstreichen und Inline-Code.
- Unterseiten und Breadcrumb-Navigation für verschachtelte Notizen.
- Seiten per Drag-and-drop sortieren und verschachteln.
- Seitenwahl mit Suchfunktion.
- Chronologische Rückgängig-/Wiederholen-Historie für Bearbeitungen und Seitennavigation.
- Inhaltsverzeichnis aus den Überschriften einer Seite.
- Eigene wiederverwendbare Seitenvorlagen und eine vorbereitete Vorlage für Krankheitsprofile.
- Gespeicherte Versionen in einer Vorschau ansehen und eine ältere Seite als unabhängige Kopie wiederherstellen.
- Direkter Zugang zum Notebook-Export.
- Erweiterte Tabellen: Kopfzeile, Zeilen und Spalten umordnen, Spalten ausrichten und Breiten anpassen.
- Bilder als Dateien einfügen, ausrichten, proportional skalieren und innerhalb der Notizen verschieben.
- Bildverschiebungen mit Vorschau und Abbruchmöglichkeit.

### Notebook: Bedienung und Schutz bestehender Inhalte

- Verbesserte Texteingabe, Listen und To-dos sowie Fokusführung und Klicks in Seitenränder.
- Formatierungen bleiben beim Teilen und Zusammenführen unterstützter Textblöcke erhalten.
- Zusätzliche feste Vor-Update-Sicherungen der vorhandenen Notebook-Snapshots.
- **Verbesserte Sicherheit im Notebook:** XSS-Lücke bei der Verarbeitung von HTML und Markdown-Links behoben und mit Browser-Regressionstests überprüft. Bei potenziell unsicheren Inhalten erscheint ein dezenter, wegklickbarer Sicherheitshinweis. Gefilterte Bestandsblöcke bleiben im gespeicherten Original erhalten; betroffene Inhalte werden bei Bedarf gegen Bearbeitung geschützt.
- Abgesicherte Historie und Löschaktionen bei alten Seiten mit doppelten oder fehlenden IDs. Neue Seiten erhalten auf Kollisionen geprüfte IDs.
- Backspace in einem leeren Aufklappblock-Titel entfernt keine noch vorhandenen Texte, Bilder oder Metadaten im Blockinhalt. Vollständig leere Aufklappblöcke lassen sich weiterhin in Absätze umwandeln und per Rückgängig wiederherstellen.
- Unabhängige Sicherungskopien bleiben in der Versionsauswahl erreichbar, wenn die Hauptdatenbank beschädigt oder gesperrt ist und die Kopien selbst lesbar sind.
- Von der Ladefehlerseite kann eine lesbare Wiederherstellungsversion in eine neue Datei exportiert werden; die Quelle wird dabei nicht ersetzt.
- Recovery-Fehler behoben: Eine gesperrte ältere Recovery-Datei kann nach erneutem Öffnen keinen neueren bestätigten Speicherstand mehr verdecken.
- Ist der Speicherstand nicht sicher prüfbar, erscheint eine Ladefehlermeldung. Die verfügbaren Quellen bleiben für die Wiederherstellung erhalten.

### Hauptbildschirm, Deckübersicht und Darstellung

- **Sichtbare Scrollleiste auf dem Hauptbildschirm bei langen Decklisten** sowie in der eigenen Deckübersicht; einheitliche Gestaltung passend zum Theme.
- Neue Hintergrundauswahl „None“.
- Eigene einfarbige Hintergründe mit getrennten Farben für Hell- und Dunkelmodus.
- Einfarbige Hintergründe erhalten das Dashboard-Layout; Farbauswahl auch im nativen Einstellungsdialog.
- Angepasste Hintergründe der oberen und unteren Werkzeugleisten beim Wechsel zwischen Dashboard, Deckübersicht und Lernen.
- Einheitliche Aktivitätskurven in Dashboard und Deckübersicht, einschließlich Flächenfüllung, Tagesmarkierung und Angaben beim Darüberfahren.

### MindMap und FreeMap

- Trackpad-Zoom und native Zoomgesten vergrößern die Zeichenfläche, während die umliegenden Bedienelemente ihre Größe behalten.
- Erneutes Zentrieren nach dem Wechsel in den Vollbildmodus und zurück.
- Angepasstes Einstellungssymbol in der Map-Navigation.

### AI-Assistent

- Eigene Schnellaktionen lassen sich bearbeiten; IDs, Tastenkürzel und weitere Einstellungen bleiben erhalten.
- Änderungen können abgebrochen werden. Ein zuvor begonnener Entwurf für einen neuen Button wird wiederhergestellt.
- Präziserer Hinweis zum Kartenkontext: Schnellaktionen benötigen den Kartentext unabhängig vom Kontextschalter; dieser steuert den zusätzlichen Kartenkontext bei selbst eingegebenen Fragen.
- Der Kartenkontext-Hinweis ist in kleinen Fenstern scrollbar.

### SoundCloud

- Wiedergabe in neueren Qt-Versionen korrigiert, einschließlich der Einbindung in das eingebettete SoundCloud-Widget.
- Zusätzlicher Audiowiedergabeweg über Ankis separaten mpv-Prozess für eingebettete Browser ohne AAC-Unterstützung.
- Wiedergabe, Pause, Spulen, Playlists und automatischer Titelwechsel mit dem offiziellen Widget geprüft.
- Gewählte Lautstärke wird nach dem Neuladen des Widgets wieder angewendet.
- Zusätzliche Audioprozesse werden beim Wechsel zu lokaler Musik beziehungsweise beim Profilende pausiert und aufgeräumt.

### Sprachen und Paket

- Neue und überarbeitete Texte für die zusätzlichen Bedienelemente in den zehn vorhandenen Oberflächensprachen.
- Versionsnummer in Add-on-Anzeige und Manifest auf **1.6.5** gesetzt.
- Bereinigtes Release-Paket: Bildentwürfe, Prompt-Dateien, Profilverzeichnisse, Datenbanken und Recovery-Kopien werden nicht mitgeliefert.

## Englische Einträge im Add-on

Die folgenden Einträge sind identisch in `changelog.py` enthalten. Bereits mit 1.6.0 eingeführte Funktionen werden nicht erneut als neue Features aufgeführt.

```json
{
  "version": "1.6.5",
  "date": "October 29, 2026",
  "items": [
    {
      "tag": "Fixed",
      "text": "Fixed a recovery issue where a locked older recovery file could hide a newer confirmed Notebook save after reopening. If the saved state cannot be checked safely, a load error is shown and the available sources remain available for recovery."
    },
    {
      "tag": "Highlight",
      "text": "The Notebook gains expanded block controls, nested pages, breadcrumbs, and drag-and-drop page organization."
    },
    {
      "tag": "New",
      "text": "Added Heading 3, block insertion, duplication, reordering, and moving blocks to another page."
    },
    {
      "tag": "New",
      "text": "Added text and background colors, strikethrough, and inline-code formatting controls."
    },
    {
      "tag": "New",
      "text": "Added a chronological undo/redo history for Notebook edits and page navigation."
    },
    {
      "tag": "New",
      "text": "Added a heading outline, reusable page templates, and a built-in disease-profile template."
    },
    {
      "tag": "New",
      "text": "Added saved-version previews, restoring a page as an independent copy, and a direct Notebook export action."
    },
    {
      "tag": "New",
      "text": "Added persistent pre-update copies of existing Notebook snapshots."
    },
    {
      "tag": "New",
      "text": "Added table header styling, row and column reordering, column alignment, and adjustable column widths."
    },
    {
      "tag": "New",
      "text": "Added image-file insertion, alignment, proportional resizing, and moving images within notes."
    },
    {
      "tag": "Improved",
      "text": "Refined typing, list and to-do editing, focus behavior, and clicks in Notebook page margins. Supported text blocks retain their formatting when split or merged."
    },
    {
      "tag": "Security",
      "text": "Improved Security in Notebook: fixed an XSS vulnerability in HTML and Markdown-link handling, verified with browser regression tests. Potentially unsafe content triggers a discreet, dismissible security notice; original stored blocks are preserved."
    },
    {
      "tag": "New",
      "text": "Added a None background option and custom solid background colors for light and dark modes."
    },
    {
      "tag": "Improved",
      "text": "Refined toolbar backgrounds when switching between the dashboard, deck overview, and reviews."
    },
    {
      "tag": "Improved",
      "text": "Restored visible, theme-matched scrollbars on the main Dashboard for long deck lists and in the Custom Deck Overview."
    },
    {
      "tag": "Improved",
      "text": "Unified review-activity charts across the dashboard and deck overview."
    },
    {
      "tag": "Improved",
      "text": "Trackpad pinch gestures zoom the MindMap and FreeMap canvases without zooming their surrounding controls. Maps recenter after fullscreen changes."
    },
    {
      "tag": "New",
      "text": "Custom AI Quick Actions can now be edited while preserving their IDs, shortcuts and other settings. Cancelling restores any unfinished new-button draft."
    },
    {
      "tag": "Improved",
      "text": "Clarified that Quick Actions send card text independently of the context switch used for manually typed questions."
    },
    {
      "tag": "Improved",
      "text": "Extended translations for the new controls across all ten existing interface languages."
    },
    {
      "tag": "Fixed",
      "text": "Protected existing Notebook pages with duplicate or missing IDs from ambiguous undo/redo and deletion operations. Newly created pages use collision-checked IDs."
    },
    {
      "tag": "Fixed",
      "text": "Backspace in an empty toggle title preserves its body, images and original metadata. Completely empty toggles can still become paragraphs and be undone."
    },
    {
      "tag": "Fixed",
      "text": "Independent Notebook backup copies can still be listed when the main database is damaged or locked. The load-error screen can export a selected readable recovery version to a new file without replacing the original."
    },
    {
      "tag": "Improved",
      "text": "Fixed SoundCloud playback in newer Qt builds and added a dedicated audio fallback for embedded browsers without AAC support. Playback controls, seeking, playlists and automatic track changes were verified with the live official widget."
    },
    {
      "tag": "Improved",
      "text": "Release packages exclude generated image drafts, prompt files, profile data, databases and recovery copies."
    },
    {
      "tag": "Improved",
      "text": "The Notebook page picker supports search. Image dragging includes a preview and can be cancelled before the move is applied."
    },
    {
      "tag": "Improved",
      "text": "Custom solid backgrounds preserve the Dashboard layout and provide separate light- and dark-mode color controls, including in the native settings fallback."
    },
    {
      "tag": "Improved",
      "text": "SoundCloud restores the selected volume after widget reloads and pauses and cleans up its additional audio process when switching to local music or closing the profile."
    },
    {
      "tag": "Improved",
      "text": "Adjusted the Map settings icon and made the AI card-context information popover scrollable in smaller windows."
    }
  ]
}
```

## Prüfstand und Paket

Die Produktänderungen wurden mit 167 Python-Tests, 43 Browser-Testdateien, sieben zusätzlichen plattformbezogenen Tests und nativen Notebook-/SoundCloud-Prüfungen unter macOS getestet. Windows-Dateisperren wurden simuliert; native Windows-/Linux-Läufe stehen weiterhin aus. Diese Ergebnisse sind keine Garantie universeller Bugfreiheit.

Am 29.10.2026 wurde ausschließlich der Changelog vervollständigt und sein Datum aktualisiert; die Versionsnummer war bereits 1.6.5. Das Paket wurde mit identischen übrigen Produktdateien neu gebaut. Prüfsumme und Metadatenprüfung: [changelog-package-validation-2026-10-29.json](release-1.6.5/changelog-package-validation-2026-10-29.json).
