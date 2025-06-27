### AUTO-GENERATED FILE. DO NOT EDIT.

def incidents(params: dict = None) -> dict:
    """
    Returns a paginated list of incidents within a specified time range.
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/incidents"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

def incidents_incidentId(params: dict = None) -> dict:
    """
    Returns an incident by id
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/incidents/{incidentId}"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

