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
IDLE_SLEEP = 60       # when no startups
ACTIVE_SLEEP = 5      # between processing

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
# PPT → PDF CONVERSION
# -----------------------------
def convert_to_pdf(input_path):
    try:
        output_dir = tempfile.mkdtemp()

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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # find generated PDF
        for file in os.listdir(output_dir):
            if file.endswith(".pdf"):
                return os.path.join(output_dir, file)

        raise Exception("PDF conversion failed")

    except Exception as e:
        raise Exception(f"Conversion error: {e}")


# -----------------------------
# MAIN WORKER LOOP
# -----------------------------
def run_worker():
    print("🚀 Worker started...")

    while True:
        startup = fetch_one_submitted_startup()

        if not startup:
            print("😴 No new startups. Sleeping...")
            time.sleep(IDLE_SLEEP)
            continue

        startup_id = startup.get("id")
        print(f"\n📥 Processing: {startup_id}")

        try:
            # -----------------------------
            # MARK PROCESSING
            # -----------------------------
            update_startup_status(startup_id, "processing")

            pitch_url = startup.get("pitchDeckUrl")

            if not pitch_url:
                raise Exception("No pitch deck URL found")

            # -----------------------------
            # DOWNLOAD FILE
            # -----------------------------
            print("⬇ Downloading pitch deck...")
            input_path = download_file_from_url(pitch_url)

            # -----------------------------
            # CONVERT TO PDF
            # -----------------------------
            print("📄 Converting to PDF...")
            pdf_path = convert_to_pdf(input_path)

            # -----------------------------
            # EVALUATE STARTUP
            # -----------------------------
            print("🤖 Evaluating startup...")
            result = evaluate_startup(pdf_path, startup)

            print("\n📊 FINAL RESULT:", result)

            # -----------------------------
            # STORE RESULT (FIXED STRUCTURE)
            # -----------------------------
            print("💾 Storing result...")

            store_screening_result(startup, {
                "scores": {
                    "Founder_and_Team": result.get("Founder_and_Team", 0),
                    "Problem_and_Market": result.get("Problem_and_Market", 0),
                    "Solution_and_Product": result.get("Solution_and_Product", 0),
                    "Traction_and_Validation": result.get("Traction_and_Validation", 0),
                    "Business_Model_and_Scalability": result.get("Business_Model_and_Scalability", 0),
                    "Incubation_Fit": result.get("Incubation_Fit", 0),
                },
                "totalScore": result.get("Total_Score", 0),
                "decision": result.get("Decision", "Reject"),
                "reasoning": result.get("Reasoning", ""),
                "red_flags": result.get("Red_Flags", [])
            })

            # -----------------------------
            # MARK COMPLETED
            # -----------------------------
            update_startup_status(startup_id, "analyzed")

            print(f"✅ Successfully processed: {startup_id}")

            # -----------------------------
            # CLEANUP
            # -----------------------------
            try:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            except Exception as cleanup_error:
                print("⚠ Cleanup error:", cleanup_error)

            time.sleep(ACTIVE_SLEEP)

        except Exception as e:
            print(f"❌ Error processing {startup_id}: {e}")

            update_startup_status(startup_id, "failed")

            time.sleep(ACTIVE_SLEEP)


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    run_worker()