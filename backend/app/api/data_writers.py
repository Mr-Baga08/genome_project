# backend/app/api/data_writers.py
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Query, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Dict, Any, Optional, Union
import asyncio
import tempfile
import json
import uuid
from pathlib import Path
import logging
from datetime import datetime

from ..services.data_writers import DataWritersService, WriteOperation
from ..models.enhanced_models import SequenceData, AnnotationData
from ..database.database_setup import DatabaseManager
from ..utils.file_handlers import FileHandler
from ..websockets.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data-writers", tags=["Data Writers"])

# Initialize services
data_writers_service = DataWritersService()
file_handler = FileHandler()

# ============================================================================
# BIOLOGICAL FORMAT WRITING ENDPOINTS
# ============================================================================

@router.post("/write-fasta", response_model=Dict[str, Any])
async def write_fasta_file(
    sequences: List[Dict[str, Any]],
    filename: Optional[str] = None,
    parameters: Dict[str, Any] = {}
):
    """Write sequences to FASTA format"""
    try:
        if not sequences:
            raise HTTPException(status_code=400, detail="No sequences provided")
        
        result = await data_writers_service.write_sequences(
            sequences=sequences,
            format_type="fasta",
            filename=filename,
            parameters=parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "operation": result,
            "download_url": f"/api/v1/data-writers/download/{result['operation_id']}"
        }
        
    except Exception as e:
        logger.error(f"Error writing FASTA file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to write FASTA: {str(e)}")

@router.post("/write-fastq", response_model=Dict[str, Any])
async def write_fastq_file(
    sequences: List[Dict[str, Any]],
    filename: Optional[str] = None,
    parameters: Dict[str, Any] = {}
):
    """Write sequences with quality scores to FASTQ format"""
    try:
        if not sequences:
            raise HTTPException(status_code=400, detail="No sequences provided")
        
        # Validate that sequences have quality scores
        for seq in sequences:
            if 'quality' not in seq:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Sequence {seq.get('id', 'unknown')} missing quality scores for FASTQ format"
                )
        
        result = await data_writers_service.write_sequences(
            sequences=sequences,
            format_type="fastq",
            filename=filename,
            parameters=parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "operation": result,
            "download_url": f"/api/v1/data-writers/download/{result['operation_id']}"
        }
        
    except Exception as e:
        logger.error(f"Error writing FASTQ file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to write FASTQ: {str(e)}")

@router.post("/write-gff3", response_model=Dict[str, Any])
async def write_gff3_file(
    annotations: List[Dict[str, Any]],
    filename: Optional[str] = None,
    parameters: Dict[str, Any] = {}
):
    """Write annotations to GFF3 format"""
    try:
        if not annotations:
            raise HTTPException(status_code=400, detail="No annotations provided")
        
        result = await data_writers_service.write_sequences(
            sequences=annotations,
            format_type="gff3",
            filename=filename,
            parameters=parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "operation": result,
            "download_url": f"/api/v1/data-writers/download/{result['operation_id']}"
        }
        
    except Exception as e:
        logger.error(f"Error writing GFF3 file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to write GFF3: {str(e)}")

@router.post("/write-bed", response_model=Dict[str, Any])
async def write_bed_file(
    features: List[Dict[str, Any]],
    filename: Optional[str] = None,
    parameters: Dict[str, Any] = {}
):
    """Write genomic features to BED format"""
    try:
        if not features:
            raise HTTPException(status_code=400, detail="No features provided")
        
        result = await data_writers_service.write_sequences(
            sequences=features,
            format_type="bed",
            filename=filename,
            parameters=parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "operation": result,
            "download_url": f"/api/v1/data-writers/download/{result['operation_id']}"
        }
        
    except Exception as e:
        logger.error(f"Error writing BED file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to write BED: {str(e)}")

@router.post("/write-vcf", response_model=Dict[str, Any])
async def write_vcf_file(
    variants: List[Dict[str, Any]],
    filename: Optional[str] = None,
    parameters: Dict[str, Any] = {}
):
    """Write variants to VCF format"""
    try:
        if not variants:
            raise HTTPException(status_code=400, detail="No variants provided")
        
        result = await data_writers_service.write_sequences(
            sequences=variants,
            format_type="vcf",
            filename=filename,
            parameters=parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "operation": result,
            "download_url": f"/api/v1/data-writers/download/{result['operation_id']}"
        }
        
    except Exception as e:
        logger.error(f"Error writing VCF file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to write VCF: {str(e)}")

@router.post("/write-sam", response_model=Dict[str, Any])
async def write_sam_file(
    alignments: List[Dict[str, Any]],
    filename: Optional[str] = None,
    parameters: Dict[str, Any] = {}
):
    """Write alignments to SAM format"""
    try:
        if not alignments:
            raise HTTPException(status_code=400, detail="No alignments provided")
        
        result = await data_writers_service.write_sequences(
            sequences=alignments,
            format_type="sam",
            filename=filename,
            parameters=parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "operation": result,
            "download_url": f"/api/v1/data-writers/download/{result['operation_id']}"
        }
        
    except Exception as e:
        logger.error(f"Error writing SAM file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to write SAM: {str(e)}")

# ============================================================================
# MULTI-FORMAT WRITING ENDPOINTS
# ============================================================================

@router.post("/write-multiple-formats", response_model=Dict[str, Any])
async def write_multiple_formats(
    data: List[Dict[str, Any]],
    formats: List[str],
    base_filename: Optional[str] = None,
    parameters: Dict[str, Any] = {}
):
    """Write the same data to multiple formats simultaneously"""
    try:
        if not data:
            raise HTTPException(status_code=400, detail="No data provided")
        
        if not formats:
            raise HTTPException(status_code=400, detail="No formats specified")
        
        # Validate all formats are supported
        supported_formats = list(data_writers_service.supported_formats.keys())
        invalid_formats = [f for f in formats if f not in supported_formats]
        if invalid_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported formats: {invalid_formats}. Supported: {supported_formats}"
            )
        
        results = []
        
        for format_type in formats:
            format_filename = f"{base_filename or 'data'}.{format_type}"
            
            result = await data_writers_service.write_sequences(
                sequences=data,
                format_type=format_type,
                filename=format_filename,
                parameters=parameters
            )
            
            if "error" in result:
                logger.warning(f"Failed to write {format_type}: {result['error']}")
            
            results.append({
                "format": format_type,
                "result": result,
                "download_url": f"/api/v1/data-writers/download/{result.get('operation_id', 'error')}" if "error" not in result else None
            })
        
        successful_writes = [r for r in results if "error" not in r["result"]]
        
        return {
            "status": "completed",
            "total_formats": len(formats),
            "successful_writes": len(successful_writes),
            "failed_writes": len(formats) - len(successful_writes),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in multi-format writing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Multi-format writing failed: {str(e)}")

@router.post("/batch-write", response_model=Dict[str, Any])
async def batch_write_sequences(
    sequence_batches: List[List[Dict[str, Any]]],
    format_configs: List[Dict[str, str]],
    background_tasks: BackgroundTasks
):
    """Write multiple sequence batches to different formats in parallel"""
    try:
        if len(sequence_batches) != len(format_configs):
            raise HTTPException(
                status_code=400, 
                detail="Number of sequence batches must match number of format configurations"
            )
        
        # Start batch writing in background
        batch_id = str(uuid.uuid4())
        background_tasks.add_task(
            _execute_batch_write,
            batch_id,
            sequence_batches,
            format_configs
        )
        
        return {
            "status": "started",
            "batch_id": batch_id,
            "message": "Batch writing started in background",
            "monitor_url": f"/api/v1/data-writers/batch-status/{batch_id}"
        }
        
    except Exception as e:
        logger.error(f"Error starting batch write: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch write failed: {str(e)}")

# ============================================================================
# ANALYSIS RESULTS EXPORT ENDPOINTS
# ============================================================================

@router.post("/export-analysis-results", response_model=Dict[str, Any])
async def export_analysis_results(
    results: Dict[str, Any],
    format_type: str = Query(..., regex="^(json|csv|excel|xml)$"),
    filename: Optional[str] = None
):
    """Export analysis results to various formats"""
    try:
        if not results:
            raise HTTPException(status_code=400, detail="No results provided")
        
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            analysis_type = results.get('analysis_type', 'analysis')
            filename = f"{analysis_type}_results_{timestamp}.{format_type}"
        
        result = await data_writers_service.write_analysis_results(
            analysis_results=results,
            format_type=format_type,
            filename=filename
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "operation": result,
            "download_url": f"/api/v1/data-writers/download/{result['operation_id']}"
        }
        
    except Exception as e:
        logger.error(f"Error exporting analysis results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/export-formats")
async def get_supported_export_formats():
    """Get list of supported export formats for analysis results"""
    return {
        "formats": {
            "json": {
                "description": "JavaScript Object Notation",
                "extensions": [".json"],
                "use_cases": ["API responses", "data interchange", "web applications"]
            },
            "csv": {
                "description": "Comma-Separated Values",
                "extensions": [".csv"],
                "use_cases": ["spreadsheet import", "data analysis", "R/Python processing"]
            },
            "excel": {
                "description": "Microsoft Excel format",
                "extensions": [".xlsx"],
                "use_cases": ["business reports", "multi-sheet data", "formatted output"]
            },
            "xml": {
                "description": "Extensible Markup Language",
                "extensions": [".xml"],
                "use_cases": ["structured data", "database exchange", "system integration"]
            }
        }
    }

# ============================================================================
# SEQUENCE DATA MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/sequences/write-by-ids")
async def write_sequences_by_ids(
    sequence_ids: List[str],
    format_type: str,
    filename: Optional[str] = None,
    parameters: Dict[str, Any] = {},
    db_manager: DatabaseManager = Depends()
):
    """Write sequences from database to specified format"""
    try:
        # Retrieve sequences from database
        sequences_collection = await db_manager.get_collection("sequences")
        
        sequences_data = []
        for seq_id in sequence_ids:
            seq_doc = await sequences_collection.find_one({"_id": seq_id})
            if seq_doc:
                sequences_data.append(seq_doc)
            else:
                logger.warning(f"Sequence not found: {seq_id}")
        
        if not sequences_data:
            raise HTTPException(status_code=404, detail="No sequences found with provided IDs")
        
        result = await data_writers_service.write_sequences(
            sequences=sequences_data,
            format_type=format_type,
            filename=filename,
            parameters=parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "operation": result,
            "sequences_written": len(sequences_data),
            "download_url": f"/api/v1/data-writers/download/{result['operation_id']}"
        }
        
    except Exception as e:
        logger.error(f"Error writing sequences by IDs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to write sequences: {str(e)}")

@router.post("/sequences/convert-and-write")
async def convert_and_write_sequences(
    sequences: List[Dict[str, Any]],
    input_format: str,
    output_format: str,
    filename: Optional[str] = None,
    conversion_parameters: Dict[str, Any] = {},
    write_parameters: Dict[str, Any] = {}
):
    """Convert sequences from one format to another and write to file"""
    try:
        from ..services.data_converters import DataConverterService
        
        # Convert sequences first
        if input_format != output_format:
            converted_data = await DataConverterService.sequence_converter(
                sequences, f"{input_format}_to_{output_format}", conversion_parameters
            )
        else:
            converted_data = sequences
        
        # Write converted data
        result = await data_writers_service.write_sequences(
            sequences=converted_data,
            format_type=output_format,
            filename=filename,
            parameters=write_parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "conversion": f"{input_format} → {output_format}",
            "operation": result,
            "download_url": f"/api/v1/data-writers/download/{result['operation_id']}"
        }
        
    except Exception as e:
        logger.error(f"Error in convert and write: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Convert and write failed: {str(e)}")

# ============================================================================
# FILE DOWNLOAD AND MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/download/{operation_id}")
async def download_file(operation_id: str):
    """Download file created by a write operation"""
    try:
        # Find the file associated with the operation ID
        output_dir = Path(data_writers_service.output_directory)
        
        # Look for files with the operation ID in the name
        matching_files = list(output_dir.glob(f"*{operation_id}*"))
        
        if not matching_files:
            raise HTTPException(status_code=404, detail="File not found or operation ID invalid")
        
        file_path = matching_files[0]
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.get("/operations")
async def list_write_operations(
    limit: int = Query(50, ge=1, le=100),
    format_filter: Optional[str] = Query(None)
):
    """List recent write operations"""
    try:
        # This would typically come from a database of operations
        # For now, we'll scan the output directory
        output_dir = Path(data_writers_service.output_directory)
        
        operations = []
        for file_path in output_dir.iterdir():
            if file_path.is_file():
                file_stat = file_path.stat()
                file_format = file_path.suffix[1:] if file_path.suffix else "unknown"
                
                if format_filter and file_format != format_filter:
                    continue
                
                operations.append({
                    "operation_id": file_path.stem,
                    "filename": file_path.name,
                    "format": file_format,
                    "size_bytes": file_stat.st_size,
                    "created_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    "download_url": f"/api/v1/data-writers/download/{file_path.stem}"
                })
        
        # Sort by creation time (newest first) and limit
        operations.sort(key=lambda x: x["created_at"], reverse=True)
        operations = operations[:limit]
        
        return {
            "operations": operations,
            "total_found": len(operations),
            "limit": limit,
            "format_filter": format_filter
        }
        
    except Exception as e:
        logger.error(f"Error listing operations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list operations: {str(e)}")

@router.delete("/operations/{operation_id}")
async def delete_write_operation(operation_id: str):
    """Delete a write operation and its associated files"""
    try:
        output_dir = Path(data_writers_service.output_directory)
        matching_files = list(output_dir.glob(f"*{operation_id}*"))
        
        if not matching_files:
            raise HTTPException(status_code=404, detail="Operation not found")
        
        deleted_files = []
        for file_path in matching_files:
            if file_path.exists():
                file_path.unlink()
                deleted_files.append(file_path.name)
        
        return {
            "status": "success",
            "operation_id": operation_id,
            "deleted_files": deleted_files,
            "message": f"Deleted {len(deleted_files)} file(s)"
        }
        
    except Exception as e:
        logger.error(f"Error deleting operation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

# ============================================================================
# BATCH AND STREAMING ENDPOINTS
# ============================================================================

@router.post("/batch-status/{batch_id}")
async def get_batch_write_status(batch_id: str):
    """Get status of batch write operation"""
    try:
        # In production, this would query a task queue or database
        # For now, return a mock status
        return {
            "batch_id": batch_id,
            "status": "completed",
            "progress": 100,
            "total_batches": 1,
            "completed_batches": 1,
            "failed_batches": 0,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting batch status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch status: {str(e)}")

@router.get("/stream-large-file/{operation_id}")
async def stream_large_file(operation_id: str):
    """Stream large files for download"""
    try:
        output_dir = Path(data_writers_service.output_directory)
        matching_files = list(output_dir.glob(f"*{operation_id}*"))
        
        if not matching_files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = matching_files[0]
        
        def iterfile():
            with open(file_path, mode="rb") as file_like:
                yield from file_like
        
        return StreamingResponse(
            iterfile(),
            media_type='application/octet-stream',
            headers={"Content-Disposition": f"attachment; filename={file_path.name}"}
        )
        
    except Exception as e:
        logger.error(f"Error streaming file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File streaming failed: {str(e)}")

# ============================================================================
# FORMAT VALIDATION AND INFORMATION ENDPOINTS
# ============================================================================

@router.get("/formats")
async def get_supported_formats():
    """Get list of all supported writing formats"""
    return {
        "formats": data_writers_service.supported_formats,
        "total_formats": len(data_writers_service.supported_formats)
    }

@router.get("/formats/{format_name}")
async def get_format_info(format_name: str):
    """Get detailed information about a specific format"""
    if format_name not in data_writers_service.supported_formats:
        raise HTTPException(status_code=404, detail=f"Format '{format_name}' not supported")
    
    format_info = data_writers_service.supported_formats[format_name]
    use_cases = await data_writers_service.get_format_use_cases(format_name)
    
    return {
        "format": format_name,
        "info": format_info,
        "use_cases": use_cases,
        "example_parameters": _get_format_example_parameters(format_name)
    }

@router.post("/validate-data")
async def validate_data_for_format(
    data: List[Dict[str, Any]],
    format_type: str,
    parameters: Dict[str, Any] = {}
):
    """Validate data structure for a specific format before writing"""
    try:
        if format_type not in data_writers_service.supported_formats:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format_type}")
        
        validation_result = await _validate_data_structure(data, format_type, parameters)
        
        return {
            "valid": validation_result["valid"],
            "format": format_type,
            "data_count": len(data),
            "validation_details": validation_result,
            "ready_to_write": validation_result["valid"]
        }
        
    except Exception as e:
        logger.error(f"Error validating data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

# ============================================================================
# SYSTEM MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/cleanup")
async def cleanup_old_files(
    max_age_hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    background_tasks: BackgroundTasks
):
    """Clean up old output files"""
    try:
        background_tasks.add_task(
            data_writers_service.cleanup_old_files,
            max_age_hours
        )
        
        return {
            "status": "started",
            "message": f"Cleanup started for files older than {max_age_hours} hours",
            "max_age_hours": max_age_hours
        }
        
    except Exception as e:
        logger.error(f"Error starting cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@router.get("/disk-usage")
async def get_disk_usage():
    """Get disk usage statistics for output directory"""
    try:
        output_dir = Path(data_writers_service.output_directory)
        
        total_size = 0
        file_count = 0
        format_breakdown = {}
        
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                file_size = file_path.stat().st_size
                total_size += file_size
                file_count += 1
                
                file_format = file_path.suffix[1:] if file_path.suffix else "no_extension"
                if file_format not in format_breakdown:
                    format_breakdown[file_format] = {"count": 0, "size_bytes": 0}
                
                format_breakdown[file_format]["count"] += 1
                format_breakdown[file_format]["size_bytes"] += file_size
        
        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_files": file_count,
            "format_breakdown": format_breakdown,
            "directory_path": str(output_dir)
        }
        
    except Exception as e:
        logger.error(f"Error getting disk usage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get disk usage: {str(e)}")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _execute_batch_write(
    batch_id: str,
    sequence_batches: List[List[Dict[str, Any]]],
    format_configs: List[Dict[str, str]]
):
    """Execute batch write operation in background"""
    try:
        result = await data_writers_service.batch_write_sequences(
            sequence_batches, format_configs
        )
        
        # In production, you would store this result in a database or cache
        logger.info(f"Batch write {batch_id} completed: {result}")
        
    except Exception as e:
        logger.error(f"Batch write {batch_id} failed: {str(e)}")

def _get_format_example_parameters(format_name: str) -> Dict[str, Any]:
    """Get example parameters for a specific format"""
    examples = {
        "fasta": {
            "line_length": 80,
            "include_description": True
        },
        "fastq": {
            "quality_encoding": "phred33"
        },
        "gff3": {
            "version": "3.2.1",
            "include_fasta": False
        },
        "bed": {
            "track_name": "features",
            "track_description": "Genomic features"
        },
        "vcf": {
            "include_header": True,
            "reference_genome": "hg38"
        },
        "sam": {
            "include_header": True,
            "sort_by_position": True
        },
        "csv": {
            "delimiter": ",",
            "include_headers": True
        },
        "json": {
            "pretty_print": True,
            "indent": 2
        }
    }
    
    return examples.get(format_name, {})

async def _validate_data_structure(
    data: List[Dict[str, Any]], 
    format_type: str, 
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate data structure for specific format"""
    errors = []
    warnings = []
    
    if not data:
        errors.append("No data provided")
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    # Format-specific validation
    if format_type == "fasta":
        for i, item in enumerate(data):
            if "sequence" not in item:
                errors.append(f"Item {i}: Missing 'sequence' field")
            if "id" not in item:
                warnings.append(f"Item {i}: Missing 'id' field, will auto-generate")
                
    elif format_type == "fastq":
        for i, item in enumerate(data):
            if "sequence" not in item:
                errors.append(f"Item {i}: Missing 'sequence' field")
            if "quality" not in item:
                errors.append(f"Item {i}: Missing 'quality' field required for FASTQ")
            elif len(item.get("sequence", "")) != len(item.get("quality", [])):
                errors.append(f"Item {i}: Sequence and quality lengths don't match")
                
    elif format_type == "gff3":
        required_fields = ["seqid", "source", "type", "start", "end", "score", "strand", "phase"]
        for i, item in enumerate(data):
            for field in required_fields:
                if field not in item:
                    errors.append(f"Item {i}: Missing required GFF3 field '{field}'")
                    
    elif format_type == "bed":
        for i, item in enumerate(data):
            if "chrom" not in item:
                errors.append(f"Item {i}: Missing 'chrom' field")
            if "chromStart" not in item:
                errors.append(f"Item {i}: Missing 'chromStart' field")
            if "chromEnd" not in item:
                errors.append(f"Item {i}: Missing 'chromEnd' field")
                
    elif format_type == "vcf":
        for i, item in enumerate(data):
            required_vcf_fields = ["chrom", "pos", "ref", "alt"]
            for field in required_vcf_fields:
                if field not in item:
                    errors.append(f"Item {i}: Missing required VCF field '{field}'")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "data_count": len(data),
        "format": format_type
    }

# ============================================================================
# REALTIME PROGRESS ENDPOINTS (for large operations)
# ============================================================================

@router.websocket("/ws/write-progress/{operation_id}")
async def write_progress_websocket(websocket, operation_id: str):
    """WebSocket endpoint for real-time write progress updates"""
    try:
        await websocket.accept()
        
        # In production, this would connect to a progress tracking system
        # For now, send mock progress updates
        for progress in range(0, 101, 10):
            await websocket.send_json({
                "operation_id": operation_id,
                "progress": progress,
                "status": "writing" if progress < 100 else "completed",
                "timestamp": datetime.utcnow().isoformat()
            })
            await asyncio.sleep(0.5)  # Simulate work
            
    except Exception as e:
        logger.error(f"WebSocket error for operation {operation_id}: {str(e)}")
    finally:
        await websocket.close()

# ============================================================================
# BULK OPERATIONS ENDPOINTS
# ============================================================================

@router.post("/bulk-convert-write")
async def bulk_convert_and_write(
    data_sources: List[Dict[str, Any]],  # Each source has data, input_format, output_format
    background_tasks: BackgroundTasks
):
    """Convert and write multiple data sources in bulk"""
    try:
        bulk_id = str(uuid.uuid4())
        
        background_tasks.add_task(
            _execute_bulk_convert_write,
            bulk_id,
            data_sources
        )
        
        return {
            "status": "started",
            "bulk_id": bulk_id,
            "total_sources": len(data_sources),
            "monitor_url": f"/api/v1/data-writers/bulk-status/{bulk_id}"
        }
        
    except Exception as e:
        logger.error(f"Error starting bulk operation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Bulk operation failed: {str(e)}")

@router.get("/bulk-status/{bulk_id}")
async def get_bulk_operation_status(bulk_id: str):
    """Get status of bulk convert and write operation"""
    # In production, this would query the actual status from a task queue
    return {
        "bulk_id": bulk_id,
        "status": "completed",
        "progress": 100,
        "total_operations": 1,
        "completed_operations": 1,
        "failed_operations": 0
    }

async def _execute_bulk_convert_write(
    bulk_id: str,
    data_sources: List[Dict[str, Any]]
):
    """Execute bulk convert and write operations"""
    try:
        from ..services.data_converters import DataConverterService
        
        for i, source in enumerate(data_sources):
            data = source.get("data", [])
            input_format = source.get("input_format", "fasta")
            output_format = source.get("output_format", "fasta")
            filename = source.get("filename", f"bulk_output_{i+1}")
            
            # Convert if needed
            if input_format != output_format:
                converted_data = await DataConverterService.sequence_converter(
                    data, f"{input_format}_to_{output_format}", {}
                )
            else:
                converted_data = data
            
            # Write data
            await data_writers_service.write_sequences(
                sequences=converted_data,
                format_type=output_format,
                filename=filename
            )
        
        logger.info(f"Bulk operation {bulk_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Bulk operation {bulk_id} failed: {str(e)}")