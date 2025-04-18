#!/bin/bash

# Create virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create needed directories
echo "Creating directories..."
mkdir -p uploads results

echo "Setup complete! You can now run the backend with: python main.py"
echo "Make sure to set your NVIDIA_PERSONAL_API_KEY environment variable before running."
