# crm_sync.py
# CRM-Anbindung (optional) — 03.11.2026
#
# Schickt die FERTIGE Tagesauswertung an das PVWERK-CRM, damit du sie auch
# dort ansehen kannst. Das Tool selbst bleibt unverändert: Es zeichnet
# weiter lokal auf, rechnet weiter lokal, und funktioniert ohne CRM genauso
# wie bisher. Diese Datei ist eine reine Ergänzung.
#
# WAS ÜBERTRAGEN WIRD
#   Nur das Ergebnis von analysis.analyze() — also Summen, Kategorien,
#   Top-Programme, Fokuszahlen, auffällige Abläufe.
#
# WAS NICHT ÜBERTRAGEN WIRD
#   Die Rohdaten aus tracker.db. Insbesondere FENSTERTITEL verlassen
#   deinen Rechner nicht. Die Felder "segments" und "tasks" werden vor dem
#   Senden entfernt — sie können einzelne Fenstertitel enthalten.
#
# WER DIE DATEN SEHEN KANN
#   Nur du. Im CRM ist die Tabelle so abgesichert, dass auch Administratoren
#   keine fremden Zeilen lesen können — das ist in der Datenbank erzwungen,
#   nicht bloß in der Oberfläche ausgeblendet.
#
# AN/AUS
#   Standardmäßig AUS. Es passiert nichts, solange in der config.json kein
#   Token steht. Du erzeugst es im CRM unter "Meine Produktivität" und
#   kannst es dort jederzeit zurückziehen — danach wird nichts mehr
#   angenommen, auch wenn das Tool es noch versucht.

import json
import urllib.request
import urllib.error

TIMEOUT = 20


def ist_aktiv(cfg):
    """CRM-Übertragung nur, wenn BEIDES hinterlegt ist."""
    return bool((cfg or {}).get("crm_url")) and bool((cfg or {}).get("crm_token"))


def _ohne_rohdaten(auswertung):
    """Felder entfernen, die einzelne Fenstertitel enthalten können."""
    schlank = dict(auswertung or {})
    for feld in ("segments", "tasks"):
        schlank.pop(feld, None)
    return schlank


def sende_tag(cfg, tag_iso, auswertung, tool_version=None):
    """
    Überträgt die Auswertung eines Tages.

    Rückgabe: (ok: bool, meldung: str)
    Wirft nicht — ein Übertragungsfehler darf das Tool nie stören, die
    Auswertung liegt ohnehin vollständig lokal vor.
    """
    if not ist_aktiv(cfg):
        return False, "CRM-Anbindung ist nicht eingerichtet."

    basis = str(cfg["crm_url"]).rstrip("/")
    ziel = basis + "/api/produktivitaet/tag"
    rumpf = json.dumps({
        "tag": tag_iso,
        "auswertung": _ohne_rohdaten(auswertung),
        "tool_version": tool_version,
    }).encode("utf-8")

    anfrage = urllib.request.Request(ziel, data=rumpf, method="POST")
    anfrage.add_header("Content-Type", "application/json")
    anfrage.add_header("Authorization", "Bearer " + str(cfg["crm_token"]))

    try:
        with urllib.request.urlopen(anfrage, timeout=TIMEOUT) as antwort:
            if 200 <= antwort.status < 300:
                return True, "Übertragen."
            return False, "Unerwartete Antwort: HTTP %s" % antwort.status
    except urllib.error.HTTPError as e:
        # Klartext statt HTTP-Code: Der häufigste Fall ist ein im CRM
        # zurückgezogenes Token, und das soll man sofort verstehen.
        try:
            detail = json.loads(e.read().decode("utf-8", "ignore")).get("error", "")
        except Exception:
            detail = ""
        if e.code == 401:
            return False, "Token wird nicht mehr akzeptiert — im CRM ein neues erzeugen."
        if e.code == 413:
            return False, "Auswertung zu groß. " + detail
        return False, "Abgelehnt (HTTP %s)%s" % (e.code, ": " + detail if detail else "")
    except urllib.error.URLError as e:
        return False, "CRM nicht erreichbar: %s" % getattr(e, "reason", e)
    except Exception as e:  # noqa: BLE001
        return False, "Übertragung fehlgeschlagen: %s" % e


def teste_verbindung(cfg):
    """
    Prüft Adresse und Token, ohne echte Daten abzulegen: überträgt eine
    leere Auswertung für den 1.1.1970. Das CRM legt dafür eine Zeile an,
    die man dort mit einem Klick wieder löschen kann.
    """
    return sende_tag(cfg, "1970-01-01", {"active": 0, "hinweis": "Verbindungstest"}, "test")
