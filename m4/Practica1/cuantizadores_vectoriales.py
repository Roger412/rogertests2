from pathlib import Path
import numpy as np
import soundfile as sf
import pickle

# ==========================================
# CONFIGURACIÓN
# ==========================================
frame_length = 320
hop_length = 128
lpc_order = 12
preemphasis = 0.95
codebook_size = 64
train_count = 10

dataset_root = Path("C:\\Users\\joser\\OneDrive\\Documentos\\GitHub\\rogertests2\\rogertests2\\m4\\Practica1\\dataset_recortado")


# ==========================================
# PREPROCESAMIENTO
# ==========================================
def pre_emphasis(signal, a=0.95): # preénfasis clásico
    y = np.empty_like(signal)
    y[0] = signal[0]
    y[1:] = signal[1:] - a * signal[:-1]
    return y


def frame_signal(signal, frame_length=320, hop_length=128): # ventana de hamming
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
    """
    Devuelve:
      w = [1, w1, w2, ..., wp]
      e = error final de predicción
    """
    w = np.zeros(order + 1) 
    e = r[0] # energía del marco (r[0] es la autocorrelación en lag 0, que representa la energía total del marco)
    w[0] = 1.0

    if e <= 1e-12: # Si la energía es muy baja, no se pueden calcular coeficientes LPC válidos
        return w, 1e-12

    for i in range(1, order + 1): # Para cada orden de predicción desde 1 hasta el orden deseado
        acc = r[i]
        for j in range(1, i):
            acc += w[j] * r[i - j]

        k = -acc / e # El coeficiente de reflexión para el orden actual se calcula como la relación entre la suma acumulada (acc) y el error de predicción (e). El signo negativo se debe a la convención utilizada en la formulación de Levinson-Durbin.
        w_prev = w.copy()
        w[i] = k

        for j in range(1, i):
            w[j] = w_prev[j] + k * w_prev[i - j] # Los coeficientes LPC para los órdenes anteriores se actualizan utilizando el coeficiente de reflexión k y los coeficientes LPC previos

        e = e * (1.0 - k * k) # El error de predicción se actualiza multiplicándolo por (1 - k^2)
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
            s += A_asc[j] * A_asc[j + i] # La correlación corta para el lag i se calcula sumando el producto de los coeficientes LPC A_asc[j] y A_asc[j + i] para j desde 0 hasta p - i
        ra[i] = s

    return ra


# ==========================================
# DISTANCIA ITAKURA-SAITO
# ==========================================
def itakura_saito_distance_from_correlations(r_i, w_centroid, sigma2=1.0):
    ra = short_correlation_from_lpc(w_centroid)
    return (1.0 / sigma2) * (r_i[0] * ra[0] + 2.0 * np.dot(r_i[1:], ra[1:])) # D = (1/σ²) * (r_i[0] * ra[0] + 2 * sum(r_i[k] * ra[k] for k in 1..p)) donde r_i es el vector de autocorrelación del marco actual y ra es la correlación corta del polinomio LPC del centroide


# ==========================================
# UTILIDAD: ORDENAR Y SEPARAR LSF
# ==========================================
def enforce_lsf_spacing(lsf, min_sep=0.02):
    lsf = np.sort(np.clip(lsf, 1e-3, np.pi - 1e-3)).copy() # Asegura que los LSF estén ordenados y dentro del rango (0, π)

    for i in range(1, len(lsf)):
        if lsf[i] <= lsf[i - 1] + min_sep: # Si el LSF actual está demasiado cerca del anterior, se ajusta para mantener la separación mínima
            lsf[i] = lsf[i - 1] + min_sep # Esto garantiza que cada LSF esté al menos min_sep radianes por encima del anterior

    if lsf[-1] >= np.pi - 1e-3: # Si el último LSF está demasiado cerca de π, se ajusta para mantener la separación mínima desde el final
        lsf[-1] = np.pi - 1e-3
        for i in range(len(lsf) - 2, -1, -1):
            if lsf[i] >= lsf[i + 1] - min_sep:
                lsf[i] = lsf[i + 1] - min_sep

    return lsf


# ==========================================
# LPC -> LSF
# ==========================================
def lpc_to_lsf_from_levinson(w):
    """
    Convierte w=[1,w1,...,wp] a LSF
    """
    w = np.asarray(w, dtype=np.float64)
    p = len(w) - 1

    if p % 2 != 0:
        raise ValueError("El orden LPC debe ser par.")

    A_asc = w.copy() # A(z) = 1 - w1*z^-1 - w2*z^-2 - ... - wp*z^-p se representa como A_asc = [1, -w1, -w2, ..., -wp]
    A_flip = np.r_[0.0, A_asc[::-1]] # A(z^-1) = 1 - w1*z - w2*z^2 - ... - wp*z^p se representa como A_flip = [0, -wp, -w(p-1), ..., -w1]
    A_pad = np.r_[A_asc, 0.0] 

    P_asc = A_pad + A_flip # P(z) = A(z) + A(z^-1) se representa como P_asc = [1, -w1, -w2, ..., -wp, 0] + [0, -wp, -w(p-1), ..., -w1, 0]
    Q_asc = A_pad - A_flip # Q(z) = A(z) - A(z^-1) se representa como Q_asc = [1, -w1, -w2, ..., -wp, 0] - [0, -wp, -w(p-1), ..., -w1, 0]

    P_desc = P_asc[::-1] # Para usar np.roots, los coeficientes deben estar en orden descendente, por lo que se invierte el orden de P_asc y Q_asc
    Q_desc = Q_asc[::-1]

    roots_P = np.roots(P_desc) # Obtenemos las raices de P(z) y Q(z)
    roots_Q = np.roots(Q_desc)

    roots_P = roots_P[np.abs(roots_P + 1) > 1e-3] # Filtramos las raíces de P(z) que están demasiado cerca de -1, ya que estas no corresponden a LSF válidos
    roots_Q = roots_Q[np.abs(roots_Q - 1) > 1e-3] # Filtramos las raíces de Q(z) que están demasiado cerca de 1, ya que estas no corresponden a LSF válidos

    roots_P = roots_P[np.abs(np.abs(roots_P) - 1.0) < 1.5e-1] # Filtramos las raíces de P(z) que no están lo suficientemente cerca del círculo unitario, ya que solo las raíces cercanas al círculo unitario corresponden a LSF válidos
    roots_Q = roots_Q[np.abs(np.abs(roots_Q) - 1.0) < 1.5e-1] 

    ang_P = np.angle(roots_P) # Calculamos los ángulos de las raíces filtradas de P(z) y Q(z), que corresponden a los LSF en radianes
    ang_Q = np.angle(roots_Q)

    ang_P = np.sort(ang_P[(ang_P > 0) & (ang_P < np.pi)]) # Filtramos los ángulos de P(z) para quedarnos solo con aquellos que están en el rango (0, π), ya que los LSF deben estar en este rango
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
# EXTRACCIÓN DE VECTORES DE ENTRENAMIENTO
# ==========================================
def extract_training_vectors_from_word(word_dir, train_count=10):
    """
    Regresa:
      lsf_vectors: [N, 12]
      r_vectors:   [N, 13]
      w_vectors:   [N, 13]
    """
    wav_files = sorted(word_dir.glob("*.wav"))[:train_count]
    window = np.hamming(frame_length)

    lsf_vectors = []
    r_vectors = []
    w_vectors = []

    total_frames = 0
    low_energy_frames = 0
    lsf_fail_frames = 0
    ok_frames = 0

    for wav_file in wav_files:
        signal, fs = sf.read(wav_file)

        if signal.ndim > 1:
            signal = np.mean(signal, axis=1)

        signal = pre_emphasis(signal, preemphasis)
        frames = frame_signal(signal, frame_length, hop_length)

        print(f"{wav_file.name}: muestras={len(signal)}, frames={len(frames)}")

        if len(frames) == 0:
            continue

        windowed = frames * np.hamming(frame_length)
        frame_energies = np.sum(windowed ** 2, axis=1)

        if len(frame_energies) == 0:
            continue

        energy_threshold = 0.05 * np.max(frame_energies)

        for frame, e_frame in zip(frames, frame_energies):
            total_frames += 1

            if e_frame < energy_threshold:
                low_energy_frames += 1
                continue

            xw = frame * np.hamming(frame_length)
            r = autocorrelation(xw, lpc_order)

            if r[0] <= 1e-10:
                low_energy_frames += 1
                continue

            w, err = levinson_durbin(r, lpc_order)

            try:
                lsf = lpc_to_lsf_from_levinson(w)
                lsf_vectors.append(lsf)
                r_vectors.append(r)
                w_vectors.append(w)
                ok_frames += 1
            except Exception:
                lsf_fail_frames += 1
                continue

    print("Resumen extracción:")
    print("  total_frames      =", total_frames)
    print("  low_energy_frames =", low_energy_frames)
    print("  lsf_fail_frames   =", lsf_fail_frames)
    print("  ok_frames         =", ok_frames)

    return np.array(lsf_vectors), np.array(r_vectors), np.array(w_vectors)


# ==========================================
# CENTROIDE LSF a LPC VÁLIDO
# usando el vector real más cercano
# ==========================================
def nearest_valid_w_for_centroid(centroid_lsf, X_lsf, X_w):
    dists = np.linalg.norm(X_lsf - centroid_lsf, axis=1)
    idx = np.argmin(dists)
    return X_w[idx]


# ==========================================
# LBG EN LSF + ASIGNACIÓN ITAKURA-SAITO
# ==========================================
def initialize_codebook_lsf(X_lsf):
    c1 = np.mean(X_lsf, axis=0)
    return np.array([enforce_lsf_spacing(c1)])


def split_codebook(codebook, delta=0.005):
    new_codebook = []
    for c in codebook:
        c1 = enforce_lsf_spacing(c - delta)
        c2 = enforce_lsf_spacing(c + delta)
        new_codebook.append(c1)
        new_codebook.append(c2)
    return np.array(new_codebook)


def train_codebook_lbg_is(X_lsf, X_r, X_w, codebook_size=16, max_iter=60, tol=1e-4):
    if len(X_lsf) == 0:
        raise ValueError("No hay vectores para entrenar.")

    codebook = initialize_codebook_lsf(X_lsf)

    while len(codebook) < codebook_size:
        codebook = split_codebook(codebook)

        if len(codebook) > codebook_size:
            codebook = codebook[:codebook_size]

        prev_global_dist = np.inf

        for _ in range(max_iter):
            # usar como LPC del centroide el vector real más cercano al centroide LSF
            centroid_w = np.array([
                nearest_valid_w_for_centroid(c, X_lsf, X_w) for c in codebook
            ])

            clusters = [[] for _ in range(len(codebook))]
            total_dist = 0.0

            for x_lsf, r_i in zip(X_lsf, X_r):
                dists = []
                for w_c in centroid_w:
                    d = itakura_saito_distance_from_correlations(r_i, w_c, sigma2=1.0)
                    dists.append(d)

                dists = np.array(dists)
                idx = np.argmin(dists)

                clusters[idx].append(x_lsf)
                total_dist += dists[idx]

            mean_dist = total_dist / len(X_lsf)

            new_codebook = []
            for i, cluster in enumerate(clusters):
                if len(cluster) == 0:
                    new_codebook.append(codebook[i])
                else:
                    c = np.mean(np.vstack(cluster), axis=0)
                    c = enforce_lsf_spacing(c)
                    new_codebook.append(c)

            new_codebook = np.array(new_codebook)

            if np.abs(prev_global_dist - mean_dist) < tol:
                codebook = new_codebook
                break

            codebook = new_codebook
            prev_global_dist = mean_dist

    final_centroid_w = np.array([
        nearest_valid_w_for_centroid(c, X_lsf, X_w) for c in codebook
    ])

    return codebook, final_centroid_w


# ==========================================
# ENTRENAMIENTO DE CODEBOOKS
# ==========================================
codebooks_lsf = {}
codebooks_w = {}

for word_dir in sorted(dataset_root.iterdir()):
    if not word_dir.is_dir():
        continue

    word = word_dir.name
    print("=" * 60)
    print(f"Palabra: {word}")

    X_lsf, X_r, X_w = extract_training_vectors_from_word(word_dir, train_count=train_count)

    print(f"Vectores LSF extraídos: {X_lsf.shape}")
    print(f"Vectores r extraídos: {X_r.shape}")
    print(f"Vectores w extraídos: {X_w.shape}")

    if len(X_lsf) < codebook_size:
        print(f"Advertencia: {word} solo tiene {len(X_lsf)} vectores válidos; no alcanza para codebook de {codebook_size}. Se omite.")
        continue

    cb_lsf, cb_w = train_codebook_lbg_is(
        X_lsf,
        X_r,
        X_w,
        codebook_size=codebook_size,
        max_iter=60,
        tol=1e-4
    )

    codebooks_lsf[word] = cb_lsf
    codebooks_w[word] = cb_w

    print(f"Codebook LSF de {word}: {cb_lsf.shape}")
    print(f"Codebook W de {word}: {cb_w.shape}")


# ==========================================
# GUARDAR RESULTADOS
# ==========================================
lsf_filename = f"codebooks_{codebook_size}_lsf_roger.pkl"
w_filename = f"codebooks_{codebook_size}_w_roger.pkl"

with open(lsf_filename, "wb") as f:
    pickle.dump(codebooks_lsf, f)

with open(w_filename, "wb") as f:
    pickle.dump(codebooks_w, f)

print("=" * 60)
print("Se guardaron:")
print(f" - {lsf_filename}")
print(f" - {w_filename}")