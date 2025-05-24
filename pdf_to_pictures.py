import os
from pathlib import Path
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError
# 确保 Pillow 也安装了 (通常是 pdf2image 的依赖): pip install Pillow

# --- Configuration ---
# 1. SET YOUR PDF FILENAME HERE:
pdf_filename = "marxism_theory.pdf"  # IMPORTANT: Change this to your PDF file's name

# 2. (Optional) FOR WINDOWS or if Poppler is not in PATH:
#    Uncomment the line below and set the correct path to your Poppler 'bin' directory.
#    Use 'r' before the string for raw path handling on Windows.
# poppler_bin_path = r"C:\path\to\your\poppler-x.x.x\bin"
poppler_bin_path = None  # Set to None if Poppler is in system PATH or on Linux/macOS with standard install

# --- Script Logic ---

output_dir_name = "marxism_theory_images"  # Directory to save the images

try:
    # Get the absolute path of the directory where this script is located
    script_dir = Path(__file__).parent.resolve()

    # Construct the full paths
    pdf_path = script_dir / pdf_filename
    output_dir_path = script_dir / output_dir_name

    print(f"Script directory: {script_dir}")
    print(f"Looking for PDF: {pdf_path}")
    print(f"Output directory: {output_dir_path}")

    # Check if the PDF file exists
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Input PDF file not found at: '{pdf_path}'")

    # Create the output directory if it doesn't exist
    output_dir_path.mkdir(parents=True, exist_ok=True)
    print(f"Ensured output directory exists.")

    # --- MODIFIED PART START ---

    print(f"\nStarting conversion of '{pdf_filename}' to images in memory...")

    # Convert PDF pages to a list of PIL Image objects
    # REMOVED: output_folder, output_file, paths_only
    images = convert_from_path(
        pdf_path=pdf_path,
        fmt='jpeg',               # Still specify desired format for internal conversion if needed
        poppler_path=poppler_bin_path
        # dpi=300               # Uncomment to set resolution (dots per inch)
    )

    print(f"Conversion complete. Saving {len(images)} images...")

    # Iterate through the images and save them with custom filenames
    for i, image in enumerate(images):
        # Create filename like 'page_0001.jpg', 'page_0002.jpg', etc.
        # Page number starts from 1, so use i + 1
        # .zfill(4) ensures the number is padded with leading zeros to 4 digits
        page_num_str = str(i + 1).zfill(4)
        output_filename = f"page_{page_num_str}.jpg"
        output_filepath = output_dir_path / output_filename

        # Save the image object to the constructed path
        # Specify format as 'JPEG' for saving
        image.save(output_filepath, 'JPEG')

    print(f"\nSuccessfully saved {len(images)} JPG images.")
    print(f"Images saved in: '{output_dir_path}'")

    # --- MODIFIED PART END ---

except PDFInfoNotInstalledError:
    print("\n--- ERROR ---")
    print("Poppler not found or not in PATH. `pdf2image` requires Poppler.")
    print("Please install Poppler for your OS:")
    print("  - macOS: brew install poppler")
    print("  - Debian/Ubuntu: sudo apt-get install poppler-utils")
    print("  - Windows: Download Poppler, extract it, and either add its 'bin' directory to PATH")
    print("             OR set the 'poppler_bin_path' variable in this script.")
    print("-------------")
except (PDFPageCountError, PDFSyntaxError) as e:
    print(f"\n--- ERROR ---")
    print(f"Failed to process '{pdf_filename}'. It might be corrupted, password-protected, or not a valid PDF.")
    print(f"Details: {e}")
    print("-------------")
except FileNotFoundError as e:
     print(f"\n--- ERROR ---")
     print(e)
     print("Make sure the PDF file name in the script is correct and the file is in the same directory.")
     print("-------------")
except Exception as e:
    print(f"\n--- An unexpected error occurred ---")
    print(e)
    print("-------------")