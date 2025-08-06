import os
import tkinter as tk
from tkinter import filedialog

SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

def get_images_from_directory(directory_path):
    """Get list of supported image files from directory."""
    if not os.path.exists(directory_path):
        return []
    
    image_files = []
    for filename in os.listdir(directory_path):
        if any(filename.lower().endswith(ext) for ext in SUPPORTED_IMAGE_EXTENSIONS):
            image_files.append(os.path.join(directory_path, filename))
    print(f"DEBUG: Found {len(image_files)} images in '{directory_path}'")
    return sorted(image_files)

def select_image_file():
    """Open file dialog to select an image."""
    try:
        root = tk.Tk()
        root.withdraw()  # Hide main window
        
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp"),
            ("JPEG files", "*.jpg *.jpeg"),
            ("PNG files", "*.png"),
            ("All files", "*.*")
        ]
        
        image_path = filedialog.askopenfilename(
            title="Select Background Image",
            filetypes=filetypes
        )
        root.destroy()
        
        return image_path if image_path else None
        
    except ImportError:
        print("Tkinter not available. Cannot open file dialog.")
        return None

def select_image_directory():
    """Open directory dialog to select folder with images."""
    try:
        root = tk.Tk()
        root.withdraw()  # Hide main window
        
        directory_path = filedialog.askdirectory(title="Select Image Directory")
        root.destroy()
        
        return directory_path if directory_path else None
        
    except ImportError:
        print("Tkinter not available. Cannot open directory dialog.")
        return None 