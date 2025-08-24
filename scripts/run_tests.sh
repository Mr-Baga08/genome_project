# scripts/run_tests.sh - Test Runner Script
"""
#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Running Bioinformatics Platform Tests${NC}"

# Check if test dependencies are installed
echo -e "${YELLOW}📦 Installing test dependencies...${NC}"
pip install -r test_requirements.txt

# Start test services (MongoDB, Redis)
echo -e "${YELLOW}🚀 Starting test services...${NC}"
docker-compose -f docker-compose.test.yml up -d mongodb redis

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 10

# Run tests with different markers
echo -e "${YELLOW}🔬 Running unit tests...${NC}"
pytest tests/unit/ -m "unit" --cov=app --cov-report=term-missing

echo -e "${YELLOW}🔗 Running integration tests...${NC}"
pytest tests/integration/ -m "integration"

echo -e "${YELLOW}🎭 Running end-to-end tests...${NC}"
pytest tests/e2e/ -m "e2e"

echo -e "${YELLOW}⚡ Running performance tests...${NC}"
pytest tests/performance/ -m "performance"

# Generate coverage report
echo -e "${YELLOW}📊 Generating coverage report...${NC}"
pytest --cov=app --cov-report=html --cov-report=term

# Cleanup test services
echo -e "${YELLOW}🧹 Cleaning up test services...${NC}"
docker-compose -f docker-compose.test.yml down

echo -e "${GREEN}✅ All tests completed!${NC}"
echo -e "📊 Coverage report available at: htmlcov/index.html"
"""
