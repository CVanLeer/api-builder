"""API client utilities with automatic retry on authentication failures."""
import requests
from typing import Dict, Any, Optional
from cli.config import get_saved_token, auto_authenticate, settings
import logging

logger = logging.getLogger(__name__)


def make_api_request(
    method: str, 
    endpoint: str, 
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    retry_auth: bool = True
) -> requests.Response:
    """
    Make an API request with automatic retry on 401 errors.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        params: Query parameters
        json_data: JSON body data
        retry_auth: Whether to retry with auto-authentication on 401
        
    Returns:
        Response object
        
    Raises:
        HTTPError: If request fails after retry
    """
    url = f"{settings.api_base_url}{endpoint}"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }
    
    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        json=json_data
    )
    
    if response.status_code == 401 and retry_auth:
        logger.info("Received 401 error, attempting automatic re-authentication...")
        if auto_authenticate():
            # Retry the request with new token
            headers["Authorization"] = f"Bearer {get_saved_token()}"
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data
            )
        else:
            logger.error("Automatic re-authentication failed. Please run 'auth get-token' manually.")
    
    response.raise_for_status()
    return response