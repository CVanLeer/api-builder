from pydantic_settings import BaseSettings
from pathlib import Path
import json

class Settings(BaseSettings):
    api_base_url: str
    api_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()

def get_saved_token() -> str:
    try:
        with open(Path.home() / ".tattle-cli/credentials.json") as f:
            return json.load(f)["access_token"]
    except Exception:
        return ""

def save_token(token: str):
    path = Path.home() / ".tattle-cli"
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "credentials.json", "w") as f:
        json.dump({"access_token": token}, f)