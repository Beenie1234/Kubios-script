"""
main.py  – entry-point and orchestration layer
––––––––––––––––––––––––––––––––––––––––––––––
If called without CLI parameters we pop the Tk-GUI from gui.py.
Otherwise we read user_config.json + CLI overrides and run directly.
"""

from __future__ import annotations
import argparse, logging, sys
from pathlib import Path
from typing import Dict, List, Any

from config import CONFIG, LOG_FILE, DAY_INTERVALS, MAX_SAMPLES_PER_FILE
from file_io import read_edf_list, resolve_edf_paths
from kubios_control import open_kubios, bring_kubios_to_front, close_kubios
from analysis_driver import (open_edf_file, perform_read,
                             detect_analysis_error)
from sample_and_saver import add_sample, save_results
from analysis_logic import split_samples

# ------------------------------------------------------------------ logging --
logging.basicConfig(filename=LOG_FILE,
                    level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s  %(message)s")
logger = logging.getLogger(__name__)

# ------------------------------------------------------------- CLI Handling --
def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--excel", help="Excel path with EDF list")
    p.add_argument("--kubios", help="Path to launch_kubioshrv.exe")
    p.add_argument("--intervals",
                   help="Day intervals as e.g. 07-14,15-23,23-07 "
                        "(overrides config)")
    p.add_argument("--nogui", action="store_true",
                   help="Force CLI even if no flags are given")
    return p.parse_args()

def parse_interval_spec(spec: str) -> List[tuple[str,int,int]]:
    out: list[tuple[str,int,int]] = []
    for rng in spec.split(","):
        start, end = rng.split("-")
        out.append(("custom", int(start), int(end)))
    return out

# ---------------------------------------------------- Result aggregation ------
class RunStatus:
    def __init__(self) -> None:
        self.ok:   list[str] = []   # output filenames
        self.fail: list[str] = []   # description strings

    def log_ok(self, msg: str)   -> None: self.ok.append(msg)
    def log_err(self, msg: str)  -> None: self.fail.append(msg)

    def summary(self) -> str:
        ok_part   = "\n  ".join(self.ok)   or "Ingen"
        fail_part = "\n  ".join(self.fail) or "Ingen"
        return (f"\n===  KØRSEL FÆRDIG  ===\n"
                f"Fuldførte analyser ({len(self.ok)}):\n  {ok_part}\n\n"
                f"Fejlede analyser   ({len(self.fail)}):\n  {fail_part}\n")

# ----------------------------------------------------------- Pipeline --------
def run_pipeline(conf: Dict[str, Any]) -> None:
    """
    Called both from GUI (gui.py) and when main.py is executed CLI.
    Expects conf to contain 'excel_path', 'kubios_path', 'day_intervals'.
    """
    excel_path  = Path(conf["excel_path"])
    kubios_path = Path(conf["kubios_path"])
    intervals   = conf.get("day_intervals", DAY_INTERVALS)

    status = RunStatus()

    # ---------------------------------------------------------------- files --
    edf_names = read_edf_list(excel_path)
    edf_paths = resolve_edf_paths(excel_path, edf_names)

    logger.info("Starting run on %d EDF files", len(edf_paths))
    open_kubios(str(kubios_path))

    for edf in edf_paths:
        pid = edf.stem        # patient-id from filename
        try:
            bring_kubios_to_front()
            open_edf_file(edf)

            # --- Optional: perform a full read (read-all) first ---
            perform_read(True)

            # --- Get splits ---
            # You might want to read the true recording length via OCR here.
            # For demo we assume 150 h duration starting at 00:00:00
            splits = split_samples("00:00:00",
                                   "150:00:00",
                                   pid,
                                   MAX_SAMPLES_PER_FILE,
                                   intervals=intervals)

            for block in splits:
                samples = block["samples"]
                logger.info("Processing block %s with %d samples",
                            block["output_filename"], len(samples))

                # If recording must be re-read for each block, do it here:
                # perform_read(False, block_start, block_end)  (omitted demo)

                for smp in samples:
                    ok = add_sample(smp["start_time"],
                                    smp["length"],
                                    smp["index"],
                                    smp["label"])
                    if not ok:
                        raise RuntimeError(f"Add sample failed ({smp})")

                save_ok = save_results(Path("output"), block["output_filename"])
                if not save_ok:
                    raise RuntimeError("Save results failed")

                if detect_analysis_error("error"):
                    raise RuntimeError("Kubios reported error window")

            status.log_ok(pid)

        except Exception as e:
            logger.exception("Failure on %s", edf)
            status.log_err(f"{pid}: {e}")

    close_kubios()
    logger.info(status.summary())
    print(status.summary())

# --------------------------------------------------------- Entry-point -------
def main() -> None:
    args = parse_cli()

    # If no CLI flags AND no --nogui ➜ open GUI
    if len(sys.argv) == 1 and not args.nogui:
        import gui  # lazy import
        gui.ConfigUI().mainloop()
        return

    # Merge CLI overrides with CONFIG
    cfg = CONFIG.copy()
    if args.excel:
        cfg["excel_path"] = args.excel
    if args.kubios:
        cfg["kubios_path"] = args.kubios
    if args.intervals:
        cfg["day_intervals"] = parse_interval_spec(args.intervals)

    run_pipeline(cfg)

if __name__ == "__main__":
    main()