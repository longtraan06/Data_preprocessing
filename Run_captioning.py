import os
import sys
import captioning

# Check if folder path is provided
if len(sys.argv) < 2:
    print("Error: Missing folder path")
    print("Usage: python3 captioning_script.py /path/to/folder")
    sys.exit(1)

# Get root folder path from command-line argument
root_folder = sys.argv[1]

# Verify that root folder exists and is a directory
if not os.path.isdir(root_folder):
    print(f"Error: Directory does not exist or is not a directory: {root_folder}")
    sys.exit(1)

# Load captioning model
device, model, processor = captioning.load_model()

# Iterate through each subfolder in root folder
for subdir in os.listdir(root_folder):
    subdir_path = os.path.join(root_folder, subdir)
    if not os.path.isdir(subdir_path):
        continue

    # Preferred image: angle_middle_10.jpg in rendered_images
    preferred_image = os.path.join(subdir_path, 'rendered_images', 'angle_middle_10.jpg')
    image_path = None

    if os.path.exists(preferred_image):
        image_path = preferred_image
    else:
        # Fallback: find the first .jpg file in the subfolder
        for file in os.listdir(subdir_path):
            if file.lower().endswith('.jpg'):
                image_path = os.path.join(subdir_path, file)
                print(f"Using fallback image for {subdir}: {image_path}")
                break

    if image_path:
        try:
            caption = captioning.main(image_path, device, model, processor)
            caption_file = os.path.join(subdir_path, 'caption.txt')
            with open(caption_file, 'w') as f:
                f.write(caption)
            print(f"Caption saved at: {caption_file}")
        except Exception as e:
            print(f"Error generating caption for {image_path}: {str(e)}")
    else:
        print(f"No image found for {subdir}")
