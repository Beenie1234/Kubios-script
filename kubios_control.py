import os
import subprocess
import psutil
import time
#pywinauto biblioteket fungerer kun i Windows
from pywinauto.findwindows import find_windows
from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError
from config import (
KUBIOS_PATH,
STARTUP_DELAY,
PROCESS_NAME,
TITLE_KEYWORD)
import logging

#Modul til åbning, lukning, og styring af vinduet


def is_kubios_running(process_name=PROCESS_NAME):
    #Funktion der tester om Kubios kører
    for proc in psutil.process_iter(['pid','name']):
        if process_name.lower() in proc.info['name'].lower():
            logging.info("Kubios is running")
            return True
    logging.info("Kubios is not running")
    return False

def get_pid_by_name(process_name=PROCESS_NAME):
    #Returnerer process-ID for første process der matcher process_name
    for proc in psutil.process_iter(['pid','name']):
        name = proc.info.get('name')
        if name and process_name.lower() in name.lower():
            return proc.pid
    return None




def bring_kubios_to_front(process_name=PROCESS_NAME, title_keyword=TITLE_KEYWORD):
    #Trækker Kubios frem med pywinauto
    pid = get_pid_by_name(process_name)
    if not pid:
        logging.warning(f"No process found with the name '{process_name}'")
        return False
    try:
        #Ny variabel med værdi for process-ID af valgte title_keyword
        window_handles = find_windows(process=pid, backend="uia")

        if not window_handles:
            logging.info(f"No window found with the name '{process_name}'")
            return False

        #Lister med vinduer
        matching_windows = []
        fallback_windows = []

        for handle in window_handles:
            win = Desktop(backend="uia").window(handle=handle)
            title = win.window_text()

            if title_keyword.lower() in title.lower():
                matching_windows.append(win)
            else:
                fallback_windows.append(win)

        #Denne del af koden åbner Kubios
        for win in matching_windows + fallback_windows:
            try:
                time.sleep(0.2)
                win.restore()
                time.sleep(0.2)
                win.set_focus()
                logging.info(f"Kubios window brought to front: '{win.window_text()}'")
                return True
            except ElementNotFoundError:
                logging.error(f"No window found with the name '{win.window_text()}'")
            except Exception as e:
                logging.error(f"Failed to bring window to front: {e}")
                continue
    except Exception as e:
        logging.error(f"Error: {e}")
        return False
    return False

def open_kubios():
    if is_kubios_running():
        logging.info("Kubios is already running")
        return bring_kubios_to_front()

    if not os.path.exists(KUBIOS_PATH):
        logging.info(f"Path: {KUBIOS_PATH} does not exist")
        return False

    logging.info(f"Attempting to start Kubios")
    try:
        subprocess.Popen([KUBIOS_PATH], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(STARTUP_DELAY)
        logging.info("Kubios has been started")
        return True
    except Exception as e:
        logging.error(f"Failed to start Kubios: {e}")
        return False

def close_kubios(process_name=PROCESS_NAME):
    found = False
    for proc in psutil.process_iter(['pid','name']):
        if process_name.lower() in proc.info.get('name').lower():
            logging.info(f"CLosing process: {process_name}")
            proc.terminate()
            time.sleep(5)
    if not found:
        logging.warning(f"No process found with the name '{process_name}'")
        found = True
    return found

if __name__ == "__main__":
    open_kubios()