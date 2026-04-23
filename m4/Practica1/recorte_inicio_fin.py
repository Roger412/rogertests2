from pathlib import Path
import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt

frame_length = 320
hop_length = 128

def frame_signal(signal, frame_length=320, hop_length=128): # Función para dividir la señal en ventanas de Hamming de 320 puntos corriendose cada 128 muestas
    if len(signal) < frame_length: # Si la señal es más corta que el tamaño del marco, no se pueden crear marcos completos
        return np.empty((0, frame_length)) 
    
    num_frames = 1 + (len(signal) - frame_length) // hop_length # Calcula el número de marcos completos que se pueden crear con la señal dada, el tamaño del marco y el salto
    frames = []
    
    for i in range(num_frames): # Itera sobre el número de marcos y extrae cada marco de la señal utilizando el tamaño del marco y el salto para determinar el inicio de cada marco
        start = i * hop_length
        frame = signal[start:start + frame_length]
        frames.append(frame)
    
    return np.array(frames) # Devuelve un array de marcos, donde cada marco es una ventana de la señal original con el tamaño especificado por frame_length y el salto especificado por hop_length. Si la señal es demasiado corta para formar al menos un marco completo, devuelve un array vacío con la forma (0, frame_length).

def detect_inicio_fin(signal, frame_length=320, hop_length=128): # Función para detectar el inicio y el fin de la voz utilizando el cruce por cero (ZCR) y la energía
    frames = frame_signal(signal, frame_length, hop_length) # Divide la señal en marcos utilizando la función frame_signal. Esto crea una matriz de marcos donde cada fila corresponde a un marco de la señal original.

    if len(frames) == 0:
        return 0, len(signal), None, None, None 

    # Cálculo de ZCR
    zcr = np.zeros(len(frames))
    for i, frame in enumerate(frames):
        crossings = np.sum(np.abs(np.diff(np.sign(frame)))) / 2
        zcr[i] = crossings / frame_length

    # Cálculo de energía
    energy = np.zeros(len(frames))
    for i, frame in enumerate(frames):
        energy[i] = np.sum(frame ** 2) / frame_length

    # Umbrales inspirados directamente en el MATLAB
    zcr_threshold = 0.08 * np.max(zcr) if np.max(zcr) > 0 else 0
    energy_threshold = 0.005 * np.max(energy) if np.max(energy) > 0 else 0

    # Detección de voz
    voice_flags = (zcr > zcr_threshold) & (energy > energy_threshold)

    # Fallback: si no detecta nada, usar solo energía
    if not np.any(voice_flags):
        voice_flags = energy > energy_threshold

    first_voice_frame = np.argmax(voice_flags) if np.any(voice_flags) else None
    last_voice_frame = len(voice_flags) - 1 - np.argmax(voice_flags[::-1]) if np.any(voice_flags) else None

    if first_voice_frame is None or last_voice_frame is None:
        return 0, len(signal), zcr, energy, voice_flags

    start_sample = first_voice_frame * hop_length
    end_sample = last_voice_frame * hop_length + frame_length
    end_sample = min(end_sample, len(signal))

    return start_sample, end_sample, zcr, energy, voice_flags


input_root = Path("dataset_comandos_roger/dataset_preenfasis")
output_root = Path("dataset_comandos_roger/dataset_recortado")
output_root.mkdir(exist_ok=True)

for word_dir in input_root.iterdir():
    if word_dir.is_dir():
        out_word_dir = output_root / word_dir.name
        out_word_dir.mkdir(parents=True, exist_ok=True)

        for wav_file in word_dir.glob("*.wav"):
            signal, fs = sf.read(wav_file)

            if signal.ndim > 1:
                signal = np.mean(signal, axis=1)

            start_sample, end_sample, zcr, energy, voice_flags = detect_inicio_fin(
                signal,
                frame_length=320,
                hop_length=128
            )

            signal_trimmed = signal[start_sample:end_sample]
            out_file = out_word_dir / wav_file.name
            sf.write(out_file, signal_trimmed, fs)

            print(f"{wav_file.name} -> inicio={start_sample}, fin={end_sample}, muestras={len(signal_trimmed)}")