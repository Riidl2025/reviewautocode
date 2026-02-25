import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

from pdf_text_extractor import extract_pdf_content
from prompt import SCORING_RULES, build_prompt

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# -----------------------------
# EXTRACT JSON FROM RESPONSE
# -----------------------------
def extract_json(text):
    try:
        text = text.replace("```json", "").replace("```", "")

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise Exception("No JSON found")

        json_str = match.group(0)
        json_str = json_str.replace("\n", " ")
        json_str = re.sub(r",\s*}", "}", json_str)

        return json.loads(json_str)

    except Exception as e:
        print("❌ JSON extraction failed:", e)
        raise


# -----------------------------
# CLAMP SCORES (0–20)
# -----------------------------
def clamp(score):
    try:
        score = int(score)
        return max(0, min(20, score))
    except:
        return 0


# -----------------------------
# LENIENT DECISION LOGIC
# -----------------------------
def calculate_result(data):
    scores = {
        "Founder_and_Team": clamp(data.get("Founder_and_Team", 0)),
        "Problem_and_Market": clamp(data.get("Problem_and_Market", 0)),
        "Solution_and_Product": clamp(data.get("Solution_and_Product", 0)),
        "Traction_and_Validation": clamp(data.get("Traction_and_Validation", 0)),
        "Business_Model_and_Scalability": clamp(data.get("Business_Model_and_Scalability", 0)),
        "Incubation_Fit": clamp(data.get("Incubation_Fit", 0)),
    }

    total_score = sum(scores.values())

    # -----------------------------
    # NEW LENIENT RULES
    # -----------------------------
    if total_score >= 35:
        decision = "Incubation"
    elif total_score >= 15:
        decision = "Pre-incubation"
    else:
        decision = "Reject"

    return {
        **scores,
        "Total_Score": total_score,
        "Decision": decision,
        "Reasoning": data.get("Reasoning", ""),
        "Red_Flags": data.get("Red_Flags", []),
    }


# -----------------------------
# MAIN FUNCTION
# -----------------------------
def evaluate_startup_groq(pdf_path):
    try:
        print("📄 Extracting content from PDF...")
        content = extract_pdf_content(pdf_path)

        print("TEXT LENGTH:", len(content))

        prompt = SCORING_RULES + build_prompt(content)

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Return ONLY valid JSON. No extra text."
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        output = response.choices[0].message.content.strip()

        print("\n--- GROQ RAW OUTPUT ---\n", output)

        parsed_data = extract_json(output)

        final_result = calculate_result(parsed_data)

        return final_result

    except Exception as e:
        print("❌ Groq evaluation failed:", e)

        return {
            "Founder_and_Team": 0,
            "Problem_and_Market": 0,
            "Solution_and_Product": 0,
            "Traction_and_Validation": 0,
            "Business_Model_and_Scalability": 0,
            "Incubation_Fit": 0,
            "Total_Score": 0,
            "Decision": "Reject",
            "Reasoning": "Groq failed",
            "Red_Flags": ["evaluation_error"],
        }