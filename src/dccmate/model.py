# src/dccmate/model.py
from functools import lru_cache
from llama_cpp import Llama
from .config import MODEL_PATH, N_CTX, N_THREADS
import os

@lru_cache(maxsize=1)
def _load_llm():
    return Llama(
        model_path=str(MODEL_PATH),
        n_ctx=int(os.getenv("LLM_CTX", N_CTX)),
        num_threads=N_THREADS,
        n_gpu_layers=int(os.getenv("N_GPU_LAYERS", 32)),  # 0 = CPU
        chat_format="llama-2",
    )

def chat(messages: list[dict]) -> str:
    llm = _load_llm()
    resp = llm.create_chat_completion(messages=messages)
    return resp["choices"][0]["message"]["content"]
