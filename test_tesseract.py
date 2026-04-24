"""
Test Tesseract OCR directly on an image file
"""

import pytesseract
from PIL import Image
import os

# Set Tesseract path
pytesseract.pytesseract.pytesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

print("Testing Tesseract OCR on image files...")
print(f"Tesseract path set to: {pytesseract.pytesseract.pytesseract_cmd}")
print(f"Path exists: {os.path.exists(pytesseract.pytesseract.pytesseract_cmd)}")

# Look for image files in the current directory
image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']
image_files = []

for file in os.listdir('.'):
    if any(file.lower().endswith(ext) for ext in image_extensions):
        image_files.append(file)

if not image_files:
    print("\n❌ No image files found in current directory")
    print("Please place a PNG or JPG image in this directory and run again")
else:
    print(f"\n✓ Found {len(image_files)} image file(s): {image_files}\n")

    for image_file in image_files:
        try:
            print(f"Processing: {image_file}")
            image = Image.open(image_file)
            print(f"  Image size: {image.size}")
            print(f"  Image mode: {image.mode}")

            # Run OCR
            text = pytesseract.image_to_string(image)

            if text.strip():
                print(f"  ✅ Text extracted ({len(text)} chars):")
                print(f"  {text[:200]}...\n")
            else:
                print(f"  ⚠ No text found in image\n")

        except Exception as e:
            print(f"  ❌ Error: {str(e)}\n")


