
import os
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ===== FastAPI app =====
app = FastAPI(title="Lumio Backend", version="0.1.0")

# CORS: allow all for MVP; tighten later to your domain(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Models =====
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

# ===== Config =====
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "microsoft/mai-ds-r1:free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

SYSTEM_PROMPT = (
    "Сен — MIVO, бейнероликтерге кәсіби сценарий жазатын көмекшісің. "
    "ӘРҚАШАН тек қазақ тілінде жауап бер. Басқа тілдерде жауап беруге болмайды "
    "Жауабың қысқа бейне форматтарына (TikTok / Instagram Reels / YouTube Shorts) бейімделуі керек. "
    "Саған көбіне видео түсіруге көмектесетін құрылғы ретінде қолданады"
    "Жылы сөйлеп түсінікті жауап беруің керек "
    "Жауап құрылымы қатаң түрде төмендегідей болсын:\n\n"
    "🎬 Кіріспе: [көрерменді тарту, 1–2 сөйлем] \n"
    "🎭 Негізгі бөлім: [негізгі фактілер/кадрлар, қажет болса секундтармен: 0–5с, 5–20с, т.б.] \n"
    "🔔 Қорытынды: [қысқа түйін, әрекетке шақыру] \n"
    "🎵 Стиль кеңестері: [музыка, атмосфера, түс/фон, монтаж] \n\n"
    "Қысқа, нақты, түсінікті жаз."
)

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": os.getenv("HTTP_REFERER", "http://localhost"),
    "X-Title": os.getenv("X_TITLE", "Lumio"),
}

# ===== Routes =====

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not set")

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req.message},
        ],
        "temperature": 0.7,
        "max_tokens": 10000,
    }

    url = f"{OPENROUTER_BASE_URL}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=HEADERS, json=payload)
        r.raise_for_status()
        data = r.json()

        content = (
            data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
        ).strip()

        if not content:
            raise HTTPException(status_code=502, detail="Empty response from model")

        return ChatResponse(reply=content)

    except httpx.HTTPStatusError as e:
        detail = f"Provider error: {e.response.status_code} {e.response.text}"
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
