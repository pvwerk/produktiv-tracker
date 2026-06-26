# theme.py — zentrale Optik, angelehnt an das PVWERK-CRM
# Flat-Design, Marken-Navy-Header, Sky-Blau als Primärfarbe, Karten mit dünner Border.
import tkinter as tk
from tkinter import ttk

COLORS = {
    "bg":            "#f1f5f9",  # Seitenhintergrund (slate-100)
    "surface":       "#ffffff",  # Karten
    "border":        "#e2e8f0",  # gray/slate-200
    "navy":          "#1B3A6B",  # Marken-Navy (Header)
    "navy2":         "#2E6DB4",  # Marken-Blau
    "primary":       "#0284c7",  # sky-600
    "primary_hover": "#0369a1",  # sky-700
    "success":       "#059669",  # emerald-600
    "success_hover": "#047857",
    "danger":        "#dc2626",  # red-600
    "danger_hover":  "#b91c1c",
    "text":          "#0f172a",  # slate-900
    "muted":         "#64748b",  # slate-500
    "subtle":        "#94a3b8",  # slate-400
    "on_dark":       "#ffffff",
    "on_dark_muted": "#cbd5e1",
}

FONT = "Segoe UI"
F_H1    = (FONT, 15, "bold")
F_H2    = (FONT, 12, "bold")
F_BODY  = (FONT, 10)
F_SMALL = (FONT, 9)
F_BTN   = (FONT, 10, "bold")

_KINDS = {
    "primary":   (COLORS["primary"], COLORS["primary_hover"], COLORS["on_dark"], None),
    "success":   (COLORS["success"], COLORS["success_hover"], COLORS["on_dark"], None),
    "danger":    (COLORS["danger"],  COLORS["danger_hover"],  COLORS["on_dark"], None),
    "secondary": (COLORS["surface"], "#f1f5f9",               COLORS["text"],    COLORS["border"]),
    "ghost":     (COLORS["bg"],      "#e2e8f0",               COLORS["muted"],   None),
}


def style_button(btn, kind="secondary", compact=False):
    bg, hover, fg, border = _KINDS.get(kind, _KINDS["secondary"])
    btn.configure(bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
                  relief="flat", bd=0, cursor="hand2",
                  font=((FONT, 9, "bold") if compact else F_BTN),
                  padx=(9 if compact else 12), pady=(5 if compact else 7),
                  highlightthickness=(1 if border else 0),
                  highlightbackground=(border or bg), highlightcolor=(border or bg))
    btn._kind = kind
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover), add="+")
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg), add="+")
    return btn


def button(parent, text, command, kind="secondary", compact=False, **kw):
    b = tk.Button(parent, text=text, command=command, **kw)
    return style_button(b, kind, compact)


def set_kind(btn, kind, text=None, compact=False):
    """Wechselt Button-Stil sauber (alte Hover-Bindings entfernen)."""
    btn.unbind("<Enter>")
    btn.unbind("<Leave>")
    if text is not None:
        btn.configure(text=text)
    style_button(btn, kind, compact)


def card(parent, padx=0, pady=0, **kw):
    return tk.Frame(parent, bg=COLORS["surface"], highlightbackground=COLORS["border"],
                    highlightcolor=COLORS["border"], highlightthickness=1, bd=0, **kw)


def entry(parent, **kw):
    return tk.Entry(parent, relief="flat", bg="white", fg=COLORS["text"],
                    highlightthickness=1, highlightbackground=COLORS["border"],
                    highlightcolor=COLORS["primary"], insertbackground=COLORS["text"], **kw)


def dialog(win):
    """Toplevel-Hintergrund auf Surface setzen."""
    win.configure(bg=COLORS["surface"])
    return win


def dialog_header(parent, text):
    h = tk.Frame(parent, bg=COLORS["navy"])
    h.pack(fill="x")
    tk.Label(h, text=text, bg=COLORS["navy"], fg=COLORS["on_dark"], font=F_H2).pack(
        side="left", padx=16, pady=11)
    return h


def label(parent, text, on="bg", kind="body", **kw):
    bg = COLORS["surface"] if on == "surface" else (COLORS["navy"] if on == "navy" else COLORS["bg"])
    fg = {"body": COLORS["text"], "muted": COLORS["muted"], "h1": COLORS["text"],
          "h2": COLORS["text"], "on_dark": COLORS["on_dark"], "on_dark_muted": COLORS["on_dark_muted"]}[kind]
    font = {"body": F_BODY, "muted": F_SMALL, "h1": F_H1, "h2": F_H2,
            "on_dark": F_H1, "on_dark_muted": F_SMALL}[kind]
    return tk.Label(parent, text=text, bg=bg, fg=fg, font=font, **kw)


def apply(root):
    """Globale Optik setzen (Root-Hintergrund + ttk-Styles)."""
    root.configure(bg=COLORS["bg"])
    try:
        root.option_add("*Font", (FONT, 10))
    except Exception:
        pass
    s = ttk.Style(root)
    try:
        s.theme_use("clam")
    except Exception:
        pass
    s.configure("TNotebook", background=COLORS["bg"], borderwidth=0, tabmargins=(4, 4, 4, 0))
    s.configure("TNotebook.Tab", font=(FONT, 10, "bold"), padding=(16, 8),
                background="#e2e8f0", foreground=COLORS["muted"], borderwidth=0)
    s.map("TNotebook.Tab",
          background=[("selected", COLORS["surface"])],
          foreground=[("selected", COLORS["navy"])])
    s.configure("TCombobox", fieldbackground="white", background="white",
                bordercolor=COLORS["border"], arrowcolor=COLORS["navy"], padding=4)
    s.configure("Vertical.TScrollbar", background="#e2e8f0", troughcolor=COLORS["bg"], borderwidth=0)
    return s
