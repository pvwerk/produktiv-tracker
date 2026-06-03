# config.py — Einstellungen + Kategorisierung
# Alles lokal. Eine benutzerbearbeitbare config.json wird im Datenordner abgelegt.
import os
import json

APP_NAME = "Produktivitaets-Tracker"
APP_TITLE = "Produktivitäts-Tracker"

# Sekunden zwischen zwei Messungen
DEFAULT_SAMPLE_INTERVAL = 3
# Ab so vielen Sekunden ohne Maus/Tastatur gilt die Zeit als "abwesend" (nicht produktiv)
DEFAULT_IDLE_THRESHOLD = 60

# Browser-Prozesse (Kleinschreibung)
BROWSER_PROCESSES = {"firefox.exe", "chrome.exe", "msedge.exe", "brave.exe", "opera.exe"}

# Standard-Kategorien: Prozessname -> Kategorie
DEFAULT_PROCESS_CATEGORIES = {
    "outlook.exe": "E-Mail",
    "hxoutlook.exe": "E-Mail",
    "thunderbird.exe": "E-Mail",
    "agfeo dashboard.exe": "Telefonie (AGFEO)",
    "dashboard.exe": "Telefonie (AGFEO)",
    "winword.exe": "Office",
    "excel.exe": "Office",
    "powerpnt.exe": "Office",
    "teams.exe": "Kommunikation",
    "ms-teams.exe": "Kommunikation",
    "explorer.exe": "System/Dateien",
}

# Hinweise, um die AGFEO-Software zu erkennen (Prozessname enthält einen dieser Texte)
AGFEO_PROCESS_HINTS = ["agfeo", "dashboard"]

# Domain (Host) -> Kategorie. Host wird auf Hauptadresse reduziert (z.B. www.westnetz.de)
DEFAULT_DOMAIN_CATEGORIES = {
    "mail.google.com": "E-Mail",
    "outlook.office.com": "E-Mail",
    "outlook.office365.com": "E-Mail",
    "web.de": "E-Mail",
    "gmx.net": "E-Mail",
    "youtube.com": "Privat/Ablenkung",
    "www.youtube.com": "Privat/Ablenkung",
    "facebook.com": "Privat/Ablenkung",
    "instagram.com": "Privat/Ablenkung",
}

# Produktivitäts-Einordnung je Kategorie: "produktiv" | "neutral" | "ablenkung".
# WICHTIG: Das ist KEINE Leistungsbewertung, sondern hilft NUR ihr selbst, Muster zu sehen.
DEFAULT_PRODUCTIVITY_LEVELS = {
    "Telefonie (AGFEO)": "produktiv",
    "Office": "produktiv",
    "E-Mail": "neutral",
    "Web": "neutral",
    "Kommunikation": "neutral",
    "System/Dateien": "neutral",
    "Sonstige Programme": "neutral",
    "Unbekannt": "neutral",
    "Privat/Ablenkung": "ablenkung",
}

LEVEL_COLORS = {"produktiv": "#16a34a", "neutral": "#3b82f6", "ablenkung": "#ef4444",
                "Abwesend": "#9ca3af"}

# Fokus-/Auswertungs-Parameter (in Minuten bzw. Sekunden)
DEFAULT_FOCUS_MIN_MINUTES = 15      # ab hier gilt ein ununterbrochener Block als "Fokus"
DEFAULT_DEEPWORK_MIN_MINUTES = 25   # ab hier "Deep Work"
DEFAULT_IDLE_TOLERANCE = 120        # kurze Pausen (< X s) brechen einen Fokusblock nicht
DEFAULT_SWITCH_PENALTY = 45         # geschätzte verlorene Sekunden je unnötigem Wechsel
# Datenschutz: Fenstertitel speichern? (für Sequenz-Erkennung hilfreich, aber inhaltsnah)
DEFAULT_STORE_TITLES = True


def data_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def db_path():
    return os.path.join(data_dir(), "tracker.db")


def config_path():
    return os.path.join(data_dir(), "config.json")


def _consent_path():
    return os.path.join(data_dir(), ".consent")


def has_consent():
    return os.path.exists(_consent_path())


def set_consent():
    try:
        with open(_consent_path(), "w", encoding="utf-8") as f:
            f.write("ok")
    except Exception:
        pass


def load_config():
    """Lädt config.json, legt sie beim ersten Start mit Defaults an."""
    path = config_path()
    cfg = {
        "sample_interval": DEFAULT_SAMPLE_INTERVAL,
        "idle_threshold": DEFAULT_IDLE_THRESHOLD,
        "process_categories": DEFAULT_PROCESS_CATEGORIES,
        "domain_categories": DEFAULT_DOMAIN_CATEGORIES,
        "agfeo_process_hints": AGFEO_PROCESS_HINTS,
        "productivity_levels": DEFAULT_PRODUCTIVITY_LEVELS,
        "focus_min_minutes": DEFAULT_FOCUS_MIN_MINUTES,
        "deepwork_min_minutes": DEFAULT_DEEPWORK_MIN_MINUTES,
        "idle_tolerance": DEFAULT_IDLE_TOLERANCE,
        "switch_penalty": DEFAULT_SWITCH_PENALTY,
        "store_window_titles": DEFAULT_STORE_TITLES,
    }
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                stored = json.load(f)
            # gespeicherte Werte über die Defaults legen
            for k, v in stored.items():
                cfg[k] = v
        except Exception:
            pass
    else:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return cfg
