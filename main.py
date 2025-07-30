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
import pyautogui

from config import CONFIG, LOG_FILE, DAY_INTERVALS, MAX_SAMPLES_PER_FILE
from file_io import read_edf_list, resolve_edf_paths
from kubios_control import open_kubios, bring_kubios_to_front, close_kubios
from analysis_driver import (open_edf_file, perform_read,
                             detect_analysis_error, read_time_and_length, detect_analysis_window, detect_save_dialog,
                             detect_open_data_file)
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

    # Get custom sample windows from config if they exist
    sample_windows = cfg.get("sample_windows", None)

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

            # FIXED: Issue 2 - Use None for intervals if they equal DEFAULT_INTERVALS
            use_custom_intervals = cfg.get("use_custom_intervals", False)
            intervals_param = None if not use_custom_intervals else intervals

            # split til blokke ifølge optagelsen - FIXED: Pass sample_windows parameter
            blocks = split_samples(
                start_str,
                length_str,
                pid,
                MAX_SAMPLES_PER_FILE,
                intervals=intervals_param,  # Use None for default behavior
                sample_windows=sample_windows,  # Add this parameter
                use_custom_intervals=use_custom_intervals  # Add this flag
            )

            for blk_idx, blk in enumerate(blocks):

                # FIXED: Reopen file for each block (not just non-first blocks)
                if blk_idx != 0:
                    open_edf_file(edf)
                    time.sleep(2)  # Give it time to load

                first = blk["samples"][0]
                last = blk["samples"][-1]

                # FIXED: Issue 1 - Use block_start_time and block_end_time (relative) for Kubios operations
                block_start_str = first["block_start_time"]  # This is relative start time
                block_end_str = first["block_end_time"]  # This is relative end time

                print(f"Block {blk_idx + 1} start: {block_start_str}, end: {block_end_str}")

                # Check if we should read all (first block starting at 00:00:00 with end matching total length)
                read_all = (block_start_str == "00:00:00" and block_end_str == length_str)

                if detect_open_data_file():
                    print("Detected 'open data file'-window")

                # FIXED: Use block end time instead of block length
                perform_read(read_all, block_start_str, block_end_str if not read_all else None)
                time.sleep(2)


                # FIXED: Only detect analysis window AFTER the read is complete
                analysis_window_detected = False
                for detection_try in range(10):  # Try multiple times

                    if detect_analysis_window():
                        logger.info("Detected analysis window")
                        analysis_window_detected = True
                        break
                    time.sleep(1)

                if not analysis_window_detected:
                    logger.warning("Failed to detect analysis window, continuing anyway")

                # Add samples - samples still use absolute time for display
                for smp in blk["samples"]:
                    print(f"Adding sample: {smp['start_time']}, {smp['length']}, {smp['index']}, {smp['label']}")
                    add_sample(smp["start_time"], smp["length"], smp["index"], smp["label"])
                    time.sleep(0.5)

                # FIXED: Better save dialog handling
                try:
                    last_sample = blk["samples"][-1]
                    logger.info("=== LAST SAMPLE DIAGNOSTICS ===")
                    logger.info(f"Recording start: {start_str}")
                    logger.info(f"Recording duration: {length_str}")
                    logger.info(f"Last sample: {last_sample}")

                    # Calculate actual end times
                    recording_start = str_to_td(start_str.replace('.', ':'))
                    recording_duration = str_to_td(length_str)
                    recording_absolute_end = recording_start + recording_duration

                    last_sample_start = str_to_td(last_sample['start_time'])
                    last_sample_length = str_to_td(last_sample['length'])
                    last_sample_end = last_sample_start + last_sample_length

                    logger.info(f"Recording absolute end: {td_to_str(recording_absolute_end)}")
                    logger.info(f"Last sample start: {last_sample['start_time']}")
                    logger.info(f"Last sample length: {last_sample['length']}")
                    logger.info(f"Last sample end: {td_to_str(last_sample_end)}")
                    logger.info(f"Sample exceeds recording: {last_sample_end > recording_absolute_end}")
                    logger.info("=== END DIAGNOSTICS ===")

                    save_results(str(output_dir), blk["output_filename"])
                    logger.info(f"Saved results for analysis to {blk['output_filename']}")

                except Exception as save_exc:
                    logger.error(f"Save operation failed: {save_exc}")
                    # Continue with next block even if save fails

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