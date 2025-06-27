### AUTO-GENERATED FILE. DO NOT EDIT.

def webhook_subscription_settings(params: dict = None) -> dict:
    """
    Get partner's webhook subscription settings
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/webhook-subscription-settings"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

