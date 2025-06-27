"""
Generates the API client from the OpenAPI spec using openapi-python-client.
"""

import subprocess
from pathlib import Path

OPENAPI_PATH = Path("openapi/example_api.yaml")
OUTPUT_DIR = Path("api_client")

def generate_sdk():
    print(f"Generating client SDK from {OPENAPI_PATH}...")
    subprocess.run([
        "openapi-python-client",
        "generate",
        "--path", str(OPENAPI_PATH),
        "--output", str(OUTPUT_DIR),
        "--custom-template-path", "templates"  # Optional: if we add templates later
    ], check=True)

if __name__ == "__main__":
    generate_sdk() 