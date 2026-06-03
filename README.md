# Produktivitäts-Tracker

Eine lokale Windows-App, mit der **du selbst** deinen Arbeitstag am PC auswertest —
um Zeit zu sparen, fokussierter zu arbeiten und **Doppelarbeit / unsaubere Abläufe**
aufzudecken. Du startest und stoppst die Aufzeichnung jederzeit selbst.

> **Alle Daten bleiben ausschließlich lokal auf deinem PC.** Nichts geht ins Internet.
> Nur du siehst die Auswertung. Details: siehe `DATENSCHUTZ.md`.

## Was es erfasst
- Aktives **Programm/Fenster** + Dauer.
- Browser (Firefox & Chrome): nur die **Hauptadresse** (z. B. `www.westnetz.de`).
- **AGFEO-Dashboard**, E-Mail u. a. als eigene Kategorien.
- **Leerlauf** = „Abwesend" (zählt nicht als Arbeit).

## Auswertungen (das Besondere)
Fünf Tabs mit Diagrammen:

1. **Übersicht** – Zeit je Kategorie, Produktiv/Neutral/Ablenkung, Top-Webseiten, Kopfzahlen.
2. **Fokus & Ablenkung** – wie lange am Stück konzentriert? Deep-Work-Blöcke (≥25 min),
   Fokus-Anteil, Aufgabenwechsel pro Stunde, geschätzt verlorene Zeit.
3. **Workflow-Probleme** – **App-Flapping**: häufiges Hin-und-Her zwischen zwei Tools
   (oft = manuelles Übertragen von Daten → Automatisierungs-Kandidat) und
   **wiederkehrende Abläufe**, die sich standardisieren/automatisieren lassen.
4. **Tagesverlauf** – wann wurde produktiv/neutral/abgelenkt gearbeitet (Stunden-Heatmap),
   Top-Programme.
5. **Wochen-Trend** – aktive Zeit, Fokus-Anteil, Aufgabenwechsel und Doppelarbeit über 7 Tage.

## Export
- **PDF-Bericht**: alle Auswertungen + konkrete Optimierungs-Hinweise.
- **CSV**: Tabellen/Rohdaten.
- **Für KI exportieren**: CSV **+ fertiger Prompt mit deinen Kennzahlen** → in eine KI
  (z. B. Grok) einfügen, CSV anhängen → ausführliche Optimierungs-Analyse.
- **Offline nachtragen**: Meetings/Telefonate ohne PC manuell ergänzen.

## Bedienung
1. `Produktivitaets-Tracker.exe` doppelklicken.
2. **„Tracking starten"**. Oben siehst du live, was läuft; die Tabs aktualisieren sich.
3. Fenster schließen = läuft im Infobereich (Tray) weiter. „Beenden" stoppt ganz.
4. Zeitraum oben umstellen (Heute / Gestern / Letzte 7 Tage).

## Einstellungen (`⚙`)
Öffnet `config.json`. Anpassbar u. a.:
- `sample_interval`, `idle_threshold`
- `process_categories`, `domain_categories`, `productivity_levels`
- `focus_min_minutes`, `deepwork_min_minutes`, `switch_penalty`
- `agfeo_process_hints`
- `store_window_titles` (Datenschutz: Fenstertitel mitspeichern ja/nein)

Nach dem Speichern: Tracking stoppen/neu starten, dann oben Neu-Laden (Pfeil).

## Was das Tool bewusst NICHT macht
Kein Keylogger, keine Screenshots, keine Kamera/Mikrofon, keine vollständigen URLs,
keine Cloud, keine Fremd-/Live-Überwachung, keine Leistungsbewertung. Siehe `DATENSCHUTZ.md`.

## Build (Entwickler)
Die Windows-`.exe` wird automatisch per GitHub-Actions (`.github/workflows/build.yml`,
PyInstaller `build.spec`) gebaut und ans Release **`latest`** gehängt. Lokal testen:
`pip install -r requirements.txt && python app.py` (Windows).
