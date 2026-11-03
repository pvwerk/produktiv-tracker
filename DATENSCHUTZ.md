# Datenschutz & Transparenz

Dieses Tool ist ein **freiwilliges Selbst-Auswertungs-Werkzeug**. Es hilft *dir*, deinen
eigenen Arbeitstag am PC zu verstehen und Abläufe zu verbessern. Es ist **kein
Überwachungs- oder Bewertungswerkzeug**.

## Was erfasst wird
- Welches **Programm/Fenster** gerade aktiv ist und wie lange.
- Im Browser nur die **Hauptadresse** (z. B. `www.westnetz.de`) — **nicht** der volle Link,
  keine Suchbegriffe, keine Seiteninhalte.
- **Leerlauf** (keine Maus/Tastatur) als „Abwesend".
- Optional der Fenstertitel (für die Erkennung wiederkehrender Abläufe) —
  abschaltbar über `store_window_titles: false` in der `config.json`.

## Was dieses Tool BEWUSST NICHT macht
- **Keine** Tastatureingaben / kein Mitschneiden von Texten (kein Keylogger).
- **Keine** Screenshots, **keine** Kamera, **kein** Mikrofon.
- **Keine** vollständigen URLs oder Dateipfade.
- **Keine** Cloud, solange du nichts anderes einstellst — es wird **nichts** ins Internet
  gesendet. Alle Daten liegen lokal in
  `%LOCALAPPDATA%\Produktivitaets-Tracker\tracker.db`.
  *Ausnahme, die du selbst einschaltest:* die optionale **CRM-Anbindung** (siehe unten).
- **Keine** Live-Überwachung durch Vorgesetzte oder Dritte.
- **Keine** Leistungsbewertung / kein Ranking / keine arbeitsrechtlichen Konsequenzen.

## Deine Kontrolle
- Du **startest und stoppst** die Aufzeichnung selbst.
- Du kannst die Daten **jederzeit einsehen, exportieren und löschen** (Datei `tracker.db`).
- Die Auswertung gehört **dir**. Du entscheidest, ob und was du teilst.

## Optionale CRM-Anbindung (standardmäßig AUS)

Seit 03.11.2026 kannst du einstellen, dass das Tool deine **fertige Tagesauswertung**
zusätzlich ins PVWERK-CRM überträgt, damit du sie auch dort ansehen kannst
(Menüpunkt „Meine Produktivität"). Das Tool arbeitet davon unabhängig weiter — die
Anbindung ersetzt nichts, sie kommt nur dazu.

**Es passiert nichts, solange du kein Token einträgst.** Das Token erzeugst du selbst im
CRM und kannst es dort jederzeit zurückziehen; danach wird nichts mehr angenommen.

Übertragen werden **nur Auswertungszahlen**: Summen je Kategorie, Top-Programme,
Hauptadressen, Fokuskennzahlen, auffällige Abläufe.
**Nicht** übertragen werden die Rohdaten aus `tracker.db` — insbesondere **Fenstertitel**
verlassen deinen Rechner nicht (die Felder `segments` und `tasks` werden vor dem Senden
entfernt, zusätzlich auch serverseitig).

**Wer die Daten im CRM sehen kann: nur du.** Das ist in der Datenbank erzwungen, nicht
bloß in der Oberfläche ausgeblendet — auch Administratoren und Geschäftsführung können
fremde Zeilen weder lesen noch ändern noch löschen. Im CRM kannst du jeden übertragenen
Tag einzeln wieder löschen.

## Rechtlicher Rahmen (DE)
Auch bei freiwilliger Nutzung gelten DSGVO/§ 26 BDSG. Empfohlen:
- **Schriftliche, freiwillige Einwilligung** mit klarer Zweckbindung (nur Workflow-
  Optimierung), **jederzeit widerrufbar ohne Nachteil**.
- Falls ein **Betriebsrat** existiert: nach § 87 Abs. 1 Nr. 6 BetrVG beteiligen.
- Im Zweifel den/die Datenschutzbeauftragte:n kurz drüberschauen lassen.

## Methodische Ehrlichkeit
Die Kennzahl „geschätzt verlorene Zeit" ist eine **grobe Schätzung** auf Basis von
Studien (Mark et al., CHI 2008: ~23 Min Refokussierung nach Unterbrechung; APA/Meyer
et al. 2001: Aufgabenwechsel kostet bis zu 40 % der produktiven Zeit), **kein Messwert**
über die konkrete Person.
