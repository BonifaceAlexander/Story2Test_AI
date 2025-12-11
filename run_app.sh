#!/bin/bash
# Helper script to run Story2Test AI in the virtual environment

# 1. Create venv if it doesn't exist (optional check, assuming .venv exists based on file list)
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# 2. Activate venv
source .venv/bin/activate

# 3. Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# 4. Run Streamlit app
echo "Starting Story2Test AI..."
streamlit run streamlit_app.py
