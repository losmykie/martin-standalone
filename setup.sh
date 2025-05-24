#!/bin/bash

# Setup script for AWS Bedrock Chat application

# Create virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit .env file with your AWS credentials and admin password"
fi

# Create instance directory for SQLite database
if [ ! -d instance ]; then
    echo "Creating instance directory for database..."
    mkdir -p instance
fi

echo ""
echo "Setup complete! To run the application:"
echo "1. Edit the .env file with your AWS credentials"
echo "2. Run 'python app.py'"
echo "3. Access the application at http://localhost:5000"
echo ""
echo "Default login:"
echo "  Username: admin"
echo "  Password: (set in .env file)"