# UGENE Workflow Designer - Production-Ready Web Application

A modern, full-stack web application for building and executing bioinformatics workflows using the UGENE toolkit. This application provides a drag-and-drop interface for creating complex bioinformatics pipelines, real-time task monitoring, and integrated visualization tools.

## 🏗️ Architecture Overview

### Backend (Python/FastAPI)
- **Object-Oriented Design**: Robust OOP architecture with TaskManager, UgeneRunner, and service classes
- **Task Management**: Persistent task queue using Redis Queue (RQ) for background processing  
- **Database**: MongoDB for storing workflow definitions, task metadata, and user data
- **API**: RESTful endpoints for workflow submission, task monitoring, and file management
- **Docker Integration**: UGENE SDK runs in isolated Docker containers

### Frontend (React 18)
- **Modern React**: Functional components with hooks, Context API for state management
- **Bootstrap 5**: Clean, responsive UI with consistent styling
- **Real-time Updates**: Live task status monitoring and notifications
- **Visualization**: Integrated IGV genome browser, JBrowse, and UMAP analysis
- **File Management**: Upload, download, and organize workflow input/output files

## 🚀 Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed
- At least 8GB RAM and 4GB free disk space
- Modern web browser (Chrome/Firefox/Safari)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ugene-workflow-designer

# Copy environment file
cp .env.example .env

# Edit environment variables as needed
nano .env
```

### 2. Build and Launch

```bash
# Build all services
docker-compose build

# Start the application stack
docker-compose up -d

# Check service health
docker-compose ps
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Manual Development Setup

### Backend Setup

```bash
cd backend

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
export MONGODB_URL="mongodb://localhost:27017"
export REDIS_URL="redis://localhost:6379"
export DATABASE_NAME="ugene_workflows"

# Start MongoDB and Redis
docker run -d -p 27017:27017 --name mongo mongo:6.0
docker run -d -p 6379:6379 --name redis redis:7-alpine

# Initialize database
python -c "from app.database import init_database; import asyncio; asyncio.run(init_database())"

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal, start worker process
python -m app.worker
```

### Frontend Setup

```bash
cd frontend

# Install Node.js dependencies
npm install

# Set environment variables
echo "REACT_APP_API_URL=http://localhost:8000" > .env.local

# Start development server
npm start
```

### UGENE SDK Setup

```bash
# Download UGENE SDK
cd ugene-sdk
curl -L -o ugene-sdk.tar.gz "https://github.com/ugeneunipro/ugene/releases/download/51.0/ugene-51.0-linux-x86-64.tar.gz"
tar -xzf ugene-sdk.tar.gz

# Build Docker image
docker build -t ugene_sdk_docker_image .
```

## 📊 API Documentation

### Core Endpoints

#### Workflow Management
- `POST /workflows/` - Submit workflow for execution
- `GET /tasks/` - List all tasks with pagination
- `GET /tasks/{task_id}` - Get task details and status
- `GET /tasks/{task_id}/results` - Get task output files
- `GET /download/{task_id}/{filename}` - Download result file

#### File Management
- `POST /upload` - Upload input files
- `POST /data/umap` - Process CSV for UMAP analysis

#### System Health
- `GET /health` - Check system status

### Example API Usage

```javascript
// Submit a workflow
const workflow = {
  nodes: [
    {
      id: 1,
      name: "Read FASTQ File with SE Reads",
      type: "reader",
      position: { x: 100, y: 100 }
    },
    {
      id: 2, 
      name: "Align with MUSCLE",
      type: "aligner",
      position: { x: 300, y: 100 }
    }
  ],
  connections: [{ from: 1, to: 2 }]
};

const response = await fetch('/workflows/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    nodes: workflow.nodes,
    connections: workflow.connections,
    priority: 'medium'
  })
});

const result = await response.json();
console.log('Task ID:', result.task_id);
```

## 🎨 Frontend Components

### Main Components

#### Genomics.js (Main Workflow Designer)
- Drag-and-drop workflow builder
- Visual connection system between elements
- Real-time canvas updates
- Bootstrap 5 styling throughout

#### RunningProcesses.js
- Live task monitoring with real API data
- Progress indicators and status badges
- Auto-refresh functionality

#### LogViewer.js  
- Real-time log streaming from tasks
- Filtering and search capabilities
- Download logs functionality

#### Visualization Components
- **IGVViewer.js**: Integrated Genome Browser
- **JBrowseViewer.js**: Advanced genome visualization
- **UmapGenomeVisualization.js**: Dimensionality reduction plots

### State Management

The application uses React Context API for centralized state management:

```javascript
const { state, actions } = useAppContext();

// Submit workflow
await actions.submitWorkflow('high');

// Load tasks
await actions.loadTasks(1, 10);

// Add notification
actions.addNotification({
  type: 'success',
  title: 'Task Complete',
  message: 'Workflow execution finished'
});
```

## 🐳 Docker Configuration

### Services Overview

1. **MongoDB**: Primary database for task/workflow storage
2. **Redis**: Message queue for background task processing  
3. **UGENE SDK**: Containerized bioinformatics toolkit
4. **Backend**: FastAPI application server
5. **Worker**: Background task processor
6. **Frontend**: React application (production build)
7. **Nginx**: Reverse proxy and static file server

### Volume Mounts
- `mongodb_data`: Persistent MongoDB storage
- `redis_data`: Redis data persistence  
- `ugene_workdir`: Shared workspace for UGENE executions
- `upload_storage`: User file uploads

## 🔒 Production Deployment

### Security Considerations

1. **Environment Variables**: Store secrets in `.env` file
2. **CORS Configuration**: Restrict allowed origins
3. **File Upload Limits**: Configure max file sizes
4. **Database Security**: Use strong MongoDB credentials
5. **SSL/TLS**: Configure HTTPS in production

### Performance Optimization

1. **Database Indexing**: Indexes on task_id, status, timestamps
2. **Redis Caching**: Cache frequently accessed data
3. **File Storage**: Consider cloud storage for large files
4. **Container Resources**: Set appropriate CPU/memory limits
5. **Load Balancing**: Use multiple worker containers

### Monitoring and Logging

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f worker

# Monitor resource usage
docker stats

# Health checks
curl http://localhost:8000/health
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests  
```bash
cd frontend
npm test
```

### Integration Tests
```bash
# Test complete workflow submission
python tests/test_integration.py
```

## 🤝 Development Workflow

### Code Structure

```
ugene-workflow-designer/
├── backend/
│   ├── app/
│   │   ├── models/          # Pydantic models
│   │   ├── services/        # Business logic classes  
│   │   ├── utils/           # Utility functions
│   │   ├── main.py          # FastAPI application
│   │   └── worker.py        # Background task processor
│   ├── tests/               # Backend tests
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API service layer
│   │   ├── context/         # State management
│   │   └── data/            # Static data files
│   ├── public/              # Static assets
│   └── package.json         # Node.js dependencies
├── ugene-sdk/               # UGENE Docker setup
├── nginx/                   # Reverse proxy config
├── docker-compose.yml       # Container orchestration
└── README.md               # This file
```

### Adding New Workflow Elements

1. **Update Elements Data**:
```javascript
// frontend/src/data/elements.js
{
  name: 'My New Tool',
  subElements: [
    {
      name: 'New Analysis Tool',
      type: 'analyzer',
      properties: 'Tool description'
    }
  ]
}
```

2. **Add Command Mapping**:
```python
# backend/app/utils/ugene_commands.py
COMMAND_MAPPINGS = {
    'New Analysis Tool': 'analyze --tool=newtool'
}
```

3. **Update Validation**:
```python
# backend/app/utils/validators.py
supported_node_types.add('analyzer')
```

## 🐛 Troubleshooting

### Common Issues

**Docker Container Won't Start**
```bash
# Check logs
docker-compose logs service_name

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Database Connection Issues**  
```bash
# Check MongoDB status
docker exec -it ugene_mongodb mongosh
# Test connection: db.runCommand("ping")
```

**Task Processing Stuck**
```bash
# Restart worker
docker-compose restart worker

# Check Redis queue
docker exec -it ugene_redis redis-cli
# Command: LLEN default
```

**Frontend Build Errors**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## 📈 Performance Tuning

### Database Optimization
- Index frequently queried fields
- Use MongoDB aggregation for complex queries
- Consider read replicas for scaling

### Redis Configuration
- Adjust memory limits based on workload
- Configure persistence settings
- Monitor queue lengths

### Container Resources
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## 🔄 Updates and Maintenance

### Updating UGENE SDK
1. Check latest release: https://github.com/ugeneunipro/ugene/releases
2. Update Dockerfile with new version URL
3. Rebuild container: `docker-compose build ugene_sdk`

### Database Migrations
```python
# Create migration script
# backend/migrations/001_add_indexes.py
async def migrate():
    db = get_database()
    await db.tasks.create_index([("priority", 1), ("status", 1)])
```

### Backup Strategy
```bash
# MongoDB backup
docker exec ugene_mongodb mongodump --out /backup

# Redis backup  
docker exec ugene_redis redis-cli BGSAVE
```

## 📋 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- UGENE Development Team for the bioinformatics toolkit
- FastAPI and React communities for excellent frameworks
- Bootstrap team for the UI framework
- All open-source contributors

## 📞 Support

For issues and questions:
1. Check the [troubleshooting](#troubleshooting) section
2. Search existing GitHub issues
3. Create a new issue with detailed information
4. Contact the development team

---

**Built with ❤️ for the bioinformatics community**
