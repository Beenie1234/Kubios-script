import json
import os
from pathlib import Path
import logging


#Standard-config som fallback
DEFAULTS = {
    "kubios_path": r'C:\Program Files\Kubios\KubiosHRVScientific\application\launch_kubioshrv.exe',
    "excel_path": str(Path(__file__).parent.parent / "Files_to_analyze.xlsx"),
    "log_file": str(Path(__file__) / "kubios_automation.log"),
    "output_dir": str(Path(__file__).parent.parent / "Output"),
    "files_dir": str(Path(__file__).parent.parent)
}

#EXCEL_PATH = r"C:\Users\canno\OneDrive - University of Copenhagen\Skrivebord\Sven\EDF_Auto_Analyze\Files_to_analyze.xlsx"
STARTUP_DELAY = 10
LOG_FILE ='kubios_automation.log'
PROCESS_NAME = "kubioshrv"
TITLE_KEYWORD = "Kubios"

DAY_INTERVALS = [
    ("dag", 7, 15),
    ("aften", 15, 23),
    ("nat", 23, 7)
]
MAX_READ_LENGTH = 60
MAX_READ_LENGTH_SPLIT = 60
MAX_SAMPLES_PER_FILE = 15


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
OUTPUT_DIR = CONFIG["output_dir"]
FILES_DIR = CONFIG["files_dir"]


