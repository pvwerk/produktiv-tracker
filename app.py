# app.py — Einstiegspunkt
import os
import sys


def selbsttest():
    """16.11.2026: Prüft in der GEBAUTEN App, was sich im Quelltext nicht
    zeigt -- vor allem HTTPS (die Mac-App fand die Zertifikate nicht).
    Aufruf im Build: PT_SELBSTTEST=1 <App>. Exit 0 = ok."""
    import urllib.request
    import netz
    import updater
    req = urllib.request.Request(updater.VERSION_URL, headers={"User-Agent": "ProduktivTracker"})
    with urllib.request.urlopen(req, timeout=20, context=netz.ssl_kontext()) as r:
        print("HTTPS ok:", r.status)
    import activity
    print("Messung ok:", activity.get_idle_seconds() >= 0)
    return 0


def main():
    if os.environ.get("PT_SELBSTTEST"):
        sys.exit(selbsttest())
    from gui import App
    App().run()


if __name__ == "__main__":
    main()
