import os
import cv2
import shutil

source_root = "data/train"
damaged_root = "damaged"

os.makedirs(damaged_root, exist_ok=True)

bad = 0

for label in os.listdir(source_root):

    src_folder = os.path.join(source_root, label)
    dst_folder = os.path.join(damaged_root, label)

    os.makedirs(dst_folder, exist_ok=True)

    for file in os.listdir(src_folder):

        src_path = os.path.join(src_folder, file)

        try:
            img = cv2.imread(src_path)

            if img is None:
                dst_path = os.path.join(dst_folder, file)
                shutil.move(src_path, dst_path)
                bad += 1

        except:
            dst_path = os.path.join(dst_folder, file)
            shutil.move(src_path, dst_path)
            bad += 1

print("Moved", bad, "damaged images to", damaged_root)