#!/bin/bash
# Start the realtime agent server

# Activate the virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate || source .venv/Scripts/activate
fi

# Check if Deepgram API key is set
if [ -z "$DEEPGRAM_API_KEY" ]; then
    echo "Warning: DEEPGRAM_API_KEY environment variable is not set."
    echo "It will be loaded from .env file if available."
fi

# Run the server
python -m backend.main_realtime 