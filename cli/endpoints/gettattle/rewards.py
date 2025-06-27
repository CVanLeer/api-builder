### AUTO-GENERATED FILE. DO NOT EDIT.

def rewards(params: dict = None) -> dict:
    """
    Get paginated rewards
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/rewards"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

def rewards_rewardId(params: dict = None) -> dict:
    """
    Get reward by id
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/rewards/{rewardId}"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

