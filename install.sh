#!/bin/bash

# TPDB Poster Sync - Installation and Setup Script

set -e

echo "TPDB Poster Sync Setup"
echo "====================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check Python version
python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" || {
    echo "Error: Python 3.8 or higher is required"
    exit 1
}

echo "✓ Python $(python3 --version | cut -d' ' -f2) detected"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate
echo "✓ Virtual environment activated"

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Create sample config if needed
if [ ! -f "config.yaml" ]; then
    if [ -f "config.sample.yaml" ]; then
        cp config.sample.yaml config.yaml
        echo "✓ Created config.yaml from sample"
    else
        echo "! Please create config.yaml (see README for details)"
    fi
fi

# Create directories
mkdir -p logs
echo "✓ Created log directory"

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your settings"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Test with: python main.py --dry-run"
echo "4. Start syncing: python main.py"
