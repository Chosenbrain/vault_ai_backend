import os
import asyncio
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI
from fastapi.middleware.cors import CORSMiddleware

from extractor import extract_credentials, redact_message
from tools import VAULT_FUNCTIONS, SYSTEM_PROMPT

# Load API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="VaultAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------- Flutter request model ---------
class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_unlocked: bool = False
    video_verified: bool = False


# --------- Simple health-check ----------
@app.get("/health")
async def health():
    return {"status": "ok"}


# --------- Main chat endpoint ----------
@app.post("/chat")
async def chat(req: ChatRequest):
    """
    This endpoint:
    1. Extracts secrets safely
    2. Redacts message for LLM
    3. Calls OpenAI with tools enabled
    4. Streams LLM response to Flutter
    """
    
    # Step 1: Extract credentials and redact user message
    extracted = extract_credentials(req.message)
    safe_message = redact_message(req.message)

    # Prepare system + user messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(
            UNLOCKED=req.session_unlocked,
            VERIFIED=req.video_verified
        )},
        {"role": "user", "content": safe_message},
    ]

    # Step 2: Make streaming call to OpenAI
    async def event_stream() -> AsyncGenerator[bytes, None]:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=VAULT_FUNCTIONS,  # <-- real tools
            function_call="auto",
            stream=True,
        )

        async for chunk in response:
            # Is the model calling a tool?
            if chunk.choices[0].delta.get("function_call"):
                fn = chunk.choices[0].delta["function_call"]
                yield f"[TOOL_CALL]{fn}".encode()
                continue

            delta = chunk.choices[0].delta.get("content")
            if delta:
                yield delta.encode()

        yield b""

    return StreamingResponse(event_stream(), media_type="text/plain")
