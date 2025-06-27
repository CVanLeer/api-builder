### AUTO-GENERATED FILE. DO NOT EDIT.

def channels(params: dict = None) -> dict:
    """
    Get paginated channels
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/channels"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

