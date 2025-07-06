import os
from .envloader import resolve_env_file, load_env

ENV_FILE = resolve_env_file()

if not load_env(ENV_FILE) and not os.getenv("DCCMATE_SUPPRESS_ENV_WARN"):
    print(
        "⚠️  No .env file found!\n"
        "Please create one at $HOME/.dccmate/.env or run:\n"
        "    dccmate init\n"
        "to copy a sample env file.\n"
    )
