# analysis.py — Auswertungs-Engine
# Kern: aus den Roh-Messungen einen Segment-Stream bauen und daraus Workflow-
# Kennzahlen ableiten: Fokus/Fragmentierung, App-Flapping (Doppelarbeit zwischen
# zwei Tools), wiederkehrende Sequenzen (Automatisierungs-Kandidaten),
# Tageszeit-Muster, geschätzte verlorene Zeit.
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# Studien-Grundlage für die Schätzung verlorener Zeit (im UI zitiert):
# - Mark et al., CHI 2008: ~23 Min Refokussierung nach Unterbrechung.
# - APA / Rubinstein, Meyer & Evans 2001: Aufgabenwechsel kann bis zu 40 % der
#   produktiven Zeit kosten.
SOURCE_NOTE = ("Schätzung auf Basis von Studien (Mark et al., CHI 2008: ~23 Min "
               "Refokussierung nach Unterbrechung; APA/Meyer et al. 2001: Aufgaben-"
               "wechsel kostet bis zu 40 % der produktiven Zeit). Kein Messwert.")


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


def level_for(cfg, category):
    return (cfg or {}).get("productivity_levels", {}).get(category, "neutral")


def _activity_key(s):
    if s["idle"]:
        return "__idle__"
    return s["domain"] or s["process"] or s["category"] or "Unbekannt"


def _label_for_key(key, s):
    if key == "__idle__":
        return "Abwesend"
    return s["domain"] or s["process"] or s["category"] or "Unbekannt"


# ── Aufgaben-Erkennung ─────────────────────────────────────────────────
# Mehrere Fenster gehören zur SELBEN Aufgabe, wenn im Fenstertitel dieselbe
# "Schlagzeile" (z.B. Kundenname/Adresse) steht. Pro Seite/App kann in den
# Einstellungen ein Abgleich-Muster (Regex) definiert werden, das den
# Identifikator aus dem Titel zieht. Beispiel-Konfig (config.json):
#   "task_matchers": [
#     {"match": "verwaltung.mein-handwerker.de", "pattern": "Kunde:?\\s*([^|\\-–]+)"},
#     {"match": "westnetz.de", "pattern": "([0-9]{5,})"}
#   ]
# Ohne Treffer wird wie bisher nach Domain/Programm gruppiert.
def task_key(s, cfg):
    if s["idle"]:
        return "__idle__"
    matchers = (cfg or {}).get("task_matchers", []) or []
    title = s.get("title") or ""
    dom = (s.get("domain") or "").lower()
    proc = (s.get("process") or "").lower()
    for m in matchers:
        target = str(m.get("match") or "").strip().lower()
        if not target:
            continue
        if target in dom or target in proc:
            pat = m.get("pattern")
            token = None
            if pat:
                try:
                    mm = re.search(pat, title, re.IGNORECASE)
                    if mm:
                        token = mm.group(1) if mm.groups() else mm.group(0)
                except re.error:
                    token = None
            else:
                token = title  # kein Muster -> ganzer Titel als Identifikator
            if token:
                norm = re.sub(r"\s+", " ", token).strip().lower()
                if norm:
                    return "task:" + norm
    return _activity_key(s)


def task_label(key, s):
    if key == "__idle__":
        return "Abwesend"
    if isinstance(key, str) and key.startswith("task:"):
        return "🧩 " + key[5:].strip().title()
    return _label_for_key(key, s)


def build_segments(samples, cfg=None):
    """Fasst aufeinanderfolgende Messungen DERSELBEN Aufgabe zu Segmenten zusammen."""
    cfg = cfg or {}
    segs = []
    for s in samples:
        dur = float(s["duration"] or 0)
        if dur <= 0:
            continue
        if dur > 600:  # PC war aus / große Lücke -> kappen
            dur = 600
        key = task_key(s, cfg)
        if segs and segs[-1]["key"] == key:
            segs[-1]["dur"] += dur
            segs[-1]["end"] = s["ts"]
        else:
            segs.append({
                "key": key,
                "label": task_label(key, s),
                "app": s["process"] or "",
                "domain": s["domain"] or "",
                "category": "Abwesend" if s["idle"] else (s["category"] or "Unbekannt"),
                "idle": bool(s["idle"]),
                "dur": dur,
                "start": s["ts"] - dur,
                "end": s["ts"],
            })
    return segs


def _focus_blocks(segments, idle_tolerance, pause_tolerance):
    """Blöcke fokussierter Arbeit. Kurze Pausen (Idle) UND kurze Abstecher in eine
    andere Tätigkeit (< pause_tolerance) brechen den Block nicht ab — die Aufgabe
    wird pausiert und fortgesetzt, sobald sie wieder aktiv ist."""
    blocks = []
    cur = None  # {key, dur, start, end}
    for s in segments:
        if s["idle"]:
            if cur and s["dur"] < idle_tolerance:
                continue  # kurze Pause -> Block bleibt offen
            if cur:
                blocks.append(cur)
                cur = None
            continue
        if cur and s["key"] == cur["key"]:
            cur["dur"] += s["dur"]
            cur["end"] = s["end"]
        elif cur and s["dur"] < pause_tolerance:
            continue  # kurzer Abstecher -> Pause, Block bleibt offen
        else:
            if cur:
                blocks.append(cur)
            cur = {"key": s["key"], "label": s["label"], "dur": s["dur"],
                   "start": s["start"], "end": s["end"]}
    if cur:
        blocks.append(cur)
    return blocks


def _task_stream(active_segs, pause_tolerance):
    """Aufgaben-Folge für Wechsel/Flapping/Sequenzen: kurze Abstecher, die von
    DERSELBEN Aufgabe umschlossen sind, werden entfernt (Pause statt Wechsel)."""
    filtered = []
    for idx, s in enumerate(active_segs):
        if filtered and s["dur"] < pause_tolerance and s["key"] != filtered[-1]["key"]:
            nxt = active_segs[idx + 1]["key"] if idx + 1 < len(active_segs) else None
            if filtered[-1]["key"] == nxt:
                continue  # eingeschlossener kurzer Abstecher -> überspringen
        filtered.append(s)
    active_keys, visits = [], defaultdict(int)
    for s in filtered:
        if not active_keys or active_keys[-1] != s["key"]:
            active_keys.append(s["key"])
            visits[s["key"]] += 1
    return active_keys, visits


def _flapping(active_keys, labels, durs):
    """Erkennt A-B-A-Pendeln zwischen zwei Tätigkeiten (Doppelarbeit/Übertragung)."""
    pairs = defaultdict(lambda: {"count": 0, "keys": None})
    for i in range(1, len(active_keys) - 1):
        a, b, c = active_keys[i - 1], active_keys[i], active_keys[i + 1]
        if a == c and a != b:
            pk = frozenset((a, b))
            pairs[pk]["count"] += 1
            pairs[pk]["keys"] = (a, b)
    out = []
    for pk, info in pairs.items():
        a, b = info["keys"]
        time_ab = durs.get(a, 0) + durs.get(b, 0)
        out.append({
            "a": labels.get(a, a), "b": labels.get(b, b),
            "count": info["count"], "time": time_ab,
        })
    out.sort(key=lambda x: x["count"], reverse=True)
    return out[:8]


def _sequences(active_keys, labels, durs, min_count=3):
    """Wiederkehrende Tätigkeits-Folgen (Automatisierungs-Kandidaten)."""
    grams = Counter()
    positions = defaultdict(list)
    for n in (4, 3):
        for i in range(len(active_keys) - n + 1):
            g = tuple(active_keys[i:i + n])
            # echte Mehr-Schritt-Abläufe: mind. 3 verschiedene Tätigkeiten.
            # Reines A-B-A-Pendeln wird bereits als "Flapping" erfasst.
            if len(set(g)) < 3:
                continue
            grams[g] += 1
            positions[g].append(i)
    candidates = [(g, c) for g, c in grams.items() if c >= min_count]
    # längere zuerst, dann häufigere
    candidates.sort(key=lambda x: (len(x[0]), x[1]), reverse=True)
    out = []
    used_short = set()
    for g, c in candidates:
        # 3er-Gramm überspringen, wenn es in einem bereits gelisteten 4er steckt
        if len(g) == 3 and g in used_short:
            continue
        if len(g) == 4:
            for i in range(2):
                used_short.add(g[i:i + 3])
        approx = c * sum(durs.get(k, 0) / max(1, _key_count(active_keys, k)) for k in g)
        out.append({
            "labels": [labels.get(k, k) for k in g],
            "count": c, "approx_time": approx,
        })
        if len(out) >= 8:
            break
    return out


def _key_count(keys, k):
    return max(1, keys.count(k))


def analyze(samples, cfg=None):
    cfg = cfg or {}
    idle_tol = float(cfg.get("idle_tolerance", 120))
    pause_tol = float(cfg.get("pause_tolerance", 90))
    focus_min = float(cfg.get("focus_min_minutes", 15)) * 60
    deep_min = float(cfg.get("deepwork_min_minutes", 25)) * 60
    penalty = float(cfg.get("switch_penalty", 45))

    total = active = idle = 0.0
    by_category = defaultdict(float)
    by_app = defaultdict(float)
    by_domain = defaultdict(float)
    by_level = defaultdict(float)
    hourly_level = defaultdict(lambda: defaultdict(float))  # stunde -> level -> sek
    interruptions = 0

    prev_level = None
    for s in samples:
        dur = float(s["duration"] or 0)
        if dur <= 0:
            continue
        if dur > 600:
            dur = 600
        total += dur
        if s["idle"]:
            idle += dur
            if prev_level == "produktiv":
                interruptions += 1
            prev_level = "idle"
        else:
            active += dur
            cat = s["category"] or "Unbekannt"
            lvl = level_for(cfg, cat)
            by_category[cat] += dur
            by_level[lvl] += dur
            if s["process"]:
                by_app[s["process"]] += dur
            if s["domain"]:
                by_domain[s["domain"]] += dur
            hourly_level[datetime.fromtimestamp(s["ts"]).hour][lvl] += dur
            if prev_level == "produktiv" and lvl == "ablenkung":
                interruptions += 1
            prev_level = lvl

    # Segmente nach Aufgabe (mehrere Fenster derselben Aufgabe = 1 Segment)
    segments = build_segments(samples, cfg)
    active_segs = [s for s in segments if not s["idle"]]
    labels = {}
    seg_durs = defaultdict(float)
    for s in active_segs:
        labels[s["key"]] = s["label"]
        seg_durs[s["key"]] += s["dur"]
    # Aufgaben-Folge mit Pause/Resume (kurze Abstecher entfernt)
    active_keys, visits = _task_stream(active_segs, pause_tol)
    switches = max(0, len(active_keys) - 1)
    task_count = len([k for k in seg_durs if k != "__idle__"])

    blocks = _focus_blocks(segments, idle_tol, pause_tol)
    focus_blocks = [b for b in blocks if b["dur"] >= focus_min]
    deepwork = [b for b in blocks if b["dur"] >= deep_min]
    focus_time = sum(b["dur"] for b in focus_blocks)
    longest = max((b["dur"] for b in blocks), default=0)

    flapping = _flapping(active_keys, labels, seg_durs)
    sequences = _sequences(active_keys, labels, seg_durs)

    # Batching: häufig kurz geöffnete Tätigkeiten
    batching = []
    for key, cnt in visits.items():
        if key in ("__idle__", "", None):
            continue
        dur = by_domain.get(key, 0) or by_app.get(key, 0) or seg_durs.get(key, 0)
        if cnt >= 5 and dur > 0:
            batching.append({"key": labels.get(key, key), "visits": cnt,
                             "duration": dur, "avg": dur / cnt})
    batching.sort(key=lambda x: x["visits"], reverse=True)

    lost = min(switches * penalty, 0.30 * active)

    tasks = sorted(
        ({"label": labels.get(k, k), "duration": d, "visits": visits.get(k, 1)}
         for k, d in seg_durs.items() if k != "__idle__"),
        key=lambda x: -x["duration"])[:12]

    return {
        "total": total, "active": active, "idle": idle, "switches": switches,
        "task_count": task_count, "tasks": tasks,
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
        "by_app": dict(sorted(by_app.items(), key=lambda x: -x[1])),
        "by_domain": dict(sorted(by_domain.items(), key=lambda x: -x[1])),
        "by_level": dict(by_level),
        "hourly_level": {h: dict(v) for h, v in sorted(hourly_level.items())},
        "focus": {
            "blocks": [b["dur"] for b in blocks],
            "focus_count": len(focus_blocks),
            "deepwork_count": len(deepwork),
            "focus_time": focus_time,
            "longest": longest,
            "focus_quote": (focus_time / active) if active else 0,
            "avg_segment": (active / (switches + 1)) if active else 0,
            "switches_per_hour": (switches / (active / 3600)) if active > 0 else 0,
        },
        "flapping": flapping,
        "sequences": sequences,
        "batching": batching[:10],
        "interruptions": interruptions,
        "lost_estimate": lost,
        "segments": segments,
    }


def best_focus_window(hourly_level):
    """Findet das beste zusammenhängende 2-Stunden-Fenster (meiste produktive Zeit)."""
    prod = {h: v.get("produktiv", 0) for h, v in hourly_level.items()}
    if not prod or sum(prod.values()) == 0:
        return None
    best_h, best_sum = None, -1
    for h in range(0, 23):
        s = prod.get(h, 0) + prod.get(h + 1, 0)
        if s > best_sum:
            best_sum, best_h = s, h
    if best_h is None or best_sum <= 0:
        return None
    return (best_h, best_h + 2)


def optimization_hints(A):
    hints = []
    active = A["active"] or 1
    f = A["focus"]
    win = best_focus_window(A.get("hourly_level", {}))
    if win:
        hints.append(f"Deine produktivsten Stunden: {win[0]:02d}–{win[1]:02d} Uhr. "
                     f"Leg anspruchsvolle Aufgaben bevorzugt in dieses Fenster.")
    if f["deepwork_count"] == 0 and active > 1800:
        hints.append("Heute kein echter Deep-Work-Block (≥ 25 Min am Stück) — der Tag war "
                     "stark zerstückelt. Versuch feste, ungestörte Fokusfenster.")
    elif f["focus_count"] > 0:
        hints.append(f"{f['focus_count']} Fokusblock(s), längster {fmt_dur(f['longest'])}. "
                     f"Fokus-Anteil {f['focus_quote']*100:.0f}% der aktiven Zeit.")
    if A["switches"] > 0:
        hints.append(f"{A['switches']} Aufgabenwechsel ({f['switches_per_hour']:.0f}/Std). "
                     f"Geschätzt verlorene Zeit dadurch: ~{fmt_dur(A['lost_estimate'])}. ({SOURCE_NOTE})")
    for fl in A["flapping"][:3]:
        hints.append(f"Häufiges Hin-und-Her zwischen '{fl['a']}' und '{fl['b']}' "
                     f"({fl['count']}x). Das deutet auf manuelles Übertragen zwischen zwei "
                     f"Tools hin — Kandidat für Automatisierung/Vorlage.")
    for sq in A["sequences"][:2]:
        hints.append("Wiederkehrender Ablauf: " + " -> ".join(sq["labels"]) +
                     f" ({sq['count']}x). Prüfen, ob sich das standardisieren/automatisieren lässt.")
    for b in A["batching"][:2]:
        hints.append(f"'{b['key']}' {b['visits']}x geöffnet (Ø {fmt_dur(b['avg'])}). "
                     f"In feste Blöcke bündeln spart Wechselzeit.")
    distract = A["by_level"].get("ablenkung", 0)
    if distract > 0:
        hints.append(f"Ablenkung: {fmt_dur(distract)} ({distract/active*100:.0f}% der aktiven Zeit).")
    if A["idle"] > 0 and A["total"] > 0:
        hints.append(f"Abwesend/Leerlauf: {fmt_dur(A['idle'])} "
                     f"({A['idle']/A['total']*100:.0f}% der erfassten Zeit).")
    if not hints:
        hints.append("Keine auffälligen Muster — fokussierte, saubere Arbeitsweise.")
    return hints
