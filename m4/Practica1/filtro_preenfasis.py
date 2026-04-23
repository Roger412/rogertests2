from pathlib import Path
import numpy as np
import soundfile as sf

# Parámetro de preénfasis
a = 0.95

# Carpeta original
dataset_root = Path("dataset_comandos_roger")

# Carpeta de salida
output_root = Path("dataset_comandos_roger/dataset_preenfasis")
output_root.mkdir(exist_ok=True)

def pre_enfasis(signal, a=0.95):
    y = np.empty_like(signal) # Crear un array vacío del mismo tamaño que la señal original
    y[0] = signal[0] # El primer valor se mantiene igual
    y[1:] = signal[1:] - a * signal[:-1] # Aplicar la fórmula de preénfasis para el resto de la señal 
                                            # s~[n] = s[n] - 0.95 * s[n-1] en discreto, que es igual a
                                            # H(z) = 1 - 0.95 * z^-1 en el dominio de la frecuencia
    return y

for word_dir in dataset_root.iterdir():
    if word_dir.is_dir():
        out_word_dir = output_root / word_dir.name
        out_word_dir.mkdir(parents=True, exist_ok=True)

        for wav_file in word_dir.glob("*.wav"):
            signal, fs = sf.read(wav_file)

            # Si la señal tiene más de un canal, convertir a mono promediando los canales
            if signal.ndim > 1:
                signal = np.mean(signal, axis=1)

            # Aplicar preénfasis
            signal_pre = pre_enfasis(signal, a)

            # Guardar
            out_file = out_word_dir / wav_file.name
            sf.write(out_file, signal_pre, fs)

print("Preénfasis aplicado a todos los archivos.")