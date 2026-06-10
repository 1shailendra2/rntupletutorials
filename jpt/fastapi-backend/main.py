"""Voice-Powered Inventory Management — FastAPI Backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers import auth, products, transactions, alerts  # noqa: E402

app = FastAPI(
    title="Voice Inventory API",
    description="Backend for a voice-powered inventory management system",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True},
)

# ── OpenAPI security scheme (adds "Authorize" button in Swagger UI) ────
app.openapi_schema_extra = None  # reset cache if any

from fastapi.openapi.utils import get_openapi  # noqa: E402


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

# ── CORS ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(transactions.router)
app.include_router(alerts.router)


@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "Voice Inventory API"}
