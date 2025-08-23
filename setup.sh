#!/bin/bash

# UGENE Workflow Designer - Quick Setup Script
# This script performs the initial setup after pasting all the code

echo "🔧 Setting up UGENE Workflow Designer..."

# Define the required Python version
PYTHON_VERSION="python3.11"

# Make this script executable
chmod +x setup.sh

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env file from template"
    echo "   Please edit .env to configure your environment"
fi

# Install frontend dependencies (if Node.js is available)
if command -v npm &> /dev/null; then
    echo "📦 Installing frontend dependencies..."
    (cd frontend && npm install)
else
    echo "⚠️  Node.js not found. Please install Node.js and run 'npm install' in the frontend directory"
fi

# Install backend dependencies (if the specified Python version is available)
if command -v $PYTHON_VERSION &> /dev/null; then
    echo "🐍 Setting up Python virtual environment with $PYTHON_VERSION..."
    cd backend
    $PYTHON_VERSION -m venv venv
    source venv/bin/activate
    echo "   Installing backend dependencies..."
    pip install -r requirements.txt
    deactivate
    cd ..
else
    echo "⚠️  $PYTHON_VERSION not found. Please install Python 3.11 to proceed with the backend setup."
fi

echo ""
echo "✅ Setup complete! Next steps:"
echo ""
echo "1. Edit the .env file with your configuration"
echo "2. If you haven't already, paste the code from the artifacts into the respective files"
echo "3. Start with Docker: docker-compose up -d"
echo "   OR start manually:"
echo "   - Backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "   - Frontend: cd frontend && npm start"
echo ""
echo "📖 See README.md for detailed instructions"
