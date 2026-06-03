# ki_prompt.py — baut einen starken, mit echten Kennzahlen gefüllten KI-Prompt
from analysis import fmt_dur


def build_ki_prompt(A, period_label=""):
    f = A["focus"]
    flap = "; ".join(f"{x['a']} <-> {x['b']} ({x['count']}x)" for x in A["flapping"][:5]) or "keines"
    seqs = " | ".join(" -> ".join(s["labels"]) + f" ({s['count']}x)" for s in A["sequences"][:4]) or "keine"
    levels = A["by_level"]
    return f"""Du bist mein persönlicher Produktivitäts- und Workflow-Coach. Ich hänge dir eine CSV
mit meiner PC-Aktivität an ({period_label}). Spalten: Typ;Name;Sekunden;Lesbar;Detail.

Hier schon die wichtigsten Kennzahlen aus den Daten:
- Aktive Zeit: {fmt_dur(A['active'])}, Abwesend: {fmt_dur(A['idle'])}
- Produktiv/Neutral/Ablenkung: {fmt_dur(levels.get('produktiv',0))} / {fmt_dur(levels.get('neutral',0))} / {fmt_dur(levels.get('ablenkung',0))}
- Fokus-Anteil: {f['focus_quote']*100:.0f}%  ·  Fokusblöcke (>=15min): {f['focus_count']}  ·  Deep Work (>=25min): {f['deepwork_count']}  ·  längster Block: {fmt_dur(f['longest'])}
- Aufgabenwechsel: {A['switches']} (~{f['switches_per_hour']:.0f}/Std)  ·  Unterbrechungen: {A['interruptions']}
- Häufiges Hin-und-Her zwischen zwei Tools (mögliche Doppelarbeit/manuelle Übertragung): {flap}
- Wiederkehrende Abläufe (Automatisierungs-Kandidaten): {seqs}
- Geschätzt verlorene Zeit durch Wechseln: ~{fmt_dur(A['lost_estimate'])}

Werte die angehängte CSV gründlich aus und antworte auf Deutsch, klar strukturiert:

1. ÜBERBLICK: War der Tag fokussiert oder zersplittert? Beziehe dich auf Fokus-Anteil,
   Deep-Work-Blöcke und Aufgabenwechsel.
2. DOPPELARBEIT / UNSAUBERE ABLÄUFE: Schau dir das "Hin-und-Her zwischen zwei Tools" an.
   Wo deutet das auf manuelles Übertragen von Daten zwischen zwei Programmen hin?
   Schlage konkret vor, wie man das vereinfachen/automatisieren könnte (Vorlage, Export/Import,
   Schnittstelle, Copy-Workflow).
3. WIEDERKEHRENDE ABLÄUFE: Welche der erkannten Sequenzen lohnt sich zu standardisieren oder
   zu automatisieren? Schätze das Einsparpotenzial.
4. BÜNDELN & TAGESRHYTHMUS: Welche Tätigkeiten (E-Mail, Telefonie) über den Tag verteilt
   immer wieder kurz? Schlage feste Zeitblöcke vor. Wann war ich am produktivsten?
5. ZEITFRESSER & ABLENKUNG: Wo geht am meisten Zeit verloren?
6. 3–5 KONKRETE NÄCHSTE SCHRITTE für morgen, mit Zahlen begründet.

Sei konkret, nenne immer Zahlen aus den Daten, keine Floskeln. Die geschätzten Werte
("verlorene Zeit") sind grobe Schätzungen aus Studien, kein Messwert — behandle sie so.
"""
