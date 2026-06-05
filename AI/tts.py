from TTS.api import TTS
import torch
import sounddevice as sd
import numpy as np
import os 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_PATH = os.path.join(BASE_DIR, "jinxVoice.wav")
# Load model
print("Loading XTTS v2...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

# Generate and save embedding from your sample
gpt_cond_latent, speaker_embedding = tts.synthesizer.tts_model.get_conditioning_latents(
    audio_path=[VOICE_PATH]
)

torch.save({
    "gpt_cond_latent": gpt_cond_latent,
    "speaker_embedding": speaker_embedding
}, "jinx_voice.pth")
print("Saved jinx_voice.pth")

# Test inference with a few Jinx-like lines
test_lines = [
    "Boom! Was that supposed to impress me?",
    "Oh great, another boring day. Lucky me.",
    "You think you can hide from me? Cute."
]

print("\nPlaying test lines... press Ctrl+C to skip\n")

for line in test_lines:
    print(f">> {line}")
    out = tts.synthesizer.tts_model.inference(
        text=line,
        language="en",
        gpt_cond_latent=gpt_cond_latent,
        speaker_embedding=speaker_embedding,
    )
    audio_np = np.array(out["wav"], dtype=np.float32)
    sd.play(audio_np, samplerate=24000)
    sd.wait()
    input("   [Enter for next line]")