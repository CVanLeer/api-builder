### AUTO-GENERATED FILE. DO NOT EDIT.

def locations(params: dict = None) -> dict:
    """
    Get paginated locations
    """
    from cli.utils.api_client import make_api_request

    response = make_api_request("GET", "/locations", params=params)
    return response.json()

def locations_locationId(params: dict = None) -> dict:
    """
    Get location by id
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/locations/{locationId}"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

def locations_metrics(params: dict = None) -> dict:
    """
    Returns a paginated list of locations, and their associated incident stats for the given time period
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{settings.api_base_url}/locations/metrics"
    headers = {
        "Authorization": f"Bearer {get_saved_token()}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()

