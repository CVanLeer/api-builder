### AUTO-GENERATED FILE. DO NOT EDIT.

def reward_codes_rewardId(params: dict = None) -> dict:
    """
    Get paginated reward codes for a given reward
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/reward-codes/{rewardId}"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

