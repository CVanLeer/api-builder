### AUTO-GENERATED FILE. DO NOT EDIT.

def merchants(params: dict = None) -> dict:
    """
    Get paginated merchants
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/merchants"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

def merchants_merchantId(params: dict = None) -> dict:
    """
    Get merchant by id
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/merchants/{merchantId}"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

