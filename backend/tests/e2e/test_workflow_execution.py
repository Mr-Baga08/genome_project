# backend/tests/e2e/test_workflow_execution.py - End-to-End Tests
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app

class TestWorkflowExecution:
    """End-to-end tests for complete workflow execution"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.mark.e2e
    def test_complete_sequence_analysis_workflow(self, client):
        """Test complete sequence analysis workflow from upload to results"""
        
        # Step 1: Upload sequence file
        fasta_content = """>test_seq_1
ATCGATCGATCGATCGATCG
>test_seq_2
GCTAGCTAGCTAGCTAGCTA
"""
        
        files = {"file": ("test.fasta", fasta_content, "text/plain")}
        response = client.post("/api/v1/readers/alignment", files=files)
        assert response.status_code == 200
        
        sequences = response.json()
        assert len(sequences) == 2
        
        # Step 2: Create and execute workflow
        workflow_definition = {
            "name": "Basic Analysis Workflow",
            "nodes": [
                {
                    "type": "statistics",
                    "parameters": {}
                },
                {
                    "type": "blast_search", 
                    "parameters": {
                        "database": "nr",
                        "evalue": 1e-5
                    }
                }
            ],
            "connections": [
                {"from": "statistics", "to": "blast_search"}
            ]
        }
        
        workflow_request = {
            "workflow_definition": workflow_definition,
            "input_data": sequences
        }
        
        response = client.post("/api/v1/workflows/execute", json=workflow_request)
        assert response.status_code == 200
        
        execution_result = response.json()
        assert "workflow_id" in execution_result
        assert execution_result["status"] == "started"
        
        workflow_id = execution_result["workflow_id"]
        
        # Step 3: Poll for completion
        max_attempts = 30
        for attempt in range(max_attempts):
            response = client.get(f"/api/v1/workflows/{workflow_id}/status")
            
            if response.status_code == 200:
                status = response.json()
                
                if status["status"] in ["completed", "failed"]:
                    assert status["status"] == "completed"
                    assert len(status["results"]) > 0
                    break
                    
            time.sleep(1)
        else:
            pytest.fail("Workflow did not complete within expected time")
    
    @pytest.mark.e2e
    def test_error_handling_workflow(self, client):
        """Test workflow error handling"""
        
        # Create workflow with invalid element
        workflow_definition = {
            "name": "Invalid Workflow",
            "nodes": [
                {
                    "type": "invalid_element_type",
                    "parameters": {}
                }
            ],
            "connections": []
        }
        
        workflow_request = {
            "workflow_definition": workflow_definition,
            "input_data": []
        }
        
        response = client.post("/api/v1/workflows/execute", json=workflow_request)
        
        # Should either reject immediately or fail during execution
        if response.status_code == 200:
            # If accepted, should fail during execution
            workflow_id = response.json()["workflow_id"]
            
            # Poll for failure
            for _ in range(10):
                status_response = client.get(f"/api/v1/workflows/{workflow_id}/status")
                if status_response.status_code == 200:
                    status = status_response.json()
                    if status["status"] == "failed":
                        assert "error" in status
                        break
                time.sleep(0.5)
            else:
                pytest.fail("Workflow should have failed")
        else:
            # Immediate rejection is also acceptable
            assert response.status_code in [400, 422]