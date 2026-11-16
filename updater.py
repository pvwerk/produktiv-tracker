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
# 16.11.2026 macOS: eigene Versionsdatei, weil Windows- und Mac-Build getrennt
# laufen -- schlägt einer fehl, darf der andere kein Update anbieten, das es
# gar nicht gibt.
IS_MAC = sys.platform == "darwin"
MAC_VERSION_URL = BASE + "/version-mac.json"
MAC_ZIP_NAME = "Produktivitaets-Tracker-mac.zip"
MAC_ZIP_URL = BASE + "/" + MAC_ZIP_NAME


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
        data = json.loads(_get(MAC_VERSION_URL if IS_MAC else VERSION_URL).decode("utf-8"))
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
    if IS_MAC:
        return _apply_update_mac()
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
            # Alte Instanz aktiv beenden, dann warten bis sie wirklich weg ist.
            # taskkill als Sicherheitsnetz, falls sich die App nicht selbst beendet
            # (sonst kann die laufende .exe nicht ersetzt werden -> Updater haengt).
            f'taskkill /f /im "{name}" >nul 2>&1\r\n'
            ":loop\r\n"
            f'tasklist /fi "imagename eq {name}" | find /i "{name}" >nul 2>&1 && '
            f'(timeout /t 1 /nobreak >nul & taskkill /f /im "{name}" >nul 2>&1 & goto loop)\r\n'
            f'move /y "{new_path}" "{exe_path}" >nul\r\n'
            f'start "" "{exe_path}"\r\n'
            'del "%~f0"\r\n'
        )
    # CREATE_NO_WINDOW: Batch laeuft versteckt (kein schwarzes Fenster). Nicht mit
    # DETACHED_PROCESS kombinieren -> sonst erscheint doch ein Konsolenfenster.
    NO_WINDOW = 0x08000000
    NEW_GROUP = 0x00000200
    subprocess.Popen(["cmd", "/c", bat],
                     creationflags=NO_WINDOW | NEW_GROUP,
                     close_fds=True)
    return True


def _apply_update_mac():
    """macOS: neue .app laden, entpacken, nach Programmende austauschen, neu starten.

    Die alte .app wird nicht gelöscht, sondern in den Papierkorb des
    Benutzers gelegt (~/.Trash) -- so bleibt sie wiederherstellbar.
    """
    import autostart
    app = autostart.mac_app_pfad()
    if not app:
        return False
    arbeit = tempfile.mkdtemp(prefix="pt_update_")
    zip_pfad = os.path.join(arbeit, MAC_ZIP_NAME)
    with open(zip_pfad, "wb") as f:
        f.write(_get(MAC_ZIP_URL, timeout=180))
    # ditto erhält Programmpaket-Struktur und Signatur (unzip nicht zuverlässig)
    subprocess.run(["/usr/bin/ditto", "-x", "-k", zip_pfad, arbeit], check=True)
    neu = os.path.join(arbeit, os.path.basename(app))
    if not os.path.isdir(neu):
        kandidaten = [d for d in os.listdir(arbeit) if d.endswith(".app")]
        if not kandidaten:
            return False
        neu = os.path.join(arbeit, kandidaten[0])
    papierkorb = os.path.expanduser("~/.Trash/Produktivitaets-Tracker-alt-%d.app" % os.getpid())
    skript = os.path.join(arbeit, "austausch.sh")
    with open(skript, "w", encoding="utf-8") as f:
        f.write(
            "#!/bin/sh\n"
            # warten, bis die laufende App beendet ist
            f"while kill -0 {os.getpid()} 2>/dev/null; do sleep 0.5; done\n"
            f'mv "{app}" "{papierkorb}" || exit 1\n'
            f'mv "{neu}" "{app}" || mv "{papierkorb}" "{app}"\n'
            f'xattr -dr com.apple.quarantine "{app}" 2>/dev/null\n'
            f'open "{app}"\n'
        )
    subprocess.Popen(["/bin/sh", skript], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True
