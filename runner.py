import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import webview

APP_PATH = Path(__file__).parent / "app.py"
GATE_PATH = Path(__file__).parent / "main.py"
PORT = 8501
URL = f"http://localhost:{PORT}"


def wait_for_server(timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(URL, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


if __name__ == "__main__":
    server = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", str(APP_PATH),
        "--server.headless", "true",
        "--server.port", str(PORT),
        "--browser.gatherUsageStats", "false",
    ])

    gate = subprocess.Popen([sys.executable, str(GATE_PATH)])

    try:
        if wait_for_server():
            webview.create_window("Thai License Plate OCR", URL, width=1200, height=900)
            webview.start()
        else:
            print("เปิดเซิร์ฟเวอร์ไม่สำเร็จ")
    finally:
        gate.terminate()
        server.terminate()