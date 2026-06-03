# report.py — Export als PDF (Diagramme) und CSV
import csv

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_pdf import PdfPages

import analysis
import charts


def _a4():
    fig = Figure(figsize=(8.27, 11.69))
    FigureCanvasAgg(fig)
    return fig


def _hints_page(A):
    fig = _a4()
    ax = fig.add_axes([0.08, 0.06, 0.84, 0.88]); ax.axis("off")
    ax.text(0, 1, "Beobachtungen & Optimierungs-Vorschläge", fontsize=13,
            fontweight="bold", va="top")
    y = 0.93
    for h in analysis.optimization_hints(A):
        # einfacher Zeilenumbruch für lange Hinweise
        line = "• " + h
        while len(line) > 95:
            cut = line.rfind(" ", 0, 95)
            if cut <= 0:
                break
            ax.text(0, y, line[:cut], fontsize=9.5, va="top"); y -= 0.032
            line = "   " + line[cut + 1:]
        ax.text(0, y, line, fontsize=9.5, va="top"); y -= 0.045
        if y < 0.12:
            break
    ax.text(0, 0.04,
            "Hinweis: Geschätzte Werte basieren auf Studien (s. Text) und sind keine "
            "exakten Messungen. Alle Daten stammen ausschließlich von diesem PC und bleiben lokal.",
            fontsize=7.5, style="italic", va="top", color="#6b7280")
    return fig


def export_pdf(A, period_label, path):
    with PdfPages(path) as pdf:
        for draw in (charts.draw_overview, charts.draw_focus,
                     charts.draw_workflow, charts.draw_timeline):
            fig = _a4()
            try:
                draw(fig, A, period_label)
            except Exception as e:  # eine kaputte Seite soll den Rest nicht verhindern
                fig.clear()
                fig.text(0.1, 0.5, f"Diagramm-Fehler: {e}", fontsize=9)
            pdf.savefig(fig)
        pdf.savefig(_hints_page(A))
    return path


def export_csv(samples, A, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Typ", "Name", "Sekunden", "Lesbar", "Detail"])
        w.writerow(["Gesamt", "Erfasst", int(A["total"]), analysis.fmt_dur(A["total"]), ""])
        w.writerow(["Gesamt", "Aktiv", int(A["active"]), analysis.fmt_dur(A["active"]), ""])
        w.writerow(["Gesamt", "Abwesend", int(A["idle"]), analysis.fmt_dur(A["idle"]), ""])
        w.writerow(["Gesamt", "Aufgabenwechsel", A["switches"], "", ""])
        w.writerow(["Gesamt", "Unterbrechungen", A["interruptions"], "", ""])
        w.writerow(["Gesamt", "Geschätzt verlorene Zeit", int(A["lost_estimate"]),
                    analysis.fmt_dur(A["lost_estimate"]), "Schätzung (Studienbasis)"])
        f_ = A["focus"]
        w.writerow(["Fokus", "Fokus-Anteil %", round(f_["focus_quote"] * 100), "", ""])
        w.writerow(["Fokus", "Fokusblöcke >=15min", f_["focus_count"], "", ""])
        w.writerow(["Fokus", "Deep-Work >=25min", f_["deepwork_count"], "", ""])
        w.writerow(["Fokus", "Längster Block", int(f_["longest"]), analysis.fmt_dur(f_["longest"]), ""])
        for lvl, sec in A["by_level"].items():
            w.writerow(["Level", lvl, int(sec), analysis.fmt_dur(sec), ""])
        for cat, sec in A["by_category"].items():
            w.writerow(["Kategorie", cat, int(sec), analysis.fmt_dur(sec), ""])
        for app, sec in A["by_app"].items():
            w.writerow(["Programm", app, int(sec), analysis.fmt_dur(sec), ""])
        for dom, sec in A["by_domain"].items():
            w.writerow(["Webseite", dom, int(sec), analysis.fmt_dur(sec), ""])
        for fl in A["flapping"]:
            w.writerow(["Doppelarbeit (Pendeln)", f"{fl['a']} <-> {fl['b']}", fl["count"],
                        analysis.fmt_dur(fl["time"]), f"{fl['count']}x Hin-und-Her"])
        for sq in A["sequences"]:
            w.writerow(["Wiederkehrender Ablauf", " -> ".join(sq["labels"]), sq["count"],
                        analysis.fmt_dur(sq["approx_time"]), f"{sq['count']}x"])
        for b in A["batching"]:
            w.writerow(["Häufig geöffnet", b["key"], b["visits"],
                        analysis.fmt_dur(b["duration"]), f"Ø {analysis.fmt_dur(b['avg'])}"])
        for hour, cats in A["hourly_level"].items():
            for lvl, sec in cats.items():
                w.writerow([f"Stunde {hour:02d}", lvl, int(sec), analysis.fmt_dur(sec), ""])
    return path
