import logging
import time

from pathlib import Path
import psutil
import pyautogui
from pywinauto import Application, Desktop
from pywinauto.findwindows import find_windows

from config import TITLE_KEYWORD, EXCEL_PATH, PROCESS_NAME
from file_io import read_edf_list, resolve_edf_paths
from kubios_control import open_kubios, bring_kubios_to_front, get_pid_by_name

def detect_analysis_error():
    try:
        error_windows = []
        for win in Desktop(backend='uia').windows():
            title = win.window_text()
            if "error" in title.lower() and win.process_id() == get_pid_by_name(PROCESS_NAME):
                logging.info(f"Detected error window in title: {title}")
                win.set_focus()
                time.sleep(0.3)
                try:
                    win.close()
                    time.sleep(0.3)
                    logging.info("Closing error window")
                except Exception as e:
                    logging.error(f"Could not close window {title} : {e}")
                error_windows.append(title)

        return bool(error_windows)
    except Exception as e:
        logging.info(f"Could not detect error window: {e}")
        return False


def open_edf_file(edf_path):
    #Åbner EDF-filen i Kubios via PyAutoGui og fokuserer det med PyWinAuto
    logging.info(f"Opening EDF file {edf_path}")
    try:
        app = Application(backend="uia").connect(title_re=TITLE_KEYWORD, process=get_pid_by_name(PROCESS_NAME))
        app.top_window().set_focus()
        time.sleep(4)

        pyautogui.hotkey('ctrl', 'o')
        time.sleep(4)
        pyautogui.write(str(edf_path), interval=0.015)
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(2)
    except Exception as e:
        logging.error(f"Error opening EDF file: {e}")
        raise

def read_time_and_length():
    print("TEst")


if __name__ == "__main__":

    open_kubios(r"C:\Program Files\Kubios\KubiosHRVScientific\application\launch_kubioshrv.exe")
    edf_file_path = resolve_edf_paths(EXCEL_PATH, read_edf_list(EXCEL_PATH))
    open_edf_file(edf_file_path[0])
    detect_analysis_error()



