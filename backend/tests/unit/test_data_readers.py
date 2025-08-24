# backend/tests/unit/test_data_readers.py - Unit Tests for Data Readers
import pytest
import io
from unittest.mock import patch, AsyncMock
from app.services.data_readers import DataReaderService

class TestDataReaderService:
    """Unit tests for DataReaderService"""
    
    @pytest.mark.asyncio
    async def test_read_fasta_alignment(self, sample_fasta_content):
        """Test reading FASTA alignment files"""
        result = await DataReaderService.read_alignment(sample_fasta_content, "fasta")
        
        assert len(result) == 3
        assert result[0]["id"] == "seq1"
        assert result[0]["sequence"] == "ATCGATCGATCGATCG"
        assert result[0]["length"] == 16
        assert "Test sequence 1" in result[0]["description"]
    
    @pytest.mark.asyncio
    async def test_read_empty_fasta(self):
        """Test reading empty FASTA file"""
        empty_content = ""
        result = await DataReaderService.read_alignment(empty_content, "fasta")
        assert result == []
    
    @pytest.mark.asyncio
    async def test_read_invalid_fasta(self):
        """Test reading invalid FASTA content"""
        invalid_content = "This is not a valid FASTA file"
        with pytest.raises(Exception):
            await DataReaderService.read_alignment(invalid_content, "fasta")
    
    @pytest.mark.asyncio
    async def test_read_gff_annotations(self, sample_gff_content):
        """Test reading GFF3 annotation files"""
        result = await DataReaderService.read_annotations(sample_gff_content, "gff3")
        
        assert len(result) == 3
        assert result[0]["seqid"] == "chr1"
        assert result[0]["type"] == "gene"
        assert result[0]["start"] == 1000
        assert result[0]["end"] == 2000
        assert result[0]["attributes"]["ID"] == "gene1"
    
    @pytest.mark.asyncio
    async def test_read_fastq_se_reads(self, sample_fastq_content):
        """Test reading single-end FASTQ files"""
        result = await DataReaderService.read_fastq_se_reads(sample_fastq_content)
        
        assert len(result) == 2
        assert result[0]["id"] == "seq1"
        assert result[0]["sequence"] == "ATCGATCGATCGATCG"
        assert result[0]["length"] == 16
        assert len(result[0]["quality"]) > 0
    
    @pytest.mark.asyncio
    async def test_read_fastq_pe_reads(self, sample_fastq_content):
        """Test reading paired-end FASTQ files"""
        result = await DataReaderService.read_fastq_pe_reads(sample_fastq_content, sample_fastq_content)
        
        assert len(result) == 2
        assert result[0]["pair_id"] == "seq1"
        assert "r1" in result[0]
        assert "r2" in result[0]
        assert result[0]["r1"]["sequence"] == "ATCGATCGATCGATCG"
    
    @pytest.mark.asyncio
    async def test_calculate_gc_content(self):
        """Test GC content calculation"""
        # 50% GC content
        sequence = "ATCG"
        gc_content = DataReaderService._calculate_gc_content(sequence)
        assert gc_content == 50.0
        
        # 0% GC content
        sequence = "ATAT"
        gc_content = DataReaderService._calculate_gc_content(sequence)
        assert gc_content == 0.0
        
        # 100% GC content
        sequence = "GCGC"
        gc_content = DataReaderService._calculate_gc_content(sequence)
        assert gc_content == 100.0
    
    @pytest.mark.asyncio
    async def test_parse_gff_attributes(self):
        """Test GFF attributes parsing"""
        attr_string = "ID=gene1;Name=test_gene;Note=description"
        attributes = DataReaderService._parse_gff_attributes(attr_string)
        
        assert attributes["ID"] == "gene1"
        assert attributes["Name"] == "test_gene"
        assert attributes["Note"] == "description"

