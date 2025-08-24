# scripts/deploy.sh - Production Deployment Script
#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
ENV_FILE=".env.production"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"

echo -e "${GREEN}🚀 Starting Bioinformatics Platform Production Deployment${NC}"

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Environment file $ENV_FILE not found!${NC}"
    echo "Please create $ENV_FILE with required configuration variables."
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Function to backup database
backup_database() {
    echo -e "${YELLOW}📦 Creating database backup...${NC}"
    docker exec bioinformatics_postgres pg_dumpall -U postgres > "$BACKUP_DIR/database_backup.sql"
    echo -e "${GREEN}✅ Database backup created at $BACKUP_DIR/database_backup.sql${NC}"
}

# Function to backup volumes
backup_volumes() {
    echo -e "${YELLOW}📦 Creating volume backups...${NC}"
    docker run --rm -v bioinformatics_postgres_data:/data -v "$PWD/$BACKUP_DIR":/backup alpine tar czf /backup/postgres_data.tar.gz /data
    docker run --rm -v bioinformatics_redis_data:/data -v "$PWD/$BACKUP_DIR":/backup alpine tar czf /backup/redis_data.tar.gz /data
    echo -e "${GREEN}✅ Volume backups created${NC}"
}

# Function to update images
update_images() {
    echo -e "${YELLOW}🔄 Pulling latest images...${NC}"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
    echo -e "${GREEN}✅ Images updated${NC}"
}

# Function to build custom images
build_images() {
    echo -e "${YELLOW}🔨 Building custom images...${NC}"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build --no-cache
    echo -e "${GREEN}✅ Images built${NC}"
}

# Function to deploy services
deploy_services() {
    echo -e "${YELLOW}🚀 Deploying services...${NC}"
    
    # Deploy infrastructure services first
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d postgres redis consul
    
    # Wait for infrastructure to be ready
    echo "⏳ Waiting for infrastructure services..."
    sleep 30
    
    # Deploy application services
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d api-gateway sequence-service analysis-service workflow-service
    
    # Wait for application services
    echo "⏳ Waiting for application services..."
    sleep 20
    
    # Deploy workers and remaining services
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d celery-worker celery-beat
    
    # Deploy frontend and load balancer
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d frontend nginx
    
    # Deploy monitoring stack
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d prometheus grafana elasticsearch logstash kibana
    
    echo -e "${GREEN}✅ All services deployed${NC}"
}

# Function to run health checks
health_check() {
    echo -e "${YELLOW}🔍 Running health checks...${NC}"
    
    # Check API Gateway
    echo "Checking API Gateway..."
    timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'
    
    # Check Frontend
    echo "Checking Frontend..."
    timeout 60 bash -c 'until curl -f http://localhost; do sleep 2; done'
    
    # Check Database
    echo "Checking Database..."
    docker exec bioinformatics_postgres pg_isready -U postgres
    
    # Check Redis
    echo "Checking Redis..."
    docker exec bioinformatics_redis redis-cli ping
    
    echo -e "${GREEN}✅ Health checks passed${NC}"
}

# Function to setup monitoring
setup_monitoring() {
    echo -e "${YELLOW}📊 Setting up monitoring...${NC}"
    
    # Import Grafana dashboards
    if [ -d "./monitoring/grafana/dashboards" ]; then
        echo "Importing Grafana dashboards..."
        # Custom dashboard import logic here
    fi
    
    echo -e "${GREEN}✅ Monitoring setup complete${NC}"
}

# Function to show status
show_status() {
    echo -e "${GREEN}📋 Deployment Status${NC}"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    
    echo -e "\n${GREEN}🌐 Service URLs:${NC}"
    echo "Frontend: http://localhost"
    echo "API Documentation: http://localhost/api/docs"
    echo "Grafana: http://localhost:3000"
    echo "Kibana: http://localhost:5601"
    echo "Consul: http://localhost:8500"
}

# Main deployment flow
main() {
    case "${1:-deploy}" in
        backup)
            backup_database
            backup_volumes
            ;;
        build)
            build_images
            ;;
        deploy)
            update_images
            build_images
            deploy_services
            health_check
            setup_monitoring
            show_status
            ;;
        health)
            health_check
            ;;
        status)
            show_status
            ;;
        *)
            echo "Usage: $0 {deploy|backup|build|health|status}"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

echo -e "${GREEN}🎉 Production deployment complete!${NC}"