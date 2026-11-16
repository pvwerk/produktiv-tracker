# netz.py — HTTPS-Kontext für alle Verbindungen des Tools (CRM, Update).
# 16.11.2026: In der Mac-App (PyInstaller, Python von python.org) findet
# Python die Stammzertifikate von macOS NICHT -> jede HTTPS-Verbindung
# scheiterte mit CERTIFICATE_VERIFY_FAILED (CRM-Anbindung und
# Update-Prüfung). Darum am Mac die mitgelieferten Zertifikate von certifi.
# Windows nutzt weiter den Zertifikatsspeicher von Windows (unverändert).
import ssl
import sys


def ssl_kontext():
    if sys.platform == "darwin":
        try:
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            pass
    return ssl.create_default_context()
