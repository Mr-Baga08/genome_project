# backend/tests/unit/test_file_manager.py - File Management Tests
import pytest
import tempfile
from pathlib import Path
from fastapi import UploadFile
from io import BytesIO
from app.services.file_manager import FileManager

class TestFileManager:
    """Unit tests for FileManager"""
    
    @pytest.fixture
    def file_manager(self, temp_directory):
        """Create FileManager with temporary directories"""
        manager = FileManager()
        manager.upload_dir = temp_directory / "uploads"
        manager.data_dir = temp_directory / "data"
        manager.temp_dir = temp_directory / "temp"
        
        # Create directories
        for directory in [manager.upload_dir, manager.data_dir, manager.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        return manager
    
    @pytest.mark.asyncio
    async def test_upload_fasta_file(self, file_manager, sample_fasta_content):
        """Test uploading FASTA file"""
        file_content = sample_fasta_content.encode()
        file_obj = UploadFile(
            filename="test.fasta",
            file=BytesIO(file_content),
            size=len(file_content)
        )
        
        result = await file_manager.upload_file(file_obj, "user123", "sequences")
        
        assert result["original_name"] == "test.fasta"
        assert result["size"] == len(file_content)
        assert result["category"] == "sequences"
        assert result["user_id"] == "user123"
        assert "hash" in result
        assert result["format_info"]["format"] == "fasta"
    
    @pytest.mark.asyncio
    async def test_file_validation_size_limit(self, file_manager):
        """Test file size validation"""
        # Create file larger than limit
        large_content = b"A" * (file_manager.max_file_size + 1)
        file_obj = UploadFile(
            filename="large_file.fasta",
            file=BytesIO(large_content),
            size=len(large_content)
        )
        
        with pytest.raises(Exception) as exc_info:
            await file_manager.upload_file(file_obj)
        
        assert "exceeds maximum allowed size" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_file_validation_extension(self, file_manager):
        """Test file extension validation"""
        file_content = b"Invalid file content"
        file_obj = UploadFile(
            filename="test.invalid",
            file=BytesIO(file_content),
            size=len(file_content)
        )
        
        with pytest.raises(Exception) as exc_info:
            await file_manager.upload_file(file_obj)
        
        assert "is not allowed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_detect_fasta_format(self, file_manager, sample_fasta_content, temp_directory):
        """Test FASTA format detection"""
        fasta_file = temp_directory / "test.fasta"
        fasta_file.write_text(sample_fasta_content)
        
        format_info = await file_manager._detect_file_format(fasta_file)
        
        assert format_info["format"] == "fasta"
        assert format_info["details"]["sequence_count"] == 3
        assert "DNA" in format_info["details"]["detected_types"]
    
    @pytest.mark.asyncio
    async def test_cleanup_temp_files(self, file_manager):
        """Test temporary file cleanup"""
        # Create some temporary files
        temp_file1 = file_manager.temp_dir / "temp1.txt"
        temp_file2 = file_manager.temp_dir / "temp2.txt"
        
        temp_file1.write_text("temp content 1")
        temp_file2.write_text("temp content 2")
        
        # Both files should be cleaned up (max_age_hours=0 means clean all)
        deleted_count = await file_manager.cleanup_temp_files(max_age_hours=0)
        
        assert deleted_count == 2
        assert not temp_file1.exists()
        assert not temp_file2.exists()