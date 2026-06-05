import queue
import tkinter as tk
import random
import os
from PIL import Image, ImageTk, ImageSequence
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
_tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
_voice = torch.load(_VOICE_PTH)
_voice["gpt_cond_latent"] = _voice["gpt_cond_latent"].cuda()
_voice["speaker_embedding"] = _voice["speaker_embedding"].cuda()
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

class Jinx:
    def __init__(self):
        self.expression_job = None
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.config(bg="black")
        self.root.wm_attributes("-transparentcolor", "black")
        self.drag_reaction_cooldown = 30.0
        self.last_drag_time = 0
        self.is_dragging = False

        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<Button-3>", lambda e: self.root.destroy())
        
        self.pet_width = 300
        self.pet_height = 300
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.transition_playing = False
        self.is_sleeping = False
        self.sleep_after = 200000  #sleep after 200 seconds of direct inactivity
        self.sleep_job = None
        

        self.canvas = tk.Canvas(
            self.root,
            width=self.pet_width,
            height=self.pet_height,
            bg="black",
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack()
        self.canvas_image = self.canvas.create_image(
            self.pet_width // 2,
            self.pet_height // 2,
            anchor="center"
        )
        self.bubble = tk.Label(
            self.root,
            text="",
            bg="#2b2b2b",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=5,
            wraplength=200,
            justify="center",
            highlightthickness=1,
            highlightbackground="#444444"
        )
        # Hide it initially
        self.bubble_visible = False
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

            self.preloaded_images[path] = ImageTk.PhotoImage(img)

        self.old_pos = None
        self.canvas.bind("<ButtonPress-1>", self.mouse_press)
        self.canvas.bind("<B1-Motion>", self.mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_release)

        self.currentBaseCollection = self.expressionsBase
        self.currentBlinkImage = self.expressionBaseClosed
        self.state = "base"

        self.update_image(self.expressionsBase[2])
        self.move_to_bottom_left()
        #self.schedule_expression()
        self.new_schedule_expression()
        self.blink()
        self.reset_sleep_timer()

    def load_gif(self, path):
        gif = Image.open(path)

        frames = []

        for frame in ImageSequence.Iterator(gif):
            frame = frame.convert("RGBA")
            frame = frame.resize((self.pet_width, self.pet_height), Image.LANCZOS)

            frames.append(ImageTk.PhotoImage(frame))

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
                self.canvas.itemconfig(self.canvas_image, image=frames[index])
                self.photo = frames[index]

                self.root.after(delay, animate, index + 1)

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
            self.root.after_cancel(self.sleep_job)
        # Wake up if currently sleeping
        if self.is_sleeping:
            self.wake_up()
        # Start new inactivity countdown
        self.sleep_job = self.root.after(
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
                # Use after() to update UI from a background thread
                self.root.after(0, self.show_bubble, message)

    def show_bubble(self, text):
        self.bubble.config(text=text)
        # Position bubble above the pet's head
        self.bubble.place(x=25, y=10, width=200) 
        self.bubble_visible = True
        speak_async(text)
        # Auto-hide after 15 seconds
        self.root.after(20000, self.hide_bubble)

    def hide_bubble(self):
        if self.bubble_visible:
            self.bubble.place_forget()
            self.bubble_visible = False

    def move_to_bottom_left(self):
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"+20+{sh - self.pet_height - 20}")

    def update_image(self, path):
        self.photo = self.preloaded_images[path]
        self.canvas.itemconfig(self.canvas_image, image=self.photo)

    #new expression logic
    def new_schedule_expression(self):
        if self.expression_job:
            self.root.after_cancel(self.expression_job)

        self.expression_job = self.root.after(
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
            self.root.after(1000, self.blink) # Check again after 1 second
            return
        # close eyes
        self.update_image(self.currentBlinkImage)

        # reopen after short delay
        self.root.after(
            200,
            lambda: self.update_image(random.choice(self.currentBaseCollection))
        )

        # schedule next blink randomly
        next_blink = random.randint(3000, 7000)
        self.root.after(next_blink, self.blink)



    def mouse_press(self, event):
        self.reset_sleep_timer()
        self.is_dragging = False
        self.old_pos = (event.x_root, event.y_root)

    def mouse_move(self, event):
        self.reset_sleep_timer()
        if self.old_pos:
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
                
            dx = event.x_root - self.old_pos[0]
            dy = event.y_root - self.old_pos[1]
            x = self.root.winfo_x() + dx
            y = self.root.winfo_y() + dy
            self.root.geometry(f"+{x}+{y}")
            self.old_pos = (event.x_root, event.y_root)

    def mouse_release(self, event):
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
        self.root.mainloop()

if __name__ == "__main__":
    pet = Jinx()
    pet.run()