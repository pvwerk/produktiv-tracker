# sampler.py — Hintergrund-Messschleife
import time
import threading

import config
import storage
import win_activity
import browser_url


def categorize(cfg, exe, domain):
    """Bestimmt die Kategorie aus Prozess + Host."""
    proc_cats = cfg.get("process_categories", {})
    dom_cats = cfg.get("domain_categories", {})
    hints = [h.lower() for h in cfg.get("agfeo_process_hints", [])]
    exe = (exe or "").lower()

    # AGFEO-Erkennung über Hinweise
    for h in hints:
        if h and h in exe:
            return "Telefonie (AGFEO)"

    if exe in proc_cats:
        return proc_cats[exe]

    if exe in config.BROWSER_PROCESSES:
        if domain and domain in dom_cats:
            return dom_cats[domain]
        return "Web"

    if not exe:
        return "Unbekannt"
    return "Sonstige Programme"


class Tracker:
    def __init__(self, on_update=None):
        self.cfg = config.load_config()
        self.interval = float(self.cfg.get("sample_interval", config.DEFAULT_SAMPLE_INTERVAL))
        self.idle_threshold = float(self.cfg.get("idle_threshold", config.DEFAULT_IDLE_THRESHOLD))
        self._thread = None
        self._stop = threading.Event()
        self.running = False
        self.session_id = None
        self.on_update = on_update
        self.current = {"process": "", "category": "", "domain": "", "title": "", "idle": False}
        self._url_cache = {}  # (hwnd, title) -> host

    def reload_config(self):
        self.cfg = config.load_config()
        self.interval = float(self.cfg.get("sample_interval", config.DEFAULT_SAMPLE_INTERVAL))
        self.idle_threshold = float(self.cfg.get("idle_threshold", config.DEFAULT_IDLE_THRESHOLD))
        self.store_titles = bool(self.cfg.get("store_window_titles", True))

    def start(self):
        if self.running:
            return
        storage.init_db()
        self.reload_config()
        self.session_id = storage.start_session()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self.running = True
        self._thread.start()

    def stop(self):
        if not self.running:
            return
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        storage.stop_session(self.session_id)
        self.session_id = None
        self.running = False
        self.current = {"process": "", "category": "", "domain": "", "title": "", "idle": False}
        if self.on_update:
            try:
                self.on_update()
            except Exception:
                pass

    def _browser_host(self, hwnd, exe, title):
        key = (hwnd, title)
        if key in self._url_cache:
            return self._url_cache[key]
        host = browser_url.get_browser_host(hwnd, exe)
        if not host:
            host = None
        # Cache klein halten
        if len(self._url_cache) > 200:
            self._url_cache.clear()
        self._url_cache[key] = host
        return host

    def _loop(self):
        last = time.time()
        while not self._stop.is_set():
            time.sleep(self.interval)
            now = time.time()
            dur = now - last
            last = now

            idle_secs = win_activity.get_idle_seconds()
            is_idle = idle_secs >= self.idle_threshold

            hwnd, exe, title = win_activity.get_foreground()
            domain = None
            if not is_idle and exe in config.BROWSER_PROCESSES:
                domain = self._browser_host(hwnd, exe, title)

            category = "Abwesend" if is_idle else categorize(self.cfg, exe, domain)
            stored_title = title if getattr(self, "store_titles", True) else ""

            try:
                storage.add_sample(now, dur, exe, category, domain, stored_title, is_idle)
            except Exception:
                pass

            self.current = {
                "process": exe, "category": category,
                "domain": domain or "", "title": title, "idle": is_idle,
            }
            if self.on_update:
                try:
                    self.on_update()
                except Exception:
                    pass
