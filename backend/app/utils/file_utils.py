# backend/app/utils/file_utils.py
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
import mimetypes

class FileManager:
    """Utility class for file operations"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> Path:
        """Save uploaded file and return path"""
        safe_filename = self.sanitize_filename(filename)
        file_path = self.base_dir / safe_filename
        
        # Handle file name conflicts
        counter = 1
        original_path = file_path
        while file_path.exists():
            name_parts = original_path.stem, counter, original_path.suffix
            file_path = original_path.parent / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
            counter += 1
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return file_path
    
    def sanitize_filename(self, filename: str) -> str:
        """Remove potentially dangerous characters from filename"""
        # Remove path traversal characters
        safe_name = os.path.basename(filename)
        
        # Replace dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
        for char in dangerous_chars:
            safe_name = safe_name.replace(char, '_')
        
        return safe_name
    
    def get_file_info(self, file_path: Path) -> dict:
        """Get information about a file"""
        if not file_path.exists():
            return {}
        
        stat = file_path.stat()
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        return {
            'name': file_path.name,
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'mime_type': mime_type,
            'extension': file_path.suffix.lower()
        }
    
    def create_temp_workspace(self, prefix: str = "ugene_") -> Path:
        """Create a temporary workspace directory"""
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=self.base_dir))
        return temp_dir
    
    def cleanup_workspace(self, workspace_path: Path):
        """Clean up a workspace directory"""
        if workspace_path.exists():
            shutil.rmtree(workspace_path, ignore_errors=True)
    
    def list_files(self, directory: Path, pattern: str = "*") -> List[Path]:
        """List files in directory matching pattern"""
        if not directory.exists():
            return []
        
        return list(directory.glob(pattern))

