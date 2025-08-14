#!/bin/bash
# Launch the API Central Interactive Terminal

# Navigate to the project directory
cd "$(dirname "$0")"

# Clear the screen
clear

# Run the interactive terminal
poetry run python interactive_terminal.py