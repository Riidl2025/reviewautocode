import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import io
import subprocess
import os
import platform


# -----------------------------------------
# GET SOFFICE COMMAND (CROSS PLATFORM)
# -----------------------------------------
def get_soffice_command():
    system = platform.system()

    # 🔥 Windows (local machine)
    if system == "Windows":
        possible_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        raise Exception("LibreOffice not found on Windows. Please install it.")

    # 🔥 Linux / Render
    else:
        return "soffice"


# -----------------------------------------
# CONVERT PPT/PPTX → PDF
# -----------------------------------------
def convert_to_pdf(input_path: str) -> str:
    try:
        if input_path.lower().endswith(".pdf"):
            return input_path

        soffice_cmd = get_soffice_command()

        output_dir = os.path.dirname(input_path)

        subprocess.run([
            soffice_cmd,
            "--headless",
            "--convert-to",
            "pdf",
            input_path,
            "--outdir",
            output_dir
        ], check=True)

        pdf_path = os.path.splitext(input_path)[0] + ".pdf"

        if not os.path.exists(pdf_path):
            raise Exception("PDF not generated")

        return pdf_path

    except Exception as e:
        raise Exception(f"PPT to PDF conversion failed: {e}")


# -----------------------------------------
# TEXT EXTRACTION (PDF TEXT LAYER)
# -----------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    all_text = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    all_text.append(text.strip())
    except Exception as e:
        print("pdfplumber error:", e)

    return "\n".join(all_text)


# -----------------------------------------
# OCR FROM IMAGES INSIDE PDF
# -----------------------------------------
def extract_text_from_images(pdf_path: str) -> str:
    ocr_texts = []

    try:
        doc = fitz.open(pdf_path)

        for page_index in range(len(doc)):
            page = doc[page_index]
            images = page.get_images(full=True)

            for img in images:
                xref = img[0]
                base_image = doc.extract_image(xref)

                image_bytes = base_image["image"]

                try:
                    image = Image.open(io.BytesIO(image_bytes))
                    text = pytesseract.image_to_string(image)

                    if text and text.strip():
                        ocr_texts.append(text.strip())

                except Exception:
                    continue

    except Exception as e:
        print("OCR error:", e)

    return "\n".join(ocr_texts)


# -----------------------------------------
# MAIN PIPELINE (FINAL)
# -----------------------------------------
def extract_pdf_content(file_path: str) -> str:
    # Step 1: Convert PPT → PDF (if needed)
    pdf_path = convert_to_pdf(file_path)
    print("Converted to PDF:", pdf_path)

    # Step 2: Extract text layer
    slide_text = extract_text_from_pdf(pdf_path)

    # Step 3: OCR extraction
    image_text = extract_text_from_images(pdf_path)

    # Step 4: Combine cleanly
    combined_text = "\n\n".join(
        [text for text in [slide_text, image_text] if text]
    )

    # Step 5: Limit size for LLM
    if len(combined_text) > 15000:
        combined_text = combined_text[:15000]

    return combined_text