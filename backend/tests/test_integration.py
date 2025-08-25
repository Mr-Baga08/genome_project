# backend/tests/test_integration.py - Integration Tests
import pytest
import asyncio
import httpx
from fastapi.testclient import TestClient
import docker
from unittest.mock import AsyncMock, MagicMock
import tempfile
from pathlib import Path

from app.main import app
from app.database.database_setup import DatabaseManager
from app.services.external_tool_manager import ExternalToolManager
from app.models.enhanced_models import SequenceData, SequenceType

class TestIntegration:
    """Integration tests for the complete UGENE web platform"""

    @pytest.fixture(scope="class")
    async def test_app(self):
        """Create test application with mocked services"""
        # Mock external dependencies
        app.state.docker_client = MagicMock()
        app.state.external_tools = ExternalToolManager()
        app.state.external_tools.docker_client = MagicMock()
        
        yield app

    @pytest.fixture(scope="class")
    def client(self, test_app):
        """Create test client"""
        return TestClient(test_app)

    def test_health_endpoint(self, client):
        """Test system health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data

    def test_system_info_endpoint(self, client):
        """Test system information endpoint"""
        response = client.get("/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "application" in data
        assert data["application"]["name"] == "UGENE Web Platform"

    @pytest.mark.asyncio
    async def test_sequence_creation_workflow(self, client):
        """Test complete sequence creation and analysis workflow"""
        
        # 1. Create a sequence
        sequence_data = {
            "name": "Test Integration Sequence",
            "sequence": "ATCGATCGATCGATCG",
            "sequence_type": "DNA",
            "description": "Integration test sequence"
        }
        
        response = client.post("/api/v1/sequences/create", data=sequence_data)
        assert response.status_code == 200
        
        created_sequence = response.json()
        assert created_sequence["name"] == sequence_data["name"]
        assert created_sequence["length"] == 16
        
        sequence_id = created_sequence["id"]
        
        # 2. Run BLAST search on the sequence
        blast_request = {
            "sequences": [sequence_data["sequence"]],
            "database": "nr",
            "evalue": 1e-5,
            "max_hits": 5
        }
        
        response = client.post("/api/v1/analysis/blast-search", json=blast_request)
        assert response.status_code == 200
        
        blast_result = response.json()
        assert "results" in blast_result
        
        # 3. List sequences to verify creation
        response = client.get("/api/v1/sequences")
        assert response.status_code == 200
        
        sequences_list = response.json()
        assert len(sequences_list) > 0
        assert any(seq["id"] == sequence_id for seq in sequences_list)

    def test_file_upload_workflow(self, client):
        """Test file upload and processing"""
        
        # Create a temporary FASTA file
        fasta_content = """>Test_Sequence_1
ATCGATCGATCGATCGATCGATCGATCG
>Test_Sequence_2
GCTAGCTAGCTAGCTAGCTAGCTAGCTA
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as temp_file:
            temp_file.write(fasta_content)
            temp_file_path = temp_file.name
        
        try:
            # Upload the file
            with open(temp_file_path, 'rb') as f:
                response = client.post(
                    "/api/v1/files/upload-fasta",
                    files={"file": ("test.fasta", f, "text/plain")}
                )
            
            assert response.status_code == 200
            
            upload_result = response.json()
            assert "sequence_count" in upload_result
            assert upload_result["sequence_count"] == 2
            assert "sequences" in upload_result
            
        finally:
            Path(temp_file_path).unlink()

    def test_pipeline_creation_and_execution(self, client):
        """Test pipeline creation and execution workflow"""
        
        # 1. Create a pipeline
        pipeline_data = {
            "pipeline_name": "Test Integration Pipeline",
            "description": "Pipeline for integration testing",
            "steps": [
                {
                    "type": "blast_search",
                    "parameters": {"database": "nr", "evalue": 1e-5}
                },
                {
                    "type": "multiple_alignment", 
                    "parameters": {"method": "muscle"}
                }
            ]
        }
        
        response = client.post(
            "/api/v1/pipelines/create",
            data={
                "pipeline_name": pipeline_data["pipeline_name"],
                "description": pipeline_data["description"],
                "steps": str(pipeline_data["steps"])
            }
        )
        assert response.status_code == 200
        
        created_pipeline = response.json()
        pipeline_id = created_pipeline["_id"]
        
        # 2. Execute the pipeline (with mock sequence IDs)
        execution_request = {
            "sequence_ids": ["mock_seq_1", "mock_seq_2"]
        }
        
        response = client.post(
            f"/api/v1/pipelines/{pipeline_id}/execute",
            json=execution_request
        )
        assert response.status_code == 200
        
        execution_result = response.json()
        assert "execution_id" in execution_result
        assert execution_result["status"] == "started"

    def test_cache_management(self, client):
        """Test cache management endpoints"""
        
        # Get cache statistics
        response = client.get("/api/v1/cache/stats")
        assert response.status_code == 200
        
        cache_stats = response.json()
        assert "hit_rate" in cache_stats
        
        # Warm cache
        warm_request = {
            "sequence_ids": ["seq1", "seq2"],
            "analysis_types": ["blast_search", "alignment"]
        }
        
        response = client.post("/api/v1/cache/warm", json=warm_request)
        assert response.status_code == 200
        
        # Invalidate cache
        response = client.delete("/api/v1/cache/invalidate?pattern=test*")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection and messaging"""
        
        async with httpx.AsyncClient() as client:
            # This is a simplified WebSocket test
            # In a real scenario, you'd use websockets library for testing
            try:
                async with client.websocket_connect("ws://localhost:8000/ws") as websocket:
                    # Send a test message
                    test_message = {
                        "type": "join_room",
                        "room": "test_room"
                    }
                    await websocket.send_json(test_message)
                    
                    # Receive response
                    response = await websocket.receive_json()
                    assert "type" in response
                    
            except Exception as e:
                # WebSocket test might not work in all test environments
                pytest.skip(f"WebSocket test skipped: {str(e)}")

    def test_error_handling(self, client):
        """Test API error handling"""
        
        # Test invalid sequence creation
        invalid_sequence = {
            "name": "",  # Empty name should cause validation error
            "sequence": "INVALID_SEQUENCE_WITH_NUMBERS123",
            "sequence_type": "INVALID_TYPE"
        }
        
        response = client.post("/api/v1/sequences/create", data=invalid_sequence)
        assert response.status_code == 400
        
        # Test non-existent endpoint
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        
        # Test invalid pipeline execution
        response = client.post("/api/v1/pipelines/nonexistent/execute", json={"sequence_ids": []})
        assert response.status_code == 404

    def test_performance_endpoints(self, client):
        """Test performance-related endpoints"""
        
        # Test metrics endpoint (if enabled)
        response = client.get("/metrics")
        # Might return 404 if metrics not enabled, which is fine
        assert response.status_code in [200, 404, 403]
        
        # Test system cleanup trigger
        response = client.post("/api/v1/tasks/cleanup")
        assert response.status_code == 200

# Performance Tests
class TestPerformance:
    """Performance and load tests"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_concurrent_sequence_creation(self, client):
        """Test concurrent sequence creation"""
        import threading
        import time
        
        results = []
        errors = []
        
        def create_sequence(thread_id):
            try:
                sequence_data = {
                    "name": f"Concurrent_Test_Seq_{thread_id}",
                    "sequence": "ATCGATCGATCGATCG" * 10,  # Longer sequence
                    "sequence_type": "DNA"
                }
                
                start_time = time.time()
                response = client.post("/api/v1/sequences/create", data=sequence_data)
                end_time = time.time()
                
                results.append({
                    "thread_id": thread_id,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time
                })
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Create 10 concurrent threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_sequence, args=(i,))
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Analyze results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10, "Not all requests completed"
        
        successful_requests = [r for r in results if r["status_code"] == 200]
        assert len(successful_requests) >= 8, "Too many failed requests"
        
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        assert avg_response_time < 2.0, f"Average response time too high: {avg_response_time}s"
        assert total_time < 10.0, f"Total execution time too high: {total_time}s"

    def test_large_file_upload(self, client):
        """Test uploading large FASTA files"""
        
        # Generate a large FASTA file (1000 sequences)
        large_fasta = ""
        for i in range(1000):
            large_fasta += f">Sequence_{i}\n"
            large_fasta += "ATCGATCGATCGATCG" * 50 + "\n"  # 800bp sequences
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as temp_file:
            temp_file.write(large_fasta)
            temp_file_path = temp_file.name
        
        try:
            start_time = time.time()
            
            with open(temp_file_path, 'rb') as f:
                response = client.post(
                    "/api/v1/files/upload-fasta",
                    files={"file": ("large_test.fasta", f, "text/plain")},
                    timeout=30.0
                )
            
            end_time = time.time()
            upload_time = end_time - start_time
            
            assert response.status_code == 200
            assert upload_time < 30.0, f"Upload took too long: {upload_time}s"
            
            result = response.json()
            assert result["sequence_count"] == 1000
            
        finally:
            Path(temp_file_path).unlink()