# charts.py — Diagramme auf matplotlib-Figure (ohne pyplot, für GUI + PDF nutzbar)
from analysis import fmt_dur
from config import LEVEL_COLORS

BLUE = "#2563eb"
GREEN = "#16a34a"
RED = "#ef4444"
GREY = "#9ca3af"


def _short(s, n=30):
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def _barh(ax, data, title, color=BLUE, top=8, unit_minutes=True):
    items = list(data.items())[:top]
    if not items:
        ax.text(0.5, 0.5, "keine Daten", ha="center", va="center", color=GREY)
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.axis("off")
        return
    labels = [_short(k) for k, _ in items]
    vals = [(v / 60.0 if unit_minutes else v) for _, v in items]
    y = range(len(labels))
    ax.barh(list(y), vals, color=color)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Minuten" if unit_minutes else "", fontsize=8)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.tick_params(axis="x", labelsize=7)


def draw_overview(fig, A, period_label=""):
    fig.clear()
    fig.suptitle(f"Überblick — {period_label}", fontsize=12, fontweight="bold")
    # Kopfzahlen
    axh = fig.add_axes([0.06, 0.82, 0.88, 0.12]); axh.axis("off")
    f = A["focus"]
    axh.text(0, 0.7,
             f"Aktiv: {fmt_dur(A['active'])}    Abwesend: {fmt_dur(A['idle'])}    "
             f"Aufgaben: {A.get('task_count', 0)}    Wechsel: {A['switches']}    Fokus-Anteil: {f['focus_quote']*100:.0f}%",
             fontsize=10, va="center")
    axh.text(0, 0.2,
             f"Deep-Work-Blöcke (≥25min): {f['deepwork_count']}    "
             f"längster Block: {fmt_dur(f['longest'])}    "
             f"geschätzt verlorene Zeit: ~{fmt_dur(A['lost_estimate'])}",
             fontsize=9, va="center", color="#374151")
    # Kategorien
    ax1 = fig.add_axes([0.30, 0.46, 0.64, 0.30])
    _barh(ax1, A["by_category"], "Zeit je Kategorie")
    # Level-Verteilung (Donut)
    ax2 = fig.add_axes([0.06, 0.08, 0.34, 0.30])
    lv = A["by_level"]
    order = ["produktiv", "neutral", "ablenkung"]
    vals = [lv.get(k, 0) for k in order]
    if sum(vals) > 0:
        ax2.pie(vals, labels=[k.capitalize() for k in order],
                colors=[LEVEL_COLORS[k] for k in order],
                autopct=lambda p: f"{p:.0f}%", textprops={"fontsize": 8},
                wedgeprops={"width": 0.42})
        ax2.set_title("Produktiv / Neutral / Ablenkung", fontsize=9, fontweight="bold")
    else:
        ax2.axis("off")
    # Top Webseiten
    ax3 = fig.add_axes([0.52, 0.08, 0.42, 0.30])
    _barh(ax3, A["by_domain"], "Top Webseiten", color="#0ea5e9")


def draw_focus(fig, A, period_label=""):
    fig.clear()
    fig.suptitle("Fokus & Ablenkung", fontsize=12, fontweight="bold")
    f = A["focus"]
    ax = fig.add_axes([0.08, 0.55, 0.84, 0.32])
    blocks = sorted(f["blocks"], reverse=True)[:15]
    if blocks:
        mins = [b / 60.0 for b in blocks]
        ax.bar(range(len(mins)), mins, color=GREEN)
        ax.axhline(25, color=RED, ls="--", lw=1, label="Deep-Work-Schwelle (25 min)")
        ax.axhline(15, color="#f59e0b", ls=":", lw=1, label="Fokus-Schwelle (15 min)")
        ax.set_ylabel("Block-Länge (min)", fontsize=8)
        ax.set_xlabel("Arbeitsblöcke (längste zuerst)", fontsize=8)
        ax.legend(fontsize=7)
        ax.set_title("Wie lange am Stück konzentriert gearbeitet?", fontsize=10, fontweight="bold")
    else:
        ax.axis("off"); ax.text(0.5, 0.5, "keine Daten", ha="center", color=GREY)
    axt = fig.add_axes([0.08, 0.08, 0.84, 0.40]); axt.axis("off")
    lines = [
        f"Fokus-Anteil: {f['focus_quote']*100:.0f}% der aktiven Zeit",
        f"Fokusblöcke (≥15 min): {f['focus_count']}    davon Deep Work (≥25 min): {f['deepwork_count']}",
        f"Längster Block: {fmt_dur(f['longest'])}    Ø Segment: {fmt_dur(f['avg_segment'])}",
        f"Aufgabenwechsel: {A['switches']}  (~{f['switches_per_hour']:.0f} pro aktive Stunde)",
        f"Unterbrechungen (Fokus → Ablenkung/Pause): {A['interruptions']}",
        "",
        f"Geschätzt verlorene Zeit durch Wechseln: ~{fmt_dur(A['lost_estimate'])}",
    ]
    y = 0.95
    for ln in lines:
        axt.text(0, y, ln, fontsize=10, va="top"); y -= 0.11


def draw_workflow(fig, A, period_label=""):
    fig.clear()
    fig.suptitle("Workflow-Probleme: Doppelarbeit & wiederkehrende Abläufe",
                 fontsize=12, fontweight="bold")
    # Flapping
    ax = fig.add_axes([0.34, 0.58, 0.60, 0.30])
    fl = A["flapping"]
    if fl:
        labels = [_short(f"{x['a']} ↔ {x['b']}", 34) for x in fl]
        vals = [x["count"] for x in fl]
        y = range(len(labels))
        ax.barh(list(y), vals, color=RED)
        ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Hin-und-Her-Wechsel", fontsize=8)
        ax.set_title("Pendeln zwischen zwei Tools (oft = manuelles Übertragen)",
                     fontsize=9, fontweight="bold")
    else:
        ax.axis("off"); ax.text(0.5, 0.5, "kein auffälliges Pendeln", ha="center", color=GREY)
    # Sequenzen als Text
    axt = fig.add_axes([0.06, 0.06, 0.88, 0.44]); axt.axis("off")
    axt.text(0, 0.98, "Wiederkehrende Abläufe (Automatisierungs-Kandidaten):",
             fontsize=10, fontweight="bold", va="top")
    y = 0.86
    if A["sequences"]:
        for sq in A["sequences"][:6]:
            txt = "  •  " + " → ".join(_short(x, 18) for x in sq["labels"]) + f"   ({sq['count']}x)"
            axt.text(0, y, txt, fontsize=9, va="top"); y -= 0.10
    else:
        axt.text(0, y, "  keine wiederkehrenden Mehr-Schritt-Abläufe erkannt", fontsize=9,
                 va="top", color=GREY)


def draw_timeline(fig, A, period_label=""):
    fig.clear()
    fig.suptitle("Tagesverlauf", fontsize=12, fontweight="bold")
    ax = fig.add_axes([0.10, 0.42, 0.84, 0.46])
    hours = list(range(24))
    hl = A["hourly_level"]
    levels = ["produktiv", "neutral", "ablenkung"]
    bottoms = [0] * 24
    any_data = False
    for lv in levels:
        vals = [hl.get(h, {}).get(lv, 0) / 60.0 for h in hours]
        if sum(vals) > 0:
            any_data = True
        ax.bar(hours, vals, bottom=bottoms, color=LEVEL_COLORS[lv], label=lv.capitalize())
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax.set_xticks(hours); ax.set_xticklabels([str(h) for h in hours], fontsize=7)
    ax.set_xlabel("Stunde", fontsize=8); ax.set_ylabel("Minuten", fontsize=8)
    ax.legend(fontsize=7)
    ax.set_title("Wann wurde produktiv / neutral / abgelenkt gearbeitet?",
                 fontsize=10, fontweight="bold")
    if not any_data:
        ax.text(0.5, 0.5, "keine Daten", transform=ax.transAxes, ha="center", color=GREY)
    ax2 = fig.add_axes([0.10, 0.06, 0.84, 0.26])
    _barh(ax2, A["by_app"], "Top Programme", color="#7c3aed", top=7)


def draw_trend(fig, days):
    """days: Liste von dicts {label, active_min, focus_pct, switches, flapping}."""
    fig.clear()
    fig.suptitle("Wochen-Trend (letzte 7 Tage)", fontsize=12, fontweight="bold")
    if not days:
        fig.text(0.5, 0.5, "keine Daten", ha="center", color=GREY)
        return
    x = list(range(len(days)))
    labels = [d["label"] for d in days]
    # oben: aktive Minuten + Fokus-%
    ax = fig.add_axes([0.10, 0.56, 0.80, 0.32])
    ax.bar(x, [d["active_min"] for d in days], color="#93c5fd", label="aktive Minuten")
    ax.set_ylabel("aktive Minuten", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7)
    ax2 = ax.twinx()
    ax2.plot(x, [d["focus_pct"] for d in days], color=GREEN, marker="o", label="Fokus-%")
    ax2.set_ylabel("Fokus-%", fontsize=8, color=GREEN)
    ax2.set_ylim(0, 100)
    ax.set_title("Aktive Zeit & Fokus-Anteil", fontsize=10, fontweight="bold")
    # unten: Wechsel + Flapping
    axb = fig.add_axes([0.10, 0.10, 0.80, 0.34])
    axb.bar([i - 0.2 for i in x], [d["switches"] for d in days], width=0.4,
            color="#f59e0b", label="Aufgabenwechsel")
    axb.bar([i + 0.2 for i in x], [d["flapping"] for d in days], width=0.4,
            color=RED, label="Doppelarbeit-Pendeln")
    axb.set_xticks(x); axb.set_xticklabels(labels, fontsize=7)
    axb.legend(fontsize=7)
    axb.set_title("Aufgabenwechsel & Doppelarbeit", fontsize=10, fontweight="bold")
