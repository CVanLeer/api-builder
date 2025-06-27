"""
Watches the openapi/ folder and regenerates the client when any file changes.
"""

import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess

OPENAPI_DIR = Path("openapi")

class ChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(".yaml") or event.src_path.endswith(".json"):
            print(f"Detected change in {event.src_path}, regenerating SDK...")
            subprocess.run(["python", "scripts/regen_client.py"])

if __name__ == "__main__":
    print(f"Watching {OPENAPI_DIR} for changes...")
    event_handler = ChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, str(OPENAPI_DIR), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join() 