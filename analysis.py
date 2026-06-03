# analysis.py — Auswertung der Messdaten
import time
from datetime import datetime, timedelta
from collections import defaultdict


def day_bounds(dt=None):
    dt = dt or datetime.now()
    start = datetime(dt.year, dt.month, dt.day)
    end = start + timedelta(days=1)
    return start.timestamp(), end.timestamp()


def range_bounds(start_date, end_date):
    s = datetime(start_date.year, start_date.month, start_date.day)
    e = datetime(end_date.year, end_date.month, end_date.day) + timedelta(days=1)
    return s.timestamp(), e.timestamp()


def fmt_dur(seconds):
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def aggregate(samples):
    total = 0.0
    active = 0.0
    idle = 0.0
    by_category = defaultdict(float)
    by_app = defaultdict(float)
    by_domain = defaultdict(float)
    hourly = defaultdict(lambda: defaultdict(float))  # stunde -> kategorie -> sek
    # Aufgaben-Wechsel + Häufigkeit kurzer Besuche (Batching-Potenzial)
    visits = defaultdict(int)        # (kategorie/app) -> Anzahl getrennter Besuche
    switches = 0

    last_key = None
    for s in samples:
        dur = float(s["duration"] or 0)
        if dur <= 0 or dur > 600:  # unplausible Lücken (PC aus etc.) kappen
            dur = min(max(dur, 0), 600)
        total += dur
        if s["idle"]:
            idle += dur
            key = "Abwesend"
        else:
            active += dur
            cat = s["category"] or "Unbekannt"
            by_category[cat] += dur
            if s["process"]:
                by_app[s["process"]] += dur
            if s["domain"]:
                by_domain[s["domain"]] += dur
            hour = datetime.fromtimestamp(s["ts"]).hour
            hourly[hour][cat] += dur
            key = s["domain"] or s["process"] or cat
        if key != last_key:
            switches += 1
            visits[key] += 1
            last_key = key

    # Häufig unterbrochene Tätigkeiten (viele Besuche, je kurz) → Batching-Kandidaten
    batching = []
    for key, cnt in visits.items():
        if key in ("Abwesend", "", None):
            continue
        dur = by_domain.get(key, 0) or by_app.get(key, 0)
        if cnt >= 5 and dur > 0:
            batching.append({"key": key, "visits": cnt, "duration": dur,
                             "avg": dur / cnt})
    batching.sort(key=lambda x: x["visits"], reverse=True)

    return {
        "total": total, "active": active, "idle": idle,
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
        "by_app": dict(sorted(by_app.items(), key=lambda x: -x[1])),
        "by_domain": dict(sorted(by_domain.items(), key=lambda x: -x[1])),
        "hourly": {h: dict(c) for h, c in sorted(hourly.items())},
        "switches": switches,
        "batching": batching[:10],
    }


def optimization_hints(agg):
    hints = []
    active = agg["active"] or 1
    # Ablenkung
    distract = agg["by_category"].get("Privat/Ablenkung", 0)
    if distract > 0:
        hints.append(f"Privat/Ablenkung: {fmt_dur(distract)} "
                     f"({distract/active*100:.0f}% der aktiven Zeit).")
    # E-Mail-Fragmentierung
    for b in agg["batching"]:
        hints.append(
            f"'{b['key']}' wurde {b['visits']}x geoeffnet (Durchschnitt {fmt_dur(b['avg'])} je Besuch, "
            f"gesamt {fmt_dur(b['duration'])}). Buendeln spart Wechselzeit.")
    # Viele Wechsel insgesamt
    if agg["switches"] > 120:
        hints.append(f"Sehr viele Aufgabenwechsel ({agg['switches']}). "
                     f"Feste Zeitblöcke je Tätigkeit reduzieren Reibung.")
    # Leerlauf
    if agg["idle"] > 0 and agg["total"] > 0:
        hints.append(f"Abwesend/Leerlauf: {fmt_dur(agg['idle'])} "
                     f"({agg['idle']/agg['total']*100:.0f}% der erfassten Zeit).")
    if not hints:
        hints.append("Keine auffälligen Muster — gute, fokussierte Arbeitsweise.")
    return hints
