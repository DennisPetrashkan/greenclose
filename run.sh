#!/bin/bash
# GreenClose — local dev server
# Usage: bash run.sh

cd "$(dirname "$0")"

# Load .env if present
if [ -f .env ]; then
  export $(cat .env | grep -v '#' | xargs)
fi

pip install -r requirements.txt -q

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
