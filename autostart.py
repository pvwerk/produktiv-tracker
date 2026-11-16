# autostart.py — Autostart: startet das Tool bei der Anmeldung automatisch mit.
# Windows: Eintrag in HKEY_CURRENT_USER\...\Run (pro Benutzer, keine Adminrechte nötig).
# macOS (16.11.2026): Startobjekt ~/Library/LaunchAgents/<MAC_LABEL>.plist,
#   ebenfalls nur für den eigenen Benutzer. Es öffnet die App per "open -a",
#   damit sie wie per Doppelklick startet (mit Dock-Symbol, ohne Terminal).
import os
import sys
import plistlib

MAC_LABEL = "de.photovoltaikwerk.produktiv-tracker"


def _is_mac():
    return sys.platform == "darwin"


def _mac_plist():
    return os.path.expanduser("~/Library/LaunchAgents/%s.plist" % MAC_LABEL)


def mac_app_pfad():
    """Pfad der laufenden .app (…/Produktivitaets-Tracker.app) oder None."""
    p = os.path.abspath(sys.executable)
    for _ in range(3):  # .app/Contents/MacOS/<exe>
        p = os.path.dirname(p)
    return p if p.endswith(".app") else None


def _mac_enable():
    app = mac_app_pfad()
    if not app:
        return False
    try:
        os.makedirs(os.path.dirname(_mac_plist()), exist_ok=True)
        with open(_mac_plist(), "wb") as f:
            plistlib.dump({
                "Label": MAC_LABEL,
                "ProgramArguments": ["/usr/bin/open", "-a", app],
                "RunAtLoad": True,
            }, f)
        return True
    except Exception:
        return False


def _mac_disable():
    try:
        os.remove(_mac_plist())
    except FileNotFoundError:
        pass
    except Exception:
        return False
    return True


def _mac_is_enabled():
    try:
        with open(_mac_plist(), "rb") as f:
            return bool(plistlib.load(f).get("ProgramArguments"))
    except Exception:
        return False

APP_VALUE = "ProduktivitaetsTracker"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _is_windows():
    return sys.platform.startswith("win")


def is_frozen():
    # Nur die installierte .exe sinnvoll in den Autostart eintragen (nicht im Dev-Modus).
    return getattr(sys, "frozen", False)


def _exe_command():
    return '"%s"' % os.path.abspath(sys.executable)


def enable():
    """Trägt das Tool in den Autostart ein. True bei Erfolg."""
    if _is_mac():
        return is_frozen() and _mac_enable()
    if not (_is_windows() and is_frozen()):
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, APP_VALUE, 0, winreg.REG_SZ, _exe_command())
        return True
    except Exception:
        return False


def disable():
    """Entfernt den Autostart-Eintrag. True bei Erfolg (oder wenn nicht vorhanden)."""
    if _is_mac():
        return _mac_disable()
    if not _is_windows():
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, APP_VALUE)
        return True
    except FileNotFoundError:
        return True
    except Exception:
        return False


def is_enabled():
    """True, wenn der Autostart-Eintrag gesetzt ist."""
    if _is_mac():
        return _mac_is_enabled()
    if not _is_windows():
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as k:
            val, _ = winreg.QueryValueEx(k, APP_VALUE)
            return bool(val)
    except Exception:
        return False


def sync(enabled):
    """Registry an gewünschten Zustand angleichen + Pfad aktuell halten."""
    return enable() if enabled else disable()
