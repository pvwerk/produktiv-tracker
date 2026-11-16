# activity.py — Plattform-Weiche: aktives Fenster, Prozess und Leerlauf.
# 16.11.2026: Mac-Fassung (Jan + Andre arbeiten auch am Mac). Windows bleibt
# unverändert in win_activity.py, macOS steckt in mac_activity.py.
#
# get_foreground() -> (handle, prozessname_klein, fenstertitel)
#   handle: Windows = Fenster-Handle, macOS = Prozess-ID des Programms.
# get_idle_seconds() -> Sekunden seit der letzten Maus-/Tastatureingabe.
import sys

IS_MAC = sys.platform == "darwin"

if IS_MAC:
    from mac_activity import get_foreground, get_idle_seconds  # noqa: F401
else:
    from win_activity import get_foreground, get_idle_seconds  # noqa: F401
