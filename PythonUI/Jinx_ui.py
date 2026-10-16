import queue
import random
import os
from PIL import Image, ImageSequence
from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter
import sys
import threading
import numpy as np
import sounddevice as sd
import torch
from TTS.api import TTS
import time

# ── TTS Setup ─────────────────────────────────────────────────────────────────
_BASE_DIR_TTS = os.path.dirname(os.path.abspath(__file__))
_VOICE_PTH = os.path.join(_BASE_DIR_TTS, "jinx_voice.pth")
_PADDING = np.zeros(int(24000 * 0.3), dtype=np.float32)
_START_PADDING = np.zeros(int(24000 * 0.05), dtype=np.float32)  # 50ms
tts_queue = queue.Queue()
print("Loading XTTS v2...")
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
_tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(_DEVICE)
_voice = torch.load(_VOICE_PTH, map_location=_DEVICE)
_voice["gpt_cond_latent"] = _voice["gpt_cond_latent"].to(_DEVICE)
_voice["speaker_embedding"] = _voice["speaker_embedding"].to(_DEVICE)
_tts_lock = threading.Lock()
print("TTS ready.")

def tts_worker():
    while True:
        text = tts_queue.get()
        if text is None:
            break
        synthesize_and_play(text)
        tts_queue.task_done()
def speak_async(text: str):
    tts_queue.put(text)
def synthesize_and_play(text: str):
    with _tts_lock:
        out = _tts.synthesizer.tts_model.inference(
            text=text,
            language="en",
            gpt_cond_latent=_voice["gpt_cond_latent"],
            speaker_embedding=_voice["speaker_embedding"],
            speed=1.3
        )

    audio_np = np.array(out["wav"], dtype=np.float32)
    audio_np = np.concatenate([_START_PADDING, audio_np, _PADDING])

    # Play audio in a separate lightweight thread
    threading.Thread(
        target=lambda: (sd.play(audio_np, 24000), sd.wait()),
        daemon=True
    ).start()
    
# Start TTS worker thread
threading.Thread(target=tts_worker, daemon=True).start()

def pil_to_pixmap(img):
    img = img.convert("RGBA")
    qimg = QImage(img.tobytes(), img.width, img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())

class Jinx(QWidget):
    message_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.expression_job = None
        # Frameless, always-on-top window with a see-through background
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        # Keep showing even though this process is never the active app
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.drag_reaction_cooldown = 30.0
        self.last_drag_time = 0
        self.is_dragging = False

        self.pet_width = 300
        self.pet_height = 300
        self.setFixedSize(self.pet_width, self.pet_height)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.transition_playing = False
        self.is_sleeping = False
        self.sleep_after = 200000  #sleep after 200 seconds of direct inactivity
        self.sleep_job = None
        

        self.photo = None
        self.bubble = QLabel(self)
        self.bubble.setWordWrap(True)
        self.bubble.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bubble.setStyleSheet(
            "background-color: #2b2b2b; color: white; font-weight: bold; font-size: 13px;"
            "padding: 5px 10px; border: 1px solid #444444;"
        )
        # Hide it initially
        self.bubble.hide()
        self.bubble_visible = False
        self.bubble_job = None
        self.message_received.connect(self.show_bubble)
        threading.Thread(target=self.listen_for_messages, daemon=True).start()
        
        self.expressionsBase = [
            os.path.join(self.base_dir, "expressionsV2/jinxbase1.png"),
            os.path.join(self.base_dir, "expressionsV2/jinxbase4.png"),
            os.path.join(self.base_dir, "expressionsV2/jinxbase3.png"),
        ]
        self.expressionsBase2 = [
            os.path.join(self.base_dir, "expressionsV2/jinxcrossedleft.png"),
            os.path.join(self.base_dir, "expressionsV2/jinxcrossedright.png"),
            os.path.join(self.base_dir, "expressionsV2/jinxcrossed.png")
        ]
        self.expressionBase3 = [
            os.path.join(self.base_dir, "expressionsV2/jinxconfident.png"),
            os.path.join(self.base_dir, "expressionsV2/jinxconfidentright.png"),
            os.path.join(self.base_dir, "expressionsV2/jinxconfidentleft.png")
        ]
        self.expressionBaseClosed = os.path.join(self.base_dir, "expressionsV2/jinxbaseclosed.png")
        self.expressionCrossedClosed = os.path.join(self.base_dir, "expressionsV2/jinxcrossedclosed.png")
        self.expressionConfidentClosed = os.path.join(self.base_dir, "expressionsV2/jinxconfidentclosed.png")

        self.reactionTransition = [
            os.path.join(self.base_dir, "transitionalgifs/jinxBaseToLean.gif"),
            os.path.join(self.base_dir, "transitionalgifs/jinxLeanToBase.gif"),
            os.path.join(self.base_dir, "transitionalgifs/jinxBaseToSleep.gif"),
            os.path.join(self.base_dir, "transitionalgifs/jinxSleepToBase.gif"),
            os.path.join(self.base_dir, "transitionalgifs/jinxBaseToCrossed.gif"),
            os.path.join(self.base_dir, "transitionalgifs/jinxCrossedToBase.gif"),
            os.path.join(self.base_dir, "transitionalgifs/jinxBaseToConfident.gif"),
            os.path.join(self.base_dir, "transitionalgifs/jinxConfidentToBase.gif"),
            os.path.join(self.base_dir, "transitionalgifs/jinxBaseToSmirk.gif"),
            os.path.join(self.base_dir, "transitionalgifs/jinxSmirkToBase.gif")
        ]

        self.preloaded_gifs = {
            "drag_start": self.load_gif(self.reactionTransition[0]),
            "drag_end": self.load_gif(self.reactionTransition[1]),
            "sleep_start": self.load_gif(self.reactionTransition[2]),
            "sleep_end": self.load_gif(self.reactionTransition[3]),
            "crossed_start": self.load_gif(self.reactionTransition[4]),
            "crossed_end": self.load_gif(self.reactionTransition[5]),
            "confident_start": self.load_gif(self.reactionTransition[6]),
            "confident_end": self.load_gif(self.reactionTransition[7]),
            "smirk_start": self.load_gif(self.reactionTransition[8]),
            "smirk_end": self.load_gif(self.reactionTransition[9])
        }
        self.preloaded_images = {}

        for path in self.expressionsBase + [self.expressionBaseClosed] + self.expressionsBase2 + [self.expressionCrossedClosed] + self.expressionBase3 + [self.expressionConfidentClosed]:
            img = Image.open(path).convert("RGBA")
            img = img.resize((self.pet_width, self.pet_height), Image.LANCZOS)

            self.preloaded_images[path] = pil_to_pixmap(img)

        self.old_pos = None

        self.currentBaseCollection = self.expressionsBase
        self.currentBlinkImage = self.expressionBaseClosed
        self.state = "base"

        self.update_image(self.expressionsBase[2])
        self.move_to_bottom_left()
        #self.schedule_expression()
        self.new_schedule_expression()
        self.blink()
        self.reset_sleep_timer()

    # ── Timer helpers (stand-ins for Tk's after/after_cancel) ──────────────────
    def after(self, ms, func, *args):
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: func(*args))
        timer.timeout.connect(timer.deleteLater)
        timer.start(ms)
        return timer

    def after_cancel(self, timer):
        try:
            timer.stop()
        except RuntimeError:
            pass  # timer already fired and was deleted

    def set_frame(self, pixmap):
        self.photo = pixmap
        self.update()

    def paintEvent(self, event):
        if self.photo:
            QPainter(self).drawPixmap(0, 0, self.photo)

    def load_gif(self, path):
        gif = Image.open(path)

        frames = []

        for frame in ImageSequence.Iterator(gif):
            frame = frame.convert("RGBA")
            frame = frame.resize((self.pet_width, self.pet_height), Image.LANCZOS)

            frames.append(pil_to_pixmap(frame))

        delay = gif.info.get("duration", 100)

        return {
            "frames": frames,
            "delay": delay
        }
    def play_gif(self, gif_data, loop=False, on_complete=None):
        if self.transition_playing:
            return

        self.transition_playing = True

        frames = gif_data["frames"]
        delay = gif_data["delay"]

        def animate(index=0):
            if index < len(frames):
                self.set_frame(frames[index])

                self.after(delay, animate, index + 1)

            else:
                self.transition_playing = False

                if on_complete:
                    on_complete()

                elif loop:
                    animate(0)

        animate()

    def reset_sleep_timer(self):
        # Cancel previous timer
        if self.sleep_job:
            self.after_cancel(self.sleep_job)
        # Wake up if currently sleeping
        if self.is_sleeping:
            self.wake_up()
        # Start new inactivity countdown
        self.sleep_job = self.after(
            self.sleep_after,
            self.go_to_sleep
        )
    def go_to_sleep(self):
        if self.transition_playing or self.is_dragging:
            self.reset_sleep_timer()
            return
        self.is_sleeping = True
        if self.state == "crossed":
            self.play_gif(
                self.preloaded_gifs["crossed_end"], 
                on_complete=lambda: self.play_gif(self.preloaded_gifs["sleep_start"])
            )
        elif self.state == "confident":
            self.play_gif(
                self.preloaded_gifs["confident_end"], 
                on_complete=lambda: self.play_gif(self.preloaded_gifs["sleep_start"])
            )
        else:
            self.play_gif(
                self.preloaded_gifs["sleep_start"]
            )
    def wake_up(self):
        self.is_sleeping = False
        self.play_gif(
            self.preloaded_gifs["sleep_end"],
            on_complete=lambda: self.new_schedule_expression()
        )
        

    def listen_for_messages(self):
        """Listens for text sent from the AI Agent via stdout/stdin pipe"""
        for line in sys.stdin:
            message = line.strip()
            if message:
                # Hand off to the UI thread via a Qt signal
                self.message_received.emit(message)

    def show_bubble(self, text):
        self.bubble.setText(text)
        # Position bubble above the pet's head
        self.bubble.setFixedWidth(200)
        self.bubble.adjustSize()
        self.bubble.move(25, 10)
        self.bubble.show()
        self.bubble.raise_()
        self.bubble_visible = True
        speak_async(text)
        # Auto-hide after 20 seconds
        if self.bubble_job:
            self.after_cancel(self.bubble_job)
        self.bubble_job = self.after(20000, self.hide_bubble)

    def hide_bubble(self):
        if self.bubble_visible:
            self.bubble.hide()
            self.bubble_visible = False

    def move_to_bottom_left(self):
        sh = QApplication.primaryScreen().geometry().height()
        self.move(20, sh - self.pet_height - 20)

    def update_image(self, path):
        self.set_frame(self.preloaded_images[path])

    #new expression logic
    def new_schedule_expression(self):
        if self.expression_job:
            self.after_cancel(self.expression_job)

        self.expression_job = self.after(
            2000,
            self.change_expressionV2
        )
    def change_expressionV2(self):
        if self.transition_playing or self.is_dragging or self.is_sleeping:
            self.new_schedule_expression()
            return
        if random.random() < 0.4:
            # Pick a new state different from the current
            possible_states = ["base", "crossed", "confident", "smirk"]
            possible_states.remove(self.state)
            new_state = random.choice(possible_states)
            self.switch_state(new_state)
        else:
            # Stay in current state
            self.update_image(random.choice(self.currentBaseCollection))
        self.new_schedule_expression()
    def switch_state(self, new_state):
        if self.state == new_state:
            return  # nothing to do
        if new_state == "base":
            if self.state == "crossed":
                self.play_gif(
                    self.preloaded_gifs["crossed_end"], 
                    on_complete=lambda: self.update_image(random.choice(self.expressionsBase))
                )
            elif self.state == "confident":
                self.play_gif(
                    self.preloaded_gifs["confident_end"], 
                    on_complete=lambda: self.update_image(random.choice(self.expressionsBase))
                )
            self.currentBaseCollection = self.expressionsBase
            self.currentBlinkImage = self.expressionBaseClosed
        elif new_state == "crossed":
            if self.state == "base":
                self.play_gif(
                    self.preloaded_gifs["crossed_start"], 
                    on_complete=lambda: self.update_image(random.choice(self.expressionsBase2))
                )
            elif self.state == "confident":
                self.play_gif(
                    self.preloaded_gifs["confident_end"], 
                    on_complete=lambda: self.play_gif(
                        self.preloaded_gifs["crossed_start"], 
                        on_complete=lambda: self.update_image(random.choice(self.expressionsBase2))
                    )
                )
            self.currentBaseCollection = self.expressionsBase2
            self.currentBlinkImage = self.expressionCrossedClosed
        elif new_state == "confident":
            if self.state == "base":
                self.play_gif(
                    self.preloaded_gifs["confident_start"], 
                    on_complete=lambda: self.update_image(random.choice(self.expressionBase3))
                )
            elif self.state == "crossed":
                self.play_gif(
                    self.preloaded_gifs["crossed_end"], 
                    on_complete=lambda: self.play_gif(
                        self.preloaded_gifs["confident_start"], 
                        on_complete=lambda: self.update_image(random.choice(self.expressionBase3))
                    )
                )
            self.currentBaseCollection = self.expressionBase3
            self.currentBlinkImage = self.expressionConfidentClosed
        elif new_state == "smirk":
            if self.state == "base":
                self.currentBaseCollection = self.expressionsBase
                self.currentBlinkImage = self.expressionBaseClosed
                self.play_gif(
                    self.preloaded_gifs["smirk_start"], 
                    on_complete=lambda: self.play_gif(self.preloaded_gifs["smirk_end"])
                )
                
            elif self.state == "crossed":
                self.currentBaseCollection = self.expressionsBase
                self.currentBlinkImage = self.expressionBaseClosed
                self.play_gif(
                    self.preloaded_gifs["crossed_end"], 
                    on_complete=lambda: self.play_gif(
                        self.preloaded_gifs["smirk_start"], 
                        on_complete=lambda: self.play_gif(self.preloaded_gifs["smirk_end"])
                    )
                )
                
            elif self.state == "confident":
                self.currentBaseCollection = self.expressionsBase
                self.currentBlinkImage = self.expressionBaseClosed
                self.play_gif(
                    self.preloaded_gifs["confident_end"], 
                    on_complete=lambda: self.play_gif(
                        self.preloaded_gifs["smirk_start"], 
                        on_complete=lambda: self.play_gif(self.preloaded_gifs["smirk_end"])
                    )
                )
            return # Smirk is temporary and doesn't change base state
                
        self.state = new_state

    def blink(self):
        if self.transition_playing or self.is_dragging or self.is_sleeping:
            self.after(1000, self.blink) # Check again after 1 second
            return
        # close eyes
        self.update_image(self.currentBlinkImage)

        # reopen after short delay
        self.after(
            200,
            lambda: self.update_image(random.choice(self.currentBaseCollection))
        )

        # schedule next blink randomly
        next_blink = random.randint(3000, 7000)
        self.after(next_blink, self.blink)



    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            QApplication.quit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            QApplication.quit()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.reset_sleep_timer()
        self.is_dragging = False
        pos = event.globalPosition().toPoint()
        self.old_pos = (pos.x(), pos.y())

    def mouseMoveEvent(self, event):
        self.reset_sleep_timer()
        if self.old_pos:
            pos = event.globalPosition().toPoint()
            current_time = time.time()
            # Only signal Electron if we haven't already reported this drag session
            if not self.is_dragging :
                self.play_gif(
                    self.preloaded_gifs["drag_start"]
                )
                self.is_dragging = True
                if (current_time - self.last_drag_time) >= self.drag_reaction_cooldown: 
                    print("EVENT:DRAGGED", flush=True) # Send once
                    self.last_drag_time = current_time
                    self.is_dragging = True
                
            dx = pos.x() - self.old_pos[0]
            dy = pos.y() - self.old_pos[1]
            self.move(self.x() + dx, self.y() + dy)
            self.old_pos = (pos.x(), pos.y())

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.old_pos is None:
            return
        self.reset_sleep_timer()
        self.old_pos = None
        self.is_dragging = False
        self.currentBaseCollection = self.expressionsBase
        self.currentBlinkImage = self.expressionBaseClosed
        self.state = "base"
        self.play_gif(
        self.preloaded_gifs["drag_end"], on_complete=lambda: self.update_image(random.choice(self.expressionsBase))
        )

        
        
        self.new_schedule_expression() # Resume normal expression changes

    def run(self):
        self.show()
        QApplication.instance().exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = Jinx()
    pet.run()