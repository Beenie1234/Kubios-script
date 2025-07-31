"""
SAMPLE HÅNDTERING
Dette modul håndterer tilføjelse af prøver og gemning af resultater i programmet
"""
from pathlib import Path

import pyautogui
import logging
import time

from PIL import ImageGrab, ImageOps

from analysis_driver import click_center_left, click_right_of, click_right_upper, detect_save_dialog, \
    detect_analysis_error, wait_for_window_closed


def add_sample(start_time: str, length_time: str, sample_number_in_sequence: int, sample_name: str,
               add_btn_imgs=None,
               start_field_img="assets/images/start_sample_field.png",
               length_field_img="assets/images/length_sample_field.png",
               ok_cancel_img="assets/images/ok_cancel_add_sample.png") -> bool:
    """
    Tilføjer et nyt sample til analysen
    - start_time: Hvornår prøven skal starte (i tid format)
    - length_time: Hvor lang prøven skal være
    - sample_number_in_sequence: Hvilket nummer prøven har i rækken
    - sample_name: Navn på prøven
    Returnerer True hvis det lykkedes, False hvis det fejlede
    """

    try:
        # Hvis der ikke er angivet billeder til knapper, brug standard billeder
        if add_btn_imgs is None:
            add_btn_imgs = [
                "assets/images/add_remove_sample.png",
                "assets/images/add_remove_sample_marked.png",
                "assets/images/add_remove_sample_blue.png"
            ]

        # Find "add sample" knappen på skærmen
        add_btn = None
        for img in add_btn_imgs:
            try:
                add_btn = pyautogui.locateOnScreen(img, confidence=0.8)
                if add_btn:
                    break
            except pyautogui.ImageNotFoundException:
                continue

        if not add_btn:
            raise RuntimeError(f"Kunne ikke finde 'tilføj prøve' knappen")

        # Hvis det ikke er den første prøve, klik på knappen for at åbne popup
        if sample_number_in_sequence > 1:
            time.sleep(0.2)
            click_center_left(add_btn)
            time.sleep(0.2)
            # Skift til popup billeder
            start_field_img = "assets/images/add_sample_popup_start.png"
            length_field_img = "assets/images/add_sample_popup_length.png"

        time.sleep(0.7)

        # Find feltet hvor starttiden skal indtastes
        try:
            start_field = pyautogui.locateOnScreen(start_field_img, confidence=0.8)
        except pyautogui.ImageNotFoundException:
            logging.error("Kunne ikke finde start-felt billedet")
            raise RuntimeError(f"Kunne ikke finde start-felt billedet: {start_field_img}")

        # Klik på start-feltet og indtast starttiden
        click_right_of(start_field)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")  # Vælg alt tekst
        time.sleep(0.1)
        pyautogui.write(start_time, interval=0.01)  # Skriv starttiden
        time.sleep(1)

        # Find feltet hvor længden skal indtastes
        try:
            length_field = pyautogui.locateOnScreen(length_field_img, confidence=0.8)
        except pyautogui.ImageNotFoundException:
            logging.error("Kunne ikke finde længde-felt billedet")
            raise RuntimeError(f"Kunne ikke finde længde-felt billedet: {length_field_img}")

        if not length_field:
            logging.error("Kunne ikke finde længde-felt billedet")
            raise RuntimeError(f"Kunne ikke finde længde-felt billedet: {length_field_img}")

        # Klik på length-feltet og indtast længden
        click_right_of(length_field)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")  # Vælg alt tekst
        time.sleep(0.1)
        pyautogui.write(length_time, interval=0.01)  # Skriv længden

        # Hvis det ikke er den første prøve, klik OK knappen
        if sample_number_in_sequence > 1:
            ok_cancel_btn = pyautogui.locateOnScreen(ok_cancel_img, confidence=0.8)
            if not ok_cancel_btn:
                logging.error("Kunne ikke finde OK/cancel knappen")
                raise RuntimeError(f"Kunne ikke finde OK/cancel knappen: {ok_cancel_img}")

            time.sleep(0.2)
            click_center_left(ok_cancel_btn)
            time.sleep(2)

        # Vent på at "behandler" vinduet lukker
        wait_for_window_closed("processing")

        # Find prøve-etiketten og indtast prøvens navn
        try:
            sample_tag = pyautogui.locateOnScreen("assets/images/color_label.png", confidence=0.8)
            print("Prøve-etiket fundet")
        except pyautogui.ImageNotFoundException:
            logging.error("Kunne ikke finde prøve-etiketten")
            print("Kunne ikke finde prøve-etiketten")
            raise RuntimeError(f"Kunne ikke finde prøve-etiketten")

        if not sample_tag:
            logging.error("Kunne ikke finde prøve-etiketten")
            print("Kunne ikke finde prøve-etiketten")
            raise RuntimeError(f"Kunne ikke finde prøve-etiketten: {sample_tag}")

        # Klik på etiket-feltet og indtast prøvens navn
        time.sleep(0.5)
        click_right_of(sample_tag)
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "a")  # Vælg alt tekst
        time.sleep(0.5)
        pyautogui.write(sample_name, interval=0.01)  # Skriv prøvens navn
        time.sleep(0.5)

        # Vent på at "behandler" vinduet lukker igen
        wait_for_window_closed("processing")

        return True
    except Exception as e:
        logging.error(f"Fejl i add_sample funktionen: {e}")
        return False


def debug_region(region, pause: float = 1):
    """
    Hjælpefunktion til at se hvilket område på skærmen der arbejdes med
    Tegner en firkant rundt om området med musen
    """
    try:
        left, top, right, bottom = region
        # Tag et skærmbillede af området
        screenshot_sample = ImageGrab.grab(bbox=region)
        screenshot_sample.save("assets/images/sample_debug.png")

        # Bevæg musen rundt om området for at vise hvor det er
        pyautogui.moveTo(left, top, duration=pause)
        pyautogui.moveTo(right, top, duration=pause)
        pyautogui.moveTo(right, bottom, duration=pause)
        pyautogui.moveTo(left, bottom, duration=pause)
        return True
    except Exception as e:
        logging.error(f"Fejl i debug_region: {e}")
        return None


def save_results(save_dir: str, filename: str, save_cancel_img: str = "assets/images/save_dialog_save_cancel.png",
                 save_dialog_dir_img: str = "assets/images/save_as_dir_box.png",
                 filename_img: str = "assets/images/save_dialog_filename.png"):
    """
    Gemmer resultaterne i en bestemt mappe med et bestemt filnavn
    - save_dir: Mappen hvor filen skal gemmes
    - filename: Navnet på filen
    Returnerer True hvis det lykkedes, False hvis det fejlede
    """

    try:
        # Åbn gem-dialogen med Ctrl+S
        pyautogui.hotkey("ctrl", "s")

        if detect_save_dialog():
            print("Gem-dialog fundet")

        # Find feltet hvor mappen skal indtastes
        path_field = pyautogui.locateOnScreen(save_dialog_dir_img, confidence=0.8)
        time.sleep(0.5)
        if not path_field:
            raise RuntimeError(f"Kunne ikke finde mappe-feltet i gem-dialogen")

        # Klik på mappe-feltet og indtast mappen
        click_center_left(path_field)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")  # Vælg alt tekst
        time.sleep(0.2)
        pyautogui.write(save_dir, interval=0.01)  # Skriv mappen
        pyautogui.hotkey("enter")  # Tryk Enter

        # Find feltet hvor filnavnet skal indtastes
        filename_field = pyautogui.locateOnScreen(filename_img, confidence=0.8)
        time.sleep(0.5)
        if not filename_field:
            raise RuntimeError(f"Kunne ikke finde filnavn-feltet")

        # Klik på filnavn-feltet og indtast filnavnet
        time.sleep(0.2)
        click_right_upper(filename_field)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")  # Vælg alt tekst
        time.sleep(0.2)
        pyautogui.write(filename, interval=0.01)  # Skriv filnavnet
        time.sleep(0.2)

        # Find og klik på gem-knappen
        save_cancel_btn = pyautogui.locateOnScreen(save_cancel_img, confidence=0.8)
        if not save_cancel_btn:
            raise RuntimeError(f"Kunne ikke finde gem/annuller knappen")
        time.sleep(0.2)
        click_center_left(save_cancel_btn)
        time.sleep(0.2)

        # Vent på at "behandler" vinduet lukker
        wait_for_window_closed("processing")
        print("Resultater gemt")
        return True
    except Exception as e:
        logging.error(f"Fejl i save_results funktionen: {e}")
        return False


# Test området - kører kun hvis filen startes direkte
if __name__ == "__main__":
    time.sleep(3)

    # Tilføj 3 prøver som test
    i = 1
    while i < 4:
        add_sample(str(f"{i - 1}8:57:01"), "02:00:00", i, f"prøve {i}")
        i += 1

    time.sleep(3)
    # Gem resultaterne
    save_results(str(Path(__file__).parent.parent), "Test")

