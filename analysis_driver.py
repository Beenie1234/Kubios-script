"""

Dette modul styrer selve analysen og interaktionen med Kubios programmet
"""

import logging
import time
import pytesseract
from PIL import ImageGrab

import pyautogui
from pywinauto import Application, Desktop


from config import TITLE_KEYWORD, EXCEL_PATH, PROCESS_NAME
from file_io import read_edf_list, resolve_edf_paths
from kubios_control import open_kubios, bring_kubios_to_front, get_pid_by_name


def wait_for_window_closed(window_title_substring: str, hold_closed_seconds: float = 6.0,
                           timeout: float = 120.0, retry_interval: float = 1.0) -> bool:
    """
    Wait for a window to not be open (and stay closed for hold_closed_seconds).

    Returns:
        True if window is not open (either never found or closed for hold_closed_seconds)
        False if timeout reached while window is still open or error occurred
    """
    start_time = time.time()
    first_closed_time = None

    while time.time() - start_time < timeout:
        try:
            windows = Desktop(backend='uia').windows()
            found = any(window_title_substring.lower() in w.window_text().lower() for w in windows)
            now = time.time()

            if found:
                # Window is open - reset the closed timer
                first_closed_time = None
                logging.debug(f"Window '{window_title_substring}' is still open at {now}")
            else:
                # Window is not found
                if first_closed_time is None:
                    # First time we noticed it's closed
                    first_closed_time = now
                    logging.debug(f"Window '{window_title_substring}' first detected as closed at {now}")
                else:
                    # Window has been closed for some time
                    time_closed = now - first_closed_time
                    if time_closed >= hold_closed_seconds:
                        logging.info(
                            f"Window '{window_title_substring}' has been closed for {time_closed:.1f}s (>= {hold_closed_seconds}s)")
                        return True
                    else:
                        logging.debug(
                            f"Window '{window_title_substring}' closed for {time_closed:.1f}s, waiting for {hold_closed_seconds}s total")

        except Exception as e:
            logging.error(f"Exception while checking window status: {e}")
            return False

        time.sleep(retry_interval)

    # Timeout reached
    if first_closed_time is None:
        logging.warning(f"Timeout: Window '{window_title_substring}' was still open after {timeout}s")
        return False
    else:
        time_closed = time.time() - first_closed_time
        logging.warning(
            f"Timeout: Window '{window_title_substring}' was closed for {time_closed:.1f}s but didn't reach {hold_closed_seconds}s within {timeout}s timeout")
        return False
def detect_open_data_file():
    try:
        open_data_file_label = None
        for analysis_window in range(3):
            print(f"trying to detect open data file dialog. Try no. {analysis_window+1}")
            try:
                open_data_file_label = pyautogui.locateOnScreen("assets/images/read_data_file.png", confidence=0.8)
                if open_data_file_label is not None:
                    return True
                continue
            except pyautogui.ImageNotFoundException as exc:
                time.sleep(5)
                continue
        return False

    except Exception as e:
        logging.error(f"Failed to detect analysis window: {e}")
        return False

def detect_save_dialog():
    try:
        save_dialog_label = None
        for analysis_window in range(30):
            print(f"trying to detect save dialog. Try no. {analysis_window+1}")
            try:
                save_dialog_label = pyautogui.locateOnScreen("assets/images/save_cancel.png", confidence=0.8)
                if save_dialog_label is not None:
                    return True
                continue
            except pyautogui.ImageNotFoundException as exc:
                time.sleep(5)
                continue
        return False


    except Exception as e:
        logging.error(f"Failed to detect analysis window: {e}")
        return False


def detect_analysis_window():
        try:
            analysis_window_label = None
            for analysis_window in range(25):
                print(f"trying to detect analysis window. Try no. {analysis_window}")
                if detect_analysis_error("error"):  # press enter if error when opening HRV recording
                    logging.error(f"Error encountered when attempting to open EDF file")
                    bring_kubios_to_front("kubios", "error")
                    pyautogui.hotkey('enter')
                try:
                    analysis_window_label = pyautogui.locateOnScreen("assets/images/analysis_window.png", confidence=0.8)
                    if analysis_window_label is not None:
                        return True
                    continue
                except pyautogui.ImageNotFoundException as exc:
                    time.sleep(5)
                    continue
            return False


        except Exception as e:
            logging.error(f"Failed to detect analysis window: {e}")
            return False



def detect_analysis_error(error_title: str):
    try:
        error_windows = []
        for win in Desktop(backend='uia').windows():
            title = win.window_text()
            if error_title in title.lower() and win.process_id() == get_pid_by_name(PROCESS_NAME):
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
            logging.info(f"Time: {time_region}. Length: {length_region}")
            return time_text, length_text
        except Exception as e:
            logging.error(f"Could not extract time text from image: {e}")
        return None, None


    except Exception as e:
        print(str(e))
        return None, None


def perform_read(read_all: bool, start_time: str = None, end_time: str = None):


    try:
        if read_all:
            btn_img = "assets/images/read_all_blue.png"
        else:
            btn_img = "assets/images/read_part_button.png"
        button = pyautogui.locateOnScreen(btn_img, confidence=0.8)
        if not button:
            raise RuntimeError(f"Could not find button: {button} in image: {btn_img}")
        pyautogui.click(pyautogui.center(button))
        time.sleep(2)



    except Exception as e:
        logging.error(f"Could not perform read: {e}")
        return False

    if not read_all:
        if not start_time or not end_time:
            logging.error("No start time or end time for analysis")
            return False
        try:
            pyautogui.press('tab')
            pyautogui.write(str(start_time), interval=0.05)
            pyautogui.press('tab')
            pyautogui.write(str(end_time), interval=0.05)
        except Exception as e:
           logging.error(f"Error when inputting time: {e}")
    try:
        ok_button = pyautogui.locateOnScreen("assets/images/ok_cancel_read_data_file.png", confidence=0.8)
        if not ok_button:
            raise RuntimeError(f"Could not find ok button: {ok_button} on screen")
        click_center_left(ok_button)
        time.sleep(0.5)
        return True
    except Exception as e:
        logging.error(f"Could not perform read: {e}")
        return False


def click_center_left(region):
    x = region.left + region.width // 4
    y = region.top + region.height // 2
    pyautogui.moveTo(x, y)
    time.sleep(1)
    pyautogui.click(x, y)

def click_right_of(region):
    x = region.left + region.width  + 15
    y = region.top + region.height // 2
    pyautogui.moveTo(x, y)
    time.sleep(0.5)
    pyautogui.click(x, y)

def click_right_upper(region):
    x = region.left + region.width + 15
    y = region.top + region.height // 4
    time.sleep(0.3)
    pyautogui.click(x, y)

def click_right_lower(region):
    x = region.left + region.width + 15
    y = region.top + region.height - region.height // 4
    pyautogui.click(x, y)



if __name__ == "__main__":
    if detect_analysis_window():
        print("detected analysis window")
    print("analysis window is now open")
    #open_kubios(r"C:\Program Files\Kubios\KubiosHRVScientific\application\launch_kubioshrv.exe")
    #edf_file_path = resolve_edf_paths(EXCEL_PATH, read_edf_list(EXCEL_PATH))
    #open_edf_file(edf_file_path[0])
    #detect_analysis_error("error")
    #time.sleep(10)
    #print(read_time_and_length())
    #perform_read(True, "07:56:17", "80:00:00")


