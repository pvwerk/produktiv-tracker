# updater.py — automatische Updates über das öffentliche GitHub-Release "latest"
# Prüft eine kleine version.json im Release; bei neuer Build-Nummer wird die neue
# .exe geladen und per kleinem Batch-Skript ausgetauscht (Windows).
import os
import sys
import json
import tempfile
import subprocess
import urllib.request

REPO = "pvwerk/produktiv-tracker"
BASE = f"https://github.com/{REPO}/releases/latest/download"
VERSION_URL = BASE + "/version.json"
EXE_NAME = "Produktivitaets-Tracker.exe"
EXE_URL = BASE + "/" + EXE_NAME


def local_build():
    try:
        from _buildinfo import BUILD_ID
        return BUILD_ID
    except Exception:
        return "dev"


def is_frozen():
    return getattr(sys, "frozen", False)


def _get(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "ProduktivTracker"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def remote_build():
    """Build-Nummer der neuesten Version oder None."""
    try:
        data = json.loads(_get(VERSION_URL).decode("utf-8"))
        return str(data.get("build")) if data.get("build") else None
    except Exception:
        return None


def check_update():
    """Gibt die neue Build-Nummer zurück, wenn ein Update verfügbar ist, sonst None."""
    if not is_frozen():
        return None  # im Entwicklungsmodus nicht updaten
    local = local_build()
    remote = remote_build()
    if remote and remote != "dev" and remote != local:
        return remote
    return None


def apply_update():
    """Lädt die neue .exe und startet einen Austausch + Neustart. Gibt True zurück,
    wenn der Prozess angestoßen wurde (Aufrufer soll danach die App beenden)."""
    if not is_frozen():
        return False
    exe_path = sys.executable
    exe_dir = os.path.dirname(exe_path)
    new_path = os.path.join(exe_dir, EXE_NAME + ".new")
    # Download
    data = _get(EXE_URL, timeout=120)
    with open(new_path, "wb") as f:
        f.write(data)
    # Austausch-Skript
    bat = os.path.join(tempfile.gettempdir(), "pt_update.bat")
    name = os.path.basename(exe_path)
    with open(bat, "w", encoding="ascii", errors="ignore") as f:
        f.write(
            "@echo off\r\n"
            "timeout /t 1 /nobreak >nul\r\n"
            ":loop\r\n"
            f'tasklist /fi "imagename eq {name}" | find /i "{name}" >nul && '
            "(timeout /t 1 /nobreak >nul & goto loop)\r\n"
            f'move /y "{new_path}" "{exe_path}" >nul\r\n'
            f'start "" "{exe_path}"\r\n'
            'del "%~f0"\r\n'
        )
    DETACHED = 0x00000008
    NEW_GROUP = 0x00000200
    NO_WINDOW = 0x08000000
    subprocess.Popen(["cmd", "/c", bat],
                     creationflags=DETACHED | NEW_GROUP | NO_WINDOW,
                     close_fds=True)
    return True
