# backend/tests/unit/test_analysis_tools.py - Unit Tests for Analysis Tools
import pytest
from unittest.mock import MagicMock, patch
from app.services.analysis_tools import AnalysisToolsService
from app.models.enhanced_models import SequenceData, SequenceType

class TestAnalysisToolsService:
    """Unit tests for AnalysisToolsService"""
    
    def setup_method(self):
        """Setup test method with mocked Docker client"""
        self.service = AnalysisToolsService()
        self.service.docker_client = MagicMock()
    
    @pytest.mark.asyncio
    async def test_blast_search_execution(self):
        """Test BLAST search execution"""
        sequences = ["ATCGATCGATCG", "GCTAGCTAGCTA"]
        database = "nr"
        parameters = {"evalue": "1e-5", "max_hits": 5}
        
        # Mock Docker container execution
        mock_container = MagicMock()
        mock_container.wait.return_value = {'StatusCode': 0}
        self.service.docker_client.containers.run.return_value = mock_container
        
        result = await self.service.run_blast_search(sequences, database, parameters)
        
        assert "results" in result
        assert len(result["results"]) == 2
        assert result["database"] == database
        assert result["parameters"] == parameters
    
    @pytest.mark.asyncio
    async def test_multiple_alignment_execution(self, sample_sequences):
        """Test multiple sequence alignment"""
        sequences = [seq.dict() for seq in sample_sequences]
        method = "muscle"
        parameters = {"gap_penalty": -10}
        
        result = await self.service.run_multiple_alignment(sequences, method, parameters)
        
        assert "aligned_sequences" in result
        assert len(result["aligned_sequences"]) == len(sequences)
        assert result["method"] == method
        assert "alignment_stats" in result
    
    def test_calculate_alignment_stats(self):
        """Test alignment statistics calculation"""
        aligned_sequences = [
            {"sequence": "ATCG--"},
            {"sequence": "A-CG--"},
            {"sequence": "ATCGAA"}
        ]
        
        stats = self.service._calculate_alignment_stats(aligned_sequences)
        
        assert stats["alignment_length"] == 6
        assert stats["num_sequences"] == 3
        assert "average_conservation" in stats
        assert "gap_percentage" in stats
    
    def test_calculate_gap_percentage(self):
        """Test gap percentage calculation"""
        aligned_sequences = [
            {"sequence": "AT-G"},
            {"sequence": "A--G"}
        ]
        
        gap_percentage = self.service._calculate_gap_percentage(aligned_sequences)
        
        # 3 gaps out of 8 total characters = 37.5%
        assert gap_percentage == 37.5
