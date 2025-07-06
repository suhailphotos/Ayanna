# envloader.py
import os
from pathlib import Path

def resolve_env_file(project_env_dir=".env", project_marker="pyproject.toml", user_env_subdir=".dccmate"):
    """
    Finds best .env file to use, for dev or user install.
    project_env_dir: filename to look for in dev mode (".env")
    project_marker: file to confirm project root ("pyproject.toml")
    user_env_subdir: user config dir in $HOME
    """
    # 1. Custom override
    env_file = os.environ.get("DCCMATE_ENV_FILE")
    if env_file and Path(env_file).exists():
        return Path(env_file)

    # 2. Project root (dev mode)
    cur = Path.cwd()
    for parent in [cur, *cur.parents]:
        if (parent / project_env_dir).exists() and (parent / project_marker).exists():
            return parent / project_env_dir

    # 3. User install
    user_env = Path.home() / user_env_subdir / ".env"
    if user_env.exists():
        return user_env

    return None

def load_env(env_file=None):
    from dotenv import load_dotenv
    if env_file:
        load_dotenv(dotenv_path=env_file, override=True)
        return True
    return False
