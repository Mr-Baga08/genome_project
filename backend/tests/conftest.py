# backend/tests/conftest.py - Pytest Configuration
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from httpx import AsyncClient
import motor.motor_asyncio
import redis
from unittest.mock import AsyncMock, MagicMock
import json

from app.main import app
from app.database.database_setup import DatabaseManager
from app.services.workflow_engine import WorkflowEngine
from app.models.enhanced_models import SequenceData, SequenceType, EnhancedTask
from app.websockets.connection_manager import ConnectionManager

# Test Configuration
TEST_DATABASE_URL = "mongodb://localhost:27017"
TEST_DATABASE_NAME = "test_ugene_workflows"
TEST_REDIS_URL = "redis://localhost:6379/15"  # Use database 15 for tests

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_database():
    """Setup test database"""
    client = motor.motor_asyncio.AsyncIOMotorClient(TEST_DATABASE_URL)
    database = client[TEST_DATABASE_NAME]
    
    # Setup collections and indexes
    db_manager = DatabaseManager(TEST_DATABASE_URL, TEST_DATABASE_NAME)
    await db_manager.initialize_database()
    
    yield database
    
    # Cleanup
    await client.drop_database(TEST_DATABASE_NAME)
    client.close()

@pytest.fixture(scope="session")
def test_redis():
    """Setup test Redis connection"""
    redis_client = redis.Redis.from_url(TEST_REDIS_URL)
    
    # Clear test database
    redis_client.flushdb()
    
    yield redis_client
    
    # Cleanup
    redis_client.flushdb()
    redis_client.close()

@pytest.fixture
async def test_client():
    """Create test FastAPI client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def sync_test_client():
    """Create synchronous test client for non-async tests"""
    return TestClient(app)

@pytest.fixture
def temp_directory():
    """Create temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_sequences():
    """Generate sample sequence data for testing"""
    return [
        SequenceData(
            name="Test DNA Sequence 1",
            sequence="ATCGATCGATCGATCG",
            sequence_type=SequenceType.DNA,
            description="Test sequence for unit testing"
        ),
        SequenceData(
            name="Test Protein Sequence 1", 
            sequence="MKLLVLGLFLALSLSLA",
            sequence_type=SequenceType.PROTEIN,
            description="Test protein sequence"
        ),
        SequenceData(
            name="Test RNA Sequence 1",
            sequence="AUCGAUCGAUCGAUCG",
            sequence_type=SequenceType.RNA,
            description="Test RNA sequence"
        )
    ]

@pytest.fixture
def sample_fasta_content():
    """Sample FASTA file content for testing"""
    return """>seq1 Test sequence 1
ATCGATCGATCGATCG
>seq2 Test sequence 2
GCTAGCTAGCTAGCTA
>seq3 Test sequence 3
TTAACCGGTTAACCGG
"""

@pytest.fixture
def sample_fastq_content():
    """Sample FASTQ file content for testing"""
    return """@seq1
ATCGATCGATCGATCG
+
IIIIIIIIIIIIIIII
@seq2
GCTAGCTAGCTAGCTA
+
HHHHHHHHHHHHHHHH
"""

@pytest.fixture
def sample_gff_content():
    """Sample GFF3 file content for testing"""
    return """##gff-version 3
chr1	test	gene	1000	2000	.	+	.	ID=gene1;Name=test_gene
chr1	test	CDS	1200	1800	.	+	0	ID=cds1;Parent=gene1
chr2	test	gene	3000	4000	.	-	.	ID=gene2;Name=another_gene
"""

@pytest.fixture
async def mock_workflow_engine(test_database, test_redis):
    """Create mock workflow engine for testing"""
    mock_logger = MagicMock()
    engine = WorkflowEngine(test_database, test_redis, mock_logger)
    return engine

@pytest.fixture
def mock_docker_client():
    """Mock Docker client for testing external tool integration"""
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.wait.return_value = {'StatusCode': 0}
    mock_container.logs.return_value = b"Mock tool output"
    mock_client.containers.run.return_value = mock_container
    return mock_client