#!/bin/bash

# Create venv if missing
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies if missing
pip install fastapi uvicorn --quiet

# Run FastAPI app
uvicorn main:app --reload
