import mss
import base64
import requests
from PIL import Image
import os

def take_screenshot():
    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)

        raw_file = "screen.png"
        mss.tools.to_png(shot.rgb, shot.size, output=raw_file)

    #print("Screenshot saved.")

    img = Image.open(raw_file)
    img.thumbnail((640, 360))

    small_file = "screen_small.jpg"
    img.save(small_file, quality=85)

    #print("Image resized.")

    with open(small_file, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    return img_b64, raw_file, small_file


def send_to_model(img_b64):
    #print("Sending to model...")

    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "minicpm-v",
                "prompt": (
                    "Summarize what the user is doing in 1 short sentence. "
                    "No details, no file names, no code explanation."
                ),
                "images": [img_b64],
                "stream": False
            },
            timeout=300
        )

        return res.json()["response"]

    except Exception as e:
        return f"Error: {e}"


def cleanup(raw_file, small_file):
    try:
        os.remove(raw_file)
        os.remove(small_file)
    except:
        pass

"""
img_b64, raw, small = take_screenshot()
result = send_to_model(img_b64)
cleanup(raw, small)

print(result)
"""