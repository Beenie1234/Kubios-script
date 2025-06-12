import json
import os
from pathlib import Path
import logging
#config filer + logging


#Standard-config som fallback
DEFAULTS = {
    "kubios_path": r'C:\Program Files\Kubios\KubiosHRVScientific\application\launch_kubioshrv.exe',
    "excel_path": str(Path(__file__).parent / "Files_to_analyze.xlsx"),
    "log_file": str(Path(__file__) / "kubios_automation.log")
}

#EXCEL_PATH = r"C:\Users\canno\OneDrive - University of Copenhagen\Skrivebord\Sven\EDF_Auto_Analyze\Files_to_analyze.xlsx"
STARTUP_DELAY = 60
LOG_FILE ='kubios_automation.log'
PROCESS_NAME = "kubioshrv"
TITLE_KEYWORD = "Kubios"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)


def load_config(config_path="user_config.json"):

    config_file = Path(config_path)

    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            return {**DEFAULTS, **user_config}
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
    return DEFAULTS

CONFIG = load_config()

KUBIOS_PATH = CONFIG["kubios_path"]
EXCEL_PATH = CONFIG["excel_path"]
LOG_FILE = CONFIG["log_file"]


