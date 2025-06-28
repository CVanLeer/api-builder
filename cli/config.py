"""Configuration and token management for the CLI app."""
from pydantic_settings import BaseSettings
from pathlib import Path
import json
import os
from typing import Optional
import logging
from cryptography.fernet import Fernet
import base64

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    api_base_url: str
    api_key: str = ""
    access_token: Optional[str] = ""
    auth_email: Optional[str] = ""
    auth_password_encrypted: Optional[str] = ""
    encryption_key: Optional[str] = ""

    class Config:
        """Pydantic config for environment file."""
        env_file = ".env"


settings = Settings()


def get_or_create_encryption_key() -> bytes:
    """Get or create an encryption key for storing credentials."""
    if settings.encryption_key:
        return base64.urlsafe_b64decode(settings.encryption_key)
    
    # Generate new key if not exists
    key = Fernet.generate_key()
    update_env_file("ENCRYPTION_KEY", base64.urlsafe_b64encode(key).decode())
    return key


def encrypt_password(password: str) -> str:
    """Encrypt a password using Fernet encryption."""
    key = get_or_create_encryption_key()
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()


def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a password using Fernet encryption."""
    key = get_or_create_encryption_key()
    f = Fernet(key)
    return f.decrypt(encrypted_password.encode()).decode()


def update_env_file(key: str, value: str):
    """Update or add a key-value pair in the .env file."""
    env_path = Path(".env")
    lines = []
    key_found = False
    
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    key_found = True
                else:
                    lines.append(line)
    
    if not key_found:
        lines.append(f"{key}={value}\n")
    
    with open(env_path, "w") as f:
        f.writelines(lines)
    
    # Reload settings
    global settings
    settings = Settings()


def get_saved_token() -> str:
    """Retrieve the saved access token from environment."""
    return settings.access_token or ""


def save_token(token: str):
    """Save the access token to environment file."""
    update_env_file("ACCESS_TOKEN", token)


def save_credentials(email: str, password: str):
    """Save email and encrypted password to environment file."""
    encrypted_password = encrypt_password(password)
    update_env_file("AUTH_EMAIL", email)
    update_env_file("AUTH_PASSWORD_ENCRYPTED", encrypted_password)


def get_saved_credentials() -> tuple[str, str]:
    """Get saved email and decrypted password."""
    if not settings.auth_email or not settings.auth_password_encrypted:
        return "", ""
    
    try:
        password = decrypt_password(settings.auth_password_encrypted)
        return settings.auth_email, password
    except Exception as e:
        logger.error(f"Failed to decrypt stored password: {e}")
        return "", ""


def auto_authenticate() -> bool:
    """Attempt to automatically authenticate using saved credentials."""
    import requests
    
    email, password = get_saved_credentials()
    if not email or not password:
        logger.error("No saved credentials found for automatic authentication")
        return False
    
    url = f"{settings.api_base_url}/auth/token"
    payload = {"email": email, "password": password}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            token = response.json().get("accessToken")
            save_token(token)
            logger.info("Successfully re-authenticated using saved credentials")
            return True
        else:
            logger.error(f"Auto-authentication failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Auto-authentication error: {e}")
        return False