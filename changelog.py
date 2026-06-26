# changelog.py — Änderungsverlauf, im Tool unter „🆕 Was ist neu" lesbar.
CHANGELOG = """\
Version 4 — Autostart

NEU
• Das Tool startet jetzt automatisch mit Windows (bei der Anmeldung).
• Über den Knopf „🚀 Autostart: An/Aus" unten lässt sich das jederzeit
  ein- oder ausschalten.

BEHOBEN
• Speichern der Aufgaben-Erkennungs-Regeln konnte fehlschlagen — behoben.


Version 3 — Update-Fix

BEHOBEN
• Update bleibt nicht mehr bei „Update wird installiert — die App startet gleich
  neu" hängen. Die App beendet sich jetzt sofort sauber, der Austausch läuft
  zuverlässig im Hintergrund (kein schwarzes Fenster mehr).


Version 2 — Aufgaben-Erkennung & Pause/Resume

NEU
• Mehrere Fenster = EINE Aufgabe: Wenn im Fenstertitel dieselbe „Schlagzeile"
  steht (z. B. Kundenname oder Adresse), zählen die Fenster jetzt als eine
  zusammengehörige Aufgabe — nicht mehr jedes Fenster als eigene Aufgabe.
• Selbst einstellbar: Unter „🧩 Aufgaben-Erkennung" kannst du je Seite/Programm
  festlegen, welcher Teil des Titels der Identifikator ist (z. B. für
  verwaltung.mein-handwerker.de oder westnetz.de jeweils das passende Wort).
  Mit Test-Feld zum Ausprobieren.
• Pause/Resume: Ein kurzer Abstecher in ein anderes Fenster zählt nicht mehr als
  Aufgabenwechsel — die laufende Aufgabe wird pausiert und danach fortgesetzt.
• „Was ist neu"-Knopf (dieser Verlauf) und einfacher Update-Knopf.

So funktioniert die Aufgaben-Erkennung
• Seite/App: Teil der Adresse/des Programms, z. B. westnetz.de
• Muster (Regex): der Teil in Klammern ( ) ist der Identifikator; leer = ganzer Titel.
  Beispiele:  Kunde:?\\s*([^|\\-–]+)   ·   ([0-9]{5,})   ·   ^([^|\\-–]+)

Hinweis: Für die Aufgaben-Erkennung müssen Fenstertitel gespeichert werden
(Einstellung store_window_titles = true, ist standardmäßig an). Alle Daten bleiben
weiterhin nur auf diesem PC.
"""
