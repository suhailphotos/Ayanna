import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()                                # .env is optional

NEBULA_AI_MODELS = Path(os.environ.get("NEBULA_AI_MODELS", "/mnt/ai/models"))
MODEL_NAME      = os.environ.get("MODEL_NAME", "llama-2-7b-chat.Q4_K_M.gguf")
MODEL_PATH      = NEBULA_AI_MODELS / "dccmate" / MODEL_NAME
DEFAULT_DCC     = os.environ.get("DCC_TYPE", "Houdini")
N_CTX           = int(os.environ.get("LLM_CONTEXT", "4096"))
N_THREADS       = int(os.environ.get("LLM_THREADS", str(os.cpu_count() or 8)))
