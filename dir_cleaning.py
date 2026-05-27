import os
import shutil

DOWNLOADS_DIR = 'C:/Users/maxim/Downloads'
# This script cleans your downloads directory

# You can add any file types you need
FILE_TYPES = {
    'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
    'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz'],
    'Documents': ['.pdf', '.docx', '.doc', '.txt', '.xlsx', '.pptx'],
    'Scripts and Code': ['.py', '.lua', '.json', '.html', '.css', '.js'],
    'Music and Audio': ['.mp3', '.wav', '.flac', '.ogg'],
    'Videos': ['.mp4', '.avi', '.mkv', '.mov']
}

def clean_downloads():
    # Check if the specified directory exists
    if not os.path.exists(DOWNLOADS_DIR):
        print(f"Error: Path '{DOWNLOADS_DIR}' not found. Please check the username.")
        return

    print("Scanning downloads directory...")
    moved_count = 0

    # Iterate through all items in the folder
    for item in os.listdir(DOWNLOADS_DIR):
        item_path = os.path.join(DOWNLOADS_DIR, item)

        # We only process files; folders are left untouched to preserve their inner structure
        if os.path.isfile(item_path):
            # Get the file extension in lowercase (e.g., '.PNG' -> '.png')
            _, file_extension = os.path.splitext(item)
            file_extension = file_extension.lower()

            # Find the matching category for the extension
            folder_name = 'Other'  # Default folder if the extension is unknown
            for category, extensions in FILE_TYPES.items():
                if file_extension in extensions:
                    folder_name = category
                    break

            # Create the target folder if it doesn't exist yet
            target_folder = os.path.join(DOWNLOADS_DIR, folder_name)
            if not os.path.exists(target_folder):
                os.makedirs(target_folder)

            # Move the file
            try:
                shutil.move(item_path, os.path.join(target_folder, item))
                print(f"Moved: {item} -> {folder_name}")
                moved_count += 1
            except Exception as e:
                print(f"Failed to move {item}. Error: {e}")

    print(f"\nCleanup complete! Total files moved: {moved_count}")

if __name__ == '__main__':
    clean_downloads()
