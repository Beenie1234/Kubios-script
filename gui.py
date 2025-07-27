"""gui.py – Tkinter front‑end til Kubios HRV‑automation.

Brugeren kan nu konfigurere:
    • Excel‑liste
    • Kubios‑exe‑sti
    • Intervaller
    • Output‑directory  <–– NYT
    • Files‑directory  <–– NYT

Værdierne gemmes i user_config.json, som resten af programmet læser.
"""

import json, logging
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from config import DEFAULTS, LOG_FILE, DAY_INTERVALS

logging.basicConfig(filename=LOG_FILE,
                    level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

USER_CONF = Path("user_config.json")

# ---------------------------------------------------------------- helpers ---

def load_cfg() -> dict:
    if USER_CONF.exists():
        try:
            return {**DEFAULTS, **json.loads(USER_CONF.read_text())}
        except Exception as exc:
            logger.error("GUI: could not read user_config.json: %s", exc)
    return DEFAULTS.copy()

def save_cfg(cfg: dict) -> None:
    try:
        USER_CONF.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error("GUI: could not save user_config.json: %s", exc)
        raise

# ------------------------------------------------------ run_pipeline proxy --

def _run_pipeline(cfg: dict):
    try:
        from main import run_pipeline  # type: ignore
    except ImportError:
        messagebox.showerror("main.py mangler",
                             "Kunne ikke importere run_pipeline – check main.py")
        return
    run_pipeline(cfg)

# ------------------------------------------------------- GUI class ----------

class ConfigUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HRV Automation – Setup")
        self.resizable(False, False)

        cfg = load_cfg()

        # Row 0 – Excel
        tk.Label(self, text="Excel‑liste:").grid(row=0, column=0, sticky="e", pady=4)
        self.excel_var = tk.StringVar(value=cfg["excel_path"])
        tk.Entry(self, textvariable=self.excel_var, width=55).grid(row=0, column=1)
        tk.Button(self, text="…", command=self.pick_excel, width=3).grid(row=0, column=2)

        # Row 1 – Kubios exe
        tk.Label(self, text="Kubios EXE:").grid(row=1, column=0, sticky="e", pady=4)
        self.kubios_var = tk.StringVar(value=cfg["kubios_path"])
        tk.Entry(self, textvariable=self.kubios_var, width=55).grid(row=1, column=1)
        tk.Button(self, text="…", command=self.pick_kubios, width=3).grid(row=1, column=2)

        # Row 2 – Files directory
        tk.Label(self, text="EDF‑files mappe:").grid(row=2, column=0, sticky="e", pady=4)
        self.files_var = tk.StringVar(value=cfg.get("files_dir", DEFAULTS["files_dir"]))
        tk.Entry(self, textvariable=self.files_var, width=55).grid(row=2, column=1)
        tk.Button(self, text="…", command=self.pick_filesdir, width=3).grid(row=2, column=2)

        # Row 3 – Output directory
        tk.Label(self, text="Output‑mappe:").grid(row=3, column=0, sticky="e", pady=4)
        self.out_var = tk.StringVar(value=cfg.get("output_dir", DEFAULTS["output_dir"]))
        tk.Entry(self, textvariable=self.out_var, width=55).grid(row=3, column=1)
        tk.Button(self, text="…", command=self.pick_output, width=3).grid(row=3, column=2)

        # Row 4 – Intervals
        tk.Label(self, text="Intervaller (HH-HH, komma):").grid(row=4, column=0, sticky="e", pady=4)
        default_int = ",".join(f"{s}-{e}" for _, s, e in cfg.get("day_intervals", []))
        self.int_var = tk.StringVar(value=default_int)
        tk.Entry(self, textvariable=self.int_var, width=55).grid(row=4, column=1, columnspan=2, sticky="we")

        # Row 5 – Run button
        tk.Button(self, text="Gem & kør", command=self.on_run, width=20).grid(row=5, column=1, pady=10)

    # ------------------------------------------------ browse helpers --------
    def pick_excel(self):
        f = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx;*.xls")])
        if f:
            self.excel_var.set(f)

    def pick_kubios(self):
        f = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
        if f:
            self.kubios_var.set(f)

    def pick_filesdir(self):
        d = filedialog.askdirectory()
        if d:
            self.files_var.set(d)

    def pick_output(self):
        d = filedialog.askdirectory()
        if d:
            self.out_var.set(d)

    # ------------------------------------------------ run handler ----------
    def on_run(self):
        intervals_raw = self.int_var.get().strip()
        intervals_list = []

        if intervals_raw:
            try:
                for rng in intervals_raw.split(','):
                    a, b = rng.strip().split('-')
                    start_hour = int(a)
                    end_hour = int(b)

                    # Handle 24-hour intervals (e.g., 7-7)
                    if start_hour == end_hour:
                        intervals_list.append(["24h", start_hour, start_hour])
                    else:
                        intervals_list.append(["custom", start_hour, end_hour])

            except ValueError:
                messagebox.showerror("Interval‑fejl", "Format skal være fx 07-15,15-23,23-07")
                return

        # Check if intervals match default - compare the numeric parts only
        if intervals_list:
            default_numeric = [(s, e) for _, s, e in DAY_INTERVALS]
            input_numeric = [(s, e) for _, s, e in intervals_list]
            use_default = (input_numeric == default_numeric)
        else:
            use_default = True

        cfg = {
            "excel_path": self.excel_var.get(),
            "kubios_path": self.kubios_var.get(),
            "files_dir": self.files_var.get(),
            "output_dir": self.out_var.get(),
            "day_intervals": DAY_INTERVALS if use_default else intervals_list,
            "use_custom_intervals": not use_default  # Flag to indicate custom intervals
        }

        save_cfg(cfg)
        logger.info("GUI: configuration saved – running pipeline")
        messagebox.showinfo("Starter", "Analysen starter nu – se logfil for status.")
        try:
            _run_pipeline(cfg)
            messagebox.showinfo("Færdig", "Analysen er fuldført – check output‑mappen.")
        except Exception as exc:
            logger.exception("Pipeline crashed from GUI")
            messagebox.showerror("Fejl", f"Pipeline stoppede: {exc}")

# -------------------------------------------------------------------- main --
if __name__ == "__main__":
    ConfigUI().mainloop()