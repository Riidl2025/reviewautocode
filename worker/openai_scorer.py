import os
import json
import re
from openai import OpenAI
from pdf_text_extractor import extract_pdf_content
from prompt import SCORING_RULES, build_prompt
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPEN_API_KEY"))

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found")

    return json.loads(match.group(0))


def evaluate_startup_openai(pdf_path):

    content = extract_pdf_content(pdf_path)

    prompt = SCORING_RULES + build_prompt(content)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=0.2
    )

    output = response.output[0].content[0].text.strip()

    data = extract_json(output)

    return data