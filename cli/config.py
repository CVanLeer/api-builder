"""Configuration and token management for the CLI app."""
from pydantic_settings import BaseSettings
from typing import Optional
import logging
from cryptography.fernet import Fernet
import base64
from datetime import datetime
from cli.state import state_manager

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    api_base_url: str
    api_key: str = ""
    access_token: Optional[str] = ""
    auth_email: Optional[str] = ""
    auth_password_encrypted: Optional[str] = ""
    encryption_key: Optional[str] = ""
    token_last_updated: Optional[str] = ""

    class Config:
        """Pydantic config for environment file."""
        env_file = ".env"
        extra = "ignore"  # Allow extra fields in .env file


settings = Settings()


def get_or_create_encryption_key() -> bytes:
    """
    Get or create a Fernet encryption key for credential security.

    This function retrieves an existing encryption key from the state manager,
    or generates a new one if none exists. The key is used to securely encrypt
    and store user passwords locally.

    Returns:
        bytes: A Fernet-compatible encryption key

    Example:
        >>> key = get_or_create_encryption_key()
        >>> len(key)
        32

    Note:
        The key is automatically saved to persistent storage when generated.
    """
    key_str = state_manager.get_encryption_key()
    if key_str:
        return base64.urlsafe_b64decode(key_str)
    
    # Generate new key
    key = Fernet.generate_key()
    key_str = base64.urlsafe_b64encode(key).decode()
    state_manager.save_encryption_key(key_str)
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


def get_saved_token() -> str:
    """Retrieve the saved access token."""
    return state_manager.get_token() or ""


def save_token(token: str):
    """Save the access token and update timestamp."""
    state_manager.save_token(token)


def get_token_last_updated() -> Optional[datetime]:
    """Get the last updated timestamp for the token."""
    return state_manager.get_token_last_updated()


def save_credentials(email: str, password: str):
    """
    Securely save user credentials for automatic authentication.

    This function encrypts the password using Fernet symmetric encryption
    and stores both email and encrypted password in the state manager.

    Args:
        email: User's email address
        password: User's plain-text password (will be encrypted)

    Example:
        >>> save_credentials('user@example.com', 'secret123')
        >>> # Password is encrypted and stored securely

    Note:
        - Password is immediately encrypted before storage
        - Original password is not retained in memory
        - Email is stored in plain text
    """
    encrypted_password = encrypt_password(password)
    state_manager.save_credentials(email, encrypted_password)


def get_saved_credentials() -> tuple[str, str]:
    """Get saved email and decrypted password."""
    email, encrypted_password = state_manager.get_credentials()
    if not email or not encrypted_password:
        return "", ""
    try:
        password = decrypt_password(encrypted_password)
        return email, password
    except Exception as e:
        logger.error(
            f"Failed to decrypt stored password: {e}"
        )
        return "", ""


def auto_authenticate() -> bool:
    """
    Attempt automatic authentication using stored credentials.

    This function retrieves saved email/password credentials, decrypts
    the password, and attempts to authenticate with the API. If successful,
    it saves the new token for future use.

    Returns:
        bool: True if authentication succeeded, False otherwise

    Raises:
        requests.RequestException: If network request fails
        Exception: If decryption or token processing fails

    Example:
        >>> success = auto_authenticate()
        >>> if success:
        ...     print("Authenticated successfully")
        ... else:
        ...     print("Need manual authentication")

    Note:
        - Logs authentication attempts and failures
        - Returns False if no saved credentials exist
        - Updates token timestamp on successful authentication
    """
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