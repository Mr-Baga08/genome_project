# backend/tests/performance/test_performance.py - Performance Tests
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from app.services.data_readers import DataReaderService
from app.services.analysis_tools import AnalysisToolsService

class TestPerformance:
    """Performance tests for critical components"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_large_fasta_processing_performance(self):
        """Test processing large FASTA files"""
        # Generate large FASTA content (1000 sequences)
        large_fasta = ""
        for i in range(1000):
            large_fasta += f">seq_{i}\n"
            large_fasta += "ATCGATCG" * 125 + "\n"  # 1000 bp sequences
        
        start_time = time.time()
        
        result = await DataReaderService.read_alignment(large_fasta, "fasta")
        
        processing_time = time.time() - start_time
        
        assert len(result) == 1000
        assert processing_time < 5.0  # Should process within 5 seconds
        print(f"Processed 1000 sequences in {processing_time:.2f} seconds")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_sequence_processing(self, sample_sequences):
        """Test concurrent sequence processing"""
        analysis_service = AnalysisToolsService()
        
        # Test concurrent BLAST searches
        async def run_blast_search():
            sequences = ["ATCGATCG" * 10] * 5  # 5 sequences per search
            return await analysis_service.run_blast_search(sequences, "nr")
        
        start_time = time.time()
        
        # Run 10 concurrent BLAST searches
        tasks = [run_blast_search() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        processing_time = time.time() - start_time
        
        assert len(results) == 10
        assert processing_time < 30.0  # Should complete within 30 seconds
        print(f"Completed 10 concurrent BLAST searches in {processing_time:.2f} seconds")
    
    @pytest.mark.performance
    def test_memory_usage_large_dataset(self):
        """Test memory usage with large datasets"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset
        large_dataset = []
        for i in range(10000):
            large_dataset.append({
                "id": f"seq_{i}",
                "sequence": "ATCGATCG" * 1000,  # 8kb per sequence
                "metadata": {"length": 8000, "gc_content": 50.0}
            })
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_usage = peak_memory - initial_memory
        
        # Memory usage should be reasonable (less than 500MB for this dataset)
        assert memory_usage < 500
        print(f"Memory usage for 10K sequences: {memory_usage:.2f} MB")
        
        # Cleanup
        del large_dataset