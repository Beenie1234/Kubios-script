from pywinauto.application import Application
from analysis_driver import (
open_edf_file,
)
from file_io import (
    read_edf_list, resolve_edf_paths
)
from config import (
EXCEL_PATH

)


if __name__ == '__main__':

    app = Application(backend="uia").connect(title_re=".*Kubios.*")
    edf_path_raw = read_edf_list(EXCEL_PATH)
    print(edf_path_raw)
    edf_path = resolve_edf_paths(EXCEL_PATH, edf_path_raw)
    print(edf_path)

    if edf_path:
        open_edf_file(app, edf_path[0])
