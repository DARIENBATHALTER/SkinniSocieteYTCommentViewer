#!/bin/bash
# Setup script for YouTube Comment Scraper

# Exit on error
set -e

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env template..."
    python main.py --create-env
    echo ""
    echo "Please edit the .env file to add your YouTube API key."
fi

# Create data directory
mkdir -p data

echo ""
echo "Setup complete! You can now use the YouTube Comment Scraper."
echo ""
echo "To activate the virtual environment in the future, run:"
echo "    source venv/bin/activate"
echo ""
echo "To scrape comments from a channel, run:"
echo "    python main.py <channel_id>"
echo ""
echo "To search for comments in the database, run:"
echo "    python search.py <query>"
echo ""
echo "For more information, see the README.md file."
echo "" 