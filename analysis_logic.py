

"""
analysis_logic.py: TIDSBEREGNINGER OG SAMPLE-OPDELING
Dette modul håndterer opdeling af lange optagelser i mindre samples
"""

import re
from datetime import timedelta
from typing import List, Dict, Any, Tuple
import logging

from config import DAY_INTERVALS, MAX_SAMPLES_PER_FILE, MAX_READ_LENGTH, LOG_FILE, \
    FIRST_SAMPLE_BUFFER_SECONDS

DEFAULT_INTERVALS = DAY_INTERVALS
logger = logging.getLogger(__name__)


def parse_duration(duration_str: str) -> timedelta:
    """
    Konverterer en tid-streng (fx "02:30:15") til et tids-objekt
    """
    h, m, s = map(int, duration_str.split(":"))
    return timedelta(hours=h, minutes=m, seconds=s)


def parse_time_tuple(time_str):
    """
    Opdeler en tid-streng i timer, minutter og sekunder
    """
    parts = list(map(int, re.split(r'[:.]', time_str)))
    while len(parts) < 3:
        parts.append(0)
    return parts  # altid timer, minutter, sekunder


def str_to_td(s: str):
    """
    Konverterer streng til tids-objekt
    """
    h, m, s = map(int, re.split(r'[:.]', s))
    return timedelta(hours=h, minutes=m, seconds=s)


def td_to_str(td):
    """
    Konverterer tids-objekt til streng
    """
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def interval_label(hour: int, intervals=None, use_custom_intervals=False) -> str:
    """
    Finder ud af hvilken periode på dagen en given time tilhører
    (fx "dag", "aften", "nat")
    """
    if intervals is None:
        intervals = DEFAULT_INTERVALS
    for label, start, end in intervals:
        if start < end:
            if start <= hour < end:
                if use_custom_intervals:
                    return f"{start:02d}:00:00-{end:02d}:00:00"
                return label
        else:  # fx nat (23-7) eller 24-timers intervaller
            if start == end:  # 24-timers interval
                if use_custom_intervals:
                    return "00:00:00-24:00:00"
                return "24h"
            elif hour >= start or hour < end:
                if use_custom_intervals:
                    return f"{start:02d}:00:00-{end:02d}:00:00"
                return label
    logger.error("Ukendt klokkeslæt i interval_label")
    return "ukendt"


def next_interval_end(current_time: timedelta, intervals=None) -> timedelta:
    """
    Finder hvornår det nuværende tidsinterval slutter
    """
    if intervals is None:
        intervals = DEFAULT_INTERVALS
    hour = int((current_time.total_seconds() // 3600) % 24)
    today = timedelta(days=int(current_time.total_seconds() // (24 * 3600)))

    for _, start, end in intervals:
        if start < end:
            if start <= hour < end:
                interval_end = today + timedelta(hours=end)
                if interval_end <= current_time:
                    interval_end += timedelta(days=1)
                return interval_end
        else:  # fx nat eller 24-timers intervaller
            if start == end:  # 24-timers interval
                return current_time + timedelta(days=1)
            elif hour >= start or hour < end:
                interval_end = today
                if hour >= start:
                    interval_end += timedelta(days=1, hours=end)
                else:
                    interval_end += timedelta(hours=end)
                if interval_end <= current_time:
                    interval_end += timedelta(days=1)
                return interval_end
    return current_time + timedelta(hours=8)


def split_samples(
        start_time: str,
        duration_str: str,
        patient_id: str,
        max_samples_per_file: int = MAX_SAMPLES_PER_FILE,
        intervals: List[Tuple[str, int, int]] = None,
        sample_windows: List[Tuple[str, str]] = None,
        use_custom_intervals: bool = False
) -> List[Dict[str, Any]]:
    """
    Hovedfunktionen der opdeler en lang optagelse i mindre samples
    - start_time: Hvornår optagelsen startede
    - duration_str: Hvor lang optagelsen er
    - patient_id: ID på patienten
    - max_samples_per_file: Maksimum antal samples per fil
    - intervals: Tidsintervaller (dag/aften/nat)
    - sample_windows: Specifikke tidsvinduer at analysere
    - use_custom_intervals: Om der skal bruges specielle intervaller

    Returnerer en liste med filer, der hver indeholder flere samples
    """
    logger.info(f"Opdeler samples for {patient_id}: start={start_time}, varighed={duration_str}")

    # Konverter start-tid og varighed til tids-objekter
    h, m, s = map(int, re.split(r'[:.]', start_time))
    start_offset = timedelta(hours=h, minutes=m, seconds=s)
    duration_td = parse_duration(duration_str)
    total_duration = start_offset + duration_td
    samples = []
    idx = 1

    # Hvis der er specifikke tidsvinduer angivet
    if sample_windows:
        total_days = int(((duration_td + start_offset).total_seconds() // (24 * 3600))) + 1
        for day in range(total_days):
            for w_start, w_end in sample_windows:
                sh, sm, ss = parse_time_tuple(w_start)
                eh, em, es = parse_time_tuple(w_end)

                # Beregn absolutte vinduestider for denne dag
                window_start = timedelta(days=day, hours=sh, minutes=sm, seconds=ss)
                window_end = timedelta(days=day, hours=eh, minutes=em, seconds=es)

                # Juster vinduet til at være inden for optagens grænser
                sample_start = max(start_offset, window_start)
                sample_end = min(total_duration, window_end)

                # Spring over hvis vinduet er ugyldigt eller uden for grænser
                if sample_start >= sample_end or sample_end <= start_offset:
                    continue

                # Gem sample med absolut tid
                abs_start = sample_start
                length = sample_end - sample_start
                samples.append({
                    "index": idx,
                    "start_time": td_to_str(abs_start),
                    "length": td_to_str(length),
                    "label": f"Dag {day + 1} {w_start}-{w_end}"
                })
                idx += 1
    # Standard dag/aften/nat opdeling
    else:
        t = start_offset
        while t < total_duration:
            day_num = int((t.total_seconds() // (24 * 3600)) + 1)
            abs_hour = int((t.total_seconds() // 3600) % 24)
            label = interval_label(abs_hour, intervals=intervals,
                                   use_custom_intervals=use_custom_intervals)
            sample_start = t
            sample_end = next_interval_end(t, intervals=intervals)
            if sample_end > total_duration:
                sample_end = total_duration

            # Gem sample med absolut tid
            abs_start = sample_start
            length = sample_end - sample_start
            samples.append({
                "index": idx,
                "start_time": td_to_str(abs_start),
                "length": td_to_str(length),
                "label": f"Dag {day_num} {label}"
            })
            t = sample_end
            idx += 1

    # Opdel samples der er for lange
    split_samples_list = []
    new_idx = 1
    for smp in samples:
        smp_td = str_to_td(smp["length"])
        if smp_td > timedelta(hours=MAX_READ_LENGTH):
            # Opdel dette sample i stykker på MAX_READ_LENGTH eller mindre
            seg_start = str_to_td(smp["start_time"])
            seg_length = smp_td
            while seg_length > timedelta():
                cur_len = min(seg_length, timedelta(hours=MAX_READ_LENGTH))
                split_samples_list.append({
                    "index": new_idx,
                    "start_time": td_to_str(seg_start),
                    "length": td_to_str(cur_len),
                    "label": smp["label"] + (
                        f" ({td_to_str(seg_start)} - {td_to_str(seg_start + cur_len)})" if seg_length > timedelta(
                            hours=MAX_READ_LENGTH) else "")
                })
                seg_start += cur_len
                seg_length -= cur_len
                new_idx += 1
        else:
            smp = smp.copy()
            smp["index"] = new_idx
            split_samples_list.append(smp)
            new_idx += 1

    # Gruppér opdelte samples i blokke på ≤80 timer
    blocks: List[List[Dict[str, Any]]] = []
    cur_block: List[Dict[str, Any]] = []

    for smp in split_samples_list:
        # Beregn hvor lang tidsperioden ville blive hvis vi tilføjer denne samples
        if cur_block:
            first_start = str_to_td(cur_block[0]["start_time"])
            current_end = str_to_td(smp["start_time"]) + str_to_td(smp["length"])
            total_span = current_end - first_start

            if total_span > timedelta(hours=MAX_READ_LENGTH):
                # Start en ny blok
                blocks.append(cur_block)
                cur_block = []

        cur_block.append(smp)

    if cur_block:
        blocks.append(cur_block)

    # Tilføj relative tidsstempler for blokke samt justeringer
    for block_idx, block in enumerate(blocks):
        if not block:
            continue

        # Beregn oprindelige blok start/slut tider relativt til optagelsens start
        first_sample_abs = str_to_td(block[0]["start_time"])
        last_sample = block[-1]
        last_sample_abs = str_to_td(last_sample["start_time"]) + str_to_td(last_sample["length"])

        # Gem oprindelig blok-timing info (relativt til optagelse) til Kubios
        block_start_rel = first_sample_abs - start_offset
        block_end_rel = last_sample_abs - start_offset

        # Anvend 1-sekund forskydninger på første og sidste samples
        if len(block) > 0:
            # Første samples: start x sekunder senere, reducér længde med x sekunder, hvor x er FIRST_SAMPLE_BUFFER_SECONDS
            first_sample = block[0]
            first_start_abs = str_to_td(first_sample["start_time"])
            first_length = str_to_td(first_sample["length"])

            # Anvend kun forskydning hvis det første sample starter præcis ved blok-start
            if first_start_abs == first_sample_abs:
                new_first_start = first_start_abs + timedelta(seconds=FIRST_SAMPLE_BUFFER_SECONDS)
                new_first_length = first_length - timedelta(seconds=FIRST_SAMPLE_BUFFER_SECONDS)

                # Sørg for at længden ikke bliver negativ
                if new_first_length > timedelta(0):
                    first_sample["start_time"] = td_to_str(new_first_start)
                    first_sample["length"] = td_to_str(new_first_length)

            # Sidste sample: start 2 sekunder tidligere (men behold oprindelige label og længde)
            if len(block) > 1 or block[0] != last_sample:
                last_sample = block[-1]
                last_start_abs = str_to_td(last_sample["start_time"])
                last_length = str_to_td(last_sample["length"])
                new_last_start = last_start_abs - timedelta(seconds=2)

                # Sørg for at den sidste sample ikke overskrider optagelsens varighed
                last_end_time = new_last_start + last_length
                recording_end = start_offset + duration_td

                if last_end_time > recording_end:
                    # Justér længden til at passe inden for optagens grænser
                    adjusted_length = recording_end - new_last_start
                    if adjusted_length > timedelta(0):
                        last_sample["start_time"] = td_to_str(new_last_start)
                        last_sample["length"] = td_to_str(adjusted_length)
                        logger.info(f"Justerede sidste sample længde til at passe optagelse: {td_to_str(adjusted_length)}")
                    else:
                        # Hvis selv det justerede sample ville være ugyldig, behold original
                        logger.warning("Sidste samples justering ville skabe ugyldigt sample, beholder original")
                else:
                    last_sample["start_time"] = td_to_str(new_last_start)

        # Tilføj blok-timing metadata til hver sample til brug i main.py
        for sample in block:
            sample["block_start_time"] = td_to_str(block_start_rel)  # Relativt til Kubios
            sample["block_end_time"] = td_to_str(block_end_rel)  # Sluttid til Kubios

    # Omnummerér sample i hver blok
    for block in blocks:
        for idx, sample in enumerate(block, 1):
            sample["index"] = idx

    # Opdel blokke efter max_samples_per_file, beregn fil_længde
    output_files: List[Dict[str, Any]] = []
    for block in blocks:
        for i in range(0, len(block), max_samples_per_file):
            slice_samples = block[i:i + max_samples_per_file]
            # Beregn samlet fil-længde ved brug af den oprindelige blok-timing
            if slice_samples:
                # Brug de gemte blok-timing metadata som bevarer oprindelig blok-længde
                block_start_rel = str_to_td(slice_samples[0]["block_start_time"])
                block_end_rel = str_to_td(slice_samples[0]["block_end_time"])
                file_length = block_end_rel - block_start_rel
                file_length_str = td_to_str(file_length)
            else:
                file_length_str = "00:00:00"
            output_files.append({
                "output_filename": "TEMP",
                "samples": slice_samples,
                "file_length": file_length_str
            })

    # Generer filnavne
    total_files = len(output_files)
    for i, f in enumerate(output_files, 1):
        f["output_filename"] = f"{patient_id}_HRV_analysis_{i}_of_{total_files}"

    logger.info("Genererede %d samples → %d filer (≤%dh pr blok)", len(split_samples_list), total_files, MAX_READ_LENGTH)
    return output_files

    
# Test område
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename=LOG_FILE)
    print("BRUGERDEFINEREDE VINDUER:")
    sample_windows = [("07:00:00", "15:00:00")]
    out = split_samples("08:53:47", "147:00:00", "ID3", sample_windows=sample_windows)
    for f in out:
        print(f["output_filename"], f["file_length"])
        for s in f["samples"]:
            print(f"  {s['index']}: {s['label']} start={s['start_time']} længde={s['length']}")

    print("\nSTANDARD INTERVALLER:")
    out2 = split_samples("7:53:59", "147:45:37", "ID1 baseline")
    for f in out2:
        print(f["output_filename"], f["file_length"])
        for s in f["samples"]:
            print(f"  {s['index']}: {s['label']} start={s['start_time']} længde={s['length']}")


