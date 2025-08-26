#!/bin/bash
# start_development.sh - Quick development startup script

set -e

echo "🚀 Starting UGENE Web Platform Development Environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed and running
check_docker() {
    print_status "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker."
        exit 1
    fi
    
    print_success "Docker is installed and running"
}

# Check if Docker Compose is available
check_docker_compose() {
    print_status "Checking Docker Compose..."
    
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif docker-compose version &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        print_error "Docker Compose is not available."
        exit 1
    fi
    
    print_success "Docker Compose found: $COMPOSE_CMD"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p backend/app/{models,services,api,database,builders,websockets,utils,tests}
    mkdir -p frontend/src/{components,services,hooks,context,utils}
    mkdir -p nginx logs monitoring
    
    print_success "Directories created"
}

# Create basic backend files if they don't exist
create_backend_files() {
    print_status "Creating basic backend files..."
    
    # Create __init__.py files
    touch backend/app/__init__.py
    find backend/app -type d -exec touch {}/__init__.py \;
    
    # Create basic main.py if it doesn't exist
    if [ ! -f backend/app/main.py ]; then
        cat > backend/app/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="UGENE Web Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "UGENE Web Platform API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
EOF
    fi
    
    print_success "Basic backend files created"
}

# Create basic frontend files if they don't exist
create_frontend_files() {
    print_status "Creating basic frontend files..."
    
    # Create basic public/index.html if it doesn't exist
    mkdir -p frontend/public frontend/src
    
    if [ ! -f frontend/public/index.html ]; then
        cat > frontend/public/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>UGENE Web Platform</title>
</head>
<body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
</body>
</html>
EOF
    fi
    
    # Create basic src/index.js if it doesn't exist
    if [ ! -f frontend/src/index.js ]; then
        cat > frontend/src/index.js << 'EOF'
import React from 'react';
import ReactDOM from 'react-dom/client';
import 'bootstrap/dist/css/bootstrap.min.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);
EOF
    fi
    
    # Create basic src/App.js if it doesn't exist
    if [ ! -f frontend/src/App.js ]; then
        cat > frontend/src/App.js << 'EOF'
import React from 'react';
import { Container } from 'react-bootstrap';

function App() {
    return (
        <Container className="mt-4">
            <h1>🧬 UGENE Web Platform</h1>
            <p>Welcome to the modern bioinformatics platform!</p>
        </Container>
    );
}

export default App;
EOF
    fi
    
    print_success "Basic frontend files created"
}

# Stop any existing containers
stop_existing() {
    print_status "Stopping any existing containers..."
    $COMPOSE_CMD down --remove-orphans || true
    print_success "Existing containers stopped"
}

# Build and start services
start_services() {
    print_status "Building and starting services..."
    
    # Build the images
    $COMPOSE_CMD build
    
    # Start the services
    $COMPOSE_CMD up -d
    
    print_success "Services started successfully!"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for backend to be healthy
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            print_success "Backend is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "Backend health check timeout, but it might still be starting..."
        fi
        sleep 2
    done
    
    # Wait for frontend to be ready
    for i in {1..30}; do
        if curl -f http://localhost:3000 &> /dev/null; then
            print_success "Frontend is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "Frontend health check timeout, but it might still be starting..."
        fi
        sleep 2
    done
}

# Show service status
show_status() {
    print_status "Service Status:"
    $COMPOSE_CMD ps
    
    echo ""
    print_success "🎉 UGENE Web Platform is running!"
    echo ""
    echo "📍 Access Points:"
    echo "   🌐 Frontend:        http://localhost:3000"
    echo "   🔧 Backend API:     http://localhost:8000"
    echo "   📖 API Docs:        http://localhost:8000/docs"
    echo "   ❤️  Health Check:   http://localhost:8000/health"
    echo ""
    echo "📊 Database Access:"
    echo "   🗄️  MongoDB:        mongodb://localhost:27017"
    echo "   🔄 Redis:          redis://localhost:6379"
    echo ""
    echo "🔍 Useful Commands:"
    echo "   📋 View logs:       $COMPOSE_CMD logs -f"
    echo "   🔄 Restart:         $COMPOSE_CMD restart"
    echo "   🛑 Stop:            $COMPOSE_CMD down"
    echo "   🏗️  Rebuild:        $COMPOSE_CMD build --no-cache"
}

# Cleanup function
cleanup() {
    print_warning "Received interrupt signal. Cleaning up..."
    $COMPOSE_CMD down
    exit 0
}

# Trap cleanup function on script exit
trap cleanup INT TERM

# Main execution
main() {
    echo "🧬 UGENE Web Platform Development Setup"
    echo "======================================"
    echo ""
    
    check_docker
    check_docker_compose
    create_directories
    create_backend_files
    create_frontend_files
    stop_existing
    start_services
    wait_for_services
    show_status
    
    echo ""
    print_success "Setup complete! Press Ctrl+C to stop all services."
    
    # Keep script running to maintain services
    while true; do
        sleep 30
        # Quick health check
        if ! curl -f http://localhost:8000/health &> /dev/null; then
            print_warning "Backend health check failed"
        fi
    done
}

# Run main function
main "$@"