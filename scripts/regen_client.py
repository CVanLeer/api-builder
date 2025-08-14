"""
Generates the API client from the OpenAPI spec using openapi-python-client.
"""

import subprocess
from pathlib import Path

OPENAPI_PATH = Path("openapi/openai.json")
OUTPUT_DIR = Path("api_client")

def generate_sdk():
    print(f"Generating client SDK from {OPENAPI_PATH}...")
    
    # Remove existing client directory if it exists
    if OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    
    # Generate client - it will create a new directory with the API name
    subprocess.run([
        "python", "-m", "openapi_python_client",
        "generate",
        "--path", str(OPENAPI_PATH),
        "--meta", "poetry"
    ], check=True)
    
    # Move the generated directory to the expected location
    generated_dir = Path("partners-api-client")
    if generated_dir.exists():
        import shutil
        shutil.move(str(generated_dir), str(OUTPUT_DIR))

if __name__ == "__main__":
    generate_sdk() 