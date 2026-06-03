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


def data_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def db_path():
    return os.path.join(data_dir(), "tracker.db")


def config_path():
    return os.path.join(data_dir(), "config.json")


def load_config():
    """Lädt config.json, legt sie beim ersten Start mit Defaults an."""
    path = config_path()
    cfg = {
        "sample_interval": DEFAULT_SAMPLE_INTERVAL,
        "idle_threshold": DEFAULT_IDLE_THRESHOLD,
        "process_categories": DEFAULT_PROCESS_CATEGORIES,
        "domain_categories": DEFAULT_DOMAIN_CATEGORIES,
        "agfeo_process_hints": AGFEO_PROCESS_HINTS,
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
