import asyncio
import httpx
from gtts import gTTS

async def main():
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
    command_text = "sell 8 Widget A"
    audio_file = "sell_widget_a.mp3"
    print(f"Generating audio file: '{command_text}' -> {audio_file}...")
    tts = gTTS(text=command_text, lang='en')
    tts.save(audio_file)

    # 3. Post to /transactions/voice
    print("Sending audio file to POST /transactions/voice...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    with open(audio_file, "rb") as f:
        files = {
            "file": (audio_file, f, "audio/mpeg")
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/transactions/voice",
                headers=headers,
                files=files,
                timeout=60.0
            )

    print(f"Response status: {response.status_code}")
    print("Response text:")
    print(response.text)

if __name__ == "__main__":
    asyncio.run(main())
