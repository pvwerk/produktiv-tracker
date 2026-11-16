# build-mac.spec — PyInstaller für macOS (16.11.2026): Programmpaket .app
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ["matplotlib", "PIL", "psutil", "Quartz", "certifi"]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += ["PIL._tkinter_finder", "mac_activity", "netz", "certifi"]

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # Windows-Pakete gar nicht erst einsammeln
    excludes=["PyQt5", "PyQt6", "PySide2", "PySide6", "uiautomation", "comtypes", "pystray"],
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Produktivitaets-Tracker",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False,
               name="Produktivitaets-Tracker")
app = BUNDLE(
    coll,
    name="Produktivitaets-Tracker.app",
    bundle_identifier="de.photovoltaikwerk.produktiv-tracker",
    info_plist={
        "CFBundleName": "Produktivitäts-Tracker",
        "CFBundleDisplayName": "Produktivitäts-Tracker",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
        # Text der macOS-Abfrage, wenn das Tool den Browser nach der Adresse fragt
        "NSAppleEventsUsageDescription":
            "Das Tool liest nur die Hauptadresse der geöffneten Seite "
            "(z. B. www.westnetz.de), um die Zeit der richtigen Kategorie zuzuordnen. "
            "Die Daten bleiben auf diesem Mac.",
    },
)
