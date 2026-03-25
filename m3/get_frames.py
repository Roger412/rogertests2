import os

def keep_every_n_images(folder_path, n):
    files = sorted([
        f for f in os.listdir(folder_path)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ])

    for i, filename in enumerate(files):
        if i % n != 0:
            filepath = os.path.join(folder_path, filename)
            os.remove(filepath)

    print(f"Done. Kept 1 every {n} images.")

# Example
keep_every_n_images("frames", 3)