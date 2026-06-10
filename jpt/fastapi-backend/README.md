# Voice-Powered Inventory Management — FastAPI Backend

A FastAPI backend that lets store owners manage inventory through voice commands. Audio is transcribed by **NVIDIA NIM Whisper**, parsed by **NVIDIA NIM LLM (gpt-oss-120b)**, and persisted in **Supabase** (Postgres + Auth).

## Project Structure

```
fastapi-backend/
├── main.py                  # FastAPI app entry-point
├── .env                     # Environment variables (not committed)
├── requirements.txt         # Python dependencies
├── routers/
│   ├── _deps.py             # Shared auth dependency (JWT decoder)
│   ├── auth.py              # POST /auth/signup, POST /auth/login
│   ├── products.py          # GET /products, POST /products
│   ├── transactions.py      # GET /transactions, POST /transactions/voice
│   └── alerts.py            # POST /alerts/email
└── services/
    ├── supabase_client.py   # Async Supabase REST/Auth/RPC helper
    ├── whisper_service.py   # NVIDIA NIM Whisper transcription
    ├── llm_service.py       # NVIDIA NIM LLM structured extraction
    └── email_service.py     # SMTP low-stock alert emails
```

## Prerequisites

- Python 3.10+
- A Supabase project with the schema already set up (profiles, products, transactions tables + `update_product_quantity` RPC)
- NVIDIA NIM API keys (for Whisper STT and LLM)
- An SMTP-capable email account (e.g. Gmail with App Passwords)

## Environment Variables

Create a `.env` file in the project root with:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# NVIDIA NIM — Whisper STT
NVIDIA_WHISPER_API_KEY=nvapi-...
NVIDIA_WHISPER_MODEL=whisper-large-v3
NVIDIA_WHISPER_BASE_URL=https://ai.api.nvidia.com/v1/audio/transcriptions

# NVIDIA NIM — LLM
NVIDIA_LLM_API_KEY=nvapi-...
NVIDIA_LLM_MODEL=openai/gpt-oss-120b
NVIDIA_LLM_BASE_URL=https://integrate.api.nvidia.com/v1

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=you@gmail.com
SMTP_PASSWORD=your-app-password
```

## Setup & Run

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the dev server
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

## API Endpoints

| Method | Path                     | Auth | Description                                   |
|--------|--------------------------|------|-----------------------------------------------|
| GET    | `/`                      | No   | Health check                                  |
| POST   | `/auth/signup`           | No   | Register user + create profile                |
| POST   | `/auth/login`            | No   | Login and receive JWT                         |
| GET    | `/products`              | JWT  | List all products for current user            |
| POST   | `/products`              | JWT  | Create a new product                          |
| GET    | `/transactions`          | JWT  | List transactions (newest first, w/ product)  |
| POST   | `/transactions/voice`    | JWT  | Upload audio → transcript → transaction       |
| POST   | `/alerts/email`          | No   | Send a low-stock reorder email to supplier    |

### Voice Transaction Flow

1. Client uploads an audio file to `POST /transactions/voice`
2. Audio is sent to **NVIDIA NIM Whisper** → plain-text transcript
3. Transcript is sent to **NVIDIA NIM LLM (gpt-oss-120b)** → `{ product_name, quantity, action }`
4. Product is fuzzy-matched against the user's inventory
5. Supabase RPC `update_product_quantity` updates stock & creates a transaction row
6. If the new quantity drops below the threshold, a reorder email is sent automatically

## CORS

Allowed origins:
- `http://localhost:5173` (Vite dev server)
- `http://localhost:3000` (Next.js / CRA dev server)
