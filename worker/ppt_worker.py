import os
import time
import tempfile
import shutil
import subprocess

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
# CONFIG
# -----------------------------
IDLE_SLEEP = 60       # when no entries
ACTIVE_SLEEP = 5      # between processing entries
ERROR_SLEEP = 10      # if error occurs


# -----------------------------
# LIBREOFFICE PATH
# -----------------------------
SOFFICE_PATH = shutil.which("soffice")

if SOFFICE_PATH is None:
    possible_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
    if os.path.exists(possible_path):
        SOFFICE_PATH = possible_path

if SOFFICE_PATH is None:
    raise RuntimeError("LibreOffice not found.")


# -----------------------------
# CONVERT PPT → PDF
# -----------------------------
def convert_to_pdf(input_path):
    output_dir = tempfile.mkdtemp()

    try:
        subprocess.run(
            [
                SOFFICE_PATH,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                output_dir,
                input_path,
            ],
            check=True,
        )

        filename = os.path.splitext(os.path.basename(input_path))[0] + ".pdf"
        return os.path.join(output_dir, filename)

    except Exception as e:
        raise Exception(f"PPT → PDF conversion failed: {e}")


# -----------------------------
# PROCESS ONE STARTUP
# -----------------------------
def process_startup(startup):
    startup_id = startup["id"]

    try:
        print(f"\n🚀 Processing startup: {startup_id}")

        update_startup_status(startup_id, "processing")

        # Download PPT
        ppt_path = download_file_from_url(startup["pitchDeckUrl"])

        # Convert to PDF
        pdf_path = convert_to_pdf(ppt_path)

        # Evaluate
        result = evaluate_startup(pdf_path)

        print("📊 Result:", result)

        # Store result
        store_screening_result(startup, result)

        # Mark done
        update_startup_status(startup_id, "analyzed")

        print(f"✅ Completed: {startup_id}")

    except Exception as e:
        print(f"❌ Error processing {startup_id}: {e}")
        update_startup_status(startup_id, "failed")

    finally:
        # Cleanup temp files
        try:
            if 'ppt_path' in locals() and os.path.exists(ppt_path):
                os.remove(ppt_path)
            if 'pdf_path' in locals() and os.path.exists(pdf_path):
                os.remove(pdf_path)
        except:
            pass


# -----------------------------
# MAIN WORKER LOOP
# -----------------------------
def run_worker():
    print("🔥 Worker started...")

    while True:
        try:
            processed_any = False

            # -----------------------------
            # BATCH PROCESSING LOOP
            # -----------------------------
            while True:
                startup = fetch_one_submitted_startup()

                if not startup:
                    break

                processed_any = True
                process_startup(startup)

                # small delay between items
                time.sleep(ACTIVE_SLEEP)

            # -----------------------------
            # SMART SLEEP
            # -----------------------------
            if processed_any:
                print("🔁 Batch complete. Checking again quickly...")
                time.sleep(ACTIVE_SLEEP)
            else:
                print("😴 No new entries. Sleeping...")
                time.sleep(IDLE_SLEEP)

        except Exception as e:
            print("⚠️ Worker loop error:", e)
            time.sleep(ERROR_SLEEP)


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    run_worker()