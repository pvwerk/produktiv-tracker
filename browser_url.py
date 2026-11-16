# browser_url.py — liest die aktuelle Browser-Adresse (Host) per UI-Automation
# Chrome/Edge/Brave (Chromium) und Firefox. Reduziert auf die Hauptadresse,
# z.B. "https://www.westnetz.de/kontakt?x=1" -> "www.westnetz.de".
#
# Funktioniert ohne Browser-Erweiterung über die Windows-UI-Automation.
# Falls die Adresse nicht lesbar ist, wird None geliefert (Aufrufer nutzt dann
# den Fenstertitel als Ersatz).
import subprocess
import sys
from urllib.parse import urlparse

try:
    if sys.platform == "darwin":
        raise ImportError("uiautomation gibt es nur unter Windows")
    import uiautomation as auto
except Exception:  # pragma: no cover
    auto = None

# 16.11.2026 macOS: Die Adresse kommt per AppleScript aus dem Browser. macOS
# fragt dafür einmal je Browser "... möchte ... steuern" -- ohne Zustimmung
# bleibt die Adresse leer und die Zeit zählt als "Web". Firefox kennt kein
# AppleScript für die Adresse; dort bleibt es bei "Web".
# Prozessname (klein) -> AppleScript-Ausdruck für die Adresse des aktiven Tabs
_MAC_SKRIPTE = {
    "safari": 'tell application "Safari" to return URL of front document',
    "google chrome": 'tell application "Google Chrome" to return URL of active tab of front window',
    "microsoft edge": 'tell application "Microsoft Edge" to return URL of active tab of front window',
    "brave browser": 'tell application "Brave Browser" to return URL of active tab of front window',
    "arc": 'tell application "Arc" to return URL of active tab of front window',
    "opera": 'tell application "Opera" to return URL of active tab of front window',
}


def _mac_host(exe):
    skript = _MAC_SKRIPTE.get((exe or "").lower())
    if not skript:
        return None
    # "tell application" STARTET ein Programm, das nicht läuft (16.11. im
    # Test so passiert: Safari ging auf). Deshalb nur fragen, wenn es läuft.
    programm = skript.split('"')[1]
    skript = 'if application "%s" is running then\n%s\nend if' % (programm, skript)
    try:
        r = subprocess.run(["/usr/bin/osascript", "-e", skript],
                           capture_output=True, text=True, timeout=3)
        if r.returncode != 0:
            return None
        return host_from_value(r.stdout.strip())
    except Exception:
        return None

# Namen der Adressleiste in verschiedenen Sprachen
_CHROMIUM_NAMES = (
    "address and search bar", "adress- und suchleiste", "adresse und suchleiste",
    "address bar",
)
_FIREFOX_NAMES = (
    "suche oder adresse eingeben", "search with google or enter address",
    "search or enter address", "mit google suchen oder adresse eingeben",
    "adresszeile",
)


def host_from_value(value):
    """Macht aus einem Adressleisten-Text den Host (Hauptadresse)."""
    if not value:
        return None
    v = value.strip()
    if not v or " " in v and "." not in v:
        return None
    # Wenn kein Schema da ist, eines ergänzen, damit urlparse den Host findet
    if "://" not in v:
        v = "http://" + v
    try:
        host = urlparse(v).hostname
    except Exception:
        host = None
    if not host:
        return None
    host = host.lower()
    # offensichtlichen Müll aussortieren
    if "." not in host:
        return None
    return host


def _looks_like_address(value):
    if not value:
        return False
    v = value.strip().lower()
    if " " in v and "://" not in v:
        # Suchbegriffe ignorieren (enthalten Leerzeichen, keine URL)
        if "." not in v:
            return False
    return ("." in v) or v.startswith("http")


def _find_address_edit(window, name_hints):
    """Sucht in einem Fenster das Adress-Eingabefeld (ControlType Edit)."""
    # 1) gezielt über bekannte Namen
    for nm in name_hints:
        try:
            edit = window.EditControl(Name=nm, searchDepth=25)
            if edit.Exists(0, 0):
                return edit
        except Exception:
            pass
    # 2) Fallback: alle Edit-Controls durchgehen, das wie eine URL aussieht
    try:
        edits = _all_edits(window, max_depth=25)
        for e in edits:
            try:
                val = e.GetValuePattern().Value
            except Exception:
                val = ""
            if _looks_like_address(val):
                return e
    except Exception:
        pass
    return None


def _all_edits(control, max_depth=20, _depth=0, acc=None):
    if acc is None:
        acc = []
    if _depth > max_depth or len(acc) > 400:
        return acc
    try:
        for child in control.GetChildren():
            try:
                if child.ControlTypeName == "EditControl":
                    acc.append(child)
            except Exception:
                pass
            _all_edits(child, max_depth, _depth + 1, acc)
    except Exception:
        pass
    return acc


def get_browser_host(hwnd, exe):
    """Liefert den Host des aktiven Browser-Tabs oder None."""
    if sys.platform == "darwin":
        return _mac_host(exe)
    if auto is None or not hwnd:
        return None
    try:
        window = auto.ControlFromHandle(hwnd)
        if window is None:
            return None
    except Exception:
        return None

    if exe == "firefox.exe":
        hints = _FIREFOX_NAMES
    else:
        hints = _CHROMIUM_NAMES

    try:
        edit = _find_address_edit(window, hints)
        if edit is None:
            return None
        try:
            value = edit.GetValuePattern().Value
        except Exception:
            value = edit.Name
        return host_from_value(value)
    except Exception:
        return None


def host_from_title(exe, title):
    """Notlösung: Browsertitel liefert keinen Host, nur den Seitentitel.
    Wir geben den bereinigten Seitentitel zurück (als 'domain unbekannt')."""
    if not title:
        return None
    t = title
    for suffix in (" — Mozilla Firefox", " - Mozilla Firefox", " - Google Chrome",
                   " – Google Chrome", " - Microsoft​ Edge", " - Microsoft Edge",
                   " and ", " — Brave", " - Brave"):
        if suffix in t:
            t = t.split(suffix)[0]
    return t.strip() or None
