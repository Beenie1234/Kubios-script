import logging
from pywinauto.application import Application
import time


def open_edf_file(app, edf_path):
    #Åbner EDF-filen i Kubios via Pywinauto
    logging.info(f"Åbner EDF-fil {edf_path}")
    app.top.window().menu_select("File->Open")
    time.sleep(1)
    open_dialog = app.window(title_re=".*Open.*")
    open_dialog.child_window(auto_id="1148", control_type="Edit").set_edit_text(str(edf_path))
    open_dialog.child_window(title="Open", auto_id="1", control_type="Button").click()
    time.sleep(3)




