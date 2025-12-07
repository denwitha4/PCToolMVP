#!/bin/bash

# Create venv if missing
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies if missing
pip install sqlalchemy
pip install fastapi uvicorn --quiet

# Run FastAPI app
cd ..
uvicorn main:app --reload
