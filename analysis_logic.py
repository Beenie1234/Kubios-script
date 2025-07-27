import re
from datetime import timedelta
from typing import List, Dict, Any, Tuple
import logging

from config import DAY_INTERVALS, MAX_SAMPLES_PER_FILE, MAX_READ_LENGTH, LOG_FILE

DEFAULT_INTERVALS = DAY_INTERVALS
logger = logging.getLogger(__name__)


def parse_duration(duration_str: str) -> timedelta:
    h, m, s = map(int, duration_str.split(":"))
    return timedelta(hours=h, minutes=m, seconds=s)


def parse_time_tuple(time_str):
    parts = list(map(int, re.split(r'[:.]', time_str)))
    while len(parts) < 3:
        parts.append(0)
    return parts  # always h, m, s


def str_to_td(s: str):
    h, m, s = map(int, re.split(r'[:.]', s))
    return timedelta(hours=h, minutes=m, seconds=s)


def td_to_str(td):
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def interval_label(hour: int, intervals=None, use_custom_intervals=False) -> str:
    if intervals is None:
        intervals = DEFAULT_INTERVALS
    for label, start, end in intervals:
        if start < end:
            if start <= hour < end:
                if use_custom_intervals:
                    return f"{start:02d}:00:00-{end:02d}:00:00"
                return label
        else:  # fx nat (23-7) or 24-hour intervals
            if start == end:  # 24-hour interval
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
        else:  # fx nat or 24-hour intervals
            if start == end:  # 24-hour interval
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
        use_custom_intervals: bool = False  # Add this parameter
) -> List[Dict[str, Any]]:
    logger.info(f"Splitting samples for {patient_id}: start={start_time}, duration={duration_str}")

    h, m, s = map(int, re.split(r'[:.]', start_time))
    start_offset = timedelta(hours=h, minutes=m, seconds=s)
    duration_td = parse_duration(duration_str)
    total_duration = start_offset + duration_td
    samples = []
    idx = 1

    # ----------- custom windows -----------------------------------------
    if sample_windows:
        total_days = int(((duration_td + start_offset).total_seconds() // (24 * 3600))) + 1
        for day in range(total_days):
            for w_start, w_end in sample_windows:
                sh, sm, ss = parse_time_tuple(w_start)
                eh, em, es = parse_time_tuple(w_end)

                # Calculate absolute window times for this day
                window_start = timedelta(days=day, hours=sh, minutes=sm, seconds=ss)
                window_end = timedelta(days=day, hours=eh, minutes=em, seconds=es)

                # Adjust window to be within recording bounds
                sample_start = max(start_offset, window_start)
                sample_end = min(total_duration, window_end)  # ← Key fix: cap at total_duration

                # Skip if window is invalid or outside bounds
                if sample_start >= sample_end or sample_end <= start_offset:
                    continue

                # CHANGE 1: Use absolute time instead of relative
                abs_start = sample_start
                length = sample_end - sample_start
                samples.append({
                    "index": idx,
                    "start_time": td_to_str(abs_start),  # Now absolute time
                    "length": td_to_str(length),
                    "label": f"Dag {day + 1} {w_start}-{w_end}"
                })
                idx += 1
    # ----------- default dag/aften/nat ----------------------------------
    else:
        t = start_offset
        while t < total_duration:
            day_num = int((t.total_seconds() // (24 * 3600)) + 1)
            abs_hour = int((t.total_seconds() // 3600) % 24)
            label = interval_label(abs_hour, intervals=intervals,
                                   use_custom_intervals=use_custom_intervals)  # Pass the flag here
            sample_start = t
            sample_end = next_interval_end(t, intervals=intervals)
            if sample_end > total_duration:
                sample_end = total_duration
            # CHANGE 1: Use absolute time instead of relative
            abs_start = sample_start
            length = sample_end - sample_start
            samples.append({
                "index": idx,
                "start_time": td_to_str(abs_start),  # Now absolute time
                "length": td_to_str(length),
                "label": f"Dag {day_num} {label}"
            })
            t = sample_end
            idx += 1

    # ----------- split samples that are too long -------------------------
    split_samples_list = []
    new_idx = 1
    for smp in samples:
        smp_td = str_to_td(smp["length"])
        if smp_td > timedelta(hours=MAX_READ_LENGTH):
            # split this sample into pieces of MAX_READ_LENGTH or less
            seg_start = str_to_td(smp["start_time"])  # This is now absolute time
            seg_length = smp_td
            while seg_length > timedelta():
                cur_len = min(seg_length, timedelta(hours=MAX_READ_LENGTH))
                split_samples_list.append({
                    "index": new_idx,
                    "start_time": td_to_str(seg_start),  # Keep absolute time
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

    # ----------- group split samples into ≤80 h blocks -------------------
    blocks: List[List[Dict[str, Any]]] = []
    cur_block: List[Dict[str, Any]] = []

    for smp in split_samples_list:
        # Calculate what the time span would be if we add this sample
        if cur_block:
            first_start = str_to_td(cur_block[0]["start_time"])
            current_end = str_to_td(smp["start_time"]) + str_to_td(smp["length"])
            total_span = current_end - first_start

            if total_span > timedelta(hours=MAX_READ_LENGTH):
                # Start a new block
                blocks.append(cur_block)
                cur_block = []

        cur_block.append(smp)

    if cur_block:
        blocks.append(cur_block)

    # CHANGE 2: Add relative timestamps for blocks while keeping absolute for samples
    for block_idx, block in enumerate(blocks):
        if not block:
            continue

        # Calculate original block start/end times relative to recording start
        first_sample_abs = str_to_td(block[0]["start_time"])
        last_sample = block[-1]
        last_sample_abs = str_to_td(last_sample["start_time"]) + str_to_td(last_sample["length"])

        # Store original block timing info (relative to recording) for Kubios
        block_start_rel = first_sample_abs - start_offset
        block_end_rel = last_sample_abs - start_offset  # End time relative to recording

        # Apply 1-second offsets to first and last samples
        if len(block) > 0:
            # First sample: start 1 second later, reduce length by 1 second
            first_sample = block[0]
            first_start_abs = str_to_td(first_sample["start_time"])
            first_length = str_to_td(first_sample["length"])

            # Only apply offset if the first sample starts exactly at block start
            if first_start_abs == first_sample_abs:
                new_first_start = first_start_abs + timedelta(seconds=1)
                new_first_length = first_length - timedelta(seconds=1)

                # Ensure length doesn't go negative
                if new_first_length > timedelta(0):
                    first_sample["start_time"] = td_to_str(new_first_start)
                    first_sample["length"] = td_to_str(new_first_length)

            # Last sample: start 1 second earlier (but keep original label and length)
            if len(block) > 1 or block[
                0] != last_sample:  # Only if we have multiple samples or it's not the same sample
                last_sample = block[-1]
                last_start_abs = str_to_td(last_sample["start_time"])
                new_last_start = last_start_abs - timedelta(seconds=1)
                last_sample["start_time"] = td_to_str(new_last_start)

        # Add block timing metadata to each sample for use in main.py
        for sample in block:
            sample["block_start_time"] = td_to_str(block_start_rel)  # Relative for Kubios
            sample["block_end_time"] = td_to_str(block_end_rel)  # End time for Kubios
            # sample["start_time"] now has the adjusted absolute time of day

    for block in blocks:
        for idx, sample in enumerate(block, 1):
            sample["index"] = idx

    # ----------- slice blocks by max_samples_per_file, calculate file_length ---
    output_files: List[Dict[str, Any]] = []
    for block in blocks:
        for i in range(0, len(block), max_samples_per_file):
            slice_samples = block[i:i + max_samples_per_file]
            # Calculate total file length using the original block timing (before 1-second offsets)
            if slice_samples:
                # Use the stored block timing metadata which preserves original block length
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

    total_files = len(output_files)
    for i, f in enumerate(output_files, 1):
        f["output_filename"] = f"{patient_id}_HRV_analysis_{i}_of_{total_files}"

    logger.info("Generated %d samples → %d files (≤%dh pr blok)", len(split_samples_list), total_files, MAX_READ_LENGTH)
    return output_files


# ------------------------------- quick self‑test ---------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename=LOG_FILE)
    print("CUSTOM WINDOWS:")
    sample_windows = [("07:00:00", "15:00:00")]
    out = split_samples("08:53:47", "147:00:00", "ID3", sample_windows=sample_windows)
    for f in out:
        print(f["output_filename"], f["file_length"])
        for s in f["samples"]:
            print(f"  {s['index']}: {s['label']} start={s['start_time']} length={s['length']}")

    print("\nSTANDARD INTERVALLER:")
    out2 = split_samples("7:53:59", "147:45:37", "ID1 baseline")
    for f in out2:
        print(f["output_filename"], f["file_length"])
        for s in f["samples"]:
            print(f"  {s['index']}: {s['label']} start={s['start_time']} length={s['length']}")