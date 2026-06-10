import asyncio
import httpx
from gtts import gTTS

async def run_voice_test(command_text: str, filename: str, lang_code: str, test_label: str, api_lang_param: str | None = None):
    print(f"\n--- Running Test: {test_label} ---")
    
    # 1. Login to get token
    print("Logging in to get JWT token...")
    async with httpx.AsyncClient() as client:
        login_resp = await client.post(
            "http://localhost:8000/auth/login",
            json={"email": "shailendraxherti@gmail.com", "password": "password123"}
        )
        login_data = login_resp.json()
        token = login_data["access_token"]
        print(f"Token: {token[:20]}...")

    # 2. Generate audio file speaking the inventory command
    print(f"Generating audio file: '{command_text}' ({lang_code}) -> {filename}...")
    tts = gTTS(text=command_text, lang=lang_code)
    tts.save(filename)

    # 3. Post to /transactions/voice
    print("Sending audio file to POST /transactions/voice...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    url = "http://localhost:8000/transactions/voice"
    if api_lang_param:
        url += f"?language={api_lang_param}"
        
    with open(filename, "rb") as f:
        files = {
            "file": (filename, f, "audio/mpeg")
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                files=files,
                timeout=60.0
            )

    print(f"Response status: {response.status_code}")
    print("Response text:")
    print(response.text)


async def main():
    # Test 1: English (Explicit en-US language parameter)
    await run_voice_test(
        command_text="sell 8 Widget A",
        filename="sell_widget_a.mp3",
        lang_code="en",
        test_label="English Transcription",
        api_lang_param="en-US"
    )
    
    # Test 2: Nepali (Default environment language, which is ne-NP)
    # "५ वटा कोकाकोला बेच" translates to "sell 5 Coca-Cola"
    await run_voice_test(
        command_text="५ वटा कोकाकोला बेच",
        filename="sell_coke_nepali.mp3",
        lang_code="ne",
        test_label="Nepali Transcription (Default ne-NP)",
        api_lang_param=None
    )

if __name__ == "__main__":
    asyncio.run(main())
