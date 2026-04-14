import cv2
import numpy as np
import glob
import os
import matplotlib.pyplot as plt

CHESSBOARD_SIZE = (7, 5)   # number of inner corners per row and column
SQUARE_SIZE = 0.003        # square size in meters

def calibrate_from_folder(images_folder):
    # Prepare 3D object points for the checkerboard
    objp = np.zeros((CHESSBOARD_SIZE[0] * CHESSBOARD_SIZE[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:CHESSBOARD_SIZE[0], 0:CHESSBOARD_SIZE[1]].T.reshape(-1, 2)
    objp *= SQUARE_SIZE

    objpoints = []   # 3D points in real world space
    imgpoints = []   # 2D points in image plane

    image_paths = sorted(glob.glob(os.path.join(images_folder, "*.jpg")))
    if not image_paths:
        raise RuntimeError(f"No calibration images found in: {images_folder}")

    image_size = None
    valid_count = 0

    # Enable interactive plotting
    plt.ion()
    fig = plt.figure("Checkerboard Detection")

    for path in image_paths:
        img = cv2.imread(path)
        if img is None:
            print(f"[FAIL] Could not read image: {path}")
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        ret, corners = cv2.findChessboardCorners(gray, CHESSBOARD_SIZE, None)

        if ret:
            criteria = (
                cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                30,
                0.001
            )
            corners_subpix = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

            objpoints.append(objp)
            imgpoints.append(corners_subpix)
            image_size = gray.shape[::-1]
            valid_count += 1

            print(f"[OK] Corners detected: {path}")

            # Draw and show corners with matplotlib
            vis = img.copy()
            cv2.drawChessboardCorners(vis, CHESSBOARD_SIZE, corners_subpix, ret)
            vis_rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)

            plt.clf()
            plt.imshow(vis_rgb)
            plt.title(f"Detected corners ({valid_count})")
            plt.axis("off")
            plt.pause(0.2)

        else:
            print(f"[FAIL] Corners not detected: {path}")

    plt.ioff()
    plt.close(fig)

    print(f"\nValid calibration images: {valid_count}/{len(image_paths)}")

    if len(objpoints) < 8:
        raise RuntimeError("Not enough valid calibration images. Take more chessboard photos.")

    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, image_size, None, None
    )

    print("\nRMS reprojection error:", ret)
    print("K:\n", K)
    print("dist:\n", dist)

    np.savez("camera_calibration.npz", K=K, dist=dist)
    print("\nSaved calibration to camera_calibration.npz")

if __name__ == "__main__":
    calibrate_from_folder("m3/ACT2_Panorama/calibration_dataset/frames")