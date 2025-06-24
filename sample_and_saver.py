import pyautogui
import logging
import time
import traceback

import pytesseract
from PIL import ImageGrab, ImageOps

from analysis_driver import click_center_left


def add_sample(start_time: str, length: str):

    try:

        print("Function add_sample started")

        try:
            start_sample_field = pyautogui.locateOnScreen("assets/images/start_sample_field.png", confidence = 0.8)
        except pyautogui.ImageNotFoundException:
            logging.error("No start_sample_field.png found")
            return None, None
        try:
            length_sample_field = pyautogui.locateOnScreen("assets/images/length_sample_field.png", confidence = 0.8)
        except pyautogui.ImageNotFoundException:
            logging.error("No length_sample_field.png found")
            return None, None
        try:
            sample_int = pyautogui.locateOnScreen("assets/images/sample_int.png", confidence = 0.8)
        except pyautogui.ImageNotFoundException:
            logging.error("No sample_int.png found")
            return None, None
        try:
            add_sample_images = [
                "assets/images/add_remove_sample.png",
                "assets/images/add_remove_sample_marked.png",
                "assets/images/add_remove_sample_blue.png"
            ]
            for img in add_sample_images:
                add_sample_btn = None
                try:
                    add_sample_btn = pyautogui.locateOnScreen(img, confidence = 0.8)
                    if add_sample_btn is not None:
                        break
                except pyautogui.ImageNotFoundException:
                    logging.error("No add_remove_sample.png found")
                    continue

        except Exception as e:
            logging.error(f"Exception: {e}")
            return None, None


        print("preparing region")
        sample_region = (
            int(sample_int.left + sample_int.width - 5),
            int(sample_int.top - 5),
            int(sample_int.left + sample_int.width + 20),
            int(sample_int.top + sample_int.height - 3)
        )
        print("taking screenshot...")
        screenshot_sample = ImageGrab.grab(bbox=sample_region).convert('L')

        bw = screenshot_sample.point(lambda x: 0 if x < 128 else 255, '1')
        bw.save("assets/images/sample_debug_bw.png")
        sample_text = pytesseract.image_to_string(bw, config="--psm 7 digits -c tessedit_char_whitelist=0123456789").strip()

        print(sample_text)
        if not int(sample_text) == 1:
            try:
                click_center_left(add_sample_btn)
            except Exception as e:
                logging.error(f"Failed to press add-button: {e}")
                return None, None





    except Exception as e:
        logging.error(f"Error: {e}")
        traceback.print_exc()
        return None, None


def debug_region(region, pause: float = 1):
    try:
        left, top, right, bottom = region
        screenshot_sample = ImageGrab.grab(bbox=region)

        screenshot_sample.save("assets/images/sample_debug.png")

        pyautogui.moveTo(left, top, duration = pause)
        pyautogui.moveTo(right, top, duration = pause)
        pyautogui.moveTo(right, bottom, duration = pause)
        pyautogui.moveTo(left , bottom, duration = pause)
        return True
    except Exception as e:
        logging.error(f"Error: {e}")
        return None

if __name__ == "__main__":
    time.sleep(3)
    add_sample("00:00", "00:00")