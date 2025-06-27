### AUTO-GENERATED FILE. DO NOT EDIT.

def roles(params: dict = None) -> dict:
    """
    Get paginated roles
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/roles"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

def roles_roleId(params: dict = None) -> dict:
    """
    Get role by id
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/roles/{roleId}"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

