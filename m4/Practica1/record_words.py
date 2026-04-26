import sounddevice as sd
from scipy.io.wavfile import write
from pathlib import Path
import numpy as np
import time

fs = 16000
duracion = 3
palabra = "repetir"  # <-- word to record
N = 15              # <-- number of recordings
start_index = 1     # <-- starting file number

INPUT_DEVICE = 1   # pulse

print(sd.query_devices())
print("Default devices:", sd.default.device)

carpeta = Path("C:\\Users\\joser\\OneDrive\\Documentos\\GitHub\\rogertests2\\rogertests2\\m4\\Practica1\\dataset_comandos\\") / palabra
carpeta.mkdir(parents=True, exist_ok=True)

for i in range(N):
    numero = start_index + i

    print(f"\n--- Grabación {numero:02d}/{start_index+N-1} ---")

    # Countdown
    for t in range(1, 0, -1):
        print(f"{t}...")
        time.sleep(0.5)

    print(f"Grabando {palabra}_{numero:02d}.wav")

    audio = sd.rec(
        int(duracion * fs),
        samplerate=fs,
        channels=1,
        dtype='int16',
        device=INPUT_DEVICE
    )
    sd.wait()

    audio_mono = audio[:, 0]

    # Debug stats
    print("Min:", audio_mono.min(),
          "Max:", audio_mono.max(),
          "Mean abs:", np.mean(np.abs(audio_mono)))

    archivo = carpeta / f"{palabra}_{numero:02d}.wav"
    write(str(archivo), fs, audio_mono)

    print(f"Guardado en: {archivo}")

    # Small pause between recordings
    time.sleep(1)

print("\nDataset recording complete ✅")