from datetime import timedelta
from typing import List, Dict, Any, Tuple
import logging

from config import DAY_INTERVALS, MAX_SAMPLES_PER_FILE

DEFAULT_INTERVALS = DAY_INTERVALS


def parse_duration(duration_str: str) -> timedelta:
    h, m, s = map(int, duration_str.split(":"))
    return timedelta(hours=h, minutes=m, seconds=s)


def parse_time_tuple(time_str):
    parts = list(map(int, time_str.split(':')))
    while len(parts) < 3:
        parts.append(0)
    return parts


def td_to_str(td):
    # timedelta til HH:MM:SS
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def interval_label(hour: int, intervals=None) -> str:
    if intervals is None:
        intervals = DEFAULT_INTERVALS
    for label, start, end in intervals:
        if start < end:
            if start <= hour < end:
                return label
        else:  # fx nat (23-7)
            if hour >= start or hour < end:
                return label
    logging.error("Error in interval_label function in analysis_logic.py")
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
        else:  # fx nat
            if hour >= start or hour < end:
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
        sample_windows: List[Tuple[str, str]] = None
) -> List[Dict[str, Any]]:
    logging.info(f"Splitting samples fpr {patient_id} with start time={start_time} and duration={duration_str}")
    """
    Fleksibel split: Hvis sample_windows er angivet, laves samples præcis efter windows, uanset overlap/spring.
    Output er relativ tid fra optagelsens start samt længde, ikke absolut tidspunkt.
    """
    h, m, s = map(int, start_time.split(":"))
    start_offset = timedelta(hours=h, minutes=m, seconds=s)
    duration_td = parse_duration(duration_str)
    total_duration = start_offset + duration_td
    samples = []
    idx = 1

    if sample_windows:
        logging.info(f"Using custom intervals: {sample_windows}")
        total_days = int(((duration_td + start_offset).total_seconds() // (24 * 3600))) + 1
        for day in range(total_days):
            for w_start, w_end in sample_windows:
                sh, sm, ss = parse_time_tuple(w_start)
                eh, em, es = parse_time_tuple(w_end)
                window_start = timedelta(days=day, hours=sh, minutes=sm, seconds=ss)
                window_end = timedelta(days=day, hours=eh, minutes=em, seconds=es)
                # På dag 0: hvis window ligger før optagelsens start, klip til 0
                if day == 0:
                    sample_start = max(start_offset, window_start)
                    sample_end = max(sample_start, window_end)  # sample_end kan ikke ligge før sample_start
                else:
                    sample_start = start_offset + (window_start - start_offset)
                    sample_end = start_offset + (window_end - start_offset)
                # Begræns til optagelsen!
                if sample_end < start_offset:
                    logging.debug(f"Custom sample end before recording start(skipped): {w_start}--{w_end} dag {day+1}")
                    continue
                if sample_start < start_offset:
                    logging.info(f"Custom sample start before recording start(clipped): {w_start}--{w_end} dag {day+1}")
                    sample_start = start_offset
                if sample_end > total_duration:
                    logging.info(f"Custom sample end after recording end(clipped): {w_start}--{w_end} dag {day+1}")
                    sample_end = total_duration
                if sample_start >= sample_end or sample_start >= total_duration:
                    logging.info(f"Sample start after recording end(skipped): {w_start}--{w_end} dag {day+1}")
                    continue
                rel_start = sample_start - start_offset
                length = sample_end - sample_start
                samples.append({
                    "index": idx,
                    "start_time": td_to_str(rel_start),
                    "length": td_to_str(length),
                    "label": f"Dag {day + 1} {w_start}-{w_end}"
                })
                idx += 1
    else:
        t = start_offset
        logging.info(f"Using default intervals: {intervals}")
        while t < total_duration:
            day_num = int((t.total_seconds() // (24 * 3600)) + 1)
            abs_hour = int((t.total_seconds() // 3600) % 24)
            label = interval_label(abs_hour, intervals=intervals)
            sample_start = t
            sample_end = next_interval_end(t, intervals=intervals)
            if sample_end > total_duration:
                sample_end = total_duration
            rel_start = sample_start - start_offset
            length = sample_end - sample_start
            samples.append({
                "index": idx,
                "start_time": td_to_str(rel_start),
                "length": td_to_str(length),
                "label": f"Dag {day_num} {label}"
            })
            t = sample_end
            idx += 1
    output_files = []
    n_files = (len(samples) + max_samples_per_file - 1) // max_samples_per_file
    logging.info(f"Splitting into {n_files} files with a maximum of  {max_samples_per_file} samples per file")
    for filenum in range(n_files):
        samples_in_file = samples[filenum * max_samples_per_file:(filenum + 1) * max_samples_per_file]
        # Beregn længde af optagelsen der dækkes i denne fil:
        if samples_in_file:
            file_start = samples_in_file[0]["start_time"]

            # sidste samples slut: rel_start + length
            def str_to_td(s):
                h, m, s = map(int, s.split(":"))
                return timedelta(hours=h, minutes=m, seconds=s)

            file_start_td = str_to_td(samples_in_file[0]["start_time"])
            last = samples_in_file[-1]
            file_end_td = str_to_td(last["start_time"]) + str_to_td(last["length"])
            file_length = file_end_td - file_start_td
            file_length_str = td_to_str(file_length)
        else:
            file_length_str = "00:00:00"
        output_files.append({
            "output_filename": f"{patient_id}_HRV_analysis_{filenum + 1}_of_{n_files}",
            "samples": samples_in_file,
            "file_length": file_length_str
        })
    return output_files


# Eksempel på brug:
if __name__ == "__main__":
    # Brug windows (fx overlappende og ikke sammenhængende samples)
    print("\nCUSTOM WINDOWS:\n")
    sample_windows = [
        ("07:00:00", "14:00:00"),
        ("08:00:00", "15:00:00"),
        ("09:00:00", "16:00:00")
    ]
    out = split_samples(
        start_time="08:53:03",
        duration_str="148:00:00",
        patient_id="ID3",
        sample_windows=sample_windows
    )
    for fil in out:
        print(fil["output_filename"], "Optagelseslængde: ", fil["file_length"])
        for s in fil["samples"]:
            print(f"{s['index']}: {s['label']} start={s['start_time']} length={s['length']}")

    # Fortsat muligt at bruge klassisk mode (dag/aften/nat)
    print("\nSTANDARD INTERVALLER:\n")
    out2 = split_samples(
        start_time="10:23:00",
        duration_str="140:15:00",
        patient_id="ID1"
    )
    for fil in out2:
        print(fil["output_filename"], "Optagelseslængde:", fil["file_length"])
        for s in fil["samples"]:
            print(f"{s['index']}: {s['label']} start={s['start_time']} length={s['length']}")