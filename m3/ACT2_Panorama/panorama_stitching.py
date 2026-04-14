import cv2
import numpy as np
import glob
import os
import matplotlib.pyplot as plt


def load_calibration(path="camera_calibration.npz"):
    data = np.load(path)
    return data["K"], data["dist"]


def undistort_image(img, K, dist):
    h, w = img.shape[:2]
    new_K, _ = cv2.getOptimalNewCameraMatrix(K, dist, (w, h), 1, (w, h))
    undistorted = cv2.undistort(img, K, dist, None, new_K)
    return undistorted


def detect_and_describe(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create()
    kps, desc = sift.detectAndCompute(gray, None)
    return kps, desc


def match_features(desc1, desc2, ratio=0.75):
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    knn_matches = matcher.knnMatch(desc1, desc2, k=2)

    good = []
    for pair in knn_matches:
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < ratio * n.distance:
            good.append(m)
    return good


def compute_homography(kps_ref, kps_new, matches):
    """
    Returns H such that:
        p_ref ~= H * p_new

    So this maps points from new image coordinates into reference image coordinates.
    """
    if len(matches) < 4:
        raise RuntimeError("Not enough matches to compute homography.")

    pts_ref = np.float32([kps_ref[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    pts_new = np.float32([kps_new[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(pts_new, pts_ref, cv2.RANSAC, 4.0)
    if H is None or not np.isfinite(H).all():
        raise RuntimeError("Homography estimation failed or returned invalid values.")

    return H, mask


def compute_pairwise_homographies(images):
    """
    Compute homographies only between consecutive ORIGINAL images.

    H_pair[i] maps image i -> image i-1
    """
    features = []
    for idx, img in enumerate(images):
        kps, desc = detect_and_describe(img)
        if desc is None or len(kps) < 4:
            raise RuntimeError(f"Could not extract enough descriptors from image {idx}.")
        features.append((kps, desc))

    H_pair = [np.eye(3, dtype=np.float64)]

    for i in range(1, len(images)):
        print(f"Computing homography between image {i-1} and image {i}...")

        kps_prev, desc_prev = features[i - 1]
        kps_curr, desc_curr = features[i]

        matches = match_features(desc_prev, desc_curr)
        print(f"Good matches: {len(matches)}")

        H, mask = compute_homography(kps_prev, kps_curr, matches)

        inliers = int(mask.sum()) if mask is not None else 0
        print(f"Inliers after RANSAC: {inliers}")

        H_pair.append(H)

    return H_pair


def accumulate_global_homographies(H_pair):
    """
    H_global[i] maps image i -> image 0 reference frame
    """
    H_global = [np.eye(3, dtype=np.float64)]

    for i in range(1, len(H_pair)):
        H_g = H_global[i - 1] @ H_pair[i]
        H_global.append(H_g)

    return H_global


def compute_output_canvas(images, H_global, max_canvas_dim=30000):
    """
    Compute the full canvas size needed to contain all warped images.
    Returns translation matrix T and canvas width/height.
    """
    all_corners = []

    for img, H in zip(images, H_global):
        h, w = img.shape[:2]
        corners = np.float32([
            [0, 0],
            [w, 0],
            [w, h],
            [0, h]
        ]).reshape(-1, 1, 2)

        warped_corners = cv2.perspectiveTransform(corners, H)
        all_corners.append(warped_corners)

    all_corners = np.concatenate(all_corners, axis=0)

    xmin, ymin = np.floor(all_corners.min(axis=0).ravel()).astype(np.int64)
    xmax, ymax = np.ceil(all_corners.max(axis=0).ravel()).astype(np.int64)

    tx = -xmin
    ty = -ymin

    output_w = int(xmax - xmin)
    output_h = int(ymax - ymin)

    if output_w <= 0 or output_h <= 0:
        raise RuntimeError("Invalid output canvas size.")

    if output_w > max_canvas_dim or output_h > max_canvas_dim:
        raise RuntimeError(
            f"Canvas too large: {output_w}x{output_h}. "
            "This usually means one homography went bad."
        )

    T = np.array([
        [1, 0, tx],
        [0, 1, ty],
        [0, 0, 1]
    ], dtype=np.float64)

    return T, output_w, output_h


def blend_images(images, H_global, T, output_w, output_h):
    """
    Warp all images into the common canvas and average them in overlap regions.
    """
    acc = np.zeros((output_h, output_w, 3), dtype=np.float64)
    weight = np.zeros((output_h, output_w), dtype=np.float64)

    for i, (img, H) in enumerate(zip(images, H_global)):
        print(f"Warping image {i} into global canvas...")

        H_total = T @ H
        warped = cv2.warpPerspective(img, H_total, (output_w, output_h))

        mask = np.any(warped > 0, axis=2).astype(np.float64)

        acc += warped.astype(np.float64)
        weight += mask

    weight[weight == 0] = 1.0
    panorama = (acc / weight[..., None]).astype(np.uint8)

    return panorama


def show_with_matplotlib(img_bgr, title="Image"):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    plt.figure(figsize=(16, 10))
    plt.imshow(img_rgb)
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.show()


def build_panorama(images):
    H_pair = compute_pairwise_homographies(images)
    H_global = accumulate_global_homographies(H_pair)
    T, output_w, output_h = compute_output_canvas(images, H_global)

    print(f"Final canvas size: {output_w} x {output_h}")

    panorama = blend_images(images, H_global, T, output_w, output_h)
    return panorama


if __name__ == "__main__":
    calibration_path = "m3/ACT2_Panorama/camera_calibration.npz"
    image_folder = "m3/ACT2_Panorama/dataset/panorama_frames2"

    K, dist = load_calibration(calibration_path)

    image_paths = sorted(glob.glob(os.path.join(image_folder, "*.jpg")))
    if len(image_paths) < 2:
        raise RuntimeError("Need at least 2 images.")

    images = []
    for p in image_paths:
        img = cv2.imread(p)
        if img is None:
            print(f"Warning: could not read {p}")
            continue

        und = undistort_image(img, K, dist)
        images.append(und)

    if len(images) < 2:
        raise RuntimeError("Not enough valid images to stitch.")

    panorama = build_panorama(images)

    output_path = "m3/ACT2_Panorama/panorama_result2.jpg"
    cv2.imwrite(output_path, panorama)
    print(f"Saved panorama to: {output_path}")

    # show_with_matplotlib(panorama, title="Panorama Result")