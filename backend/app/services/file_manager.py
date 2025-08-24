# backend/app/services/file_manager.py
import os
import shutil
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional, BinaryIO
from fastapi import UploadFile, HTTPException
import magic
import zipfile
import tarfile
from datetime import datetime
import aiofiles
from ..core.config import settings

class FileManager:
    """Enhanced file management system for bioinformatics data"""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.data_dir = Path(settings.DATA_DIR)
        self.temp_dir = Path(settings.TEMP_DIR)
        
        # Create directories if they don't exist
        for directory in [self.upload_dir, self.data_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Allowed file types for bioinformatics
        self.allowed_extensions = {
            '.fasta', '.fa', '.fas', '.fna', '.ffn', '.faa',
            '.fastq', '.fq', '.fastq.gz', '.fq.gz',
            '.gff', '.gff3', '.gtf',
            '.bed', '.bedgraph', '.wig', '.bigwig',
            '.vcf', '.vcf.gz',
            '.sam', '.bam', '.cram',
            '.gb', '.gbk', '.genbank',
            '.csv', '.tsv', '.txt',
            '.json', '.xml',
            '.zip', '.tar.gz', '.tar'
        }
        
        self.max_file_size = settings.MAX_FILE_SIZE
    
    async def upload_file(self, file: UploadFile, user_id: str = None, category: str = "general") -> Dict[str, Any]:
        """Upload and validate bioinformatics file"""
        try:
            # Validate file
            validation_result = await self._validate_file(file)
            if not validation_result["valid"]:
                raise HTTPException(status_code=400, detail=validation_result["error"])
            
            # Generate unique filename
            file_hash = await self._calculate_file_hash(file)
            file_extension = Path(file.filename).suffix.lower()
            unique_filename = f"{file_hash}{file_extension}"
            
            # Determine storage path
            storage_path = self._get_storage_path(category, user_id)
            file_path = storage_path / unique_filename
            
            # Create directory if it doesn't exist
            storage_path.mkdir(parents=True, exist_ok=True)
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Create file metadata
            file_metadata = {
                "original_name": file.filename,
                "stored_name": unique_filename,
                "file_path": str(file_path),
                "size": len(content),
                "hash": file_hash,
                "mime_type": file.content_type or mimetypes.guess_type(file.filename)[0],
                "category": category,
                "user_id": user_id,
                "upload_time": datetime.utcnow().isoformat(),
                "format_info": await self._detect_file_format(file_path)
            }
            
            return file_metadata
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    
    async def upload_multiple_files(self, files: List[UploadFile], user_id: str = None, category: str = "general") -> List[Dict[str, Any]]:
        """Upload multiple files"""
        results = []
        for file in files:
            try:
                result = await self.upload_file(file, user_id, category)
                results.append(result)
            except Exception as e:
                results.append({
                    "original_name": file.filename,
                    "error": str(e),
                    "success": False
                })
        
        return results
    
    async def extract_archive(self, archive_path: Path, extract_to: Path = None) -> List[Dict[str, Any]]:
        """Extract ZIP or TAR archive and return extracted files info"""
        if extract_to is None:
            extract_to = self.temp_dir / f"extract_{datetime.now().timestamp()}"
        
        extract_to.mkdir(parents=True, exist_ok=True)
        extracted_files = []
        
        try:
            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
                    for file_info in zip_ref.infolist():
                        if not file_info.is_dir():
                            extracted_files.append({
                                "name": file_info.filename,
                                "size": file_info.file_size,
                                "path": str(extract_to / file_info.filename)
                            })
            
            elif archive_path.suffix.lower() in ['.tar', '.tar.gz']:
                mode = 'r:gz' if archive_path.suffix.endswith('.gz') else 'r'
                with tarfile.open(archive_path, mode) as tar_ref:
                    tar_ref.extractall(extract_to)
                    for member in tar_ref.getmembers():
                        if member.isfile():
                            extracted_files.append({
                                "name": member.name,
                                "size": member.size,
                                "path": str(extract_to / member.name)
                            })
            
            return extracted_files
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Archive extraction failed: {str(e)}")
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get detailed file information"""
        path = Path(file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        stat = path.stat()
        
        return {
            "name": path.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "mime_type": mimetypes.guess_type(str(path))[0],
            "format_info": await self._detect_file_format(path)
        }
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than specified hours"""
        deleted_count = 0
        current_time = datetime.now()
        
        for file_path in self.temp_dir.rglob("*"):
            if file_path.is_file():
                file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age.total_seconds() > (max_age_hours * 3600):
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception:
                        continue
        
        return deleted_count
    
    # Private helper methods
    async def _validate_file(self, file: UploadFile) -> Dict[str, Any]:
        """Validate uploaded file"""
        # Check file size
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        if len(content) > self.max_file_size:
            return {
                "valid": False,
                "error": f"File size ({len(content)} bytes) exceeds maximum allowed size ({self.max_file_size} bytes)"
            }
        
        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in self.allowed_extensions:
            return {
                "valid": False,
                "error": f"File extension '{file_extension}' is not allowed. Allowed extensions: {', '.join(self.allowed_extensions)}"
            }
        
        # Check file content using python-magic
        try:
            file_type = magic.from_buffer(content[:1024], mime=True)
            # Additional content validation can be added here
        except Exception:
            # If magic detection fails, continue with filename-based validation
            pass
        
        return {"valid": True}
    
    async def _calculate_file_hash(self, file: UploadFile) -> str:
        """Calculate MD5 hash of file content"""
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        return hashlib.md5(content).hexdigest()
    
    def _get_storage_path(self, category: str, user_id: str = None) -> Path:
        """Get storage path based on category and user"""
        if user_id:
            return self.upload_dir / category / user_id
        else:
            return self.upload_dir / category / "public"
    
    async def _detect_file_format(self, file_path: Path) -> Dict[str, Any]:
        """Detect and analyze bioinformatics file format"""
        format_info = {
            "format": "unknown",
            "details": {}
        }
        
        try:
            extension = file_path.suffix.lower()
            
            if extension in ['.fasta', '.fa', '.fas', '.fna', '.ffn', '.faa']:
                format_info = await self._analyze_fasta(file_path)
            elif extension in ['.fastq', '.fq']:
                format_info = await self._analyze_fastq(file_path)
            elif extension in ['.gff', '.gff3', '.gtf']:
                format_info = await self._analyze_gff(file_path)
            elif extension in ['.vcf']:
                format_info = await self._analyze_vcf(file_path)
            elif extension in ['.bed']:
                format_info = await self._analyze_bed(file_path)
            
        except Exception as e:
            format_info["error"] = str(e)
        
        return format_info
    
    async def _analyze_fasta(self, file_path: Path) -> Dict[str, Any]:
        """Analyze FASTA file format"""
        try:
            sequences = list(SeqIO.parse(file_path, "fasta"))
            
            if not sequences:
                return {"format": "fasta", "details": {"error": "No valid sequences found"}}
            
            # Calculate statistics
            lengths = [len(seq.seq) for seq in sequences]
            sequence_types = set()
            
            for seq in sequences[:10]:  # Sample first 10 sequences for type detection
                seq_str = str(seq.seq).upper()
                if set(seq_str).issubset(set('ATCGN')):
                    sequence_types.add('DNA')
                elif set(seq_str).issubset(set('AUCGN')):
                    sequence_types.add('RNA')
                elif set(seq_str).issubset(set('ACDEFGHIKLMNPQRSTVWY')):
                    sequence_types.add('PROTEIN')
            
            return {
                "format": "fasta",
                "details": {
                    "sequence_count": len(sequences),
                    "total_length": sum(lengths),
                    "average_length": sum(lengths) / len(lengths),
                    "min_length": min(lengths),
                    "max_length": max(lengths),
                    "detected_types": list(sequence_types)
                }
            }
            
        except Exception as e:
            return {"format": "fasta", "details": {"error": str(e)}}
    
    async def _analyze_fastq(self, file_path: Path) -> Dict[str, Any]:
        """Analyze FASTQ file format"""
        try:
            sequences = list(SeqIO.parse(file_path, "fastq"))
            
            if not sequences:
                return {"format": "fastq", "details": {"error": "No valid sequences found"}}
            
            # Calculate quality statistics
            lengths = [len(seq.seq) for seq in sequences]
            qualities = []
            
            for seq in sequences[:1000]:  # Sample first 1000 for quality analysis
                if hasattr(seq, 'letter_annotations') and 'phred_quality' in seq.letter_annotations:
                    qualities.extend(seq.letter_annotations['phred_quality'])
            
            quality_stats = {}
            if qualities:
                quality_stats = {
                    "min_quality": min(qualities),
                    "max_quality": max(qualities),
                    "average_quality": sum(qualities) / len(qualities)
                }
            
            return {
                "format": "fastq",
                "details": {
                    "read_count": len(sequences),
                    "total_bases": sum(lengths),
                    "average_length": sum(lengths) / len(lengths),
                    "min_length": min(lengths),
                    "max_length": max(lengths),
                    "quality_stats": quality_stats
                }
            }
            
        except Exception as e:
            return {"format": "fastq", "details": {"error": str(e)}}
    
    async def _analyze_gff(self, file_path: Path) -> Dict[str, Any]:
        """Analyze GFF/GTF file format"""
        try:
            feature_counts = {}
            total_features = 0
            
            with open(file_path, 'r') as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    
                    parts = line.strip().split('\t')
                    if len(parts) >= 9:
                        feature_type = parts[2]
                        feature_counts[feature_type] = feature_counts.get(feature_type, 0) + 1
                        total_features += 1
            
            return {
                "format": "gff",
                "details": {
                    "total_features": total_features,
                    "feature_types": feature_counts
                }
            }
            
        except Exception as e:
            return {"format": "gff", "details": {"error": str(e)}}
    
    async def _analyze_vcf(self, file_path: Path) -> Dict[str, Any]:
        """Analyze VCF file format"""
        try:
            variant_count = 0
            chromosomes = set()
            variant_types = {}
            
            with open(file_path, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    
                    parts = line.strip().split('\t')
                    if len(parts) >= 8:
                        variant_count += 1
                        chromosomes.add(parts[0])
                        
                        # Simple variant type classification
                        ref = parts[3]
                        alt = parts[4]
                        if len(ref) == 1 and len(alt) == 1:
                            variant_types['SNP'] = variant_types.get('SNP', 0) + 1
                        elif len(ref) > len(alt):
                            variant_types['Deletion'] = variant_types.get('Deletion', 0) + 1
                        elif len(ref) < len(alt):
                            variant_types['Insertion'] = variant_types.get('Insertion', 0) + 1
            
            return {
                "format": "vcf",
                "details": {
                    "variant_count": variant_count,
                    "chromosomes": list(chromosomes),
                    "variant_types": variant_types
                }
            }
            
        except Exception as e:
            return {"format": "vcf", "details": {"error": str(e)}}
    
    async def _analyze_bed(self, file_path: Path) -> Dict[str, Any]:
        """Analyze BED file format"""
        try:
            region_count = 0
            chromosomes = set()
            total_length = 0
            
            with open(file_path, 'r') as f:
                for line in f:
                    if line.startswith('#') or not line.strip():
                        continue
                    
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        region_count += 1
                        chromosomes.add(parts[0])
                        
                        try:
                            start = int(parts[1])
                            end = int(parts[2])
                            total_length += (end - start)
                        except ValueError:
                            continue
            
            return {
                "format": "bed",
                "details": {
                    "region_count": region_count,
                    "chromosomes": list(chromosomes),
                    "total_length": total_length,
                    "average_region_size": total_length / region_count if region_count > 0 else 0
                }
            }
            
        except Exception as e:
            return {"format": "bed", "details": {"error": str(e)}}