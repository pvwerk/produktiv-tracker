# storage.py — lokale SQLite-Datenbank (bleibt nur auf diesem PC)
import sqlite3
import time
import threading

import config

_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(config.db_path(), timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db():
    with _lock, _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                duration REAL NOT NULL,
                process TEXT,
                category TEXT,
                domain TEXT,
                title TEXT,
                idle INTEGER DEFAULT 0
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(ts)")
        c.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started INTEGER NOT NULL,
                stopped INTEGER
            )"""
        )


def start_session():
    with _lock, _conn() as c:
        cur = c.execute("INSERT INTO sessions (started) VALUES (?)", (int(time.time()),))
        return cur.lastrowid


def stop_session(session_id):
    if not session_id:
        return
    with _lock, _conn() as c:
        c.execute("UPDATE sessions SET stopped=? WHERE id=?", (int(time.time()), session_id))


def add_sample(ts, duration, process, category, domain, title, idle):
    with _lock, _conn() as c:
        c.execute(
            "INSERT INTO samples (ts,duration,process,category,domain,title,idle) VALUES (?,?,?,?,?,?,?)",
            (int(ts), float(duration), process, category, domain, title, 1 if idle else 0),
        )


def fetch_samples(start_ts, end_ts):
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT ts,duration,process,category,domain,title,idle FROM samples "
            "WHERE ts>=? AND ts<? ORDER BY ts",
            (int(start_ts), int(end_ts)),
        ).fetchall()
    return [
        {"ts": r[0], "duration": r[1], "process": r[2], "category": r[3],
         "domain": r[4], "title": r[5], "idle": bool(r[6])}
        for r in rows
    ]
