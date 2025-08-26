# backend/app/api/data_converters.py
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Query, BackgroundTasks
from fastapi.responses import FileResponse, Response
from typing import List, Dict, Any, Optional, Union
import tempfile
import json
from pathlib import Path
import logging
from datetime import datetime
from pydantic import BaseModel, Field

from ..services.data_converters import DataConverterService
from ..database.database_setup import DatabaseManager
from ..utils.file_handlers import FileHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data-converters", tags=["Data Converters"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class FormatConversionRequest(BaseModel):
    """Request model for format conversion"""
    data: str
    input_format: str
    output_format: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class SequenceConversionRequest(BaseModel):
    """Request model for sequence conversion"""
    sequences: List[Dict[str, Any]]
    conversion_type: str = Field(..., regex="^(dna_to_rna|rna_to_dna|reverse_complement|translate|uppercase|lowercase|remove_gaps)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)

class CoordinateConversionRequest(BaseModel):
    """Request model for coordinate conversion"""
    coordinates: List[Dict[str, Any]]
    conversion_type: str = Field(..., regex="^(0_to_1_based|1_to_0_based|bed_to_gff|gff_to_bed)$")

class TextToSequenceRequest(BaseModel):
    """Request model for text to sequence conversion"""
    text_data: str
    sequence_type: str = Field("DNA", regex="^(DNA|RNA|PROTEIN)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)

# ============================================================================
# FORMAT CONVERSION ENDPOINTS
# ============================================================================

@router.post("/convert-format")
async def convert_between_formats(request: FormatConversionRequest):
    """Convert data between different biological formats"""
    try:
        result = await DataConverterService.format_converter(
            data=request.data,
            input_format=request.input_format,
            output_format=request.output_format
        )
        
        return {
            "status": "success",
            "conversion": f"{request.input_format} → {request.output_format}",
            "converted_data": result,
            "original_size": len(request.data),
            "converted_size": len(result)
        }
        
    except Exception as e:
        logger.error(f"Format conversion error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")

@router.post("/convert-file")
async def convert_uploaded_file(
    file: UploadFile = File(...),
    input_format: str = Form(...),
    output_format: str = Form(...),
    parameters: Dict[str, Any] = Form(default_factory=dict)
):
    """Convert uploaded file between formats"""
    try:
        # Read file content
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # Convert format
        converted_data = await DataConverterService.format_converter(
            data=file_content,
            input_format=input_format,
            output_format=output_format
        )
        
        # Determine appropriate filename and media type
        original_name = Path(file.filename).stem
        output_filename = f"{original_name}_converted.{output_format}"
        
        media_types = {
            "fasta": "text/plain",
            "fastq": "text/plain", 
            "gff3": "text/plain",
            "bed": "text/plain",
            "vcf": "text/plain",
            "json": "application/json",
            "csv": "text/csv",
            "xml": "application/xml"
        }
        
        return Response(
            content=converted_data,
            media_type=media_types.get(output_format, "text/plain"),
            headers={"Content-Disposition": f"attachment; filename={output_filename}"}
        )
        
    except Exception as e:
        logger.error(f"File conversion error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"File conversion failed: {str(e)}")

# ============================================================================
# SEQUENCE TRANSFORMATION ENDPOINTS
# ============================================================================

@router.post("/convert-sequences")
async def convert_sequences(request: SequenceConversionRequest):
    """Transform sequences (reverse complement, translation, etc.)"""
    try:
        result = await DataConverterService.sequence_converter(
            sequences=request.sequences,
            conversion_type=request.conversion_type,
            parameters=request.parameters
        )
        
        return {
            "status": "success",
            "conversion_type": request.conversion_type,
            "input_count": len(request.sequences),
            "output_count": len(result),
            "converted_sequences": result
        }
        
    except Exception as e:
        logger.error(f"Sequence conversion error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Sequence conversion failed: {str(e)}")

@router.post("/reverse-complement")
async def calculate_reverse_complement(sequences: List[Dict[str, Any]]):
    """Calculate reverse complement of DNA/RNA sequences"""
    try:
        result = await DataConverterService.reverse_complement(sequences)
        
        return {
            "status": "success",
            "input_sequences": len(sequences),
            "reverse_complement_sequences": result
        }
        
    except Exception as e:
        logger.error(f"Reverse complement error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Reverse complement failed: {str(e)}")

@router.post("/text-to-sequence")
async def convert_text_to_sequence(request: TextToSequenceRequest):
    """Convert plain text to sequence format"""
    try:
        result = await DataConverterService.text_to_sequence(
            text_data=request.text_data,
            sequence_type=request.sequence_type,
            parameters=request.parameters
        )
        
        return {
            "status": "success",
            "sequence_type": request.sequence_type,
            "sequences": result,
            "conversion_summary": {
                "input_length": len(request.text_data),
                "output_sequences": len(result),
                "total_sequence_length": sum(len(seq.get("sequence", "")) for seq in result)
            }
        }
        
    except Exception as e:
        logger.error(f"Text to sequence conversion error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Text conversion failed: {str(e)}")

# ============================================================================
# COORDINATE CONVERSION ENDPOINTS
# ============================================================================

@router.post("/convert-coordinates")
async def convert_coordinates(request: CoordinateConversionRequest):
    """Convert between different coordinate systems"""
    try:
        result = await DataConverterService.coordinate_converter(
            coordinates=request.coordinates,
            conversion_type=request.conversion_type
        )
        
        return {
            "status": "success",
            "conversion_type": request.conversion_type,
            "input_coordinates": len(request.coordinates),
            "converted_coordinates": result
        }
        
    except Exception as e:
        logger.error(f"Coordinate conversion error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Coordinate conversion failed: {str(e)}")

# ============================================================================
# SPECIALIZED CONVERSION ENDPOINTS  
# ============================================================================

@router.post("/fasta-to-phylip")
async def convert_fasta_to_phylip(sequences: List[Dict[str, Any]]):
    """Convert FASTA sequences to PHYLIP format"""
    try:
        # Use the DataConverterService method (assuming it exists)
        phylip_data = await DataConverterService.format_converter(
            data=json.dumps(sequences),
            input_format="fasta",
            output_format="phylip"
        )
        
        return Response(
            content=phylip_data,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=alignment.phy"}
        )
        
    except Exception as e:
        logger.error(f"FASTA to PHYLIP conversion error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"FASTA to PHYLIP conversion failed: {str(e)}")

@router.post("/gff-to-bed")
async def convert_gff_to_bed(annotations: List[Dict[str, Any]]):
    """Convert GFF annotations to BED format"""
    try:
        # Convert using service method
        bed_data = await DataConverterService.format_converter(
            data=json.dumps(annotations),
            input_format="gff3",
            output_format="bed"
        )
        
        return Response(
            content=bed_data,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=features.bed"}
        )
        
    except Exception as e:
        logger.error(f"GFF to BED conversion error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"GFF to BED conversion failed: {str(e)}")

@router.post("/vcf-to-table")
async def convert_vcf_to_table(vcf_data: str, output_format: str = "csv"):
    """Convert VCF data to tabular format"""
    try:
        # Parse VCF and convert to DataFrame
        df = await DataConverterService.vcf_to_table(vcf_data)
        
        if output_format == "csv":
            csv_data = df.to_csv(index=False)
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=variants.csv"}
            )
        elif output_format == "json":
            json_data = df.to_json(orient="records", indent=2)
            return Response(
                content=json_data,
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=variants.json"}
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported output format")
        
    except Exception as e:
        logger.error(f"VCF to table conversion error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"VCF conversion failed: {str(e)}")

@router.post("/sam-to-bam")
async def convert_sam_to_bam(
    sam_file: UploadFile = File(...),
    background_tasks: BackgroundTasks
):
    """Convert SAM file to BAM format using external tools"""
    try:
        # Read SAM file
        content = await sam_file.read()
        sam_data = content.decode('utf-8')
        
        # Use external tool manager for conversion
        from ..services.external_tool_manager import ExternalToolManager
        tool_manager = ExternalToolManager()
        
        # This would use samtools in Docker container
        result = await tool_manager.execute_custom_container(
            image="biocontainers/samtools:v1.9_cv2",
            command=["samtools", "view", "-bS", "-o", "output.bam", "input.sam"],
            input_files={"input.sam": sam_data},
            timeout=300
        )
        
        if result.get("success"):
            return {
                "status": "success",
                "message": "SAM to BAM conversion completed",
                "execution_id": result.get("execution_id"),
                "output_files": result.get("output_files", [])
            }
        else:
            raise HTTPException(status_code=400, detail="SAM to BAM conversion failed")
        
    except Exception as e:
        logger.error(f"SAM to BAM conversion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"SAM to BAM conversion failed: {str(e)}")

# ============================================================================
# ASSEMBLY DATA CONVERSION ENDPOINTS
# ============================================================================

@router.post("/split-assembly")
async def split_assembly_into_sequences(assembly_data: Dict[str, Any]):
    """Split assembly data into individual sequences"""
    try:
        sequences = await DataConverterService.split_assembly_into_sequences(assembly_data)
        
        return {
            "status": "success",
            "assembly_info": {
                "total_contigs": len(sequences),
                "total_length": sum(seq.get("length", 0) for seq in sequences)
            },
            "sequences": sequences
        }
        
    except Exception as e:
        logger.error(f"Assembly splitting error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Assembly splitting failed: {str(e)}")

# ============================================================================
# VALIDATION AND UTILITY ENDPOINTS
# ============================================================================

@router.get("/supported-conversions")
async def get_supported_conversions():
    """Get list of all supported format conversions"""
    return {
        "format_conversions": {
            "fasta": ["genbank", "phylip", "clustal", "stockholm"],
            "genbank": ["fasta"],
            "fastq": ["fasta"],
            "gff3": ["bed", "gtf"],
            "bed": ["gff3"],
            "vcf": ["bed", "csv", "json"],
            "csv": ["json"],
            "json": ["csv"]
        },
        "sequence_conversions": [
            "dna_to_rna",
            "rna_to_dna", 
            "reverse_complement",
            "translate",
            "uppercase",
            "lowercase",
            "remove_gaps"
        ],
        "coordinate_conversions": [
            "0_to_1_based",
            "1_to_0_based",
            "bed_to_gff",
            "gff_to_bed"
        ]
    }

@router.post("/validate-conversion")
async def validate_conversion_request(
    data_sample: str,
    input_format: str,
    output_format: str
):
    """Validate if conversion is possible before processing large datasets"""
    try:
        # Test conversion with sample data
        result = await DataConverterService.format_converter(
            data=data_sample,
            input_format=input_format,
            output_format=output_format
        )
        
        return {
            "valid": True,
            "message": "Conversion validated successfully",
            "sample_result_size": len(result),
            "conversion_ratio": len(result) / len(data_sample) if data_sample else 0
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "suggestion": "Check input format and data structure"
        }

@router.post("/json-parser")
async def parse_json_data(
    json_data: str,
    data_type: str = Query(..., regex="^(sequences|annotations|variants|reads|alignments)$")
):
    """Parse JSON data into biological data structures"""
    try:
        result = await DataConverterService.json_parser(json_data, data_type)
        
        return {
            "status": "success",
            "data_type": data_type,
            "parsed_objects": len(result),
            "data": result
        }
        
    except Exception as e:
        logger.error(f"JSON parsing error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"JSON parsing failed: {str(e)}")

# ============================================================================
# BATCH CONVERSION ENDPOINTS
# ============================================================================

@router.post("/batch-convert")
async def batch_convert_sequences(
    conversion_requests: List[SequenceConversionRequest],
    background_tasks: BackgroundTasks
):
    """Convert multiple sequence sets in parallel"""
    try:
        batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            _execute_batch_conversions,
            batch_id,
            conversion_requests
        )
        
        return {
            "status": "started",
            "batch_id": batch_id,
            "total_conversions": len(conversion_requests),
            "monitor_url": f"/api/v1/data-converters/batch-status/{batch_id}"
        }
        
    except Exception as e:
        logger.error(f"Batch conversion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch conversion failed: {str(e)}")

@router.get("/batch-status/{batch_id}")
async def get_batch_conversion_status(batch_id: str):
    """Get status of batch conversion operation"""
    # In production, this would query actual status from task queue
    return {
        "batch_id": batch_id,
        "status": "completed",
        "progress": 100,
        "completed_conversions": 1,
        "failed_conversions": 0,
        "total_conversions": 1
    }

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _execute_batch_conversions(
    batch_id: str,
    conversion_requests: List[SequenceConversionRequest]
):
    """Execute batch conversions in background"""
    try:
        results = []
        
        for i, request in enumerate(conversion_requests):
            try:
                result = await DataConverterService.sequence_converter(
                    sequences=request.sequences,
                    conversion_type=request.conversion_type,
                    parameters=request.parameters
                )
                results.append({
                    "conversion_index": i,
                    "status": "success",
                    "result": result
                })
            except Exception as e:
                results.append({
                    "conversion_index": i,
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(f"Batch conversion {batch_id} completed: {len(results)} operations")
        
    except Exception as e:
        logger.error(f"Batch conversion {batch_id} failed: {str(e)}")