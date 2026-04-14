import cv2
import os

def extract_every_n_frames(video_path, output_folder, n):

    os.makedirs(output_folder, exist_ok=True)


    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Save every n-th frame
        if frame_count % n == 0:
            filename = os.path.join(output_folder, f"frame_{saved_count:05d}.jpg")
            cv2.imwrite(filename, frame)
            saved_count += 1

        frame_count += 1

    cap.release()
    print(f"Done. Saved {saved_count} frames.")

# Example usage
extract_every_n_frames("/home/roger/Github/rogertests2/m3/ACT2_Panorama/calibration_dataset/landscape.mp4", "/home/roger/Github/rogertests2/m3/ACT2_Panorama/calibration_dataset/panorama_frames/", n=15)