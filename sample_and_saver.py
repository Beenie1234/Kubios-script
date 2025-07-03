import pyautogui
import logging
import time
import traceback

import pytesseract
from PIL import ImageGrab, ImageOps

from analysis_driver import click_center_left, click_right_of, click_right_upper


def add_sample(start_time: str, length_time: str, sample_number_in_sequence: int, sample_name: str,
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
        pyautogui.write(start_time, interval=0.01)
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
        pyautogui.write(length_time, interval=0.01)




        if sample_number_in_sequence > 1:
            ok_cancel_btn = pyautogui.locateOnScreen(ok_cancel_img, confidence=0.8)
            if not ok_cancel_btn:
                logging.error("Could not find ok cancel button")
                raise RuntimeError(f"Could not find ok cancel button: {ok_cancel_img}")

            time.sleep(0.2)
            click_center_left(ok_cancel_btn)
            time.sleep(0.2)

        try:
            sample_tag = pyautogui.locateOnScreen("assets/images/color_label.png", confidence=0.8)
            print("sample tag found")
        except pyautogui.ImageNotFoundException:
            logging.error("Could not find sample tag")
            print("Could not find sample tag")
            raise RuntimeError(f"Could not find sample tag")
        if not sample_tag:
            logging.error("Could not find sample tag")
            print("Could not find sample tag")
            raise RuntimeError(f"Could not find sample tag: {sample_tag}")
        time.sleep(0.5)
        click_right_of(sample_tag)
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.5)
        pyautogui.write(sample_name, interval=0.01)
        time.sleep(0.5)




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
def save_results(save_dir: str, filename: str, save_cancel_img: str = "assets/images/save_dialog_save_cancel.png", save_dialog_dir_img: str = "assets/images/save_as_dir_box.png", filename_img: str = "assets/images/save_dialog_filename.png"):

    try:
        pyautogui.hotkey("ctrl", "s")
        time.sleep(15)
        path_field = pyautogui.locateOnScreen(save_dialog_dir_img, confidence=0.8)
        time.sleep(0.5)
        if not path_field:
            raise RuntimeError(f"Could not find directory field in save dialog")
        click_center_left(path_field)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.write(save_dir, interval=0.01)
        filename_field = pyautogui.locateOnScreen(filename_img, confidence=0.8)
        time.sleep(0.5)
        if not filename_field:
            raise RuntimeError(f"Could not find filename field")
        time.sleep(0.2)
        click_right_upper(filename_field)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.write(filename, interval=0.01)
        time.sleep(0.2)
        save_cancel_btn = pyautogui.locateOnScreen(save_cancel_img, confidence=0.8)
        if not save_cancel_btn:
            raise RuntimeError(f"Could not find save cancel button")
        time.sleep(0.2)
        click_center_left(save_cancel_btn)
        time.sleep(3)
        print("Results saved")
        return True
    except Exception as e:
        logging.error(f"Error in save_results function: {e}")
        return False



if __name__ == "__main__":
    time.sleep(3)


    i = 1
    while i < 4:
        add_sample(str(f"{i-1}8:57:01"), "02:00:00", i, f"sample {i}")
        i+=1

    time.sleep(3)
    save_results(r"C:\Users\Mikkel\Desktop\Sven\Test output", "Beenie")
