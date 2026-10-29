from ocr import read_license_plate
from gpiozero import Button, LED
from pathlib import Path
from numbers import Real
from threading import Lock, Timer
import json
import time
import cv2
from signal import pause

# === CONFIG ====
CONFIDENCE_THRESHOLD = 0.5
BUTTON_GPIO = 2
LED_ON_SECONDS = 5
CAR_LIST_PATH = Path(__file__).with_name("CarList.txt")
IMAGES_DIR = Path(__file__).with_name("images")
green_led = LED(17)
red_led = LED(27)
processing_lock = Lock()

# === INIT ===
def normalize_text(value):
    return "".join(str(value).split()).upper()

IMAGES_DIR.mkdir(exist_ok=True)

with open(CAR_LIST_PATH, encoding="utf-8") as f:
    car_list = [normalize_text(line) for line in f if line.strip()]

# === UTILS ===
def pi_capture():
    cam = cv2.VideoCapture("/dev/video1", cv2.CAP_V4L2)

    if not cam.isOpened():
        raise RuntimeError("เปิดกล้องไม่ได้")

    try:
        time.sleep(2)
        ret,frame = cam.read()

        if not ret:
            raise RuntimeError("กล้องจับภาพไม่ได้")

        return frame
    finally:
        cam.release()

# === MAIN WORKFLOW ===
led_timer = None


def set_leds(green=False, red=False):
    global led_timer
    if led_timer:
        led_timer.cancel()
        led_timer = None
    green_led.value = green
    red_led.value = red


def finish(report_path, allowed, message, result=None):
    global led_timer
    set_leds(green=allowed, red=not allowed)
    led_timer = Timer(LED_ON_SECONDS, set_leds)
    led_timer.daemon = True
    led_timer.start()
    print(message)
    if report_path is None:
        return
    tmp = report_path.with_name(report_path.name + ".tmp")
    tmp.write_text(
        json.dumps({"allowed": allowed, "message": message.strip(), "result": result}, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(report_path)


def on_button_pressed():
    if not processing_lock.acquire(blocking=False):
        print("กำลังประมวลผลอยู่ กรุณารอ")
        return

    report_path = None
    result = None
    try:
        set_leds()
        print("Capturing image...")
        img = pi_capture()
        if img is None:
            finish(None, False, "ไม่ได้ภาพจากกล้อง")
            return

        stem = time.strftime("%Y%m%d_%H%M%S")
        image_path = IMAGES_DIR / f"{stem}.jpg"
        if not cv2.imwrite(str(image_path), img):
            finish(None, False, "บันทึกรูปไม่สำเร็จ")
            return
        report_path = image_path.with_suffix(".json")

        print("================================")
        print("     Thai License Plate OCR")
        print("================================")
        result = read_license_plate(str(image_path))

        if not result or not result.get("success"):
            finish(report_path, False, "\nOCR ไม่สำเร็จ", result)
            return

        data = result.get("data") or {}
        plates = data.get("plates") or []
        if not plates or not isinstance(plates[0], dict):
            finish(report_path, False, "\nไม่พบทะเบียนรถ", result)
            return

        confidence = data.get("confidence_score")
        if (
            not isinstance(confidence, Real)
            or confidence < CONFIDENCE_THRESHOLD
        ):
            finish(report_path, False, "\nความแม่นยำไม่เพียงพอ", result)
            return

        plate = plates[0]
        values = (
            plate.get("plate_number_normalized"),
            plate.get("plate_color"),
            data.get("region_text"),
        )
        if not all(isinstance(value, str) and value.strip() for value in values):
            finish(report_path, False, "\nข้อมูลทะเบียนไม่ครบ", result)
            return

        plate_key = tuple(normalize_text(value) for value in values)
        plate_text = "".join(plate_key)
        print(f"ทะเบียน: {plate_key[0]}, สีป้าย: {plate_key[1]}, จังหวัด: {plate_key[2]}")
        print(f"ความแม่นยำ: {confidence:.2f}")

        if plate_text in car_list:
            finish(report_path, True, "\nอนุญาตให้ผ่าน", result)
        else:
            finish(report_path, False, "\nไม่อนุญาตให้ผ่าน", result)
    except Exception as error:
        finish(report_path, False, f"\nเกิดข้อผิดพลาด: {error}", result)
    finally:
        processing_lock.release()

def main():
    set_leds()
    button = Button(BUTTON_GPIO, bounce_time=0.2)
    button.when_pressed = on_button_pressed

    pause()

if __name__ == "__main__":
    main()
