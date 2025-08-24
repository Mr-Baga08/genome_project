# backend/tests/unit/test_workflow_engine.py - Unit Tests for Workflow Engine
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.workflow_engine import WorkflowEngine

class TestWorkflowEngine:
    """Unit tests for WorkflowEngine"""
    
    @pytest.fixture
    def workflow_engine(self):
        """Create workflow engine with mocked dependencies"""
        mock_db = AsyncMock()
        mock_cache = MagicMock()
        mock_logger = MagicMock()
        
        engine = WorkflowEngine(mock_db, mock_cache, mock_logger)
        return engine
    
    @pytest.mark.asyncio
    async def test_workflow_execution_success(self, workflow_engine):
        """Test successful workflow execution"""
        workflow_definition = {
            "nodes": [
                {
                    "type": "statistics",
                    "parameters": {}
                }
            ]
        }
        
        input_data = [
            {"sequence": "ATCGATCG", "id": "seq1"},
            {"sequence": "GCTAGCTA", "id": "seq2"}
        ]
        
        workflow_id = await workflow_engine.execute_workflow(workflow_definition, input_data, "user123")
        
        assert workflow_id is not None
        assert workflow_id in workflow_engine.active_workflows
        
        # Wait for workflow completion (with timeout)
        import asyncio
        await asyncio.sleep(0.1)
        
        workflow_status = workflow_engine.get_workflow_status(workflow_id)
        assert workflow_status is not None
    
    @pytest.mark.asyncio
    async def test_filter_sequences(self, workflow_engine):
        """Test sequence filtering functionality"""
        sequences = [
            {"sequence": "ATCG", "id": "seq1"},  # Length 4
            {"sequence": "ATCGATCGATCGATCG", "id": "seq2"},  # Length 16
            {"sequence": "AT", "id": "seq3"}  # Length 2
        ]
        
        criteria = {"min_length": 5}
        
        filtered = await workflow_engine._filter_sequences(sequences, criteria)
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == "seq2"
    
    @pytest.mark.asyncio
    async def test_calculate_statistics(self, workflow_engine):
        """Test sequence statistics calculation"""
        sequences = [
            {"sequence": "ATCG", "id": "seq1"},
            {"sequence": "ATCGATCGATCG", "id": "seq2"}
        ]
        
        stats = await workflow_engine._calculate_statistics(sequences)
        
        assert stats["sequence_count"] == 2
        assert stats["total_length"] == 16
        assert stats["average_length"] == 8.0
        assert stats["min_length"] == 4
        assert stats["max_length"] == 12
