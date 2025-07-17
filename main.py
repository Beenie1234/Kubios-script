"""
main.py  – entry-point and orchestration layer
––––––––––––––––––––––––––––––––––––––––––––––
If called without CLI parameters we pop the Tk-GUI from gui.py.
Otherwise we read user_config.json + CLI overrides and run directly.
"""

from __future__ import annotations
import logging, time
from pathlib import Path
from typing import Dict, List, Any
from tkinter import messagebox

from config import CONFIG, LOG_FILE, DAY_INTERVALS, MAX_SAMPLES_PER_FILE
from file_io import read_edf_list, resolve_edf_paths
from kubios_control import open_kubios, bring_kubios_to_front, close_kubios
from analysis_driver import (open_edf_file, perform_read,
                             detect_analysis_error, read_time_and_length, detect_analysis_window)
from sample_and_saver import add_sample, save_results
from analysis_logic import split_samples, td_to_str, str_to_td

# ------------------------------------------------------------------ logging --
logging.basicConfig(filename=LOG_FILE,
                    level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s  %(message)s")
logger = logging.getLogger(__name__)




def run_pipeline(cfg: Dict[str, str | List]) -> None:


    excel_path = Path(cfg["excel_path"])
    files_dir = Path(cfg["files_dir"])
    output_dir = Path(cfg["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    kubios_exe = Path(cfg["kubios_path"])
    intervals = cfg.get("day_intervals", DAY_INTERVALS)

    success, failures = [], []

    edf_names = read_edf_list(excel_path)
    edf_paths = resolve_edf_paths(files_dir, edf_names)
    for edf in edf_paths:
        pid = edf.stem
        try:
            logger.info("=== Starting analysis of %s ===", pid)
            open_kubios(kubios_exe)
            time.sleep(4)
            bring_kubios_to_front()
            open_edf_file(edf)

            # læser start og længde med OCR
            for ocr_try in range(15):
                start_str, length_str = read_time_and_length()
                if start_str and length_str:
                    break
                logger.warning(f"OCR attempt {ocr_try+1} failed, trying again...")
                time.sleep(4)
            else:
                raise RuntimeError(f"OCR failed: Start: {start_str}, Length: {length_str}")
            logger.info(f"OCR started: start: {start_str}, length: {length_str}")

            # split til blokke ifølge optagelsen
            blocks = split_samples(start_str, length_str, pid, MAX_SAMPLES_PER_FILE, intervals=intervals)

            for blk in blocks:

                first = blk["samples"][0]
                last = blk["samples"][-1]

                block_start_td = str_to_td(first["start_time"])
                block_end_td = str_to_td(last["start_time"])
                block_len_td = block_end_td - block_start_td
                block_len_str = td_to_str(block_len_td)
                print(f"Block length: {block_len_str}")

                read_all = (block_start_td.total_seconds() == 0 and block_len_str == length_str)
                perform_read(read_all, first["start_time"], block_len_str if not read_all else None)
                if detect_analysis_window():
                    logger.info("Detected analysis window")
                for smp in blk["samples"]:
                    add_sample(smp["start_time"], smp["length"], smp["index"], smp["label"])
                    time.sleep(0.5)

                save_results(str(output_dir), blk["output_filename"])
                time.sleep(1)
                if detect_analysis_error("error"):
                    raise RuntimeError("Kubios error popup")
            success.append(pid)
            close_kubios()
            time.sleep(2)



        except Exception as exc:
            logger.exception("Analysis of %s failed!", pid)
            failures.append(f"{pid}: {exc}")
            close_kubios()
            time.sleep(5)
            continue

        ok_txt = "\n ".join(success) or "Ingen"
        fail_txt = "\n ".join(failures) or "Ingen"
        summary = f"Analysen er færdig. \n\nSucces ({len(success)}):\n {ok_txt}\n\n" \
                  f"Fails ({len(failures)}):\n {fail_txt}\n\n"
        logger.info(summary.replace("\n", " | "))
        messagebox.showinfo(title="Analysis", message=summary)



if __name__ == "__main__":
    import gui
    gui.ConfigUI().mainloop()