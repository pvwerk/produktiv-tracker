# Produktivitäts-Tracker

Eine kleine Windows-Anwendung, mit der **du selbst** deine produktive Zeit am PC
auswertest. Du startest und stoppst die Aufzeichnung jederzeit selbst.

> **Datenschutz:** Alle Daten bleiben **ausschließlich lokal auf deinem PC**
> (Ordner `%LOCALAPPDATA%\Produktivitaets-Tracker`). Es wird nichts ins Internet
> gesendet. Nur du siehst die Daten.

## Was wird erfasst?
- Welches **Programm/Fenster** gerade aktiv ist und wie lange.
- Im Browser (Firefox & Chrome): die **Hauptadresse** der Seite, z.B. `www.westnetz.de`
  (ohne den restlichen Pfad).
- **AGFEO-Dashboard**, E-Mail-Programm usw. als eigene Kategorien.
- **Leerlauf** (keine Maus/Tastatur) wird als „Abwesend" erkannt und nicht als Arbeit gezählt.

## Bedienung
1. `Produktivitaets-Tracker.exe` doppelklicken.
2. **„Tracking starten"** drücken — oben siehst du live, was gerade läuft, und unten die
   Top-Auswertung für heute.
3. Über **„Tracking stoppen"** pausierst du jederzeit.
4. Schließt du das Fenster, läuft die App im **Infobereich (Tray)** weiter.

## Auswertung
- **PDF-Bericht**: fertiger Bericht mit Diagrammen (Kategorien, Programme, Webseiten, Tagesverlauf, Hinweise).
- **CSV**: Rohdaten/Tabellen für eigene Auswertung.
- **Für KI exportieren**: erzeugt eine CSV **und** einen fertigen Prompt. Den Prompt in
  die KI (z.B. Grok) einfügen und die CSV anhängen → ausführliche Optimierungs-Analyse.

Oben rechts wählst du den **Zeitraum** (Heute / Gestern / Letzte 7 Tage).

## Einstellungen
Über **„⚙ Einstellungen"** öffnet sich `config.json`. Dort kannst du anpassen:
- `sample_interval` – Messabstand in Sekunden (Standard 3)
- `idle_threshold` – ab wie vielen Sekunden Inaktivität „Abwesend" gilt (Standard 60)
- `process_categories` / `domain_categories` – eigene Kategorien
- `agfeo_process_hints` – woran das AGFEO-Dashboard erkannt wird

Nach dem Speichern: Tracking einmal stoppen und neu starten.

## Hinweis Firefox/Chrome
Die Seitenadresse wird über die Windows-Bedienungshilfen (UI-Automation) ausgelesen.
Falls eine Adresse mal nicht erkannt wird, nutzt die App den Fenstertitel als Ersatz.
