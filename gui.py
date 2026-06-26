# gui.py — Tkinter-Dashboard mit eingebetteten Diagrammen
import os
import sys
import subprocess
import threading
import json
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
import updater
import autostart
import theme
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
        # Autostart-Registry an die Einstellung angleichen (nur installierte .exe)
        try:
            autostart.sync(self.cfg.get("autostart", True))
        except Exception:
            pass
        self.tracker = Tracker()
        self.A = None
        self.root = tk.Tk()
        self.root.title(config.APP_TITLE)
        self.root.geometry("1020x780")
        self.root.minsize(900, 660)
        theme.apply(self.root)
        self._tray = None
        self._tick = 0
        self._build()
        self._recompute()
        self._loop()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(300, self._maybe_consent)
        self.root.after(2500, lambda: self._check_update(silent=True))

    # ---------- UI ----------
    def _build(self):
        C = theme.COLORS
        # ---------- Header (Marken-Navy) ----------
        head = tk.Frame(self.root, bg=C["navy"])
        head.pack(fill="x")
        tk.Label(head, text="📊  " + config.APP_TITLE, bg=C["navy"], fg=C["on_dark"],
                 font=theme.F_H1).pack(side="left", padx=16, pady=13)
        tk.Label(head, text="Alle Daten bleiben nur auf diesem PC · nur du siehst sie",
                 bg=C["navy"], fg=C["on_dark_muted"], font=theme.F_SMALL).pack(side="right", padx=16)

        # ---------- Steuerleiste (Karte) ----------
        wrap = tk.Frame(self.root, bg=C["bg"])
        wrap.pack(fill="x", padx=12, pady=(12, 4))
        ctrl = theme.card(wrap)
        ctrl.pack(fill="x")
        inner = tk.Frame(ctrl, bg=C["surface"])
        inner.pack(fill="x", padx=12, pady=10)
        self.btn = theme.button(inner, "▶  Tracking starten", self._toggle, kind="success")
        self.btn.pack(side="left")
        self.status = tk.Label(inner, text="gestoppt", font=theme.F_BODY, fg=C["muted"], bg=C["surface"])
        self.status.pack(side="left", padx=14)
        tk.Label(inner, text="Zeitraum", font=theme.F_SMALL, fg=C["muted"], bg=C["surface"]).pack(side="left", padx=(12, 4))
        self.period = ttk.Combobox(inner, values=["Heute", "Gestern", "Letzte 7 Tage"],
                                   state="readonly", width=13)
        self.period.set("Heute")
        self.period.pack(side="left")
        self.period.bind("<<ComboboxSelected>>", lambda e: self._recompute())
        theme.button(inner, "↻", self._recompute, kind="secondary", width=2, compact=True).pack(side="left", padx=6)

        self.lbl_now = tk.Label(self.root, text="Jetzt: —", font=theme.F_BODY, anchor="w",
                                fg=C["text"], bg=C["bg"])
        self.lbl_now.pack(fill="x", padx=16, pady=(2, 2))

        # ---------- Tabs mit eingebetteten Diagrammen ----------
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=12, pady=6)
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
            fig.patch.set_facecolor("white")
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            self.tabs[name] = {"fig": fig, "canvas": canvas, "draw": draw}
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._redraw_current())

        # ---------- Footer (zwei Reihen) ----------
        foot = tk.Frame(self.root, bg=C["bg"])
        foot.pack(fill="x", padx=12, pady=(2, 12))
        row1 = tk.Frame(foot, bg=C["bg"]); row1.pack(fill="x", pady=(0, 4))
        row2 = tk.Frame(foot, bg=C["bg"]); row2.pack(fill="x")

        def fb(parent, text, cmd, kind="secondary", side="left"):
            theme.button(parent, text, cmd, kind=kind, compact=True).pack(side=side, padx=3)

        fb(row1, "📄 PDF-Bericht", self._pdf)
        fb(row1, "📑 CSV", self._csv)
        fb(row1, "🤖 Für KI exportieren", self._ki)
        fb(row1, "➕ Offline nachtragen", self._manual)
        fb(row1, "🧩 Aufgaben-Erkennung", self._task_matchers)
        fb(row1, "⚙ Einstellungen", self._settings)

        fb(row2, "ℹ Datenschutz", self._privacy)
        fb(row2, "🆕 Was ist neu", self._changelog)
        self.autostart_btn = theme.button(row2, self._autostart_label(), self._toggle_autostart,
                                           kind="secondary", compact=True)
        self.autostart_btn.pack(side="left", padx=3)
        fb(row2, "🗑 Daten löschen", self._delete_data, kind="danger")
        fb(row2, "Beenden", self._quit, side="right")
        fb(row2, "⤓ Update", lambda: self._check_update(silent=False), kind="primary", side="right")

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
            theme.set_kind(self.btn, "success", text="▶  Tracking starten")
            self.status.config(text="gestoppt", fg=theme.COLORS["muted"])
        else:
            self.tracker.start()
            theme.set_kind(self.btn, "danger", text="⏸  Tracking stoppen")
            self.status.config(text="läuft …", fg=theme.COLORS["success"])

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

    def _task_matchers(self):
        TaskMatcherDialog(self.root, on_saved=lambda: (setattr(self, "cfg", config.load_config()), self._recompute()))

    def _changelog(self):
        try:
            import changelog
            text = changelog.CHANGELOG
        except Exception:
            text = "Kein Änderungsverlauf verfügbar."
        C = theme.COLORS
        win = theme.dialog(tk.Toplevel(self.root))
        win.title("Was ist neu?")
        win.geometry("560x520")
        theme.dialog_header(win, "🆕 Änderungsverlauf")
        frame = tk.Frame(win, bg=C["surface"]); frame.pack(fill="both", expand=True, padx=14, pady=12)
        sb = tk.Scrollbar(frame); sb.pack(side="right", fill="y")
        txt = tk.Text(frame, wrap="word", font=theme.F_BODY, yscrollcommand=sb.set,
                      bg="white", fg=C["text"], relief="flat",
                      highlightthickness=1, highlightbackground=C["border"], padx=10, pady=8)
        txt.insert("1.0", text); txt.config(state="disabled")
        txt.pack(side="left", fill="both", expand=True); sb.config(command=txt.yview)

    def _delete_data(self):
        if messagebox.askyesno(
                "Daten löschen",
                "Wirklich ALLE erfassten Daten unwiderruflich löschen?\n"
                "(Einstellungen bleiben erhalten.)"):
            try:
                if self.tracker.running:
                    self.tracker.stop()
                    self.btn.config(text="▶  Tracking starten", bg="#16a34a",
                                    activebackground="#15803d")
                    self.status.config(text="gestoppt", fg="#64748b")
            except Exception:
                pass
            storage.clear_all()
            self._recompute()
            messagebox.showinfo("Erledigt", "Alle erfassten Daten wurden gelöscht.")

    def _check_update(self, silent=True):
        def work():
            try:
                new = updater.check_update()
            except Exception:
                new = None
            self.root.after(0, lambda: self._update_result(new, silent))
        threading.Thread(target=work, daemon=True).start()

    def _update_result(self, new, silent):
        if not new:
            if not silent:
                if not updater.is_frozen():
                    messagebox.showinfo("Update", "Update-Prüfung nur in der installierten "
                                                   "App (.exe) verfügbar.")
                else:
                    messagebox.showinfo("Update", "Du hast bereits die neueste Version.")
            return
        if messagebox.askyesno("Update verfügbar",
                               "Eine neuere Version ist verfügbar.\n\n"
                               "Jetzt herunterladen und installieren? "
                               "Die App startet danach automatisch neu."):
            try:
                if self.tracker.running:
                    self.tracker.stop()
                if updater.apply_update():
                    messagebox.showinfo("Update", "Update wird installiert — die App startet "
                                                  "gleich neu.")
                    # Prozess hart beenden, damit die .exe SOFORT freigegeben wird und der
                    # Updater sie austauschen kann. root.destroy() reicht nicht zuverlaessig
                    # (Tk-/Tray-Teardown kann den Prozess am Leben halten -> Updater haengt).
                    try:
                        if self._tray:
                            self._tray.stop()
                    except Exception:
                        pass
                    os._exit(0)
            except Exception as e:
                messagebox.showerror("Update fehlgeschlagen",
                                     f"{e}\n\nDu kannst die neue Version auch manuell laden.")

    def _maybe_consent(self):
        if config.has_consent():
            return
        C = theme.COLORS
        win = tk.Toplevel(self.root, bg=C["surface"])
        win.title("Willkommen — kurz zur Einordnung")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        hdr = tk.Frame(win, bg=C["navy"]); hdr.pack(fill="x")
        tk.Label(hdr, text="Dein persönliches Auswertungs-Tool", bg=C["navy"], fg=C["on_dark"],
                 font=theme.F_H2).pack(padx=20, pady=12)
        msg = ("Dieses Tool hilft DIR, deinen eigenen Arbeitstag am PC zu verstehen und\n"
               "Abläufe zu verbessern. Du startest und stoppst selbst.\n\n"
               "• Alle Daten bleiben NUR auf diesem PC — nichts geht ins Internet.\n"
               "• Kein Mitschneiden von Texten, keine Screenshots, keine Kamera.\n"
               "• Nur Hauptadresse (z. B. www.westnetz.de), nicht der volle Link.\n"
               "• Nur du siehst die Auswertung. Keine Leistungsbewertung.\n"
               "• Du kannst die Daten jederzeit löschen.")
        tk.Label(win, text=msg, justify="left", font=theme.F_BODY, bg=C["surface"], fg=C["text"]
                 ).pack(padx=22, pady=(14, 6))
        var = tk.IntVar(value=0)
        tk.Checkbutton(win, text="Ich nutze das Tool freiwillig zur eigenen Auswertung.",
                       variable=var, font=theme.F_BODY, bg=C["surface"], fg=C["text"],
                       activebackground=C["surface"], selectcolor=C["surface"]).pack(padx=22, pady=(2, 6))

        def accept():
            if not var.get():
                messagebox.showinfo("Hinweis", "Bitte das Häkchen setzen, um fortzufahren.")
                return
            config.set_consent()
            win.destroy()

        theme.button(win, "Verstanden & los", accept, kind="success").pack(pady=(4, 18))
        win.protocol("WM_DELETE_WINDOW", lambda: None)

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
        img = Image.new("RGB", (64, 64), "#1B3A6B")
        d = ImageDraw.Draw(img)
        d.rectangle([16, 30, 24, 48], fill="#0ea5e9")
        d.rectangle([28, 20, 36, 48], fill="#38bdf8")
        d.rectangle([40, 10, 48, 48], fill="#7dd3fc")
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

    def _autostart_label(self):
        return "🚀 Autostart: An" if self.cfg.get("autostart", True) else "🚀 Autostart: Aus"

    def _toggle_autostart(self):
        new = not bool(self.cfg.get("autostart", True))
        self.cfg["autostart"] = new
        config.save_config(self.cfg)
        ok = autostart.sync(new)
        try:
            self.autostart_btn.config(text=self._autostart_label())
        except Exception:
            pass
        if not autostart.is_frozen():
            messagebox.showinfo("Autostart",
                                "Einstellung gespeichert. Der Autostart wirkt nur in der installierten App (.exe).")
        elif new and not ok:
            messagebox.showwarning("Autostart", "Autostart konnte nicht eingerichtet werden.")
        elif new:
            messagebox.showinfo("Autostart", "Das Tool startet künftig automatisch mit Windows.")
        else:
            messagebox.showinfo("Autostart", "Der Autostart wurde deaktiviert.")

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
        theme.dialog(self)
        C = theme.COLORS
        theme.dialog_header(self, "➕ Offline-Tätigkeit nachtragen")
        body = tk.Frame(self, bg=C["surface"]); body.pack(fill="both", padx=18, pady=14)
        cats = sorted(set(list(cfg.get("process_categories", {}).values()) +
                          list(cfg.get("domain_categories", {}).values()) +
                          ["Telefonie (AGFEO)", "E-Mail", "Office", "Besprechung"]))
        pad = {"padx": 8, "pady": 6}

        def lab(r, t):
            tk.Label(body, text=t, bg=C["surface"], fg=C["muted"], font=theme.F_BODY).grid(
                row=r, column=0, sticky="w", **pad)

        lab(0, "Kategorie")
        self.cat = ttk.Combobox(body, values=cats, state="readonly", width=24)
        self.cat.set("Besprechung")
        self.cat.grid(row=0, column=1, **pad)
        lab(1, "Datum (TT.MM.JJJJ)")
        self.date = theme.entry(body, width=26)
        self.date.insert(0, datetime.now().strftime("%d.%m.%Y"))
        self.date.grid(row=1, column=1, **pad)
        lab(2, "Startzeit (HH:MM)")
        self.time = theme.entry(body, width=26)
        self.time.insert(0, datetime.now().strftime("%H:%M"))
        self.time.grid(row=2, column=1, **pad)
        lab(3, "Dauer (Minuten)")
        self.mins = theme.entry(body, width=26)
        self.mins.insert(0, "30")
        self.mins.grid(row=3, column=1, **pad)
        theme.button(body, "Speichern", self._save, kind="success").grid(
            row=4, column=0, columnspan=2, pady=(12, 2))

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


class TaskMatcherDialog(tk.Toplevel):
    """Aufgaben-Erkennung: pro Seite/App festlegen, woran erkannt wird, dass
    mehrere Fenster zur SELBEN Aufgabe gehören (z.B. gleicher Kundenname im Titel)."""

    def __init__(self, master, on_saved=None):
        super().__init__(master)
        self.title("Aufgaben-Erkennung")
        self.geometry("720x560")
        self.on_saved = on_saved
        self.cfg = config.load_config()
        self.rows = []  # (frame, match_entry, pattern_entry)
        theme.dialog(self)
        C = theme.COLORS
        theme.dialog_header(self, "🧩 Aufgaben-Erkennung")
        tk.Label(self, justify="left", font=theme.F_SMALL, bg=C["surface"], fg=C["muted"], wraplength=680, text=(
            "Mehrere Fenster zählen als EINE Aufgabe, wenn im Fenstertitel dieselbe „Schlagzeile\" steht "
            "(z. B. Kundenname oder Adresse). Lege je Seite/Programm fest, welcher Teil des Titels der "
            "Identifikator ist.\n\n"
            "• Seite/App: Teil der Adresse oder des Programmnamens, z. B. verwaltung.mein-handwerker.de oder westnetz.de\n"
            "• Muster (Regex): der Teil in Klammern ( ) wird als Identifikator genommen. Leer = ganzer Titel.\n"
            "  Beispiele:  Kunde:?\\s*([^|\\-–]+)   ·   ([0-9]{5,})   ·   ^([^|\\-–]+)")
        ).pack(anchor="w", padx=14)

        # Bereich für die Regeln
        self.list_frame = tk.Frame(self, bg=C["surface"])
        self.list_frame.pack(fill="both", expand=True, padx=14, pady=8)
        head = tk.Frame(self.list_frame, bg=C["surface"]); head.pack(fill="x")
        tk.Label(head, text="Seite / App", width=30, anchor="w", bg=C["surface"], fg=C["text"],
                 font=(theme.FONT, 9, "bold")).pack(side="left")
        tk.Label(head, text="Muster (Regex, Gruppe 1)", anchor="w", bg=C["surface"], fg=C["text"],
                 font=(theme.FONT, 9, "bold")).pack(side="left")

        for m in (self.cfg.get("task_matchers") or []):
            self._add_row(m.get("match", ""), m.get("pattern", ""))
        if not (self.cfg.get("task_matchers") or []):
            self._add_row("", "")

        theme.button(self, "+ Regel hinzufügen", lambda: self._add_row("", ""),
                     kind="secondary", compact=True).pack(anchor="w", padx=14)

        # Test
        test = tk.Frame(self, bg=C["surface"], highlightbackground=C["border"], highlightthickness=1)
        test.pack(fill="x", padx=14, pady=8)
        tk.Label(test, text="Test", bg=C["surface"], fg=C["navy"], font=theme.F_H2).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(test, text="Fenstertitel zum Testen:", bg=C["surface"], fg=C["muted"],
                 font=theme.F_SMALL).pack(anchor="w", padx=10)
        self.test_in = theme.entry(test); self.test_in.pack(fill="x", padx=10, pady=(2, 4))
        theme.button(test, "Identifikator anzeigen", self._test, kind="secondary", compact=True).pack(anchor="w", padx=10, pady=2)
        self.test_out = tk.Label(test, text="", bg=C["surface"], fg=C["navy"], font=(theme.FONT, 10, "bold"))
        self.test_out.pack(anchor="w", padx=10, pady=(2, 8))

        bar = tk.Frame(self, bg=C["surface"]); bar.pack(fill="x", padx=14, pady=(0, 12))
        theme.button(bar, "Speichern", self._save, kind="success").pack(side="right")
        theme.button(bar, "Abbrechen", self.destroy, kind="secondary").pack(side="right", padx=6)

    def _add_row(self, match, pattern):
        C = theme.COLORS
        f = tk.Frame(self.list_frame, bg=C["surface"]); f.pack(fill="x", pady=2)
        me = theme.entry(f, width=30); me.insert(0, match); me.pack(side="left")
        pe = theme.entry(f); pe.insert(0, pattern); pe.pack(side="left", fill="x", expand=True, padx=(4, 4))
        btn = theme.button(f, "✕", lambda: (f.destroy(), self.rows.remove(entry)), kind="danger", compact=True)
        btn.pack(side="left")
        entry = (f, me, pe)
        self.rows.append(entry)

    def _collect(self):
        out = []
        for _, me, pe in self.rows:
            m = me.get().strip()
            if m:
                out.append({"match": m, "pattern": pe.get().strip()})
        return out

    def _test(self):
        import re
        title = self.test_in.get()
        for mm in self._collect():
            pat = mm.get("pattern")
            try:
                if pat:
                    r = re.search(pat, title, re.IGNORECASE)
                    if r:
                        tok = r.group(1) if r.groups() else r.group(0)
                        tok = re.sub(r"\s+", " ", tok).strip()
                        self.test_out.config(text="„" + mm["match"] + "\"  →  Aufgabe: " + tok, fg=theme.COLORS["success"])
                        return
            except re.error as e:
                self.test_out.config(text=f"Ungültiges Muster bei „{mm['match']}\": {e}", fg=theme.COLORS["danger"])
                return
        self.test_out.config(text="Kein Treffer (kein Muster passt / greift).", fg=theme.COLORS["subtle"])

    def _save(self):
        import json
        cfg = config.load_config()
        cfg["task_matchers"] = self._collect()
        try:
            with open(config.config_path(), "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Fehler", str(e)); return
        messagebox.showinfo("Gespeichert", "Aufgaben-Erkennung gespeichert. Die Auswertung wird neu berechnet.")
        if self.on_saved:
            self.on_saved()
        self.destroy()
