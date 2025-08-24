# backend/tests/integration/test_api_endpoints.py - Integration Tests
import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

class TestAPIEndpoints:
    """Integration tests for API endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
    
    def test_get_workflow_elements(self, client):
        """Test getting available workflow elements"""
        response = client.get("/api/v1/workflow/elements")
        assert response.status_code == 200
        
        data = response.json()
        assert "Data Readers" in data
        assert "Analysis Tools" in data
        assert "Data Flow" in data
    
    @pytest.mark.asyncio
    async def test_sequence_crud_operations(self, test_client):
        """Test complete CRUD operations for sequences"""
        
        # Create sequence
        sequence_data = {
            "name": "Test Sequence",
            "sequence": "ATCGATCGATCG",
            "sequence_type": "DNA",
            "description": "Integration test sequence"
        }
        
        response = await test_client.post("/api/v1/sequences", json=sequence_data)
        assert response.status_code == 201
        created_sequence = response.json()
        sequence_id = created_sequence["id"]
        
        # Read sequence
        response = await test_client.get(f"/api/v1/sequences/{sequence_id}")
        assert response.status_code == 200
        retrieved_sequence = response.json()
        assert retrieved_sequence["name"] == "Test Sequence"
        assert retrieved_sequence["length"] == 12
        
        # Update sequence
        update_data = {"description": "Updated description"}
        response = await test_client.put(f"/api/v1/sequences/{sequence_id}", json=update_data)
        assert response.status_code == 200
        
        # Delete sequence
        response = await test_client.delete(f"/api/v1/sequences/{sequence_id}")
        assert response.status_code == 204
        
        # Verify deletion
        response = await test_client.get(f"/api/v1/sequences/{sequence_id}")
        assert response.status_code == 404
    
    def test_workflow_validation(self, client):
        """Test workflow definition validation"""
        valid_workflow = {
            "name": "Test Workflow",
            "nodes": [
                {
                    "type": "statistics",
                    "parameters": {}
                }
            ],
            "connections": []
        }
        
        response = client.post("/api/v1/workflows/validate", json=valid_workflow)
        assert response.status_code == 200
        
        validation_result = response.json()
        assert validation_result["valid"] == True
        
        # Test invalid workflow
        invalid_workflow = {
            "name": "Invalid Workflow",
            "nodes": [
                {
                    "type": "invalid_type",
                    "parameters": {}
                }
            ],
            "connections": []
        }
        
        response = client.post("/api/v1/workflows/validate", json=invalid_workflow)
        assert response.status_code == 200
        
        validation_result = response.json()
        assert validation_result["valid"] == False
        assert len(validation_result["errors"]) > 0
