# win_activity.py — aktives Fenster, Prozess und Leerlauf (nur Windows, via ctypes)
import ctypes
from ctypes import wintypes

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None

user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
kernel32 = ctypes.windll.kernel32 if hasattr(ctypes, "windll") else None


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def get_idle_seconds():
    """Sekunden seit der letzten Maus-/Tastatureingabe."""
    try:
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        millis = kernel32.GetTickCount() - info.dwTime
        return max(0.0, millis / 1000.0)
    except Exception:
        return 0.0


def get_foreground():
    """Liefert (hwnd, exe_name_lower, window_title). exe/title können leer sein."""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return (0, "", "")
        # Fenstertitel
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or ""
        # Prozess
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe = ""
        if psutil and pid.value:
            try:
                exe = (psutil.Process(pid.value).name() or "").lower()
            except Exception:
                exe = ""
        return (hwnd, exe, title)
    except Exception:
        return (0, "", "")
