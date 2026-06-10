import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("NVIDIA_LLM_API_KEY"),
    base_url=os.getenv("NVIDIA_LLM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
)

NVIDIA_LLM_MODEL = os.getenv("NVIDIA_LLM_MODEL", "openai/gpt-oss-120b")

EXTRACTION_PROMPT = (
    "Extract the product name, quantity, and action (sale or restock) from this text. "
    "Return only JSON in this format: "
    '{"product_name": "<string>", "quantity": <number>, "action": "sale" | "restock"}'
)


async def extract_transaction_from_text(transcript: str) -> dict:
    """Use NVIDIA NIM LLM (OpenAI-compatible) to parse a voice transcript into structured JSON."""
    response = client.chat.completions.create(
        model=NVIDIA_LLM_MODEL,
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": transcript},
        ],
        temperature=0.1,
        max_tokens=256,
    )

    raw_text = response.choices[0].message.content.strip()

    # Strip markdown code fences if the model wraps the output
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines).strip()

    return json.loads(raw_text)
