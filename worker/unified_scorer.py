from openai_scorer import evaluate_startup_openai
from groq_scorer import evaluate_startup_groq


def evaluate_startup(pdf_path, startup):

    try:
        data = evaluate_startup_openai(pdf_path)
    except Exception as e:
        print("OpenAI failed, switching to Groq")
        data = evaluate_startup_groq(pdf_path)

    scores = {
        "Founder_and_Team": int(data.get("Founder_and_Team", 0)),
        "Problem_and_Market": int(data.get("Problem_and_Market", 0)),
        "Solution_and_Product": int(data.get("Solution_and_Product", 0)),
        "Traction_and_Validation": int(data.get("Traction_and_Validation", 0)),
        "Business_Model_and_Scalability": int(data.get("Business_Model_and_Scalability", 0)),
        "Incubation_Fit": int(data.get("Incubation_Fit", 0)),
    }

    total_score = sum(scores.values())

    is_bad_deck = data.get("is_bad_deck", False)

    is_registered = startup.get("isRegisteredCompany", False)

    # --------------------------
    # FINAL DECISION LOGIC
    # --------------------------

    if is_bad_deck:

        decision = "Reject"

    else:

        if not is_registered:

            decision = "Pre-incubation"

        else:

            decision = "Incubation"

        # score downgrade
        if total_score < 40:
            decision = "Reject"

        elif total_score < 60 and decision == "Incubation":
            decision = "Pre-incubation"

    result = {
        **scores,
        "Total_Score": total_score,
        "Decision": decision,
        "Reasoning": data.get("Reasoning", ""),
        "Red_Flags": data.get("Red_Flags", [])
    }

    print("\n📊 FINAL RESULT:", result)

    return result