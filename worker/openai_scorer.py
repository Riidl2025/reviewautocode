import os
import json
from openai import OpenAI

from pdf_text_extractor import extract_pdf_content
from prompt import SCORING_RULES, build_prompt

from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPEN_API_KEY"))


# -----------------------------
# ROBUST JSON EXTRACTION
# -----------------------------
def extract_json_from_text(text: str) -> dict:
    text = text.replace("```json", "").replace("```", "")

    stack = []
    start = None

    for i, char in enumerate(text):
        if char == "{":
            if not stack:
                start = i
            stack.append("{")
        elif char == "}":
            stack.pop()
            if not stack and start is not None:
                json_str = text[start:i+1]
                return json.loads(json_str)

    raise ValueError("No valid JSON found")


# -----------------------------
# CLAMP SCORES
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
def calculate_total_and_decision(data: dict) -> dict:
    scores = {
        "Founder_and_Team": clamp(data.get("Founder_and_Team", 0)),
        "Problem_and_Market": clamp(data.get("Problem_and_Market", 0)),
        "Solution_and_Product": clamp(data.get("Solution_and_Product", 0)),
        "Traction_and_Validation": clamp(data.get("Traction_and_Validation", 0)),
        "Business_Model_and_Scalability": clamp(data.get("Business_Model_and_Scalability", 0)),
        "Incubation_Fit": clamp(data.get("Incubation_Fit", 0)),
    }

    total_score = sum(scores.values())

    if total_score >= 35:
        decision = "Incubate with conditions"
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
def evaluate_startup(pdf_path: str) -> dict:
    try:
        print("📄 Extracting content...")
        content = extract_pdf_content(pdf_path)

        print("TEXT LENGTH:", len(content))

        prompt = SCORING_RULES + build_prompt(content)

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            temperature=0.2
        )

        output_text = response.output[0].content[0].text.strip()

        print("\n--- OPENAI RAW OUTPUT ---\n", output_text)

        parsed_data = extract_json_from_text(output_text)

        final_result = calculate_total_and_decision(parsed_data)

        return final_result

    except Exception as e:
        print("❌ OpenAI evaluation failed:", e)
        raise