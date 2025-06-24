import pyautogui
import logging
import time
import traceback

import pytesseract
from PIL import ImageGrab, ImageOps

from analysis_driver import click_center_left, click_right_of


def add_sample(start_time: str, length_time: str, sample_number_in_sequence: int,
               add_btn_imgs=None,
               start_field_img="assets/images/start_sample_field.png",
               length_field_img="assets/images/length_sample_field.png",
               ok_cancel_img="assets/images/ok_cancel_add_sample.png") -> bool:

    try:
        if add_btn_imgs is None:
            add_btn_imgs = [
                "assets/images/add_remove_sample.png",
                "assets/images/add_remove_sample_marked.png",
                "assets/images/add_remove_sample_blue.png"
            ]
        add_btn = None
        for img in add_btn_imgs:
            try:
                add_btn = pyautogui.locateOnScreen(img, confidence=0.8)
                if add_btn:
                    break
            except pyautogui.ImageNotFoundException:
                continue
        if not add_btn:
            raise RuntimeError(f"Could not find any add sample button")


        if sample_number_in_sequence > 1:
            time.sleep(0.2)
            click_center_left(add_btn)
            time.sleep(0.2)
            start_field_img = "assets/images/add_sample_popup_start.png"
            length_field_img = "assets/images/add_sample_popup_length.png"

        time.sleep(0.7)
        try:
            start_field = pyautogui.locateOnScreen(start_field_img, confidence=0.8)
        except pyautogui.ImageNotFoundException:
            logging.error("Could not find start field image")
            raise RuntimeError(f"Could not find start field image: {start_field_img}")

        click_right_of(start_field)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.write(start_time)
        time.sleep(1)

        try:
            length_field = pyautogui.locateOnScreen(length_field_img, confidence=0.8)
        except pyautogui.ImageNotFoundException:
            logging.error("Could not find length field image")
            raise RuntimeError(f"Could not find length field image: {length_field_img}")

        if not length_field:
            logging.error("Could not find length field image")
            raise RuntimeError(f"Could not find length field image: {length_field_img}")
        click_right_of(length_field)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.write(length_time)



        ok_cancel_btn = pyautogui.locateOnScreen(ok_cancel_img, confidence=0.8)
        if not ok_cancel_btn:
            logging.error("Could not find ok cancel button")
            raise RuntimeError(f"Could not find ok cancel button: {ok_cancel_img}")

        if sample_number_in_sequence > 1:
            time.sleep(0.2)
            click_center_left(ok_cancel_btn)
            time.sleep(0.2)

        return True
    except Exception as e:
        logging.error(f"Error in add_sample function: {e}")
        return False

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
        logging.error(f"Error in debug_region: {e}")
        return None

if __name__ == "__main__":
    time.sleep(3)

    #add_sample(str(f"38:57:01"), "02:00:00", 3)
    i = 1
    while i < 4:
        add_sample(str(f"{i-1}8:57:01"), "02:00:00", i)
        i+=1