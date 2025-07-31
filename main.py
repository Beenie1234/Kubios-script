"""
Hovedprogram der koordinerer HRV-analyse pipelinen.
main.py"""

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

# Opsæt logning til fil
logging.basicConfig(filename=LOG_FILE,
                    level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s  %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline(cfg: Dict[str, str | List]) -> None:
    """
    Hovedfunktion der kører hele HRV-analyse pipelinen.

    Args:
        cfg: Konfigurationsordbog indeholdende alle indstillinger som filstier,
             intervaller og andet indlæst fra GUI eller config filen.
    """

    # config
    excel_path = Path(cfg["excel_path"])
    files_dir = Path(cfg["files_dir"])
    output_dir = Path(cfg["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)  # Opret output-directory hvis det ikke eksisterer
    kubios_exe = Path(cfg["kubios_path"])
    intervals = cfg.get("day_intervals", DAY_INTERVALS)

    # Få brugerdefinerede samplevinduer fra konfiguration hvis brugeren specificerede dem
    sample_windows = cfg.get("sample_windows", None)

    # Spor resultater til endelig sammenfatning
    success_blocks = []  # Liste over succesfuldt behandlede bloknavne
    failed_blocks = []   # Liste over ordbøger med fejldetaljer

    # Læs liste over EDF-filer der skal behandles fra Excel-fil
    edf_names = read_edf_list(excel_path)
    edf_paths = resolve_edf_paths(files_dir, edf_names)

    # Behandl hver EDF-fil
    for edf in edf_paths:
        pid = edf.stem  # Patient ID fra filnavn
        start_str, length_str = None, None  # Vil indeholde OCR-resultater
        blocks = []  # Vil indeholde analyseblokke for denne fil

        try:
            logger.info("=== Starter analyse af %s ===", pid)

            # Åbn Kubios software og indlæs EDF-filen
            open_kubios(kubios_exe)
            time.sleep(4)  # Vent på at Kubios fuldt indlæses
            bring_kubios_to_front()
            open_edf_file(edf)

            # Brug OCR til at læse optagelsens starttid og varighed fra Kubios
            for ocr_try in range(15):
                start_str, length_str = read_time_and_length()
                if start_str and length_str:
                    break  # OCR succesfuld
                logger.warning(f"OCR forsøg {ocr_try+1} fejlede, prøver igen...")
                time.sleep(4)
            else:
                # OCR fejlede efter alle forsøg
                raise RuntimeError(f"OCR fejlede: Start: {start_str}, Længde: {length_str}. Kan være ukendt filtype")

            logger.info(f"OCR data: start: {start_str}, længde: {length_str}")

            # Opdel optagelsen i analyseblokke baseret på tidsintervaller
            use_custom_intervals = cfg.get("use_custom_intervals", False)
            intervals_param = None if not use_custom_intervals else intervals

            blocks = split_samples(
                start_str,
                length_str,
                pid,
                MAX_SAMPLES_PER_FILE,
                intervals=intervals_param,
                sample_windows=sample_windows,
                use_custom_intervals=use_custom_intervals
            )

            logger.info(f"Genererede {len(blocks)} blokke for {pid}")

            # Behandl hver blok
            for blk_idx, blk in enumerate(blocks):
                block_name = blk["output_filename"]

                try:
                    logger.info(f"=== Behandler blok {blk_idx + 1}/{len(blocks)}: {block_name} ===")

                    # For blokke efter den første, genstart Kubios for at undgå hukommelsesproblemer
                    if blk_idx > 0:
                        logger.info("Genstarter Kubios for ny blok")
                        close_kubios()
                        time.sleep(3)
                        open_kubios(kubios_exe)
                        time.sleep(4)
                        bring_kubios_to_front()
                        open_edf_file(edf)
                        time.sleep(2)

                    # Få timing-information for denne blok
                    first = blk["samples"][0]
                    last = blk["samples"][-1]

                    # Blok-timing er relativt til optagelsens start (til Kubios interface)
                    block_start_str = first["block_start_time"]
                    block_end_str = first["block_end_time"]

                    logger.info(f"Blok {blk_idx + 1} tidsområde: {block_start_str} til {block_end_str}")

                    # Tjek om vi skal læse alle data (når blokken dækker hele optagelsen)
                    read_all = (block_start_str == "00:00:00" and block_end_str == length_str)

                    # Håndter Kubios-dialog hvis den vises
                    if detect_open_data_file():
                        logger.info("Detekterede 'åbn datafil' vindue")

                    # Fortæl Kubios at læse dataene for dette tidsområde
                    perform_read(read_all, block_start_str, block_end_str if not read_all else None)
                    time.sleep(2)

                    # Vent på at Kubios-analysevinduet vises
                    analysis_window_detected = False
                    for detection_try in range(10):
                        if detect_analysis_window():
                            logger.info("Analysevindue detekteret")
                            analysis_window_detected = True
                            break
                        time.sleep(1)

                    if not analysis_window_detected:
                        logger.warning("Fejlede i at detektere analysevindue, fortsætter alligevel")

                    # Tilføj alle samples for denne blok til Kubios
                    logger.info(f"Tilføjer {len(blk['samples'])} samples til blok {block_name}")
                    for smp_idx, smp in enumerate(blk["samples"]):
                        sample_info = f"Sample {smp['index']}: {smp['label']} ({smp['start_time']}, {smp['length']})"
                        logger.info(f"Tilføjer {sample_info}")
                        add_sample(smp["start_time"], smp["length"], smp["index"], smp["label"])
                        time.sleep(0.5)  # Kort pause mellem samples

                    # Log diagnostisk information om det sidste sample
                    last_sample = blk["samples"][-1]
                    recording_start = str_to_td(start_str.replace('.', ':'))
                    recording_duration = str_to_td(length_str)
                    recording_absolute_end = recording_start + recording_duration
                    last_sample_start = str_to_td(last_sample['start_time'])
                    last_sample_length = str_to_td(last_sample['length'])
                    last_sample_end = last_sample_start + last_sample_length

                    logger.info(f"Sidste sample diagnostik - Slut: {td_to_str(last_sample_end)}, Optagelse slut: {td_to_str(recording_absolute_end)}, Overskrider: {last_sample_end > recording_absolute_end}")

                    # Gem analyseresultaterne for denne blok som Excel-fil
                    save_results(str(output_dir), block_name)
                    logger.info(f"Succesfuldt gemt blok: {block_name}")

                    # Registrer succesfuld blok
                    success_blocks.append(block_name)

                    # Tjek om Kubios viste nogen fejlmeddelelser
                    if detect_analysis_error("error"):
                        raise RuntimeError("Kubios fejl-popup detekteret")

                except Exception as block_exc:
                    # Denne blok fejlede - log detaljeret information
                    logger.exception(f"Blok {block_name} fejlede!")

                    # Indsaml information om alle samples i den fejlede blok
                    sample_details = []
                    for s in blk.get('samples', []):
                        sample_details.append(f"Sample {s.get('index', '?')}: {s.get('label', 'Ukendt')} ({s.get('start_time', '?')}, {s.get('length', '?')})")

                    # Gem detaljeret fejlinformation
                    failed_block_info = {
                        'block_name': block_name,
                        'error': str(block_exc),
                        'samples': sample_details
                    }
                    failed_blocks.append(failed_block_info)

                    # Log detaljeret fejlinformation til logfil
                    logger.error(f"FEJLET BLOK: {block_name}")
                    logger.error(f"FEJL: {str(block_exc)}")
                    logger.error(f"SAMPLES I FEJLET BLOK:")
                    for sample_detail in sample_details:
                        logger.error(f"  - {sample_detail}")

                    # Fortsæt med at behandle andre blokke
                    continue

            # Luk Kubios efter behandling af alle blokke for denne fil
            close_kubios()
            time.sleep(2)
            logger.info(f"Afsluttede behandling af alle blokke for {pid}")

        except Exception as file_exc:
            # Hele filen fejlede under opsætning eller OCR
            logger.exception(f"Fil {pid} fejlede under opsætning eller OCR!")

            # Markér alle blokke for denne fil som fejlede
            if blocks:
                for blk in blocks:
                    block_name = blk["output_filename"]
                    sample_details = [f"Sample {s.get('index', '?')}: {s.get('label', 'Ukendt')}" for s in blk.get('samples', [])]

                    failed_block_info = {
                        'block_name': block_name,
                        'error': f"Fil opsætningsfejl: {str(file_exc)}",
                        'samples': sample_details
                    }
                    failed_blocks.append(failed_block_info)

                    # Log hver fejlede blok
                    logger.error(f"FEJLET BLOK (fil opsætningsfejl): {block_name}")
                    logger.error(f"FEJL: Fil opsætningsfejl: {str(file_exc)}")
                    logger.error(f"SAMPLES I FEJLET BLOK:")
                    for sample_detail in sample_details:
                        logger.error(f"  - {sample_detail}")
            else:
                # Ingen blokke blev overhovedet genereret
                failed_block_info = {
                    'block_name': f"{pid}_blokke_ikke_genereret",
                    'error': f"Opsætningsfejl: {str(file_exc)}",
                    'samples': ["Ingen samples genereret på grund af opsætningsfejl"]
                }
                failed_blocks.append(failed_block_info)

                logger.error(f"FEJLET FIL: {pid}_blokke_ikke_genereret")
                logger.error(f"FEJL: Opsætningsfejl: {str(file_exc)}")
                logger.error("Ingen samples genereret på grund af opsætningsfejl")

            # Sørg for at Kubios er lukket før fortsættelse
            close_kubios()
            time.sleep(5)
            continue

    # Opret sammenfatning for brugeren der viser hvad der lykkedes og hvad der fejlede
    success_summary = "\n".join([f"  ✓ {block}" for block in success_blocks]) if success_blocks else "  Ingen"

    # Formatér fejlede blokke med detaljeret information
    failure_details = []
    if failed_blocks:
        for failed_block in failed_blocks:
            block_name = failed_block['block_name']
            error = failed_block['error']
            samples = failed_block['samples']

            failure_details.append(f"  ✗ {block_name}")
            failure_details.append(f"    Fejl: {error}")
            failure_details.append(f"    Samples: {len(samples)} samples påvirket")
            # Vis de første få samples for ikke at overvælde brugeren
            for sample in samples[:3]:
                failure_details
                failure_details.append(f"      - {sample}")
            if len(samples) > 3:
                failure_details.append(f"      - ... and {len(samples) - 3} more samples")
            failure_details.append("")  # Empty line between failed blocks

    failure_summary = "\n".join(failure_details) if failure_details else "  None"

    detailed_summary = f"""Analysis Complete!

SUCCESSFUL BLOCKS ({len(success_blocks)}):
{success_summary}

FAILED BLOCKS ({len(failed_blocks)}):
{failure_summary}

SUMMARY: {len(success_blocks)} successful blocks, {len(failed_blocks)} failed blocks processed.
Each successful block was saved as a separate Excel file in the output directory.
"""

    # Log the summary (single line for log file)
    log_summary = f"Analysis complete: {len(success_blocks)} successful blocks, {len(failed_blocks)} failed blocks"
    logger.info(log_summary)

    # Log successful blocks summary
    if success_blocks:
        logger.info("SUCCESSFUL BLOCKS: " + ", ".join(success_blocks))

    # Show detailed summary to user
    messagebox.showinfo(title="Analysis Results", message=detailed_summary)


if __name__ == "__main__":
    import gui
    gui.ConfigUI().mainloop()