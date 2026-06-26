# autostart.py — Windows-Autostart: startet das Tool bei der Anmeldung automatisch mit.
# Eintrag in HKEY_CURRENT_USER\...\Run (pro Benutzer, keine Adminrechte nötig).
import os
import sys

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
    """Trägt das Tool in den Windows-Autostart ein. True bei Erfolg."""
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
