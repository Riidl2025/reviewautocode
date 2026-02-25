import os
import tempfile
import shutil
import subprocess
import time

from dotenv import load_dotenv

from dynamo_helper import (
    fetch_one_submitted_startup,
    update_startup_status,
    store_screening_result
)

from s3_helper import download_file_from_url
from unified_scorer import evaluate_startup

load_dotenv()


# -----------------------------
# LIBREOFFICE SETUP
# -----------------------------
SOFFICE_PATH = shutil.which("soffice")

if SOFFICE_PATH is None:
    possible_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
    if os.path.exists(possible_path):
        SOFFICE_PATH = possible_path

if SOFFICE_PATH is None:
    raise RuntimeError("LibreOffice not found.")


# -----------------------------
# PPT → PDF
# -----------------------------
def convert_to_pdf(input_path):
    output_dir = tempfile.mkdtemp()

    subprocess.run([
        SOFFICE_PATH,
        "--headless",
        "--convert-to", "pdf",
        input_path,
        "--outdir", output_dir
    ], check=True)

    for file in os.listdir(output_dir):
        if file.endswith(".pdf"):
            return os.path.join(output_dir, file)

    raise Exception("PDF conversion failed")


# -----------------------------
# CLEANUP
# -----------------------------
def cleanup_files(*paths):
    for path in paths:
        try:
            if path and os.path.exists(path):
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
        except Exception as e:
            print("Cleanup error:", e)


# -----------------------------
# MAIN WORKER
# -----------------------------
def run_worker():
    print("🚀 Worker started...")

    startup = fetch_one_submitted_startup()

    if not startup:
        print("No startups to process.")
        return

    startup_id = startup["id"]

    ppt_path = None
    pdf_path = None

    try:
        print("Processing:", startup_id)

        update_startup_status(startup_id, "processing")

        # Download
        ppt_path = download_file_from_url(startup["pitchDeckUrl"])

        # Convert
        pdf_path = convert_to_pdf(ppt_path)

        # Evaluate
        result = evaluate_startup(pdf_path)

        print("📊 Final Result:", result)

        # Store
        store_screening_result(startup, result)

        update_startup_status(startup_id, "analyzed")

        print("✅ Done:", startup_id)

    except Exception as e:
        print("❌ Worker error:", e)
        update_startup_status(startup_id, "failed")

    finally:
        cleanup_files(ppt_path, pdf_path)


# -----------------------------
# ENTRY
# -----------------------------


if __name__ == "__main__":
    run_worker()