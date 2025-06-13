import logging
from pywinauto.application import Application
import time

from pywinauto.findwindows import ElementNotFoundError

from config import TITLE_KEYWORD, EXCEL_PATH, PROCESS_NAME
from file_io import read_edf_list, resolve_edf_paths
from kubios_control import open_kubios, bring_kubios_to_front, get_pid_by_name


def open_edf_file(app, edf_path):
    #Åbner EDF-filen i Kubios via Pywinauto
    logging.info(f"Åbner EDF-fil {edf_path}")
    try:
        app.top.window().menu_select("File->Open")
        time.sleep(1)
        open_dialog = app.window(title_re=".*Open.*")
        open_dialog.child_window(auto_id="1148", control_type="Edit").set_edit_text(str(edf_path))
        open_dialog.child_window(title="Open", auto_id="1", control_type="Button").click()
        time.sleep(3)
    except (ElementNotFoundError, Exception, TimeoutError) as e:
        logging.error(f"Error opening EDF-file{e}")
        raise

if __name__ == "__main__":
    #open_kubios(r"C:\Program Files\Kubios\KubiosHRVScientific\application\launch_kubioshrv.exe")
    bring_kubios_to_front()
    kubios_app = Application(backend="uia").connect(title_re=TITLE_KEYWORD, process=get_pid_by_name(PROCESS_NAME))
    edf_file_list = read_edf_list(EXCEL_PATH)
    print(edf_file_list[0])
    edf_file_path = resolve_edf_paths(EXCEL_PATH, edf_file_list[0])
    print(edf_file_path)
    open_edf_file(kubios_app, edf_file_list[0])



