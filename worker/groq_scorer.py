import os
import json
import re
from groq import Groq
from pdf_text_extractor import extract_pdf_content
from prompt import SCORING_RULES, build_prompt
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_json(text):

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError("No JSON found")

    return json.loads(match.group(0))


def evaluate_startup_groq(pdf_path):

    content = extract_pdf_content(pdf_path)

    prompt = SCORING_RULES + build_prompt(content)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    output = response.choices[0].message.content.strip()

    data = extract_json(output)

    return data