#!/bin/bash

echo "========================================"
echo "DeepYami Translation App"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "[ERROR] Python 3 not found."
    echo "Please install Python 3 and try again."
    echo "https://www.python.org/downloads/"
    echo
    read -p "Press Enter to exit..."
    exit 1
fi

git pull

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        read -p "Press Enter to exit..."
        exit 1
    fi
    echo "Virtual environment created."
    echo
else
    echo "[1/3] Virtual environment found."
    echo
fi

# Activate virtual environment
echo "[2/3] Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to activate virtual environment."
    read -p "Press Enter to exit..."
    exit 1
fi
echo

# Install dependencies
echo "[3/3] Installing dependencies..."
echo "This may take a few minutes..."
python -m pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    echo "Please check your internet connection."
    read -p "Press Enter to exit..."
    exit 1
fi
echo "Dependencies installed."
echo

# Start application
echo "========================================"
echo "Starting application..."
echo "========================================"
echo
python app.py

if [ $? -ne 0 ]; then
    echo
    echo "[ERROR] Failed to start application."
    read -p "Press Enter to exit..."
    exit 1
fi
