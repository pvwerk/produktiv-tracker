# gui.py — Tkinter-Dashboard mit eingebetteten Diagrammen
import os
import sys
import subprocess
import threading
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import config
import storage
import analysis
import charts
import report
from sampler import Tracker
from ki_prompt import build_ki_prompt


def open_path(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


class App:
    def __init__(self):
        storage.init_db()
        self.cfg = config.load_config()
        self.tracker = Tracker()
        self.A = None
        self.root = tk.Tk()
        self.root.title(config.APP_TITLE)
        self.root.geometry("980x760")
        self.root.minsize(860, 640)
        self._tray = None
        self._tick = 0
        self._build()
        self._recompute()
        self._loop()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------
    def _build(self):
        head = tk.Frame(self.root, bg="#0f172a")
        head.pack(fill="x")
        tk.Label(head, text="📊  " + config.APP_TITLE, bg="#0f172a", fg="white",
                 font=("Segoe UI", 15, "bold")).pack(side="left", padx=14, pady=9)
        tk.Label(head, text="Alle Daten bleiben nur auf diesem PC · nur du siehst sie",
                 bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 9)).pack(side="right", padx=14)

        ctrl = tk.Frame(self.root)
        ctrl.pack(fill="x", padx=12, pady=8)
        self.btn = tk.Button(ctrl, text="▶  Tracking starten", font=("Segoe UI", 11, "bold"),
                             bg="#16a34a", fg="white", activebackground="#15803d",
                             relief="flat", padx=14, pady=8, command=self._toggle)
        self.btn.pack(side="left")
        self.status = tk.Label(ctrl, text="gestoppt", font=("Segoe UI", 10), fg="#64748b")
        self.status.pack(side="left", padx=12)
        tk.Label(ctrl, text="Zeitraum:").pack(side="left", padx=(12, 2))
        self.period = ttk.Combobox(ctrl, values=["Heute", "Gestern", "Letzte 7 Tage"],
                                   state="readonly", width=13)
        self.period.set("Heute")
        self.period.pack(side="left")
        self.period.bind("<<ComboboxSelected>>", lambda e: self._recompute())
        tk.Button(ctrl, text="↻", command=self._recompute, width=3).pack(side="left", padx=4)

        self.lbl_now = tk.Label(self.root, text="Jetzt: —", font=("Segoe UI", 10),
                                anchor="w", fg="#334155")
        self.lbl_now.pack(fill="x", padx=14)

        # Tabs mit eingebetteten Diagrammen
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=12, pady=8)
        self.tabs = {}
        for name, draw in [
            ("Übersicht", charts.draw_overview),
            ("Fokus & Ablenkung", charts.draw_focus),
            ("Workflow-Probleme", charts.draw_workflow),
            ("Tagesverlauf", charts.draw_timeline),
            ("Wochen-Trend", None),
        ]:
            frame = tk.Frame(self.nb, bg="white")
            self.nb.add(frame, text=name)
            fig = Figure(figsize=(8, 5), dpi=100)
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            self.tabs[name] = {"fig": fig, "canvas": canvas, "draw": draw}
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._redraw_current())

        # Export / Aktionen
        foot = tk.Frame(self.root)
        foot.pack(fill="x", padx=12, pady=(0, 10))
        tk.Button(foot, text="📄 PDF-Bericht", command=self._pdf).pack(side="left", padx=3)
        tk.Button(foot, text="📑 CSV", command=self._csv).pack(side="left", padx=3)
        tk.Button(foot, text="🤖 Für KI exportieren", command=self._ki).pack(side="left", padx=3)
        tk.Button(foot, text="➕ Offline nachtragen", command=self._manual).pack(side="left", padx=3)
        tk.Button(foot, text="⚙ Einstellungen", command=self._settings).pack(side="left", padx=3)
        tk.Button(foot, text="ℹ Datenschutz", command=self._privacy).pack(side="left", padx=3)
        tk.Button(foot, text="Beenden", command=self._quit).pack(side="right")

    # ---------- Daten ----------
    def _bounds(self):
        choice = self.period.get()
        today = datetime.now()
        if choice == "Gestern":
            d = today - timedelta(days=1)
            return analysis.range_bounds(d, d), "Gestern (" + d.strftime("%d.%m.%Y") + ")"
        if choice == "Letzte 7 Tage":
            s = today - timedelta(days=6)
            return analysis.range_bounds(s, today), "Letzte 7 Tage"
        return analysis.day_bounds(today), "Heute (" + today.strftime("%d.%m.%Y") + ")"

    def _recompute(self):
        (start, end), label = self._bounds()
        self._period_label = label
        try:
            samples = storage.fetch_samples(start, end)
            self.A = analysis.analyze(samples, self.cfg)
        except Exception:
            self.A = None
        self._redraw_current()

    def _trend_days(self):
        days = []
        today = datetime.now()
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            s, e = analysis.range_bounds(d, d)
            A = analysis.analyze(storage.fetch_samples(s, e), self.cfg)
            days.append({
                "label": d.strftime("%a\n%d.%m."),
                "active_min": A["active"] / 60.0,
                "focus_pct": A["focus"]["focus_quote"] * 100,
                "switches": A["switches"],
                "flapping": sum(f["count"] for f in A["flapping"]),
            })
        return days

    def _redraw_current(self):
        name = self._current_tab()
        if not name or name not in self.tabs:
            return
        t = self.tabs[name]
        try:
            if name == "Wochen-Trend":
                charts.draw_trend(t["fig"], self._trend_days())
            elif self.A is not None and t["draw"]:
                t["draw"](t["fig"], self.A, getattr(self, "_period_label", ""))
            t["canvas"].draw_idle()
        except Exception as e:
            try:
                t["fig"].clear()
                t["fig"].text(0.1, 0.5, f"Diagramm-Fehler: {e}", fontsize=9)
                t["canvas"].draw_idle()
            except Exception:
                pass

    def _current_tab(self):
        try:
            return self.nb.tab(self.nb.select(), "text")
        except Exception:
            return None

    # ---------- Tracking ----------
    def _toggle(self):
        if self.tracker.running:
            self.tracker.stop()
            self.btn.config(text="▶  Tracking starten", bg="#16a34a", activebackground="#15803d")
            self.status.config(text="gestoppt", fg="#64748b")
        else:
            self.tracker.start()
            self.btn.config(text="⏸  Tracking stoppen", bg="#dc2626", activebackground="#b91c1c")
            self.status.config(text="läuft …", fg="#16a34a")

    def _loop(self):
        # Live-Zeile schnell, Neuberechnung der Diagramme alle ~12 s
        if self.tracker.running:
            c = self.tracker.current
            where = c.get("domain") or c.get("title") or c.get("process") or "—"
            self.lbl_now.config(text=f"Jetzt: {c.get('category','')}  ·  {where}")
        else:
            self.lbl_now.config(text="Jetzt: — (Tracking gestoppt)")
        self._tick += 1
        if self._tick % 3 == 0 and self.tracker.running:
            self._recompute()
        self.root.after(4000, self._loop)

    # ---------- Export ----------
    def _pdf(self):
        if not self.A:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            initialfile=f"Produktivitaet_{datetime.now():%Y-%m-%d}.pdf")
        if not path:
            return
        try:
            report.export_pdf(self.A, self._period_label, path)
            if messagebox.askyesno("Fertig", "PDF-Bericht erstellt. Jetzt öffnen?"):
                open_path(path)
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _csv(self):
        (start, end), label = self._bounds()
        samples = storage.fetch_samples(start, end)
        A = analysis.analyze(samples, self.cfg)
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=f"Produktivitaet_{datetime.now():%Y-%m-%d}.csv")
        if not path:
            return
        try:
            report.export_csv(samples, A, path)
            if messagebox.askyesno("Fertig", "CSV erstellt. Ordner öffnen?"):
                open_path(os.path.dirname(path))
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _ki(self):
        (start, end), label = self._bounds()
        samples = storage.fetch_samples(start, end)
        A = analysis.analyze(samples, self.cfg)
        folder = filedialog.askdirectory(title="Ordner für KI-Export wählen")
        if not folder:
            return
        try:
            stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            csv_path = os.path.join(folder, f"Produktivitaet_{stamp}.csv")
            prompt_path = os.path.join(folder, f"KI-Prompt_{stamp}.txt")
            report.export_csv(samples, A, csv_path)
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(build_ki_prompt(A, label))
            messagebox.showinfo(
                "Für KI exportiert",
                "Zwei Dateien erstellt:\n\n"
                f"• {os.path.basename(csv_path)}  (Daten)\n"
                f"• {os.path.basename(prompt_path)}  (fertiger Prompt mit deinen Kennzahlen)\n\n"
                "Den Prompt in die KI (z.B. Grok) einfügen und die CSV anhängen.")
            open_path(folder)
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    # ---------- Manuelles Nachtragen ----------
    def _manual(self):
        ManualDialog(self.root, self.cfg, on_saved=self._recompute)

    def _settings(self):
        config.load_config()
        open_path(config.config_path())
        messagebox.showinfo(
            "Einstellungen",
            "config.json wurde geöffnet. Hier kannst du Kategorien, Produktivitäts-Level, "
            "Mess-Intervall, Fokus-Schwellen und die AGFEO-Erkennung anpassen. "
            "Danach Tracking einmal stoppen und neu starten, dann oben auf Neu-Laden (Pfeil).")
        self.cfg = config.load_config()

    def _privacy(self):
        messagebox.showinfo(
            "Datenschutz — was dieses Tool NICHT macht",
            "• KEINE Tastatureingaben / keine Texte mitschneiden\n"
            "• KEINE Screenshots, keine Kamera, kein Mikrofon\n"
            "• KEINE vollständigen Internet-Adressen — nur die Hauptadresse (z.B. www.westnetz.de)\n"
            "• KEINE Cloud — alles bleibt lokal auf diesem PC\n"
            "• KEINE Live-Überwachung durch Dritte — nur du siehst die Auswertung\n\n"
            "Du startest/stoppst selbst und kannst alle Daten jederzeit löschen "
            "(Daten-Ordner → tracker.db).")

    # ---------- Fenster/Tray ----------
    def _on_close(self):
        if self._ensure_tray():
            self.root.withdraw()
        else:
            self.root.iconify()

    def _ensure_tray(self):
        if self._tray is not None:
            return True
        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception:
            return False
        img = Image.new("RGB", (64, 64), "#0f172a")
        d = ImageDraw.Draw(img)
        d.rectangle([16, 30, 24, 48], fill="#16a34a")
        d.rectangle([28, 20, 36, 48], fill="#16a34a")
        d.rectangle([40, 10, 48, 48], fill="#16a34a")
        menu = pystray.Menu(
            pystray.MenuItem("Öffnen", self._tray_show, default=True),
            pystray.MenuItem("Start/Stop", lambda *_: self._toggle()),
            pystray.MenuItem("Beenden", self._tray_quit),
        )
        self._tray = pystray.Icon(config.APP_NAME, img, config.APP_TITLE, menu)
        threading.Thread(target=self._tray.run, daemon=True).start()
        return True

    def _tray_show(self, *_):
        self.root.after(0, self.root.deiconify)

    def _tray_quit(self, *_):
        self.root.after(0, self._quit)

    def _quit(self):
        try:
            if self.tracker.running:
                self.tracker.stop()
        except Exception:
            pass
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


class ManualDialog(tk.Toplevel):
    """Offline-Tätigkeit nachtragen (z.B. Meeting, Telefonat ohne PC)."""

    def __init__(self, master, cfg, on_saved=None):
        super().__init__(master)
        self.title("Offline-Tätigkeit nachtragen")
        self.cfg = cfg
        self.on_saved = on_saved
        self.resizable(False, False)
        cats = sorted(set(list(cfg.get("process_categories", {}).values()) +
                          list(cfg.get("domain_categories", {}).values()) +
                          ["Telefonie (AGFEO)", "E-Mail", "Office", "Besprechung"]))
        pad = {"padx": 10, "pady": 4}
        tk.Label(self, text="Kategorie").grid(row=0, column=0, sticky="w", **pad)
        self.cat = ttk.Combobox(self, values=cats, state="readonly", width=24)
        self.cat.set("Besprechung")
        self.cat.grid(row=0, column=1, **pad)
        tk.Label(self, text="Datum (TT.MM.JJJJ)").grid(row=1, column=0, sticky="w", **pad)
        self.date = tk.Entry(self, width=26)
        self.date.insert(0, datetime.now().strftime("%d.%m.%Y"))
        self.date.grid(row=1, column=1, **pad)
        tk.Label(self, text="Startzeit (HH:MM)").grid(row=2, column=0, sticky="w", **pad)
        self.time = tk.Entry(self, width=26)
        self.time.insert(0, datetime.now().strftime("%H:%M"))
        self.time.grid(row=2, column=1, **pad)
        tk.Label(self, text="Dauer (Minuten)").grid(row=3, column=0, sticky="w", **pad)
        self.mins = tk.Entry(self, width=26)
        self.mins.insert(0, "30")
        self.mins.grid(row=3, column=1, **pad)
        tk.Button(self, text="Speichern", command=self._save, bg="#16a34a", fg="white",
                  relief="flat", padx=12, pady=4).grid(row=4, column=0, columnspan=2, pady=10)

    def _save(self):
        try:
            d = datetime.strptime(self.date.get().strip() + " " + self.time.get().strip(),
                                  "%d.%m.%Y %H:%M")
            minutes = float(self.mins.get().strip())
            if minutes <= 0:
                raise ValueError("Dauer muss > 0 sein")
        except Exception as e:
            messagebox.showerror("Eingabe", f"Bitte Datum/Zeit/Dauer prüfen.\n{e}")
            return
        cat = self.cat.get() or "Besprechung"
        # als ein Sample am Endzeitpunkt mit der Dauer ablegen
        end_ts = d.timestamp() + minutes * 60
        storage.add_sample(end_ts, minutes * 60, "(offline)", cat, None, "manuell nachgetragen", False)
        if self.on_saved:
            self.on_saved()
        self.destroy()
