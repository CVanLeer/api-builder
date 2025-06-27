### file: scripts/generate_endpoints.py

import json
from pathlib import Path
from urllib.parse import urlparse
import re

BASE_DIR = Path(__file__).resolve().parent.parent
OPENAPI_PATH = BASE_DIR / "openapi" / "openai.json"
OUTPUT_BASE = BASE_DIR / "cli" / "endpoints" / "gettattle"


def path_to_filename(path: str) -> str:
    parts = path.strip("/").split("/")
    if not parts:
        return "root"
    return parts[0].split("{")[0].strip("/")


def path_to_function_name(path: str) -> str:
    cleaned = re.sub(r"[{}]", "", path)  # remove {} from path variables
    return cleaned.strip("/").replace("/", "_").replace("-", "_")


def generate_get_function(path: str, summary: str) -> str:
    fname = path_to_function_name(path)
    return f'''def {fname}(params: dict = None) -> dict:
    """
    {summary or "No description available."}
    """
    import requests
    from cli.config import settings, get_saved_token

    url = f"{{settings.api_base_url}}{path}"
    headers = {{
        "Authorization": f"Bearer {{get_saved_token()}}",
        "Content-Type": "application/json"
    }}

    response = requests.get(url, headers=headers, params=params or {{}})
    response.raise_for_status()
    return response.json()
'''


def main():
    if not OPENAPI_PATH.exists():
        print(f"❌ Cannot find {OPENAPI_PATH}")
        return

    with open(OPENAPI_PATH) as f:
        spec = json.load(f)

    paths = spec.get("paths", {})
    generated = {}

    for path, methods in paths.items():
        if "get" not in methods:
            continue

        summary = methods["get"].get("summary", "")
        filename = path_to_filename(path)
        fn_code = generate_get_function(path, summary)

        if filename not in generated:
            generated[filename] = {}

        func_name = path_to_function_name(path)
        if func_name not in generated[filename]:
            generated[filename][func_name] = fn_code

    for fname, functions in generated.items():
        file_path = OUTPUT_BASE / f"{fname}.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write("### AUTO-GENERATED FILE. DO NOT EDIT.\n\n")
            for fn in functions.values():
                f.write(fn + "\n")

        print(f"✅ Wrote: {file_path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()