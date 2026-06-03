# report.py — Export als CSV und PDF (mit Diagrammen)
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

import analysis


def export_csv(samples, agg, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Typ", "Name", "Sekunden", "Lesbar"])
        w.writerow(["Gesamt", "Erfasst", int(agg["total"]), analysis.fmt_dur(agg["total"])])
        w.writerow(["Gesamt", "Aktiv", int(agg["active"]), analysis.fmt_dur(agg["active"])])
        w.writerow(["Gesamt", "Abwesend", int(agg["idle"]), analysis.fmt_dur(agg["idle"])])
        w.writerow(["Gesamt", "Aufgabenwechsel", agg["switches"], ""])
        for cat, sec in agg["by_category"].items():
            w.writerow(["Kategorie", cat, int(sec), analysis.fmt_dur(sec)])
        for app, sec in agg["by_app"].items():
            w.writerow(["Programm", app, int(sec), analysis.fmt_dur(sec)])
        for dom, sec in agg["by_domain"].items():
            w.writerow(["Webseite", dom, int(sec), analysis.fmt_dur(sec)])
        # Zeitleiste je Stunde + Kategorie
        for hour, cats in agg["hourly"].items():
            for cat, sec in cats.items():
                w.writerow([f"Stunde {hour:02d}", cat, int(sec), analysis.fmt_dur(sec)])
    return path


def _bar(ax, data, title, top=10):
    items = list(data.items())[:top]
    if not items:
        ax.text(0.5, 0.5, "keine Daten", ha="center", va="center")
        ax.set_title(title)
        ax.axis("off")
        return
    labels = [k if len(k) <= 28 else k[:27] + "…" for k, _ in items]
    vals = [v / 60.0 for _, v in items]  # Minuten
    y = range(len(labels))
    ax.barh(list(y), vals, color="#2563eb")
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Minuten")
    ax.set_title(title, fontsize=11, fontweight="bold")


def export_pdf(agg, period_label, path):
    hints = analysis.optimization_hints(agg)
    with PdfPages(path) as pdf:
        # Seite 1: Überblick + Kategorien
        fig = plt.figure(figsize=(8.27, 11.69))  # A4
        fig.suptitle(f"Produktivitäts-Auswertung\n{period_label}", fontsize=14, fontweight="bold")
        ax_info = fig.add_axes([0.08, 0.80, 0.84, 0.10])
        ax_info.axis("off")
        ax_info.text(
            0, 1,
            f"Erfasst: {analysis.fmt_dur(agg['total'])}    "
            f"Aktiv: {analysis.fmt_dur(agg['active'])}    "
            f"Abwesend: {analysis.fmt_dur(agg['idle'])}    "
            f"Aufgabenwechsel: {agg['switches']}",
            fontsize=10, va="top")
        ax1 = fig.add_axes([0.30, 0.45, 0.62, 0.30])
        _bar(ax1, agg["by_category"], "Zeit je Kategorie")
        ax2 = fig.add_axes([0.30, 0.08, 0.62, 0.30])
        _bar(ax2, agg["by_domain"], "Top Webseiten")
        pdf.savefig(fig)
        plt.close(fig)

        # Seite 2: Programme + Zeitleiste
        fig2 = plt.figure(figsize=(8.27, 11.69))
        ax3 = fig2.add_axes([0.30, 0.62, 0.62, 0.30])
        _bar(ax3, agg["by_app"], "Top Programme")
        # Zeitleiste je Stunde (aktive Minuten)
        ax4 = fig2.add_axes([0.10, 0.20, 0.82, 0.30])
        hours = list(range(24))
        mins = []
        for h in hours:
            cats = agg["hourly"].get(h, {})
            mins.append(sum(cats.values()) / 60.0)
        ax4.bar(hours, mins, color="#16a34a")
        ax4.set_xticks(hours)
        ax4.set_xticklabels([str(h) for h in hours], fontsize=7)
        ax4.set_xlabel("Stunde")
        ax4.set_ylabel("aktive Minuten")
        ax4.set_title("Aktivität über den Tag", fontsize=11, fontweight="bold")
        pdf.savefig(fig2)
        plt.close(fig2)

        # Seite 3: Optimierungs-Hinweise
        fig3 = plt.figure(figsize=(8.27, 11.69))
        ax5 = fig3.add_axes([0.08, 0.08, 0.84, 0.84])
        ax5.axis("off")
        ax5.text(0, 1, "Beobachtungen & Optimierungs-Vorschläge", fontsize=13,
                 fontweight="bold", va="top")
        y = 0.93
        for h in hints:
            ax5.text(0, y, "• " + h, fontsize=10, va="top", wrap=True)
            y -= 0.06
        ax5.text(0, 0.04, "Alle Daten stammen ausschließlich von diesem PC und bleiben lokal.",
                 fontsize=8, style="italic", va="top")
        pdf.savefig(fig3)
        plt.close(fig3)
    return path
