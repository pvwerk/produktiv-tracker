# mac_activity.py — aktives Programm, Fenstertitel und Leerlauf unter macOS.
# 16.11.2026: Gegenstück zu win_activity.py.
#
# Vordergrund: CGWindowListCopyWindowInfo liefert die sichtbaren Fenster in
# Stapelreihenfolge; das erste normale Fenster (Ebene 0) gehört zum Programm
# im Vordergrund. Das ist ohne Hauptthread/Run-Loop nutzbar -- die Messung
# läuft in einem Nebenthread (sampler.py).
#
# Fenstertitel: macOS gibt kCGWindowName nur heraus, wenn das Programm die
# Freigabe "Bildschirmaufnahme" hat. Das Tool macht KEINE Bildschirmfotos --
# macOS fasst unter dieser Freigabe nur auch das Lesen der Fenstertitel
# zusammen. Ohne Freigabe bleibt der Titel leer, alles andere läuft weiter.
#
# Leerlauf: CGEventSourceSecondsSinceLastEventType(HIDSystemState) zählt
# echte Maus-/Tastatureingaben; dafür ist keine Freigabe nötig.
try:
    import Quartz
except Exception:  # pragma: no cover - nur ohne pyobjc
    Quartz = None

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None

_KEIN_FENSTER = (0, "", "")
# Fenster dieser Programme liegen oft oben, sind aber nie "das, woran man
# arbeitet" (Menüleiste, Kontrollzentrum, Benachrichtigungen ...).
_SYSTEM_EBENE = {"window server", "dock", "control centre", "kontrollzentrum",
                 "notification centre", "mitteilungszentrale", "systemuiserver",
                 "screenshot", "bildschirmfoto"}


def get_idle_seconds():
    """Sekunden seit der letzten echten Maus-/Tastatureingabe."""
    if Quartz is None:
        return 0.0
    try:
        return float(Quartz.CGEventSourceSecondsSinceLastEventType(
            Quartz.kCGEventSourceStateHIDSystemState, Quartz.kCGAnyInputEventType))
    except Exception:
        return 0.0


def _prozessname(pid, fallback):
    if psutil and pid:
        try:
            return (psutil.Process(pid).name() or fallback or "").lower()
        except Exception:
            pass
    return (fallback or "").lower()


def get_foreground():
    """Liefert (pid, prozessname_klein, fenstertitel). Name/Titel können leer sein."""
    if Quartz is None:
        return _KEIN_FENSTER
    try:
        fenster = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID) or []
        for f in fenster:
            if int(f.get("kCGWindowLayer", 1)) != 0:
                continue
            besitzer = str(f.get("kCGWindowOwnerName") or "")
            if besitzer.lower() in _SYSTEM_EBENE:
                continue
            pid = int(f.get("kCGWindowOwnerPID") or 0)
            titel = str(f.get("kCGWindowName") or "")
            return (pid, _prozessname(pid, besitzer), titel)
        return _KEIN_FENSTER
    except Exception:
        return _KEIN_FENSTER


def titel_freigabe_vorhanden():
    """True, wenn macOS die Fenstertitel herausgibt (Freigabe Bildschirmaufnahme)."""
    if Quartz is None:
        return False
    try:
        return bool(Quartz.CGPreflightScreenCaptureAccess())
    except Exception:
        return False


def titel_freigabe_anfragen():
    """Zeigt einmalig die macOS-Abfrage. Danach nur noch über die Systemeinstellungen."""
    if Quartz is None:
        return False
    try:
        return bool(Quartz.CGRequestScreenCaptureAccess())
    except Exception:
        return False
