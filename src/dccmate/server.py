# src/dccmate/server.py
import time, uuid, json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from . import prompts, model
from .config import DEFAULT_DCC

class ChatReq(BaseModel):
    messages: list[dict]
    dcc: str | None = None
    stream: bool | None = False

app = FastAPI(title="dccMate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/v1/chat/completions")
async def completions(req: ChatReq):
    # build full conversation
    convo = [prompts.system_prompt(req.dcc or DEFAULT_DCC)] + req.messages
    llm = model._load_llm()

    # ────────── STREAMING (for Open-WebUI etc.) ──────────
    if req.stream:
        def sse():
            for chunk in llm.create_chat_completion(messages=convo, stream=True):
                # Llama-cpp already returns OpenAI-style chunks
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")

    # ────────── one-shot JSON (curl, dev scripts) ──────────
    full = llm.create_chat_completion(messages=convo)
    usage = full["usage"]                     # real token counts
    answer = full["choices"][0]["message"]["content"]

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": f"dccmate-{(req.dcc or DEFAULT_DCC).lower()}",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": answer},
             "finish_reason": "stop"}
        ],
        "usage": usage,        # ← real numbers
    }

@app.get("/v1/models")
def list_models():
    return {
        "data": [
            {
                "id": f"dccmate-{DEFAULT_DCC.lower()}",
                "object": "model",
                "created": 0,
                "owned_by": "suhailphotos",
            }
        ]
    }
