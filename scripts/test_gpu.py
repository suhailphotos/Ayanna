from llama_cpp import Llama

llm = Llama(
    model_path="/mnt/ai/models/dccmate/llama-2-7b-chat.Q4_K_M.gguf",
    n_ctx=128,
    n_gpu_layers=32,
)
print(llm.create_chat_completion([{"role": "user", "content": "Say hello"}]))
