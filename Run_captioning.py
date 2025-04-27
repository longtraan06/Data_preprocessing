import os
import captioning
import sys

if len(sys.argv) < 2:
    print("Lỗi: Không cung cấp đường dẫn thư mục.")
    print("Cách dùng: python3 captioning_script.py /path/to/folder")
    sys.exit(1)

# Thư mục gốc chứa các object
root_folder = sys.argv[1]

# Load model
device, model, processor = captioning.load_model()

# Duyệt qua từng thư mục object
for subdir in os.listdir(root_folder):
    subdir_path = os.path.join(root_folder, subdir)
    if not os.path.isdir(subdir_path):
        continue

    # Ảnh ưu tiên: goc_middle_10.jpg trong rendered_images
    preferred_image = os.path.join(subdir_path, 'rendered_images', 'angle_middle_10.jpg')
    image_path = None

    if os.path.exists(preferred_image):
        image_path = preferred_image
    else:
        # Fallback: tìm ảnh .jpg đầu tiên trong thư mục
        for file in os.listdir(subdir_path):
            if file.lower().endswith('.jpg'):
                image_path = os.path.join(subdir_path, file)
                print(f"Dùng ảnh fallback cho {subdir}: {image_path}")
                break

    if image_path:
        try:
            caption = captioning.main(image_path, device, model, processor)
            caption_file = os.path.join(subdir_path, 'caption.txt')
            with open(caption_file, 'w') as f:
                f.write(caption)
            print(f" Đã lưu caption tại: {caption_file}")
        except Exception as e:
            print(f" Lỗi caption cho {image_path}: {str(e)}")
    else:
        print(f" Không tìm được ảnh nào cho {subdir}")
