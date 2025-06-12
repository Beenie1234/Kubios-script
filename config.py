import logging
#config filer + logging


EXCEL_PATH = r"C:\Users\canno\OneDrive - University of Copenhagen\Skrivebord\Sven\EDF_Auto_Analyze\Files_to_analyze.xlsx"
KUBIOS_PATH = r'C:\Program Files\Kubios\KubiosHRVScientific\application\launch_kubioshrv.exe'
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