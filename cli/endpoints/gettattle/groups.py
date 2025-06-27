### AUTO-GENERATED FILE. DO NOT EDIT.

def groups(params: dict = None) -> dict:
    """
    Get paginated groups
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/groups"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

def groups_groupId(params: dict = None) -> dict:
    """
    Get group by id
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/groups/{groupId}"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

