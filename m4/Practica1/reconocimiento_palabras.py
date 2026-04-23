from pathlib import Path
import numpy as np
import soundfile as sf
import pickle
import pandas as pd
from sklearn.metrics import confusion_matrix

# ==========================================
# CONFIGURACIÓN
# ==========================================
frame_length = 320
hop_length = 128
lpc_order = 12
preemphasis = 0.95
train_count = 10
test_count = 5

dataset_root = Path("dataset_comandos_roger/dataset_recortado")

# cargar codebooks entrenados en el paso 5
with open("codebooks_16_lsf_roger.pkl", "rb") as f:
    codebooks_lsf = pickle.load(f)

with open("codebooks_16_w_roger.pkl", "rb") as f:
    codebooks_w = pickle.load(f)


# ==========================================
# PREPROCESAMIENTO
# ==========================================
def pre_emphasis(signal, a=0.95):
    y = np.empty_like(signal)
    y[0] = signal[0]
    y[1:] = signal[1:] - a * signal[:-1]
    return y


def frame_signal(signal, frame_length=320, hop_length=128):
    if len(signal) < frame_length:
        return np.empty((0, frame_length))

    num_frames = 1 + (len(signal) - frame_length) // hop_length
    frames = []

    for i in range(num_frames):
        start = i * hop_length
        frames.append(signal[start:start + frame_length])

    return np.array(frames)


# ==========================================
# AUTOCORRELACIÓN Y LEVINSON-DURBIN
# ==========================================
def autocorrelation(x, order):
    r = np.zeros(order + 1)
    for k in range(order + 1):
        r[k] = np.sum(x[:len(x) - k] * x[k:])
    return r


def levinson_durbin(r, order):
    w = np.zeros(order + 1)
    e = r[0]
    w[0] = 1.0

    if e <= 1e-12:
        return w, 1e-12

    for i in range(1, order + 1):
        acc = r[i]
        for j in range(1, i):
            acc += w[j] * r[i - j]

        k = -acc / e
        w_prev = w.copy()
        w[i] = k

        for j in range(1, i):
            w[j] = w_prev[j] + k * w_prev[i - j]

        e = e * (1.0 - k * k)
        e = max(e, 1e-12)

    return w, e


# ==========================================
# CORRELACIÓN CORTA DEL POLINOMIO LPC
# ==========================================
def short_correlation_from_lpc(w):
    A_asc = np.asarray(w, dtype=np.float64).copy()
    p = len(A_asc) - 1
    ra = np.zeros(p + 1)

    for i in range(p + 1):
        s = 0.0
        for j in range(p + 1 - i):
            s += A_asc[j] * A_asc[j + i]
        ra[i] = s

    return ra


# ==========================================
# DISTANCIA ITAKURA-SAITO
# ==========================================
def itakura_saito_distance_from_correlations(r_i, w_centroid, sigma2=1.0):
    ra = short_correlation_from_lpc(w_centroid)
    return (1.0 / sigma2) * (r_i[0] * ra[0] + 2.0 * np.dot(r_i[1:], ra[1:]))


# ==========================================
# UTILIDAD: ORDENAR Y SEPARAR LSF
# ==========================================
def enforce_lsf_spacing(lsf, min_sep=0.02):
    lsf = np.sort(np.clip(lsf, 1e-3, np.pi - 1e-3)).copy()

    for i in range(1, len(lsf)):
        if lsf[i] <= lsf[i - 1] + min_sep:
            lsf[i] = lsf[i - 1] + min_sep

    if lsf[-1] >= np.pi - 1e-3:
        lsf[-1] = np.pi - 1e-3
        for i in range(len(lsf) - 2, -1, -1):
            if lsf[i] >= lsf[i + 1] - min_sep:
                lsf[i] = lsf[i + 1] - min_sep

    return lsf


# ==========================================
# LPC -> LSF
# ==========================================
def lpc_to_lsf_from_levinson(w):
    w = np.asarray(w, dtype=np.float64)
    p = len(w) - 1

    if p % 2 != 0:
        raise ValueError("El orden LPC debe ser par.")

    A_asc = w.copy()
    A_flip = np.r_[0.0, A_asc[::-1]]
    A_pad = np.r_[A_asc, 0.0]

    P_asc = A_pad + A_flip
    Q_asc = A_pad - A_flip

    P_desc = P_asc[::-1]
    Q_desc = Q_asc[::-1]

    roots_P = np.roots(P_desc)
    roots_Q = np.roots(Q_desc)

    roots_P = roots_P[np.abs(roots_P + 1) > 1e-3]
    roots_Q = roots_Q[np.abs(roots_Q - 1) > 1e-3]

    roots_P = roots_P[np.abs(np.abs(roots_P) - 1.0) < 1.5e-1]
    roots_Q = roots_Q[np.abs(np.abs(roots_Q) - 1.0) < 1.5e-1]

    ang_P = np.angle(roots_P)
    ang_Q = np.angle(roots_Q)

    ang_P = np.sort(ang_P[(ang_P > 0) & (ang_P < np.pi)])
    ang_Q = np.sort(ang_Q[(ang_Q > 0) & (ang_Q < np.pi)])

    lsf = np.sort(np.concatenate([ang_P, ang_Q]))

    clean = []
    for x in lsf:
        if not clean or abs(x - clean[-1]) > 1e-3:
            clean.append(float(x))
    lsf = np.array(clean, dtype=np.float64)

    if len(lsf) != p:
        raise ValueError(f"No se pudieron obtener {p} LSF válidos. Se obtuvieron {len(lsf)}.")

    return enforce_lsf_spacing(lsf, min_sep=0.02)


# ==========================================
# EXTRAER FRAMES VÁLIDOS DE PRUEBA
# ==========================================
def extract_test_vectors_from_file(wav_file):
    signal, fs = sf.read(wav_file)

    if signal.ndim > 1:
        signal = np.mean(signal, axis=1)

    signal = pre_emphasis(signal, preemphasis)
    frames = frame_signal(signal, frame_length, hop_length)
    window = np.hamming(frame_length)

    r_vectors = []
    lsf_vectors = []
    w_vectors = []

    if len(frames) == 0:
        return np.array(lsf_vectors), np.array(r_vectors), np.array(w_vectors)

    frame_energies = np.array([np.sum((frame * window) ** 2) for frame in frames])
    energy_threshold = 0.05 * np.max(frame_energies) if len(frame_energies) > 0 else 0.0

    for frame, e_frame in zip(frames, frame_energies):
        if e_frame < energy_threshold:
            continue

        xw = frame * window
        r = autocorrelation(xw, lpc_order)

        if r[0] <= 1e-10:
            continue

        w, err = levinson_durbin(r, lpc_order)

        try:
            lsf = lpc_to_lsf_from_levinson(w)
            r_vectors.append(r)
            lsf_vectors.append(lsf)
            w_vectors.append(w)
        except Exception:
            continue

    return np.array(lsf_vectors), np.array(r_vectors), np.array(w_vectors)


# ==========================================
# SCORE DE UN ARCHIVO VS UN CODEBOOK
# ==========================================
def score_against_codebook(r_vectors, codebook_w):
    """
    Promedio de la distancia mínima por frame
    """
    if len(r_vectors) == 0:
        return np.inf

    total = 0.0
    for r_i in r_vectors:
        dists = [itakura_saito_distance_from_correlations(r_i, w_c) for w_c in codebook_w]
        total += np.min(dists)

    return total / len(r_vectors)


# ==========================================
# CLASIFICAR UN ARCHIVO
# ==========================================
def classify_file(wav_file, codebooks_w):
    lsf_vectors, r_vectors, w_vectors = extract_test_vectors_from_file(wav_file)

    if len(r_vectors) == 0:
        return None, {}

    scores = {}
    for word, codebook_w in codebooks_w.items():
        scores[word] = score_against_codebook(r_vectors, codebook_w)

    predicted_word = min(scores, key=scores.get)
    return predicted_word, scores


# ==========================================
# EVALUACIÓN COMPLETA
# ==========================================
y_true = []
y_pred = []
rows = []

words = sorted(codebooks_w.keys())

for word_dir in sorted(dataset_root.iterdir()):
    if not word_dir.is_dir():
        continue

    true_word = word_dir.name
    wav_files = sorted(word_dir.glob("*.wav"))

    # usar los 5 restantes para prueba
    test_files = wav_files[train_count:train_count + test_count]

    for wav_file in test_files:
        predicted_word, scores = classify_file(wav_file, codebooks_w)

        if predicted_word is None:
            print(f"No se pudo clasificar {wav_file.name}")
            continue

        y_true.append(true_word)
        y_pred.append(predicted_word)

        row = {
            "archivo": wav_file.name,
            "real": true_word,
            "predicho": predicted_word
        }
        row.update({f"score_{k}": v for k, v in scores.items()})
        rows.append(row)

        print(f"{wav_file.name} -> real: {true_word}, predicho: {predicted_word}")

# ==========================================
# MATRIZ DE CONFUSIÓN
# ==========================================
cm = confusion_matrix(y_true, y_pred, labels=words)
cm_df = pd.DataFrame(cm, index=words, columns=words)

print("\nMatriz de confusión:")
print(cm_df)

accuracy = np.mean(np.array(y_true) == np.array(y_pred)) if len(y_true) > 0 else 0.0
print(f"\nAccuracy global: {accuracy:.4f}")

# guardar resultados
cm_df.to_csv("matriz_confusion_codebook16_roger.csv", encoding="utf-8-sig")
pd.DataFrame(rows).to_csv("resultados_prueba_codebook16_roger.csv", index=False, encoding="utf-8-sig")

print("\nSe guardaron:")
print(" - matriz_confusion_codebook16.csv")
print(" - resultados_prueba_codebook16.csv")