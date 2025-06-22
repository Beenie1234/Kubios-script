import pyautogui
import logging
import time

import pytesseract
from PIL import ImageGrab

from analysis_driver import click_center_left


def add_sample(start_time: str, length: str):

    try:
        start_sample_field = pyautogui.locateOnScreen("assets/images/start_sample_field.png", confidence = 0.8)
        length_sample_field = pyautogui.locateOnScreen("assets/images/length_sample_field.png", confidence = 0.8)
        sample_int = pyautogui.locateOnScreen("assets/images/sample_int.png", confidence = 0.8)
        add_sample_btn = pyautogui.locateOnScreen("assets/images/add_remove_sample.png", confidence = 0.8)
        if not start_sample_field or not length_sample_field:
            logging.error("No start sample or length sample field found")
            return None, None
        if not add_sample_btn:
            logging.error("No add sample button")
            return None, None
        if not sample_int:
            logging.error("No sample integer detected")
            return None, None
        sample_region = (
            int(sample_int.left + sample_int.width),
            int(sample_int.top),
            int(sample_int.left + sample_int.width + 15),
            int(sample_int.top + sample_int.height)
        )
        screenshot_sample = ImageGrab.grab(bbox=sample_region).convert('L')
        sample_text = pytesseract.image_to_string(screenshot_sample).strip()
        print(sample_region)
        debug_region(sample_region)
        print(sample_text)


        #click_center_left(add_sample_btn)
    except Exception as e:
        logging.error(f"Error: {e}")
        return None, None


def debug_region(region, pause: float = 1):
    try:
        x, y, w, h = region
        pyautogui.moveTo(x, y, duration = pause)
        pyautogui.moveTo(x + w, y, duration = pause)
        pyautogui.moveTo(x + w, y + h, duration = pause)
        pyautogui.moveTo(x , y + h, duration = pause)
        pyautogui.moveTo(x + w // 2, y + h // 2, duration = pause)
        return True
    except Exception as e:
        logging.error(f"Error: {e}")
        return None

if __name__ == "__main__":
    time.sleep(3)
    add_sample("00:00", "00:00")