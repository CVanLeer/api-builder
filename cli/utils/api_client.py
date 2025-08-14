"""
Centralized API client factory and utilities.
"""
from typing import Optional
import logging
from api_client.partners_api_client.client import Client
from api_client.partners_api_client.api.authentication import post_auth_token
from api_client.partners_api_client.models import AuthenticationRequest
from cli.config import settings
from cli.state import state_manager

logger = logging.getLogger(__name__)


def get_client() -> Client:
    """
    Get configured API client with authentication.
    This is the single entry point for all API operations.
    """
    token = state_manager.get_token()
    client = Client(
        base_url=settings.api_base_url,
        headers={"Authorization": f"Bearer {token}"} if token else {}
    )
    return client


def authenticate_client(email: str, password: str) -> Optional[str]:
    """
    Authenticate and return access token using the API client.
    """
    client = Client(base_url=settings.api_base_url)
    auth_request = AuthenticationRequest(
        email=email,
        password=password
    )
    try:
        response = post_auth_token.sync(client=client, json_body=auth_request)
        if response and hasattr(response, 'access_token'):
            return response.access_token
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
    return None


def refresh_token_if_needed() -> bool:
    """
    Automatically refresh token if expired.
    Returns True if token is valid/refreshed, False if manual auth needed.
    """
    from datetime import datetime, timedelta
    last_updated = state_manager.get_token_last_updated()
    if not last_updated or (
        datetime.utcnow() - last_updated > timedelta(hours=23)
    ):
        from cli.config import get_saved_credentials
        email, password = get_saved_credentials()
        if email and password:
            token = authenticate_client(email, password)
            if token:
                state_manager.save_token(token)
                return True
        return False
    return True