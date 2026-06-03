# gui.py — Tkinter-Oberfläche
import os
import sys
import subprocess
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import config
import storage
import analysis
import report
from sampler import Tracker
from ki_prompt import KI_PROMPT


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
        self.tracker = Tracker()
        self.root = tk.Tk()
        self.root.title(config.APP_TITLE)
        self.root.geometry("720x640")
        self.root.minsize(640, 560)
        self._tray = None
        self._build()
        self._refresh()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------
    def _build(self):
        head = tk.Frame(self.root, bg="#0f172a")
        head.pack(fill="x")
        tk.Label(head, text="📊  " + config.APP_TITLE, bg="#0f172a", fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=14, pady=10)
        tk.Label(head, text="Alle Daten bleiben nur auf diesem PC.", bg="#0f172a",
                 fg="#94a3b8", font=("Segoe UI", 9)).pack(side="right", padx=14)

        ctrl = tk.Frame(self.root)
        ctrl.pack(fill="x", padx=14, pady=12)
        self.btn = tk.Button(ctrl, text="▶  Tracking starten", font=("Segoe UI", 12, "bold"),
                             bg="#16a34a", fg="white", activebackground="#15803d",
                             relief="flat", padx=18, pady=10, command=self._toggle)
        self.btn.pack(side="left")
        self.status = tk.Label(ctrl, text="gestoppt", font=("Segoe UI", 10), fg="#64748b")
        self.status.pack(side="left", padx=14)

        live = tk.LabelFrame(self.root, text="Live", padx=12, pady=8)
        live.pack(fill="x", padx=14)
        self.lbl_now = tk.Label(live, text="Jetzt: —", font=("Segoe UI", 10), anchor="w")
        self.lbl_now.pack(fill="x")
        self.lbl_tot = tk.Label(live, text="Heute aktiv: —", font=("Segoe UI", 10), anchor="w")
        self.lbl_tot.pack(fill="x")

        mid = tk.LabelFrame(self.root, text="Heute — Top-Auswertung", padx=8, pady=6)
        mid.pack(fill="both", expand=True, padx=14, pady=10)
        cols = ("typ", "name", "dauer")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=12)
        self.tree.heading("typ", text="Typ")
        self.tree.heading("name", text="Name")
        self.tree.heading("dauer", text="Dauer")
        self.tree.column("typ", width=130, anchor="w")
        self.tree.column("name", width=400, anchor="w")
        self.tree.column("dauer", width=100, anchor="e")
        self.tree.pack(fill="both", expand=True)

        exp = tk.Frame(self.root)
        exp.pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(exp, text="Zeitraum:").pack(side="left")
        self.period = ttk.Combobox(exp, values=["Heute", "Gestern", "Letzte 7 Tage"],
                                   state="readonly", width=14)
        self.period.set("Heute")
        self.period.pack(side="left", padx=6)
        self.period.bind("<<ComboboxSelected>>", lambda e: self._refresh())
        tk.Button(exp, text="📄 PDF-Bericht", command=self._pdf).pack(side="left", padx=4)
        tk.Button(exp, text="📑 CSV", command=self._csv).pack(side="left", padx=4)
        tk.Button(exp, text="🤖 Für KI exportieren", command=self._ki).pack(side="left", padx=4)

        foot = tk.Frame(self.root)
        foot.pack(fill="x", padx=14, pady=(0, 12))
        tk.Button(foot, text="⚙ Einstellungen", command=self._settings).pack(side="left")
        tk.Button(foot, text="📁 Daten-Ordner", command=lambda: open_path(config.data_dir())).pack(side="left", padx=6)
        tk.Button(foot, text="Beenden", command=self._quit).pack(side="right")

    # ---------- Logik ----------
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

    def _current_agg(self):
        (start, end), label = self._bounds()
        samples = storage.fetch_samples(start, end)
        return analysis.aggregate(samples), label

    def _toggle(self):
        if self.tracker.running:
            self.tracker.stop()
            self.btn.config(text="▶  Tracking starten", bg="#16a34a", activebackground="#15803d")
            self.status.config(text="gestoppt", fg="#64748b")
        else:
            self.tracker.start()
            self.btn.config(text="⏸  Tracking stoppen", bg="#dc2626", activebackground="#b91c1c")
            self.status.config(text="läuft …", fg="#16a34a")

    def _refresh(self):
        # Live
        if self.tracker.running:
            c = self.tracker.current
            where = c.get("domain") or c.get("title") or c.get("process") or "—"
            self.lbl_now.config(text=f"Jetzt: {c.get('category','')}  ·  {where}")
        else:
            self.lbl_now.config(text="Jetzt: — (Tracking gestoppt)")
        try:
            agg, _ = self._current_agg()
            self.lbl_tot.config(
                text=f"Aktiv: {analysis.fmt_dur(agg['active'])}   ·   "
                     f"Abwesend: {analysis.fmt_dur(agg['idle'])}   ·   "
                     f"Aufgabenwechsel: {agg['switches']}")
            self.tree.delete(*self.tree.get_children())
            for cat, sec in list(agg["by_category"].items())[:6]:
                self.tree.insert("", "end", values=("Kategorie", cat, analysis.fmt_dur(sec)))
            for app, sec in list(agg["by_app"].items())[:6]:
                self.tree.insert("", "end", values=("Programm", app, analysis.fmt_dur(sec)))
            for dom, sec in list(agg["by_domain"].items())[:8]:
                self.tree.insert("", "end", values=("Webseite", dom, analysis.fmt_dur(sec)))
        except Exception:
            pass
        self.root.after(2000, self._refresh)

    def _pdf(self):
        agg, label = self._current_agg()
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            initialfile=f"Produktivitaet_{datetime.now():%Y-%m-%d}.pdf")
        if not path:
            return
        try:
            report.export_pdf(agg, label, path)
            if messagebox.askyesno("Fertig", "PDF-Bericht erstellt. Jetzt öffnen?"):
                open_path(path)
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _csv(self):
        (start, end), label = self._bounds()
        samples = storage.fetch_samples(start, end)
        agg = analysis.aggregate(samples)
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=f"Produktivitaet_{datetime.now():%Y-%m-%d}.csv")
        if not path:
            return
        try:
            report.export_csv(samples, agg, path)
            if messagebox.askyesno("Fertig", "CSV erstellt. Ordner öffnen?"):
                open_path(os.path.dirname(path))
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _ki(self):
        (start, end), label = self._bounds()
        samples = storage.fetch_samples(start, end)
        agg = analysis.aggregate(samples)
        folder = filedialog.askdirectory(title="Ordner für KI-Export wählen")
        if not folder:
            return
        try:
            stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            csv_path = os.path.join(folder, f"Produktivitaet_{stamp}.csv")
            prompt_path = os.path.join(folder, f"KI-Prompt_{stamp}.txt")
            report.export_csv(samples, agg, csv_path)
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(KI_PROMPT)
            messagebox.showinfo(
                "Für KI exportiert",
                "Zwei Dateien erstellt:\n\n"
                f"• {os.path.basename(csv_path)}  (Daten)\n"
                f"• {os.path.basename(prompt_path)}  (fertiger Prompt)\n\n"
                "Den Prompt in die KI (z.B. Grok) einfügen und die CSV anhängen.")
            open_path(folder)
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _settings(self):
        config.load_config()  # legt die Datei bei Bedarf an
        open_path(config.config_path())
        messagebox.showinfo(
            "Einstellungen",
            "Die Datei config.json wurde geöffnet. Dort kannst du Kategorien, "
            "das Mess-Intervall und die AGFEO-Erkennung anpassen. Nach dem Speichern "
            "Tracking einmal stoppen und neu starten.")

    # ---------- Fenster/Tray ----------
    def _on_close(self):
        # In den Tray minimieren, damit das Tracking weiterläuft
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
        import threading
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
