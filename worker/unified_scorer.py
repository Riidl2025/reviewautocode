import os
from dotenv import load_dotenv

from openai_scorer import evaluate_startup as evaluate_openai
from groq_scorer import evaluate_startup_groq

load_dotenv()


def evaluate_startup(pdf_path):
    """
    OpenAI → primary
    Groq → fallback
    """

    # -----------------------------
    # TRY OPENAI
    # -----------------------------
    try:
        print("🧠 Trying OpenAI...")

        result = evaluate_openai(pdf_path)

        # Validate output
        if not result or result.get("Total_Score", 0) == 0:
            raise Exception("Invalid OpenAI result")

        print("✅ OpenAI success")
        return result

    except Exception as e:
        print("⚠️ OpenAI failed:", e)

    # -----------------------------
    # FALLBACK → GROQ
    # -----------------------------
    try:
        print("🔁 Switching to Groq...")

        result = evaluate_startup_groq(pdf_path)

        print("✅ Groq success")
        return result

    except Exception as e:
        print("❌ Groq failed:", e)

        return {
            "Founder_and_Team": 0,
            "Problem_and_Market": 0,
            "Solution_and_Product": 0,
            "Traction_and_Validation": 0,
            "Business_Model_and_Scalability": 0,
            "Incubation_Fit": 0,
            "Total_Score": 0,
            "Decision": "Reject",
            "Reasoning": "Both OpenAI and Groq failed",
            "Red_Flags": ["evaluation_failure"],
        }