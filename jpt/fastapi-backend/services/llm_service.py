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
    "You are an inventory assistant. Extract the product name, quantity, and action (sale or restock) from this text.\n"
    "Rules:\n"
    "1. The text is from a voice command, so handle homophones (e.g., 'cell' or 'cells' or 'celling' means 'sale', 'add' or 'restock' or 'receive' means 'restock').\n"
    "2. The text may be in Nepali. Note that 'बेच' or 'बिक्री' means 'sale', and 'थप' or 'राख' or 'लोड' or 'रिस्टक' means 'restock'.\n"
    "3. Translate or transliterate any Nepali product names or phonetics into Latin/English script if they refer to English-named products (e.g., 'कोकाकोला' or 'कोका कोला' should be 'Coca-Cola', 'विजेट' or 'भिजिरहे' should be 'Widget').\n"
    "4. Return ONLY valid JSON in this format: "
    '{"product_name": "<string>", "quantity": <number>, "action": "sale" | "restock"}'
)


async def extract_transaction_from_text(transcript: str) -> dict:
    """Use NVIDIA NIM LLM (OpenAI-compatible) to parse a voice transcript into structured JSON."""
    if not transcript:
        return {"product_name": "", "quantity": 0, "action": "sale"}

    response = client.chat.completions.create(
        model=NVIDIA_LLM_MODEL,
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": transcript},
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    choice = response.choices[0]
    raw_text = choice.message.content

    # Handle cases where the model returns None content but has text in reasoning/refusal
    if not raw_text:
        # Fallback to check other fields if any
        raw_text = getattr(choice.message, "reasoning", "") or getattr(choice.message, "reasoning_content", "") or ""
        # If there is markdown/JSON inside the reasoning text, try to extract it
        if "{" in raw_text and "}" in raw_text:
            raw_text = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]
        else:
            raise ValueError(f"Model returned empty content. Full message: {choice.message}")

    raw_text = raw_text.strip()

    # Strip markdown code fences if the model wraps the output
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines).strip()

    try:
        return json.loads(raw_text)
    except Exception as e:
        # If JSON load fails, let's try one more fallback to search for any JSON substring
        if "{" in raw_text and "}" in raw_text:
            try:
                json_str = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]
                return json.loads(json_str)
            except Exception:
                pass
        raise ValueError(f"Failed to parse model output as JSON: {raw_text}. Error: {e}")
