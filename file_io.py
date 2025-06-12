from pathlib import Path
import pandas as pd
import logging
from config import LOG_FILE, EXCEL_PATH

excel_test_filepath = EXCEL_PATH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)
def read_edf_list(excel_path, sheet_name=0):
    excel_path = Path(excel_path)

    if not excel_path.exists():
        logging.error(f"Excel file or path: {excel_path} does not exist")
        raise FileNotFoundError(f"Excel file or path: {excel_path} does not exist")
    if not excel_path.is_file():
        logging.error(f"Excel file {excel_path} is not a file")
        raise ValueError(f"Excel file {excel_path} is not a file")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except PermissionError:
        logging.error(f"Excel file {excel_path} may be open or used in another process")
        raise PermissionError(f"Excel file {excel_path} may be open or used in another process")
    except Exception as e:
        logging.error(f"Error loading program:{e}")
        raise RuntimeError(f"Error loading program:{e}")

    for col in df.columns:
        non_empty = df[col].dropna()
        if not non_empty.empty:
            logging.info(f"Using column {col} as source for EDF-files")
            edf_list = non_empty.astype(str).tolist()
            edf_list = [f for f in edf_list if f.lower().endswith('.edf')]
            logging.info(f"Loaded {len(edf_list)} EDF-files from column {col}")
            return edf_list

    logging.error(f"No columns found in '{excel_path}' in sheet {sheet_name}")
    raise ValueError(f"No columns found in '{excel_path}' in sheet {sheet_name}")

def resolve_edf_paths(base_dir, edf_filenames):
    base_dir = Path(base_dir).parent
    resolved_edf_paths = []
    error_paths = []
    for name in edf_filenames:
        matches = list(base_dir.rglob(name))
        if matches:
            resolved_edf_paths.append(matches[0])
        else:
            error_paths.append(name)
            logging.warning(f"No EDF-file found with name: '{name}' in '{base_dir}'. Make sure excel file is in the same directory EDF-files")

    logging.info(f"Found {len(resolved_edf_paths)} existing EDF-files out of {len(edf_filenames)}. {error_paths} could not be resolved.")
    return resolved_edf_paths

if __name__ == "__main__":
    print(read_edf_list(excel_test_filepath))
    print(resolve_edf_paths(excel_test_filepath, read_edf_list(excel_test_filepath)))