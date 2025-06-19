import logging
import time
import pytesseract
from PIL import ImageGrab
import re
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
    logging.info("Starting to read time and length with Tesseract-OCR")
    time.sleep(1)
    screen_w, screen_h = pyautogui.size()

    screenshot = ImageGrab.grab()
    try:
        time_label = pyautogui.locateOnScreen("assets/images/time_label.png", confidence=0.8)
        length_label = pyautogui.locateOnScreen("assets/images/length_label.png", confidence=0.8)

        if not time_label and length_label:
            logging.error("Time or length label not found on screen")
            return None, None




        time_region =(
            int(time_label.left + time_label.width ),
            int(time_label.top),
            int(time_label.left + time_label.width + 45),
            int(time_label.top + time_label.height)
        )
        length_region = (
            int(length_label.left + length_label.width ),
            int(length_label.top),
            int(length_label.left + length_label.width + 50),
            int(length_label.top + length_label.height)
        )
        print(f"OCR_region for time: {time_region}. Length: {length_region}")
        screenshot_time = ImageGrab.grab(bbox=time_region).convert('L')
        screenshot_length = ImageGrab.grab(bbox=length_region).convert('L')
        time_text = pytesseract.image_to_string(screenshot_time).strip()
        length_text = pytesseract.image_to_string(screenshot_length).strip()


        try:
            print(f"Time text: {time_text}")
            print(f"Length text: {length_text}")
            return time_text, length_text
        except Exception as e:
            logging.error(f"Could not extract time text from image: {e}")
        return None, None


    except Exception as e:
        print(str(e))
        return None, None


if __name__ == "__main__":

    #open_kubios(r"C:\Program Files\Kubios\KubiosHRVScientific\application\launch_kubioshrv.exe")
    #edf_file_path = resolve_edf_paths(EXCEL_PATH, read_edf_list(EXCEL_PATH))
    #open_edf_file(edf_file_path[0])
    #detect_analysis_error()
    time.sleep(4)
    read_time_and_length()


