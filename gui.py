"""
GUI-modul - Tkinter brugergrænseflade til Kubios HRV-automatisering.

Brugeren kan konfigurere:
    • Excel-liste med filnavne
    • Kubios executable sti
    • EDF-filer mappe
    • Output-mappe
    • Tidsintervaller (dag/aften/nat)

Værdierne gemmes i user_config.json som resten af programmet læser.
"""

import json, logging
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from config import DEFAULTS, LOG_FILE, DAY_INTERVALS

# Opsæt logning
logging.basicConfig(filename=LOG_FILE,
                    level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

USER_CONF = Path("user_config.json")

# Hjælpefunktioner til konfigurationshåndtering

def load_cfg() -> dict:
    """Indlæs brugerkonfiguration fra JSON-fil eller returner standardværdier"""
    if USER_CONF.exists():
        try:
            return {**DEFAULTS, **json.loads(USER_CONF.read_text())}
        except Exception as exc:
            logger.error("GUI: kunne ikke læse user_config.json: %s", exc)
    return DEFAULTS.copy()

def save_cfg(cfg: dict) -> None:
    """Gem brugerkonfiguration til JSON-fil"""
    try:
        USER_CONF.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error("GUI: kunne ikke gemme user_config.json: %s", exc)
        raise

# Proxy-funktion til at køre hovedpipelinen

def _run_pipeline(cfg: dict):
    """Kør analyse-pipelinen med den givne konfiguration"""
    try:
        from main import run_pipeline  # type: ignore
    except ImportError:
        messagebox.showerror("main.py mangler",
                             "Kunne ikke importere run_pipeline – tjek main.py")
        return
    run_pipeline(cfg)

# Tooltip-klasse til at vise hjælpetekst

class ToolTip:
    """Opret en tooltip (hjælpetekst) for et givet widget"""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)  # Når musen kommer ind over widgetten
        self.widget.bind("<Leave>", self.leave)  # Når musen forlader widgetten
        self.tipwindow = None

    def enter(self, event=None):
        """Vis tooltip når musen kommer ind"""
        self.showtip()

    def leave(self, event=None):
        """Skjul tooltip når musen forlader"""
        self.hidetip()

    def showtip(self):
        """Opret og vis tooltip-vinduet"""
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Fjern vinduesdekoration
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                      background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        """Fjern tooltip-vinduet"""
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

# Hoved-GUI klasse

class ConfigUI(tk.Tk):
    """Hovedvindue til konfiguration af HRV-analyse indstillinger"""

    def __init__(self):
        super().__init__()
        self.title("HRV Automatisering – Opsætning")
        self.resizable(False, False)  # Fast vinduesstørrelse

        # Indlæs eksisterende konfiguration
        cfg = load_cfg()

        # Række 0 - Excel-fil vælger
        tk.Label(self, text="Excel-liste:").grid(row=0, column=0, sticky="e", pady=4)
        self.excel_var = tk.StringVar(value=cfg["excel_path"])
        tk.Entry(self, textvariable=self.excel_var, width=55).grid(row=0, column=1)
        excel_btn = tk.Button(self, text="…", command=self.pick_excel, width=3)
        excel_btn.grid(row=0, column=2)
        ToolTip(excel_btn, "Vælg Excel-fil (.xlsx, .xls, .ods) med liste over EDF-filnavne")

        # Række 1 - Kubios executable vælger
        tk.Label(self, text="Kubios EXE:").grid(row=1, column=0, sticky="e", pady=4)
        self.kubios_var = tk.StringVar(value=cfg["kubios_path"])
        tk.Entry(self, textvariable=self.kubios_var, width=55).grid(row=1, column=1)
        kubios_btn = tk.Button(self, text="…", command=self.pick_kubios, width=3)
        kubios_btn.grid(row=1, column=2)
        ToolTip(kubios_btn, "Vælg Kubios HRV executable fil (.exe)")

        # Række 2 - EDF-filer mappe vælger
        tk.Label(self, text="EDF-filer mappe:").grid(row=2, column=0, sticky="e", pady=4)
        self.files_var = tk.StringVar(value=cfg.get("files_dir", DEFAULTS["files_dir"]))
        tk.Entry(self, textvariable=self.files_var, width=55).grid(row=2, column=1)
        files_btn = tk.Button(self, text="…", command=self.pick_filesdir, width=3)
        files_btn.grid(row=2, column=2)
        ToolTip(files_btn, "Vælg mappe hvor EDF-filerne ligger")

        # Række 3 - Output mappe vælger
        tk.Label(self, text="Output-mappe:").grid(row=3, column=0, sticky="e", pady=4)
        self.out_var = tk.StringVar(value=cfg.get("output_dir", DEFAULTS["output_dir"]))
        tk.Entry(self, textvariable=self.out_var, width=55).grid(row=3, column=1)
        output_btn = tk.Button(self, text="…", command=self.pick_output, width=3)
        output_btn.grid(row=3, column=2)
        ToolTip(output_btn, "Vælg mappe hvor analyserede filer skal gemmes")

        # Række 4 - Tidsintervaller tekstfelt
        tk.Label(self, text="Intervaller (TT-TT, komma):").grid(row=4, column=0, sticky="e", pady=4)
        default_int = ",".join(f"{s}-{e}" for _, s, e in cfg.get("day_intervals", []))
        self.int_var = tk.StringVar(value=default_int)
        intervals_entry = tk.Entry(self, textvariable=self.int_var, width=55)
        intervals_entry.grid(row=4, column=1, columnspan=2, sticky="we")
        ToolTip(intervals_entry, "Angiv tidsintervaller (f.eks. 07-15,15-23,23-07 for dag/aften/nat)")

        # Række 5 - Kør knap
        run_btn = tk.Button(self, text="Gem & Kør", command=self.on_run, width=20)
        run_btn.grid(row=5, column=1, pady=10)
        ToolTip(run_btn, "Gem indstillinger og start HRV-analysen")

    # Funktioner til at vælge filer og mapper

    def pick_excel(self):
        """Åbn filvælger til Excel/LibreOffice filer"""
        f = filedialog.askopenfilename(
            filetypes=[
                ("Excel og LibreOffice filer", "*.xlsx;*.xls;*.ods"),
                ("Excel filer", "*.xlsx;*.xls"),
                ("LibreOffice Calc filer", "*.ods"),
                ("Alle filer", "*.*")
            ]
        )
        if f:
            self.excel_var.set(f)

    def pick_kubios(self):
        """Åbn filvælger til Kubios executable"""
        f = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
        if f:
            self.kubios_var.set(f)

    def pick_filesdir(self):
        """Åbn mappevælger til EDF-filer"""
        d = filedialog.askdirectory()
        if d:
            self.files_var.set(d)

    def pick_output(self):
        """Åbn mappevælger til output"""
        d = filedialog.askdirectory()
        if d:
            self.out_var.set(d)

    # Hovedfunktion når brugeren klikker "Gem & Kør"

    def on_run(self):
        """Håndter når brugeren klikker på kør-knappen"""
        intervals_raw = self.int_var.get().strip()
        intervals_list = []

        # Parse tidsintervaller hvis brugeren har angivet nogle
        if intervals_raw:
            try:
                for rng in intervals_raw.split(','):
                    a, b = rng.strip().split('-')
                    start_hour = int(a)
                    end_hour = int(b)

                    # Håndter 24-timers intervaller (f.eks. 7-7)
                    if start_hour == end_hour:
                        intervals_list.append(["24t", start_hour, start_hour])
                    else:
                        intervals_list.append(["brugerdefineret", start_hour, end_hour])

            except ValueError:
                messagebox.showerror("Interval-fejl", "Format skal være fx 07-15,15-23,23-07")
                return

        # Tjek om intervallerne matcher standardværdierne
        if intervals_list:
            default_numeric = [(s, e) for _, s, e in DAY_INTERVALS]
            input_numeric = [(s, e) for _, s, e in intervals_list]
            use_default = (input_numeric == default_numeric)
        else:
            use_default = True

        # Opret konfigurationsordbog
        cfg = {
            "excel_path": self.excel_var.get(),
            "kubios_path": self.kubios_var.get(),
            "files_dir": self.files_var.get(),
            "output_dir": self.out_var.get(),
            "day_intervals": DAY_INTERVALS if use_default else intervals_list,
            "use_custom_intervals": not use_default  # Flag til at indikere brugerdefinerede intervaller
        }

        # Gem konfiguration og start analyse
        save_cfg(cfg)
        logger.info("GUI: konfiguration gemt – kører pipeline")
        messagebox.showinfo("Starter", "Analysen starter nu – se logfil for status.")
        try:
            _run_pipeline(cfg)
            messagebox.showinfo("Færdig", "Analysen er fuldført – tjek output-mappen.")
        except Exception as exc:
            logger.exception("Pipeline krasjede fra GUI")
            messagebox.showerror("Fejl", f"Pipeline stoppede: {exc}")

# Hovedfunktion hvis scriptet køres direkte
if __name__ == "__main__":
    ConfigUI().mainloop()