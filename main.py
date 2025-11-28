import os
import asyncio
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from extractor import extract_credentials, redact_message
from tools import VAULT_FUNCTIONS, SYSTEM_PROMPT

# ---------------------------------------------------------------------
# Load API key
# ---------------------------------------------------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("❌ Missing OPENAI_API_KEY in environment variables")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------
app = FastAPI(title="VaultAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Later change to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------
class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_unlocked: bool = False
    video_verified: bool = False


# ---------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------
@app.get("/")
async def root():
    return {"status": "VaultAI backend running", "success": True}


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------
# Streaming AI logic
# ---------------------------------------------------------------------
async def ai_stream(messages):
    """Stream response from OpenAI to Flutter"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=VAULT_FUNCTIONS,          # 🔥 NEW CORRECT API
        tool_choice="auto",
        stream=True,
    )

    async for chunk in response:
        # Handle tool call chunks
        if chunk.choices and chunk.choices[0].delta.tool_calls:
            tc = chunk.choices[0].delta.tool_calls[0]
            yield f"[TOOL]{tc}".encode()
            continue

        # Handle normal text tokens
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content.encode()

    yield b""


# ---------------------------------------------------------------------
# Main Chat Endpoint
# ---------------------------------------------------------------------
@app.post("/chat")
async def chat(req: ChatRequest):

    if not req.message:
        raise HTTPException(status_code=400, detail="Missing message")

    # Extract sensitive credentials (locally)
    extracted = extract_credentials(req.message)
    safe_message = redact_message(req.message)

    print("🟦 Extracted:", extracted)
    print("🟩 Safe message:", safe_message)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(
                UNLOCKED=req.session_unlocked,
                VERIFIED=req.video_verified
            )
        },
        {"role": "user", "content": safe_message}
    ]

    return StreamingResponse(
        ai_stream(messages),
        media_type="text/event-stream"   # 🔥 Correct for Flutter streams
    )
