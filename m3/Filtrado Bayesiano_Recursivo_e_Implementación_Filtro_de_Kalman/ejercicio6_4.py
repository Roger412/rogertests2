import numpy as np
import matplotlib.pyplot as plt

# -------------------------
# Model parameters
# -------------------------
omega = 1 / 2
qc = 0.01
R = np.array([[0.1]])

c = np.cos(omega)
s = np.sin(omega)

A = np.array([
    [c, s / omega],
    [-omega * s, c]
])

H = np.array([[1.0, 0.0]])

Q = np.array([
    [
        qc * (omega - c * s) / (2 * omega**3),
        qc * s**2 / (2 * omega**2)
    ],
    [
        qc * s**2 / (2 * omega**2),
        qc * (omega + c * s) / (2 * omega)
    ]
])

# -------------------------
# Simulation
# -------------------------
rng = np.random.default_rng(42)

N = 500
x_true = np.zeros((N, 2))
y = np.zeros(N)

x_true[0] = np.array([0.0, 1.0])
y[0] = (H @ x_true[0])[0] + rng.normal(0, np.sqrt(R[0, 0]))

for k in range(1, N):
    process_noise = rng.multivariate_normal(np.zeros(2), Q)
    x_true[k] = A @ x_true[k - 1] + process_noise
    y[k] = (H @ x_true[k])[0] + rng.normal(0, np.sqrt(R[0, 0]))

# -------------------------
# Baseline solution
# -------------------------
x_base = np.zeros_like(x_true)
x_base[:, 0] = y

dy = np.r_[0, np.diff(y)]
window = 5
kernel = np.ones(window) / window
x_base[:, 1] = np.convolve(dy, kernel, mode="same")

# -------------------------
# Kalman Filter
# -------------------------
def kalman_filter(y, A, H, Q, R, m0=None, P0=None):
    y = np.asarray(y).reshape(-1)

    n = A.shape[0]
    N = len(y)

    m = np.zeros(n) if m0 is None else m0.copy()
    P = np.eye(n) if P0 is None else P0.copy()

    I = np.eye(n)

    x_est = np.zeros((N, n))
    P_est = np.zeros((N, n, n))

    for k in range(N):
        # Prediction
        if k > 0:
            m = A @ m
            P = A @ P @ A.T + Q

        # Correction
        innovation = np.array([y[k]]) - H @ m
        S = H @ P @ H.T + R
        K = P @ H.T @ np.linalg.inv(S)

        m = m + (K @ innovation).ravel()

        # Stable covariance update
        P = (I - K @ H) @ P @ (I - K @ H).T + K @ R @ K.T

        x_est[k] = m
        P_est[k] = P

    return x_est, P_est

x_kf, P_kf = kalman_filter(y, A, H, Q, R)

# -------------------------
# Error comparison
# -------------------------
error_base_x1 = x_base[:, 0] - x_true[:, 0]
error_kf_x1 = x_kf[:, 0] - x_true[:, 0]

error_base_x2 = x_base[:, 1] - x_true[:, 1]
error_kf_x2 = x_kf[:, 1] - x_true[:, 1]

rmse_base_x1 = np.sqrt(np.mean(error_base_x1**2))
rmse_kf_x1 = np.sqrt(np.mean(error_kf_x1**2))

rmse_base_x2 = np.sqrt(np.mean(error_base_x2**2))
rmse_kf_x2 = np.sqrt(np.mean(error_kf_x2**2))

print("RMSE x1 Baseline:", rmse_base_x1)
print("RMSE x1 Kalman:  ", rmse_kf_x1)
print()
print("RMSE x2 Baseline:", rmse_base_x2)
print("RMSE x2 Kalman:  ", rmse_kf_x2)

# -------------------------
# Plots
# -------------------------
t = np.arange(N)

# x1 comparison
plt.figure(figsize=(12, 5))
plt.plot(t, x_true[:, 0], label="True x1")
plt.plot(t, y, ".", markersize=2, label="Measurement y")
plt.plot(t, x_base[:, 0], label="Baseline x1")
plt.plot(t, x_kf[:, 0], label="Kalman x1")
plt.xlabel("k")
plt.ylabel("x1")
plt.title("Comparison of x1")
plt.legend()
plt.grid(True)
plt.show()

# x2 comparison
plt.figure(figsize=(12, 5))
plt.plot(t, x_true[:, 1], label="True x2")
plt.plot(t, x_base[:, 1], label="Baseline x2")
plt.plot(t, x_kf[:, 1], label="Kalman x2")
plt.xlabel("k")
plt.ylabel("x2")
plt.title("Comparison of x2")
plt.legend()
plt.grid(True)
plt.show()

# Error x1
plt.figure(figsize=(12, 5))
plt.plot(t, error_base_x1, label=f"Baseline error x1, RMSE={rmse_base_x1:.4f}")
plt.plot(t, error_kf_x1, label=f"Kalman error x1, RMSE={rmse_kf_x1:.4f}")
plt.axhline(0, linestyle="--")
plt.xlabel("k")
plt.ylabel("Error")
plt.title("Error comparison for x1")
plt.legend()
plt.grid(True)
plt.show()

# Error x2
plt.figure(figsize=(12, 5))
plt.plot(t, error_base_x2, label=f"Baseline error x2, RMSE={rmse_base_x2:.4f}")
plt.plot(t, error_kf_x2, label=f"Kalman error x2, RMSE={rmse_kf_x2:.4f}")
plt.axhline(0, linestyle="--")
plt.xlabel("k")
plt.ylabel("Error")
plt.title("Error comparison for x2")
plt.legend()
plt.grid(True)
plt.show()

# Bar plot RMSE
labels = ["x1 Baseline", "x1 Kalman", "x2 Baseline", "x2 Kalman"]
values = [rmse_base_x1, rmse_kf_x1, rmse_base_x2, rmse_kf_x2]

plt.figure(figsize=(8, 5))
plt.bar(labels, values)
plt.ylabel("RMSE")
plt.title("RMSE comparison: Baseline vs Kalman")
plt.grid(axis="y")
plt.show()