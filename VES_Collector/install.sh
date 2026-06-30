#!/bin/bash

set -e

echo "======================================"
echo "      VES Collector Setup Script"
echo "======================================"

# Check Python
if ! command -v python3 &> /dev/null
then
    echo "Python3 is not installed."
    exit 1
fi

# Install venv package if missing
if ! dpkg -s python3-venv &> /dev/null
then
    echo "Installing python3-venv..."
    sudo apt update
    sudo apt install -y python3-venv
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "======================================"
echo "Installation Complete"
echo "======================================"

echo "Select what to run:"
echo "1) VES Collector (app.py)"
echo "2) Event Generator"
echo "3) Exit"

read -p "Choice: " choice

case $choice in
    1)
        python app.py
        ;;
    2)
        python Testing/generator.py
        ;;
    *)
        echo "Exiting."
        ;;
esac