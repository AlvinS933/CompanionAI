import vision_logic as vl
import dialogue_logic as dl
import time
import threading
import sys
import random
import json
import os
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')
screenshot_interval = 5
message_history = []
history_lock = threading.Lock()  # 🔒 Protect shared history


SYSTEM_PROMPT = """

"""

message_history.append({"role": "system", "content": SYSTEM_PROMPT})

busy = False
cooldown_time = 100 
cooldown_until = time.time() + cooldown_time
rand_chance = 0.4
user_is_talking = threading.Event()  # Signal for user activity and stop current processing in this iteration
def save_history():
    with history_lock:
        snapshot = list(message_history)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"history_{timestamp}.json"
    path = os.path.join(os.path.dirname(__file__), filename)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    
    print(f"[History saved to {path}]", file=sys.stderr)
def vision_loop():
    global busy, cooldown_until
    while True:
        now = time.time()

        if busy or now < cooldown_until or random.random() > rand_chance:
            time.sleep(1)
            continue

        try:
            busy = True

            img_b64, raw, small = vl.take_screenshot()
            vision_response = vl.send_to_model(img_b64)
            vl.cleanup(raw, small)

            #print(f"\n[Vision AI]: {vision_response}\n")

            screen_msg = {
                "role": "user",
                "content": f"[SCREEN CONTEXT]\n{vision_response}"
            }

            # Snapshot history for the API call (don't hold lock during network I/O)
            with history_lock:
                history_snapshot = list(message_history)

            if user_is_talking.is_set():
                cooldown_until = time.time() + cooldown_time  # Reset cooldown if user is active
                continue  # Skip this vision update if user is currently talking

            ai_response = dl.chat(history_snapshot + [screen_msg])

            if ai_response and ai_response.strip():
                print(f"{ai_response}\n", flush=True)

                with history_lock:
                    message_history.append(screen_msg)
                    message_history.append({"role": "assistant", "content": ai_response})

                cooldown_until = time.time() + cooldown_time

        except Exception as e:
            print(f"[Vision Error]: {e}")
        finally:
            busy = False

        time.sleep(1)


def dialogue_loop():
    global busy
    for line in sys.stdin:
        user_input = line.strip()
        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit"]:
            break
        user_is_talking.set()  # Signal that user is active
        busy = True  # block vision loop while we handle user input
        try:
            with history_lock:
                message_history.append({"role": "user", "content": user_input})
                history_snapshot = list(message_history)

            ai_response = dl.chat(history_snapshot)

            with history_lock:
                message_history.append({"role": "assistant", "content": ai_response})

            print(ai_response, flush=True)
        finally:
            user_is_talking.clear()  # Clear user activity signal
            busy = False  # always release, even if dl.chat() throws
    save_history()  # Save history on exit


# ── Launch both loops ──────────────────────────────────────────────────────
vision_thread = threading.Thread(target=vision_loop, daemon=True)
vision_thread.start()

dialogue_loop()  # runs on main thread (owns stdin)