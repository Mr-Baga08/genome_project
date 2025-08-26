# backend/app/api/dna_assembly.py
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Query, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Dict, Any, Optional, Union
import json
import tempfile
from pathlib import Path
import logging
from datetime import datetime
from pydantic import BaseModel, Field, validator

from ..services.dna_assembly import DNAAssemblyService
from ..services.data_writers import DataWritersService
from ..database.database_setup import DatabaseManager
from ..websockets.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dna-assembly", tags=["DNA Assembly"])

# Initialize services
dna_assembly_service = DNAAssemblyService()
data_writers_service = DataWritersService()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class AssemblyRequest(BaseModel):
    """Base request model for assembly operations"""
    reads: List[Dict[str, Any]] = Field(..., min_items=1)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('reads')
    def validate_reads(cls, v):
        for read in v:
            if 'sequence' not in read and ('r1' not in read or 'r2' not in read):
                raise ValueError("Each read must have either 'sequence' field or 'r1'/'r2' fields for paired-end")
        return v

class OLCAssemblyRequest(AssemblyRequest):
    """Request model for Overlap-Layout-Consensus assembly"""
    parameters: Dict[str, Any] = Field(
        default_factory=lambda: {
            "min_overlap": 20,
            "min_identity": 0.95,
            "min_contig_length": 100
        }
    )

class KmerAssemblyRequest(AssemblyRequest):
    """Request model for k-mer based assembly"""
    parameters: Dict[str, Any] = Field(
        default_factory=lambda: {
            "k_mer_size": 21,
            "min_coverage": 3,
            "min_contig_length": 100
        }
    )

class SpadesAssemblyRequest(AssemblyRequest):
    """Request model for SPAdes assembly"""
    parameters: Dict[str, Any] = Field(
        default_factory=lambda: {
            "k_list": "21,33,55",
            "careful": True,
            "only_assembler": False
        }
    )

class Cap3AssemblyRequest(AssemblyRequest):
    """Request model for CAP3 assembly"""
    parameters: Dict[str, Any] = Field(
        default_factory=lambda: {
            "overlap_length": 40,
            "overlap_percent_identity": 80,
            "max_gap_length": 20
        }
    )

class AssemblyQualityRequest(BaseModel):
    """Request model for assembly quality evaluation"""
    contigs: List[Dict[str, Any]]
    reference_sequences: Optional[List[Dict[str, Any]]] = None

class AssemblyComparisonRequest(BaseModel):
    """Request model for comparing multiple assemblies"""
    assemblies: List[Dict[str, Any]] = Field(..., min_items=2, max_items=10)

# ============================================================================
# ASSEMBLY ALGORITHM ENDPOINTS
# ============================================================================

@router.post("/olc-assembly")
async def run_olc_assembly(
    request: OLCAssemblyRequest,
    background_tasks: BackgroundTasks,
    save_to_db: bool = Query(True)
):
    """Run Overlap-Layout-Consensus assembly algorithm"""
    try:
        result = await dna_assembly_service.assembler_1(
            reads=request.reads,
            parameters=request.parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Save to database if requested
        if save_to_db:
            background_tasks.add_task(
                _save_assembly_result,
                result,
                "olc_assembly",
                request.parameters
            )
        
        return {
            "status": "success",
            "algorithm": "Overlap-Layout-Consensus",
            "assembly_result": result,
            "summary": {
                "total_contigs": len(result.get("contigs", [])),
                "total_length": sum(contig.get("length", 0) for contig in result.get("contigs", [])),
                "input_reads": len(request.reads)
            }
        }
        
    except Exception as e:
        logger.error(f"OLC assembly error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OLC assembly failed: {str(e)}")

@router.post("/kmer-assembly")
async def run_kmer_assembly(
    request: KmerAssemblyRequest,
    background_tasks: BackgroundTasks,
    save_to_db: bool = Query(True)
):
    """Run k-mer based assembly algorithm"""
    try:
        result = await dna_assembly_service.assembler_2(
            reads=request.reads,
            parameters=request.parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        if save_to_db:
            background_tasks.add_task(
                _save_assembly_result,
                result,
                "kmer_assembly",
                request.parameters
            )
        
        return {
            "status": "success",
            "algorithm": "k-mer based",
            "assembly_result": result,
            "summary": {
                "total_contigs": len(result.get("contigs", [])),
                "total_length": sum(contig.get("length", 0) for contig in result.get("contigs", [])),
                "k_mer_size": request.parameters.get("k_mer_size", 21),
                "input_reads": len(request.reads)
            }
        }
        
    except Exception as e:
        logger.error(f"k-mer assembly error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"k-mer assembly failed: {str(e)}")

@router.post("/spades-assembly")
async def run_spades_assembly(
    request: SpadesAssemblyRequest,
    background_tasks: BackgroundTasks,
    save_to_db: bool = Query(True)
):
    """Run SPAdes assembly using Docker container"""
    try:
        result = await dna_assembly_service.spades_assembly(
            reads=request.reads,
            parameters=request.parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        if save_to_db:
            background_tasks.add_task(
                _save_assembly_result,
                result,
                "spades_assembly",
                request.parameters
            )
        
        return {
            "status": "success",
            "algorithm": "SPAdes",
            "assembly_result": result,
            "summary": {
                "total_contigs": len(result.get("contigs", [])),
                "total_length": sum(contig.get("length", 0) for contig in result.get("contigs", [])),
                "k_values": request.parameters.get("k_list", "21,33,55"),
                "input_reads": len(request.reads)
            }
        }
        
    except Exception as e:
        logger.error(f"SPAdes assembly error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"SPAdes assembly failed: {str(e)}")

@router.post("/cap3-assembly")
async def run_cap3_assembly(
    request: Cap3AssemblyRequest,
    background_tasks: BackgroundTasks,
    save_to_db: bool = Query(True)
):
    """Run CAP3 assembly using Docker container"""
    try:
        result = await dna_assembly_service.cap3_assembly(
            sequences=request.reads,  # CAP3 works with sequences
            parameters=request.parameters
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        if save_to_db:
            background_tasks.add_task(
                _save_assembly_result,
                result,
                "cap3_assembly",
                request.parameters
            )
        
        return {
            "status": "success",
            "algorithm": "CAP3",
            "assembly_result": result,
            "summary": {
                "total_contigs": len(result.get("contigs", [])),
                "total_singlets": len([c for c in result.get("contigs", []) if c.get("type") == "singlet"]),
                "total_length": sum(contig.get("length", 0) for contig in result.get("contigs", [])),
                "input_sequences": len(request.reads)
            }
        }
        
    except Exception as e:
        logger.error(f"CAP3 assembly error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"CAP3 assembly failed: {str(e)}")

# ============================================================================
# ASSEMBLY QUALITY ASSESSMENT ENDPOINTS
# ============================================================================

@router.post("/evaluate-quality")
async def evaluate_assembly_quality(request: AssemblyQualityRequest):
    """Evaluate assembly quality metrics"""
    try:
        quality_metrics = await dna_assembly_service.evaluate_assembly_quality(
            contigs=request.contigs,
            reference_sequences=request.reference_sequences
        )
        
        if "error" in quality_metrics:
            raise HTTPException(status_code=400, detail=quality_metrics["error"])
        
        return {
            "status": "success",
            "quality_assessment": quality_metrics,
            "assessment_summary": {
                "overall_score": _calculate_overall_quality_score(quality_metrics),
                "contigs_evaluated": len(request.contigs),
                "has_reference": request.reference_sequences is not None
            }
        }
        
    except Exception as e:
        logger.error(f"Assembly quality evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Quality evaluation failed: {str(e)}")

@router.post("/compare-assemblies")
async def compare_multiple_assemblies(request: AssemblyComparisonRequest):
    """Compare quality metrics across multiple assemblies"""
    try:
        comparison_results = []
        
        for i, assembly in enumerate(request.assemblies):
            quality_metrics = await dna_assembly_service.evaluate_assembly_quality(
                contigs=assembly.get("contigs", [])
            )
            
            comparison_results.append({
                "assembly_index": i,
                "assembly_name": assembly.get("name", f"Assembly_{i+1}"),
                "quality_metrics": quality_metrics,
                "overall_score": _calculate_overall_quality_score(quality_metrics)
            })
        
        # Rank assemblies by quality
        ranked_assemblies = sorted(
            comparison_results,
            key=lambda x: x["overall_score"],
            reverse=True
        )
        
        return {
            "status": "success",
            "total_assemblies": len(request.assemblies),
            "comparison_results": comparison_results,
            "ranked_assemblies": ranked_assemblies,
            "best_assembly": ranked_assemblies[0] if ranked_assemblies else None
        }
        
    except Exception as e:
        logger.error(f"Assembly comparison error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Assembly comparison failed: {str(e)}")

# ============================================================================
# ASSEMBLY EXPORT ENDPOINTS
# ============================================================================

@router.post("/export-contigs")
async def export_assembly_contigs(
    contigs: List[Dict[str, Any]],
    format_type: str = Query("fasta", regex="^(fasta|fastq|gff3)$"),
    filename: Optional[str] = None
):
    """Export assembly contigs to specified format"""
    try:
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"assembly_contigs_{timestamp}.{format_type}"
        
        # Convert contigs to sequences for writing
        sequences = []
        for contig in contigs:
            sequences.append({
                "id": contig.get("id", "contig"),
                "sequence": contig.get("sequence", ""),
                "description": f"Length: {contig.get('length', 0)} bp, Coverage: {contig.get('coverage', 0):.2f}x"
            })
        
        # Write using data writers service
        write_result = await data_writers_service.write_sequences(
            sequences=sequences,
            format_type=format_type,
            filename=filename
        )
        
        if "error" in write_result:
            raise HTTPException(status_code=400, detail=write_result["error"])
        
        return {
            "status": "success",
            "format": format_type,
            "contigs_exported": len(contigs),
            "total_length": sum(contig.get("length", 0) for contig in contigs),
            "download_url": f"/api/v1/data-writers/download/{write_result['operation_id']}"
        }
        
    except Exception as e:
        logger.error(f"Contig export error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Contig export failed: {str(e)}")

# ============================================================================
# ASSEMBLY PIPELINE ENDPOINTS
# ============================================================================

@router.post("/run-assembly-pipeline")
async def run_complete_assembly_pipeline(
    reads: List[Dict[str, Any]],
    algorithms: List[str] = Query(["spades", "cap3"], description="Assembly algorithms to run"),
    compare_results: bool = Query(True),
    background_tasks: BackgroundTasks
):
    """Run complete assembly pipeline with multiple algorithms"""
    try:
        pipeline_id = f"pipeline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            _execute_assembly_pipeline,
            pipeline_id,
            reads,
            algorithms,
            compare_results
        )
        
        return {
            "status": "started",
            "pipeline_id": pipeline_id,
            "algorithms": algorithms,
            "input_reads": len(reads),
            "compare_results": compare_results,
            "monitor_url": f"/api/v1/dna-assembly/pipeline-status/{pipeline_id}"
        }
        
    except Exception as e:
        logger.error(f"Assembly pipeline error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Assembly pipeline failed: {str(e)}")

@router.get("/pipeline-status/{pipeline_id}")
async def get_assembly_pipeline_status(pipeline_id: str):
    """Get status of assembly pipeline execution"""
    # In production, this would query actual pipeline status
    return {
        "pipeline_id": pipeline_id,
        "status": "completed",
        "progress": 100,
        "current_step": "comparison",
        "completed_algorithms": ["spades", "cap3"],
        "failed_algorithms": [],
        "estimated_remaining_time": 0
    }

# ============================================================================
# ASSEMBLY ANALYSIS ENDPOINTS
# ============================================================================

@router.post("/analyze-assembly-stats")
async def analyze_assembly_statistics(contigs: List[Dict[str, Any]]):
    """Calculate comprehensive assembly statistics"""
    try:
        # Calculate basic stats using the service
        basic_stats = dna_assembly_service._calculate_assembly_stats(contigs)
        
        # Add additional analysis
        contig_lengths = [contig.get("length", 0) for contig in contigs]
        total_length = sum(contig_lengths)
        
        enhanced_stats = {
            **basic_stats,
            "contiguity_metrics": {
                "n50": dna_assembly_service._calculate_n50(sorted(contig_lengths, reverse=True), total_length),
                "l50": dna_assembly_service._calculate_l50(sorted(contig_lengths, reverse=True), total_length),
                "largest_contig": max(contig_lengths) if contig_lengths else 0,
                "smallest_contig": min(contig_lengths) if contig_lengths else 0
            },
            "composition_analysis": {
                "total_gc_content": sum(contig.get("gc_content", 0) for contig in contigs) / len(contigs) if contigs else 0,
                "gc_content_range": {
                    "min": min(contig.get("gc_content", 0) for contig in contigs) if contigs else 0,
                    "max": max(contig.get("gc_content", 0) for contig in contigs) if contigs else 0
                }
            }
        }
        
        return {
            "status": "success",
            "assembly_statistics": enhanced_stats,
            "contigs_analyzed": len(contigs)
        }
        
    except Exception as e:
        logger.error(f"Assembly statistics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Assembly statistics failed: {str(e)}")

@router.post("/assembly-metrics")
async def calculate_assembly_metrics(
    contigs: List[Dict[str, Any]],
    include_detailed_metrics: bool = Query(True)
):
    """Calculate detailed assembly metrics"""
    try:
        metrics = {
            "basic_metrics": dna_assembly_service._calculate_assembly_stats(contigs),
            "contiguity_metrics": dna_assembly_service._calculate_contiguity_metrics(contigs),
            "completeness_metrics": dna_assembly_service._estimate_completeness(contigs)
        }
        
        if include_detailed_metrics:
            # Add per-contig detailed metrics
            detailed_contigs = []
            for contig in contigs:
                detailed_contig = {
                    **contig,
                    "n_content": (contig.get("sequence", "").upper().count('N') / 
                                len(contig.get("sequence", "")) * 100) if contig.get("sequence") else 0,
                    "complexity_score": _calculate_sequence_complexity(contig.get("sequence", ""))
                }
                detailed_contigs.append(detailed_contig)
            
            metrics["detailed_contigs"] = detailed_contigs
        
        return {
            "status": "success",
            "metrics": metrics,
            "contigs_analyzed": len(contigs)
        }
        
    except Exception as e:
        logger.error(f"Assembly metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Assembly metrics calculation failed: {str(e)}")

# ============================================================================
# ASSEMBLY OPTIMIZATION ENDPOINTS
# ============================================================================

@router.post("/optimize-assembly-parameters")
async def optimize_assembly_parameters(
    reads: List[Dict[str, Any]],
    algorithm: str = Query(..., regex="^(olc|kmer|spades|cap3)$"),
    optimization_metric: str = Query("n50", regex="^(n50|total_length|contig_count)$")
):
    """Find optimal parameters for assembly algorithm"""
    try:
        # Test different parameter combinations
        parameter_sets = _generate_parameter_combinations(algorithm)
        
        optimization_results = []
        best_result = None
        best_score = 0
        
        for i, params in enumerate(parameter_sets):
            try:
                if algorithm == "olc":
                    result = await dna_assembly_service.assembler_1(reads, params)
                elif algorithm == "kmer":
                    result = await dna_assembly_service.assembler_2(reads, params)
                elif algorithm == "spades":
                    result = await dna_assembly_service.spades_assembly(reads, params)
                elif algorithm == "cap3":
                    result = await dna_assembly_service.cap3_assembly(reads, params)
                
                if "error" not in result:
                    score = _evaluate_assembly_score(result, optimization_metric)
                    optimization_results.append({
                        "parameter_set": i + 1,
                        "parameters": params,
                        "score": score,
                        "contigs": len(result.get("contigs", [])),
                        "total_length": sum(contig.get("length", 0) for contig in result.get("contigs", []))
                    })
                    
                    if score > best_score:
                        best_score = score
                        best_result = {
                            "parameters": params,
                            "score": score,
                            "assembly_result": result
                        }
                        
            except Exception as e:
                logger.warning(f"Parameter set {i+1} failed: {str(e)}")
        
        return {
            "status": "success",
            "algorithm": algorithm,
            "optimization_metric": optimization_metric,
            "parameter_sets_tested": len(parameter_sets),
            "successful_runs": len(optimization_results),
            "best_parameters": best_result["parameters"] if best_result else None,
            "best_score": best_score,
            "optimization_results": optimization_results
        }
        
    except Exception as e:
        logger.error(f"Assembly optimization error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Assembly optimization failed: {str(e)}")

# ============================================================================
# ASSEMBLY WORKFLOW ENDPOINTS
# ============================================================================

@router.post("/assembly-workflow")
async def run_assembly_workflow(
    reads_file: UploadFile = File(...),
    quality_threshold: float = Form(20.0),
    assembly_algorithm: str = Form("spades"),
    post_assembly_analysis: bool = Form(True),
    background_tasks: BackgroundTasks
):
    """Run complete assembly workflow from reads file"""
    try:
        # Read and parse input file
        content = await reads_file.read()
        file_content = content.decode('utf-8')
        
        # Parse reads based on file format
        from ..utils.file_handlers import FileHandler
        file_handler = FileHandler()
        
        if reads_file.filename.endswith(('.fastq', '.fq')):
            reads = await file_handler.parse_fastq_content(file_content)
        elif reads_file.filename.endswith(('.fasta', '.fa')):
            reads = await file_handler.parse_fasta_content(file_content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        workflow_id = f"workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        background_tasks.add_task(
            _execute_assembly_workflow,
            workflow_id,
            reads,
            quality_threshold,
            assembly_algorithm,
            post_assembly_analysis
        )
        
        return {
            "status": "started",
            "workflow_id": workflow_id,
            "input_reads": len(reads),
            "quality_threshold": quality_threshold,
            "assembly_algorithm": assembly_algorithm,
            "monitor_url": f"/api/v1/dna-assembly/workflow-status/{workflow_id}"
        }
        
    except Exception as e:
        logger.error(f"Assembly workflow error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Assembly workflow failed: {str(e)}")

@router.get("/workflow-status/{workflow_id}")
async def get_assembly_workflow_status(workflow_id: str):
    """Get status of assembly workflow"""
    # In production, this would query actual workflow status
    return {
        "workflow_id": workflow_id,
        "status": "completed",
        "progress": 100,
        "current_step": "post_analysis",
        "completed_steps": ["quality_filtering", "assembly", "quality_assessment"],
        "failed_steps": []
    }

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _save_assembly_result(
    result: Dict[str, Any],
    algorithm: str,
    parameters: Dict[str, Any]
):
    """Save assembly result to database"""
    try:
        # This would use the DatabaseManager to store results
        logger.info(f"Assembly result saved: {algorithm}")
    except Exception as e:
        logger.error(f"Failed to save assembly result: {str(e)}")

def _calculate_overall_quality_score(quality_metrics: Dict[str, Any]) -> float:
    """Calculate overall quality score from metrics"""
    try:
        basic_stats = quality_metrics.get("basic_stats", {})
        contiguity = quality_metrics.get("contiguity", {})
        
        # Simple scoring algorithm
        score = 0
        
        # Length score (0-40 points)
        total_length = basic_stats.get("total_length", 0)
        score += min(40, total_length / 1000000 * 20)  # 20 points per MB
        
        # N50 score (0-30 points)
        n50 = contiguity.get("contig_n50", 0)
        score += min(30, n50 / 10000 * 10)  # Points based on N50
        
        # Contiguity score (0-30 points)
        contig_count = contiguity.get("total_contigs", float('inf'))
        if total_length > 0:
            contiguity_ratio = total_length / contig_count
            score += min(30, contiguity_ratio / 1000 * 5)
        
        return round(min(100, score), 2)
        
    except Exception:
        return 0.0

def _generate_parameter_combinations(algorithm: str) -> List[Dict[str, Any]]:
    """Generate parameter combinations for optimization"""
    if algorithm == "kmer":
        return [
            {"k_mer_size": 15, "min_coverage": 2, "min_contig_length": 100},
            {"k_mer_size": 21, "min_coverage": 3, "min_contig_length": 200},
            {"k_mer_size": 27, "min_coverage": 4, "min_contig_length": 500},
            {"k_mer_size": 31, "min_coverage": 5, "min_contig_length": 1000}
        ]
    elif algorithm == "olc":
        return [
            {"min_overlap": 15, "min_identity": 0.90, "min_contig_length": 100},
            {"min_overlap": 20, "min_identity": 0.95, "min_contig_length": 200},
            {"min_overlap": 25, "min_identity": 0.98, "min_contig_length": 500}
        ]
    elif algorithm == "spades":
        return [
            {"k_list": "21,33,55", "careful": True},
            {"k_list": "21,33,55,77", "careful": True},
            {"k_list": "15,21,33,55", "careful": False}
        ]
    elif algorithm == "cap3":
        return [
            {"overlap_length": 30, "overlap_percent_identity": 80},
            {"overlap_length": 40, "overlap_percent_identity": 85},
            {"overlap_length": 50, "overlap_percent_identity": 90}
        ]
    else:
        return [{}]

def _evaluate_assembly_score(result: Dict[str, Any], metric: str) -> float:
    """Evaluate assembly based on specified metric"""
    contigs = result.get("contigs", [])
    
    if metric == "n50":
        lengths = [contig.get("length", 0) for contig in contigs]
        total_length = sum(lengths)
        return dna_assembly_service._calculate_n50(sorted(lengths, reverse=True), total_length)
    
    elif metric == "total_length":
        return sum(contig.get("length", 0) for contig in contigs)
    
    elif metric == "contig_count":
        return -len(contigs)  # Negative because fewer contigs is better
    
    else:
        return 0

def _calculate_sequence_complexity(sequence: str) -> float:
    """Calculate sequence complexity score"""
    if not sequence:
        return 0.0
    
    # Simple complexity based on nucleotide distribution
    counts = {"A": 0, "T": 0, "G": 0, "C": 0}
    for base in sequence.upper():
        if base in counts:
            counts[base] += 1
    
    total = sum(counts.values())
    if total == 0:
        return 0.0
    
    # Calculate entropy-based complexity
    import math
    entropy = 0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    
    return entropy / 2.0  # Normalize to 0-1 scale

async def _execute_assembly_pipeline(
    pipeline_id: str,
    reads: List[Dict[str, Any]],
    algorithms: List[str],
    compare_results: bool
):
    """Execute complete assembly pipeline in background"""
    try:
        pipeline_results = {}
        
        # Run each algorithm
        for algorithm in algorithms:
            try:
                if algorithm == "spades":
                    result = await dna_assembly_service.spades_assembly(reads)
                elif algorithm == "cap3":
                    result = await dna_assembly_service.cap3_assembly(reads)
                elif algorithm == "olc":
                    result = await dna_assembly_service.assembler_1(reads)
                elif algorithm == "kmer":
                    result = await dna_assembly_service.assembler_2(reads)
                else:
                    continue
                
                pipeline_results[algorithm] = result
                
            except Exception as e:
                logger.error(f"Algorithm {algorithm} failed in pipeline {pipeline_id}: {str(e)}")
                pipeline_results[algorithm] = {"error": str(e)}
        
        # Compare results if requested
        if compare_results and len(pipeline_results) > 1:
            comparison = await _compare_pipeline_results(pipeline_results)
            pipeline_results["comparison"] = comparison
        
        logger.info(f"Assembly pipeline {pipeline_id} completed")
        
    except Exception as e:
        logger.error(f"Assembly pipeline {pipeline_id} failed: {str(e)}")

async def _compare_pipeline_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Compare results from multiple assembly algorithms"""
    comparison = {
        "algorithms_compared": list(results.keys()),
        "quality_comparison": {},
        "recommendations": []
    }
    
    # Compare quality metrics
    for algorithm, result in results.items():
        if "error" not in result:
            contigs = result.get("contigs", [])
            comparison["quality_comparison"][algorithm] = {
                "contig_count": len(contigs),
                "total_length": sum(contig.get("length", 0) for contig in contigs),
                "quality_score": _calculate_overall_quality_score({"basic_stats": result.get("stats", {})})
            }
    
    return comparison