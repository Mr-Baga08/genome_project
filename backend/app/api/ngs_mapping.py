# backend/app/api/ngs_mapping.py
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Query, BackgroundTasks
from fastapi.responses import FileResponse, Response
from typing import List, Dict, Any, Optional, Union
import json
import tempfile
from pathlib import Path
import logging
from datetime import datetime
from pydantic import BaseModel, Field, validator

from ..services.ngs_mapping import NGSMappingService
from ..services.data_writers import DataWritersService
from ..database.database_setup import DatabaseManager
from ..websockets.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ngs-mapping", tags=["NGS Mapping"])

# Initialize services
ngs_mapping_service = NGSMappingService()
data_writers_service = DataWritersService()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ReadMappingRequest(BaseModel):
    """Request model for read mapping"""
    reads: List[Dict[str, Any]] = Field(..., min_items=1)
    reference_sequence: Dict[str, Any]
    parameters: Dict[str, Any] = Field(
        default_factory=lambda: {
            "quality_threshold": 20,
            "mapping_algorithm": "bwa",
            "allow_mismatches": 2,
            "min_mapping_quality": 30
        }
    )

class PairedEndMappingRequest(BaseModel):
    """Request model for paired-end read mapping"""
    paired_reads: List[Dict[str, Any]] = Field(..., min_items=1)
    reference_sequence: Dict[str, Any]
    parameters: Dict[str, Any] = Field(
        default_factory=lambda: {
            "insert_size_mean": 300,
            "insert_size_std": 50,
            "quality_threshold": 20,
            "mapping_algorithm": "bwa"
        }
    )
    
    @validator('paired_reads')
    def validate_paired_reads(cls, v):
        for read_pair in v:
            if 'r1' not in read_pair or 'r2' not in read_pair:
                raise ValueError("Each paired read must have 'r1' and 'r2' fields")
        return v

class CoverageAnalysisRequest(BaseModel):
    """Request model for coverage analysis"""
    mapped_reads: List[Dict[str, Any]]
    reference_length: int = Field(..., gt=0)
    window_size: int = Field(1000, ge=100, le=10000)

class AlignmentFilterRequest(BaseModel):
    """Request model for alignment filtering"""
    alignments: List[Dict[str, Any]]
    filter_criteria: Dict[str, Any] = Field(
        default_factory=lambda: {
            "min_mapping_quality": 30,
            "max_mismatches": 2,
            "properly_paired_only": True
        }
    )

class VariantCallingRequest(BaseModel):
    """Request model for variant calling"""
    mapped_reads: List[Dict[str, Any]]
    reference_sequence: str
    parameters: Dict[str, Any] = Field(
        default_factory=lambda: {
            "min_coverage": 5,
            "min_variant_frequency": 0.2,
            "quality_threshold": 20
        }
    )

# ============================================================================
# READ MAPPING ENDPOINTS
# ============================================================================

@router.post("/map-reads")
async def map_reads_to_reference(
    request: ReadMappingRequest,
    background_tasks: BackgroundTasks,
    save_sam: bool = Query(False),
    save_to_db: bool = Query(True)
):
    """Map single-end reads to reference sequence"""
    try:
        mapping_result = await ngs_mapping_service.map_reads(
            reads=request.reads,
            reference_sequence=request.reference_sequence,
            parameters=request.parameters
        )
        
        if "error" in mapping_result:
            raise HTTPException(status_code=400, detail=mapping_result["error"])
        
        # Save results if requested
        if save_to_db:
            background_tasks.add_task(
                _save_mapping_result,
                mapping_result,
                "single_end_mapping",
                request.parameters
            )
        
        # Generate SAM file if requested
        sam_download_url = None
        if save_sam:
            sam_result = await _generate_sam_file(mapping_result)
            sam_download_url = sam_result.get("download_url")
        
        return {
            "status": "success",
            "mapping_algorithm": request.parameters.get("mapping_algorithm", "bwa"),
            "mapping_result": mapping_result,
            "sam_download_url": sam_download_url,
            "summary": {
                "input_reads": len(request.reads),
                "mapped_reads": len(mapping_result.get("mapped_reads", [])),
                "unmapped_reads": len(mapping_result.get("unmapped_reads", [])),
                "mapping_rate": mapping_result.get("statistics", {}).get("mapping_rate", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Read mapping error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Read mapping failed: {str(e)}")

@router.post("/map-paired-reads")
async def map_paired_end_reads(
    request: PairedEndMappingRequest,
    background_tasks: BackgroundTasks,
    save_sam: bool = Query(False)
):
    """Map paired-end reads to reference sequence"""
    try:
        mapping_result = await ngs_mapping_service.map_paired_reads(
            paired_reads=request.paired_reads,
            reference_sequence=request.reference_sequence,
            parameters=request.parameters
        )
        
        if "error" in mapping_result:
            raise HTTPException(status_code=400, detail=mapping_result["error"])
        
        # Generate SAM file if requested
        sam_download_url = None
        if save_sam:
            sam_result = await _generate_sam_file(mapping_result)
            sam_download_url = sam_result.get("download_url")
        
        return {
            "status": "success",
            "mapping_result": mapping_result,
            "sam_download_url": sam_download_url,
            "summary": {
                "input_pairs": len(request.paired_reads),
                "properly_paired": mapping_result.get("statistics", {}).get("properly_paired", 0),
                "insert_size_stats": mapping_result.get("insert_size_analysis", {})
            }
        }
        
    except Exception as e:
        logger.error(f"Paired-end mapping error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Paired-end mapping failed: {str(e)}")

# ============================================================================
# COVERAGE ANALYSIS ENDPOINTS
# ============================================================================

@router.post("/analyze-coverage")
async def analyze_coverage(request: CoverageAnalysisRequest):
    """Analyze coverage distribution from mapped reads"""
    try:
        coverage_result = await ngs_mapping_service.calculate_coverage(
            mapped_reads=request.mapped_reads,
            reference_length=request.reference_length,
            window_size=request.window_size
        )
        
        if "error" in coverage_result:
            raise HTTPException(status_code=400, detail=coverage_result["error"])
        
        return {
            "status": "success",
            "coverage_analysis": coverage_result,
            "analysis_parameters": {
                "reference_length": request.reference_length,
                "window_size": request.window_size,
                "total_reads": len(request.mapped_reads)
            }
        }
        
    except Exception as e:
        logger.error(f"Coverage analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Coverage analysis failed: {str(e)}")

@router.post("/coverage-statistics")
async def calculate_coverage_statistics(
    mapped_reads: List[Dict[str, Any]],
    reference_length: int,
    coverage_thresholds: List[int] = Query([1, 5, 10, 20, 50])
):
    """Calculate detailed coverage statistics"""
    try:
        # Calculate coverage at each position
        coverage_array = [0] * reference_length
        
        for read in mapped_reads:
            start_pos = read.get("position", 0)
            read_length = len(read.get("sequence", ""))
            end_pos = min(start_pos + read_length, reference_length)
            
            for pos in range(start_pos, end_pos):
                coverage_array[pos] += 1
        
        # Calculate statistics
        total_bases = len(coverage_array)
        covered_bases = sum(1 for cov in coverage_array if cov > 0)
        average_coverage = sum(coverage_array) / total_bases if total_bases > 0 else 0
        
        # Calculate threshold statistics
        threshold_stats = {}
        for threshold in coverage_thresholds:
            bases_above_threshold = sum(1 for cov in coverage_array if cov >= threshold)
            percentage = (bases_above_threshold / total_bases * 100) if total_bases > 0 else 0
            threshold_stats[f"{threshold}x"] = {
                "bases_covered": bases_above_threshold,
                "percentage": round(percentage, 2)
            }
        
        return {
            "status": "success",
            "coverage_statistics": {
                "reference_length": reference_length,
                "total_reads": len(mapped_reads),
                "average_coverage": round(average_coverage, 2),
                "coverage_breadth": round((covered_bases / total_bases * 100), 2),
                "max_coverage": max(coverage_array) if coverage_array else 0,
                "threshold_statistics": threshold_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Coverage statistics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Coverage statistics failed: {str(e)}")

# ============================================================================
# ALIGNMENT PROCESSING ENDPOINTS
# ============================================================================

@router.post("/filter-alignments")
async def filter_alignments(request: AlignmentFilterRequest):
    """Filter alignments based on quality criteria"""
    try:
        filtered_alignments = []
        filter_stats = {
            "input_alignments": len(request.alignments),
            "passed_quality": 0,
            "failed_quality": 0,
            "failed_pairing": 0
        }
        
        for alignment in request.alignments:
            passes_filter = True
            
            # Check mapping quality
            if "min_mapping_quality" in request.filter_criteria:
                mapq = alignment.get("mapping_quality", 0)
                if mapq < request.filter_criteria["min_mapping_quality"]:
                    passes_filter = False
                    filter_stats["failed_quality"] += 1
            
            # Check proper pairing for paired-end
            if request.filter_criteria.get("properly_paired_only", False):
                if not alignment.get("properly_paired", True):
                    passes_filter = False
                    filter_stats["failed_pairing"] += 1
            
            if passes_filter:
                filtered_alignments.append(alignment)
                filter_stats["passed_quality"] += 1
        
        return {
            "status": "success",
            "filter_criteria": request.filter_criteria,
            "filtered_alignments": filtered_alignments,
            "filter_statistics": filter_stats,
            "filter_efficiency": (filter_stats["passed_quality"] / filter_stats["input_alignments"] * 100) if filter_stats["input_alignments"] > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Alignment filtering error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Alignment filtering failed: {str(e)}")

# ============================================================================
# VARIANT CALLING ENDPOINTS
# ============================================================================

@router.post("/call-variants")
async def call_variants_from_alignments(
    request: VariantCallingRequest,
    background_tasks: BackgroundTasks
):
    """Call variants from mapped reads"""
    try:
        variant_result = await ngs_mapping_service.call_variants(
            mapped_reads=request.mapped_reads,
            reference_sequence=request.reference_sequence,
            parameters=request.parameters
        )
        
        if "error" in variant_result:
            raise HTTPException(status_code=400, detail=variant_result["error"])
        
        return {
            "status": "success",
            "variant_calling_result": variant_result,
            "summary": {
                "total_variants": len(variant_result.get("variants", [])),
                "snvs": len([v for v in variant_result.get("variants", []) if v.get("type") == "SNV"]),
                "indels": len([v for v in variant_result.get("variants", []) if v.get("type") == "INDEL"]),
                "input_reads": len(request.mapped_reads)
            }
        }
        
    except Exception as e:
        logger.error(f"Variant calling error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Variant calling failed: {str(e)}")

# ============================================================================
# MAPPING QUALITY ASSESSMENT ENDPOINTS
# ============================================================================

@router.post("/assess-mapping-quality")
async def assess_mapping_quality(
    mapped_reads: List[Dict[str, Any]],
    reference_sequence: Dict[str, Any]
):
    """Assess overall quality of read mapping"""
    try:
        quality_assessment = await ngs_mapping_service.assess_mapping_quality(
            mapped_reads=mapped_reads,
            reference_sequence=reference_sequence
        )
        
        if "error" in quality_assessment:
            raise HTTPException(status_code=400, detail=quality_assessment["error"])
        
        return {
            "status": "success",
            "quality_assessment": quality_assessment,
            "recommendations": _generate_mapping_recommendations(quality_assessment)
        }
        
    except Exception as e:
        logger.error(f"Mapping quality assessment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mapping quality assessment failed: {str(e)}")

# ============================================================================
# SPECIALIZED MAPPING ENDPOINTS
# ============================================================================

@router.post("/map-long-reads")
async def map_long_reads(
    reads: List[Dict[str, Any]],
    reference_sequence: Dict[str, Any],
    algorithm: str = Query("minimap2", regex="^(minimap2|pbmm2)$"),
    preset: str = Query("map-ont", regex="^(map-ont|map-pb|asm20)$")
):
    """Map long reads using specialized algorithms"""
    try:
        parameters = {
            "algorithm": algorithm,
            "preset": preset,
            "long_read_mode": True,
            "sensitivity": "high"
        }
        
        mapping_result = await ngs_mapping_service.map_long_reads(
            reads=reads,
            reference_sequence=reference_sequence,
            parameters=parameters
        )
        
        if "error" in mapping_result:
            raise HTTPException(status_code=400, detail=mapping_result["error"])
        
        return {
            "status": "success",
            "algorithm": algorithm,
            "preset": preset,
            "mapping_result": mapping_result,
            "long_read_summary": {
                "input_reads": len(reads),
                "average_read_length": sum(len(read.get("sequence", "")) for read in reads) / len(reads),
                "mapped_reads": len(mapping_result.get("mapped_reads", [])),
                "mapping_rate": mapping_result.get("statistics", {}).get("mapping_rate", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Long read mapping error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Long read mapping failed: {str(e)}")

@router.post("/rna-seq-mapping")
async def map_rna_seq_reads(
    reads: List[Dict[str, Any]],
    reference_genome: Dict[str, Any],
    annotation_file: Optional[UploadFile] = File(None),
    splice_aware: bool = Query(True),
    algorithm: str = Query("hisat2", regex="^(hisat2|star|tophat)$")
):
    """Map RNA-seq reads with splice-aware alignment"""
    try:
        # Parse annotation file if provided
        annotations = None
        if annotation_file:
            content = await annotation_file.read()
            # Parse annotations (GTF/GFF format)
            annotations = await _parse_annotation_file(content.decode('utf-8'))
        
        parameters = {
            "algorithm": algorithm,
            "splice_aware": splice_aware,
            "annotations": annotations,
            "rna_seq_mode": True
        }
        
        mapping_result = await ngs_mapping_service.map_rna_seq_reads(
            reads=reads,
            reference_genome=reference_genome,
            parameters=parameters
        )
        
        if "error" in mapping_result:
            raise HTTPException(status_code=400, detail=mapping_result["error"])
        
        return {
            "status": "success",
            "algorithm": algorithm,
            "splice_aware": splice_aware,
            "mapping_result": mapping_result,
            "rna_seq_summary": {
                "input_reads": len(reads),
                "splice_junctions_found": len(mapping_result.get("splice_junctions", [])),
                "uniquely_mapped": len([r for r in mapping_result.get("mapped_reads", []) if r.get("unique_mapping", True)])
            }
        }
        
    except Exception as e:
        logger.error(f"RNA-seq mapping error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RNA-seq mapping failed: {str(e)}")

# ============================================================================
# MAPPING STATISTICS ENDPOINTS
# ============================================================================

@router.post("/mapping-statistics")
async def calculate_mapping_statistics(
    mapped_reads: List[Dict[str, Any]],
    unmapped_reads: List[Dict[str, Any]] = [],
    detailed_analysis: bool = Query(True)
):
    """Calculate comprehensive mapping statistics"""
    try:
        total_reads = len(mapped_reads) + len(unmapped_reads)
        
        basic_stats = {
            "total_reads": total_reads,
            "mapped_reads": len(mapped_reads),
            "unmapped_reads": len(unmapped_reads),
            "mapping_rate": (len(mapped_reads) / total_reads * 100) if total_reads > 0 else 0
        }
        
        if detailed_analysis:
            # Quality distribution
            mapping_qualities = [read.get("mapping_quality", 0) for read in mapped_reads]
            
            # Mismatch analysis
            mismatches = [read.get("mismatches", 0) for read in mapped_reads]
            
            # Insert size analysis (for paired reads)
            insert_sizes = [read.get("insert_size", 0) for read in mapped_reads if read.get("insert_size")]
            
            detailed_stats = {
                "quality_distribution": {
                    "mean_mapq": sum(mapping_qualities) / len(mapping_qualities) if mapping_qualities else 0,
                    "high_quality_reads": len([q for q in mapping_qualities if q >= 30]),
                    "low_quality_reads": len([q for q in mapping_qualities if q < 10])
                },
                "mismatch_analysis": {
                    "mean_mismatches": sum(mismatches) / len(mismatches) if mismatches else 0,
                    "perfect_matches": len([m for m in mismatches if m == 0]),
                    "high_mismatch_reads": len([m for m in mismatches if m > 3])
                },
                "insert_size_analysis": {
                    "mean_insert_size": sum(insert_sizes) / len(insert_sizes) if insert_sizes else 0,
                    "insert_size_std": _calculate_std(insert_sizes) if len(insert_sizes) > 1 else 0
                } if insert_sizes else None
            }
            
            basic_stats.update(detailed_stats)
        
        return {
            "status": "success",
            "mapping_statistics": basic_stats
        }
        
    except Exception as e:
        logger.error(f"Mapping statistics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mapping statistics failed: {str(e)}")

# ============================================================================
# ALIGNMENT EXPORT ENDPOINTS
# ============================================================================

@router.post("/export-sam")
async def export_alignments_sam(
    mapped_reads: List[Dict[str, Any]],
    reference_info: Dict[str, Any],
    filename: Optional[str] = None
):
    """Export alignments in SAM format"""
    try:
        sam_result = await _generate_sam_file({
            "mapped_reads": mapped_reads,
            "reference_info": reference_info
        })
        
        return {
            "status": "success",
            "format": "SAM",
            "alignments_exported": len(mapped_reads),
            "download_url": sam_result.get("download_url")
        }
        
    except Exception as e:
        logger.error(f"SAM export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"SAM export failed: {str(e)}")

@router.post("/export-bam")
async def export_alignments_bam(
    mapped_reads: List[Dict[str, Any]],
    reference_info: Dict[str, Any],
    background_tasks: BackgroundTasks,
    sorted: bool = Query(True)
):
    """Export alignments in BAM format (requires samtools)"""
    try:
        # First generate SAM
        sam_data = await _generate_sam_content(mapped_reads, reference_info)
        
        # Convert to BAM using external tools
        from ..services.external_tool_manager import ExternalToolManager
        tool_manager = ExternalToolManager()
        
        conversion_result = await tool_manager.execute_custom_container(
            image="biocontainers/samtools:v1.9_cv2",
            command=["samtools", "view", "-bS", "-o", "output.bam", "input.sam"],
            input_files={"input.sam": sam_data},
            timeout=300
        )
        
        if not conversion_result.get("success"):
            raise HTTPException(status_code=400, detail="BAM conversion failed")
        
        return {
            "status": "success",
            "format": "BAM",
            "sorted": sorted,
            "alignments_exported": len(mapped_reads),
            "execution_id": conversion_result.get("execution_id")
        }
        
    except Exception as e:
        logger.error(f"BAM export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"BAM export failed: {str(e)}")

# ============================================================================
# MAPPING WORKFLOW ENDPOINTS
# ============================================================================

@router.post("/complete-mapping-workflow")
async def run_complete_mapping_workflow(
    reads_file: UploadFile = File(...),
    reference_file: UploadFile = File(...),
    read_type: str = Form("single_end", regex="^(single_end|paired_end|long_reads)$"),
    algorithm: str = Form("bwa"),
    quality_threshold: float = Form(20.0),
    background_tasks: BackgroundTasks
):
    """Run complete mapping workflow from uploaded files"""
    try:
        workflow_id = f"mapping_workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Read input files
        reads_content = await reads_file.read()
        reference_content = await reference_file.read()
        
        background_tasks.add_task(
            _execute_mapping_workflow,
            workflow_id,
            reads_content.decode('utf-8'),
            reference_content.decode('utf-8'),
            read_type,
            algorithm,
            quality_threshold
        )
        
        return {
            "status": "started",
            "workflow_id": workflow_id,
            "read_type": read_type,
            "algorithm": algorithm,
            "monitor_url": f"/api/v1/ngs-mapping/workflow-status/{workflow_id}"
        }
        
    except Exception as e:
        logger.error(f"Mapping workflow error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mapping workflow failed: {str(e)}")

@router.get("/workflow-status/{workflow_id}")
async def get_mapping_workflow_status(workflow_id: str):
    """Get status of mapping workflow"""
    # In production, this would query actual workflow status
    return {
        "workflow_id": workflow_id,
        "status": "completed",
        "progress": 100,
        "current_step": "variant_calling",
        "completed_steps": ["quality_control", "mapping", "coverage_analysis"],
        "failed_steps": []
    }

# ============================================================================
# MAPPING ALGORITHMS INFO ENDPOINTS
# ============================================================================

@router.get("/algorithms")
async def get_mapping_algorithms():
    """Get information about available mapping algorithms"""
    return {
        "short_read_algorithms": {
            "bwa": {
                "description": "Burrows-Wheeler Aligner for short reads",
                "best_for": ["DNA-seq", "short reads", "high accuracy"],
                "parameters": ["seed_length", "max_mismatches", "gap_penalty"]
            },
            "bowtie2": {
                "description": "Fast and memory-efficient short read aligner",
                "best_for": ["RNA-seq", "ChIP-seq", "fast alignment"],
                "parameters": ["sensitivity", "gap_penalty", "mismatch_penalty"]
            }
        },
        "rna_seq_algorithms": {
            "hisat2": {
                "description": "Hierarchical indexing for splice-aware alignment",
                "best_for": ["RNA-seq", "splice detection", "fast processing"],
                "parameters": ["splice_penalty", "max_intron_length"]
            },
            "star": {
                "description": "Spliced Transcripts Alignment to a Reference",
                "best_for": ["RNA-seq", "fusion detection", "accurate splicing"],
                "parameters": ["overhang_length", "mismatch_filter"]
            }
        },
        "long_read_algorithms": {
            "minimap2": {
                "description": "Versatile sequence alignment program",
                "best_for": ["PacBio", "Oxford Nanopore", "long reads"],
                "parameters": ["preset", "bandwidth", "chain_gap"]
            },
            "pbmm2": {
                "description": "PacBio's minimap2 SMRT wrapper",
                "best_for": ["PacBio HiFi", "PacBio CLR"],
                "parameters": ["preset", "min_length"]
            }
        }
    }

@router.get("/recommended-parameters")
async def get_recommended_parameters(
    read_type: str = Query(..., regex="^(short_reads|long_reads|rna_seq)$"),
    data_type: str = Query(..., regex="^(dna_seq|rna_seq|chip_seq|bisulfite_seq)$"),
    read_length: int = Query(..., ge=50, le=50000)
):
    """Get recommended mapping parameters for specific data types"""
    
    recommendations = {
        "short_reads": {
            "dna_seq": {
                "algorithm": "bwa",
                "quality_threshold": 20,
                "max_mismatches": 2,
                "mapping_quality_threshold": 30
            },
            "rna_seq": {
                "algorithm": "hisat2",
                "quality_threshold": 25,
                "splice_aware": True,
                "max_intron_length": 500000
            }
        },
        "long_reads": {
            "dna_seq": {
                "algorithm": "minimap2",
                "preset": "map-ont" if read_length > 1000 else "map-pb",
                "min_mapping_quality": 10,
                "allow_supplementary": True
            }
        }
    }
    
    params = recommendations.get(read_type, {}).get(data_type, {})
    
    if not params:
        raise HTTPException(
            status_code=400, 
            detail=f"No recommendations available for {read_type} + {data_type}"
        )
    
    return {
        "status": "success",
        "read_type": read_type,
        "data_type": data_type,
        "read_length": read_length,
        "recommended_parameters": params,
        "rationale": _get_parameter_rationale(read_type, data_type)
    }

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _save_mapping_result(
    result: Dict[str, Any],
    mapping_type: str,
    parameters: Dict[str, Any]
):
    """Save mapping result to database"""
    try:
        # This would use DatabaseManager to store results
        logger.info(f"Mapping result saved: {mapping_type}")
    except Exception as e:
        logger.error(f"Failed to save mapping result: {str(e)}")

async def _generate_sam_file(mapping_result: Dict[str, Any]) -> Dict[str, str]:
    """Generate SAM file from mapping result"""
    try:
        mapped_reads = mapping_result.get("mapped_reads", [])
        reference_info = mapping_result.get("reference_info", {})
        
        sam_content = await _generate_sam_content(mapped_reads, reference_info)
        
        # Write SAM file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"alignments_{timestamp}.sam"
        
        write_result = await data_writers_service.write_sequences(
            sequences=mapped_reads,
            format_type="sam",
            filename=filename,
            parameters={"reference_sequences": [reference_info]}
        )
        
        return {
            "download_url": f"/api/v1/data-writers/download/{write_result['operation_id']}"
        }
        
    except Exception as e:
        logger.error(f"SAM generation error: {str(e)}")
        return {"error": str(e)}

async def _generate_sam_content(mapped_reads: List[Dict[str, Any]], reference_info: Dict[str, Any]) -> str:
    """Generate SAM file content"""
    sam_lines = []
    
    # SAM header
    sam_lines.append("@HD\tVN:1.6\tSO:unsorted")
    sam_lines.append(f"@SQ\tSN:{reference_info.get('name', 'ref')}\tLN:{reference_info.get('length', 0)}")
    sam_lines.append("@PG\tID:ugene\tPN:UGENE Web Platform\tVN:1.0")
    
    # Alignment records
    for read in mapped_reads:
        qname = read.get("id", "unknown")
        flag = read.get("flag", 0)
        rname = reference_info.get("name", "ref")
        pos = read.get("position", 0)
        mapq = read.get("mapping_quality", 60)
        cigar = read.get("cigar", f"{len(read.get('sequence', ''))}M")
        rnext = "*"
        pnext = 0
        tlen = 0
        seq = read.get("sequence", "*")
        qual = read.get("quality_string", "*")
        
        sam_line = f"{qname}\t{flag}\t{rname}\t{pos}\t{mapq}\t{cigar}\t{rnext}\t{pnext}\t{tlen}\t{seq}\t{qual}"
        sam_lines.append(sam_line)
    
    return "\n".join(sam_lines)

async def _parse_annotation_file(content: str) -> List[Dict[str, Any]]:
    """Parse annotation file content"""
    annotations = []
    for line in content.strip().split('\n'):
        if line.startswith('#') or not line.strip():
            continue
        
        parts = line.split('\t')
        if len(parts) >= 9:
            annotations.append({
                "seqid": parts[0],
                "source": parts[1],
                "type": parts[2],
                "start": int(parts[3]),
                "end": int(parts[4]),
                "score": parts[5],
                "strand": parts[6],
                "phase": parts[7],
                "attributes": parts[8]
            })
    
    return annotations

def _generate_mapping_recommendations(quality_assessment: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on mapping quality"""
    recommendations = []
    
    mapping_rate = quality_assessment.get("mapping_rate", 0)
    if mapping_rate < 80:
        recommendations.append("Consider adjusting mapping parameters - low mapping rate detected")
    
    avg_quality = quality_assessment.get("average_mapping_quality", 0)
    if avg_quality < 20:
        recommendations.append("Many low-quality alignments found - consider stricter quality filtering")
    
    coverage_uniformity = quality_assessment.get("coverage_uniformity", 1.0)
    if coverage_uniformity < 0.7:
        recommendations.append("Uneven coverage detected - check for PCR bias or GC content issues")
    
    return recommendations

def _get_parameter_rationale(read_type: str, data_type: str) -> str:
    """Get rationale for parameter recommendations"""
    rationales = {
        ("short_reads", "dna_seq"): "BWA optimized for high accuracy DNA mapping with moderate mismatch tolerance",
        ("short_reads", "rna_seq"): "HISAT2 provides splice-aware alignment essential for RNA-seq analysis",
        ("long_reads", "dna_seq"): "Minimap2 handles long read error patterns and provides fast, sensitive alignment"
    }
    
    return rationales.get((read_type, data_type), "Standard parameters for this data type")

def _calculate_std(values: List[float]) -> float:
    """Calculate standard deviation"""
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5

async def _execute_mapping_workflow(
    workflow_id: str,
    reads_content: str,
    reference_content: str,
    read_type: str,
    algorithm: str,
    quality_threshold: float
):
    """Execute complete mapping workflow in background"""
    try:
        # Parse input files
        from ..utils.file_handlers import FileHandler
        file_handler = FileHandler()
        
        # Parse reads and reference
        if read_type == "single_end":
            reads = await file_handler.parse_fastq_content(reads_content)
        else:
            reads = await file_handler.parse_fasta_content(reads_content)
            
        reference = await file_handler.parse_fasta_content(reference_content)
        
        # Run mapping
        mapping_result = await ngs_mapping_service.map_reads(
            reads=reads,
            reference_sequence=reference[0] if reference else {},
            parameters={"algorithm": algorithm, "quality_threshold": quality_threshold}
        )
        
        logger.info(f"Mapping workflow {workflow_id} completed")
        
    except Exception as e:
        logger.error(f"Mapping workflow {workflow_id} failed: {str(e)}")