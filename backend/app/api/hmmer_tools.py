# backend/app/api/hmmer_tools.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
from typing import List, Dict, Any, Optional
from ..services.hmmer_tools import hmmer_tools_service
from ..models.enhanced_models import SequenceData
from ..database.database_setup import DatabaseManager
from pydantic import BaseModel
import logging
import pandas as pd

logger = logging.getLogger(__name__)
router = APIRouter()

class DESeq2Request(BaseModel):
    count_data: List[Dict[str, Any]]
    sample_info: Dict[str, Any]
    alpha: Optional[float] = 0.05
    lfc_threshold: Optional[float] = 0
    filter_low_counts: Optional[bool] = True

class KallistoRequest(BaseModel):
    fastq_files: List[Dict[str, Any]]
    transcriptome_index: str
    bootstrap_samples: Optional[int] = 100
    fragment_length: Optional[int] = 200
    fragment_sd: Optional[int] = 20
    single_end: Optional[bool] = False

class HMMERSearchRequest(BaseModel):
    sequences: List[SequenceData]
    hmm_profile: str
    evalue_threshold: Optional[float] = 1e-5
    max_hits: Optional[int] = 1000

class SalmonRequest(BaseModel):
    fastq_files: List[Dict[str, Any]]
    transcriptome_index: str
    lib_type: Optional[str] = "A"
    bootstrap_samples: Optional[int] = 100
    bias_correction: Optional[bool] = True

@router.post("/hmmer-tools/deseq2")
async def run_deseq2_analysis(
    request: DESeq2Request,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Run DESeq2 differential expression analysis"""
    try:
        # Prepare parameters
        parameters = {
            "alpha": request.alpha,
            "lfc_threshold": request.lfc_threshold,
            "filter_low_counts": request.filter_low_counts
        }
        
        # Run DESeq2 analysis
        results = await hmmer_tools_service.run_deseq2(
            request.count_data,
            request.sample_info,
            parameters
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        # Store results in database
        background_tasks.add_task(
            db_manager.store_analysis_result,
            "deseq2",
            results,
            {"parameters": parameters, "sample_count": len(request.sample_info.get('samples', []))}
        )
        
        return {
            "status": "success",
            "analysis_id": results["analysis_id"],
            "results": {
                "summary_stats": results["results"].summary_stats,
                "significant_genes_count": len(results["results"].significant_genes),
                "plot_data": results["results"].plot_data
            },
            "download_links": {
                "full_results": f"/api/v1/hmmer-tools/deseq2/{results['analysis_id']}/download",
                "significant_genes": f"/api/v1/hmmer-tools/deseq2/{results['analysis_id']}/significant"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in DESeq2 analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hmmer-tools/kallisto")
async def run_kallisto_quantification(
    request: KallistoRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Run Kallisto RNA-seq quantification"""
    try:
        # Prepare parameters
        parameters = {
            "bootstrap_samples": request.bootstrap_samples,
            "fragment_length": request.fragment_length,
            "fragment_sd": request.fragment_sd,
            "single_end": request.single_end
        }
        
        # Run Kallisto analysis
        results = await hmmer_tools_service.run_kallisto(
            request.fastq_files,
            request.transcriptome_index,
            parameters
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        # Store results in database
        background_tasks.add_task(
            db_manager.store_analysis_result,
            "kallisto",
            results,
            {"parameters": parameters, "file_count": len(request.fastq_files)}
        )
        
        return {
            "status": "success",
            "analysis_id": results["analysis_id"],
            "results": {
                "run_info": results["results"].run_info,
                "quality_metrics": results["results"].quality_metrics,
                "transcript_count": len(results["results"].abundance_estimates)
            },
            "download_links": {
                "abundance": f"/api/v1/hmmer-tools/kallisto/{results['analysis_id']}/abundance",
                "run_info": f"/api/v1/hmmer-tools/kallisto/{results['analysis_id']}/run-info"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in Kallisto analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hmmer-tools/hmmer-search")
async def run_hmmer_search(
    request: HMMERSearchRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Run HMMER profile search"""
    try:
        # Convert SequenceData to dict format
        sequence_dicts = [seq.dict() for seq in request.sequences]
        
        # Prepare parameters
        parameters = {
            "evalue_threshold": request.evalue_threshold,
            "max_hits": request.max_hits
        }
        
        # Run HMMER search
        results = await hmmer_tools_service.run_hmmer_search(
            sequence_dicts,
            request.hmm_profile,
            parameters
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        # Store results in database
        background_tasks.add_task(
            db_manager.store_analysis_result,
            "hmmer_search",
            results,
            {"parameters": parameters, "sequence_count": len(request.sequences)}
        )
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in HMMER search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hmmer-tools/salmon")
async def run_salmon_quantification(
    request: SalmonRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Run Salmon RNA-seq quantification"""
    try:
        # Prepare parameters
        parameters = {
            "lib_type": request.lib_type,
            "bootstrap_samples": request.bootstrap_samples,
            "bias_correction": request.bias_correction
        }
        
        # Run Salmon analysis
        results = await hmmer_tools_service.run_salmon(
            request.fastq_files,
            request.transcriptome_index,
            parameters
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        # Store results in database
        background_tasks.add_task(
            db_manager.store_analysis_result,
            "salmon",
            results,
            {"parameters": parameters, "file_count": len(request.fastq_files)}
        )
        
        return {
            "status": "success",
            "analysis_id": results["analysis_id"],
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in Salmon analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hmmer-tools/supported")
async def get_supported_tools():
    """Get list of supported HMMER and specialized tools"""
    try:
        result = await hmmer_tools_service.get_supported_tools()
        return result
        
    except Exception as e:
        logger.error(f"Error getting supported tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hmmer-tools/{tool_name}/info")
async def get_tool_information(tool_name: str):
    """Get detailed information about a specific tool"""
    try:
        result = await hmmer_tools_service.get_tool_info(tool_name)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "status": "success",
            "tool_info": result
        }
        
    except Exception as e:
        logger.error(f"Error getting tool info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hmmer-tools/{tool_name}/validate-parameters")
async def validate_tool_parameters(
    tool_name: str,
    parameters: Dict[str, Any]
):
    """Validate parameters for a specific tool"""
    try:
        result = await hmmer_tools_service.validate_tool_parameters(tool_name, parameters)
        
        return {
            "status": "success",
            "validation": result
        }
        
    except Exception as e:
        logger.error(f"Error validating parameters: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hmmer-tools/deseq2/{analysis_id}/download")
async def download_deseq2_results(analysis_id: str, format_type: str = "csv"):
    """Download DESeq2 results in specified format"""
    try:
        # In production, retrieve from database and format accordingly
        # For now, return mock download info
        
        return {
            "status": "success",
            "download_url": f"/download/deseq2_{analysis_id}.{format_type}",
            "format": format_type,
            "file_size": "2.5 MB"  # Mock size
        }
        
    except Exception as e:
        logger.error(f"Error preparing download: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hmmer-tools/kallisto/{analysis_id}/abundance")
async def get_kallisto_abundance(analysis_id: str):
    """Get Kallisto abundance estimates"""
    try:
        # In production, retrieve from database
        # For now, return mock data structure
        
        return {
            "status": "success",
            "analysis_id": analysis_id,
            "abundance_data": "Available for download",
            "download_url": f"/download/kallisto_{analysis_id}_abundance.tsv"
        }
        
    except Exception as e:
        logger.error(f"Error getting abundance data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hmmer-tools/batch-analysis")
async def run_batch_analysis(
    analyses: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Run multiple analyses in batch"""
    try:
        batch_id = f"batch_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
        batch_results = []
        
        for i, analysis in enumerate(analyses):
            tool_name = analysis.get('tool')
            if tool_name not in hmmer_tools_service.supported_tools:
                batch_results.append({
                    "analysis_index": i,
                    "status": "failed",
                    "error": f"Unsupported tool: {tool_name}"
                })
                continue
            
            try:
                # Route to appropriate tool
                if tool_name == 'deseq2':
                    result = await hmmer_tools_service.run_deseq2(
                        analysis['count_data'],
                        analysis['sample_info'],
                        analysis.get('parameters', {})
                    )
                elif tool_name == 'kallisto':
                    result = await hmmer_tools_service.run_kallisto(
                        analysis['fastq_files'],
                        analysis['transcriptome_index'],
                        analysis.get('parameters', {})
                    )
                elif tool_name == 'hmmer_search':
                    result = await hmmer_tools_service.run_hmmer_search(
                        analysis['sequences'],
                        analysis['hmm_profile'],
                        analysis.get('parameters', {})
                    )
                else:
                    result = {"error": f"Tool {tool_name} not implemented"}
                
                batch_results.append({
                    "analysis_index": i,
                    "tool": tool_name,
                    "status": "success" if "error" not in result else "failed",
                    "result": result
                })
                
            except Exception as e:
                batch_results.append({
                    "analysis_index": i,
                    "tool": tool_name,
                    "status": "failed",
                    "error": str(e)
                })
        
        # Store batch results
        background_tasks.add_task(
            db_manager.store_batch_analysis_result,
            batch_id,
            batch_results
        )
        
        return {
            "status": "success",
            "batch_id": batch_id,
            "total_analyses": len(analyses),
            "successful": len([r for r in batch_results if r["status"] == "success"]),
            "failed": len([r for r in batch_results if r["status"] == "failed"]),
            "results": batch_results
        }
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hmmer-tools/create-report")
async def create_analysis_report(
    analysis_ids: List[str],
    report_type: str = "summary",
    db_manager: DatabaseManager = Depends()
):
    """Create comprehensive analysis report"""
    try:
        # Retrieve analysis results from database
        analysis_results = []
        for analysis_id in analysis_ids:
            result = await db_manager.get_analysis_result(analysis_id)
            if result:
                analysis_results.append(result)
        
        if not analysis_results:
            raise HTTPException(status_code=404, detail="No analysis results found")
        
        # Create report
        report = await hmmer_tools_service.create_analysis_report(analysis_results, report_type)
        
        if "error" in report:
            raise HTTPException(status_code=400, detail=report["error"])
        
        return {
            "status": "success",
            "report": report
        }
        
    except Exception as e:
        logger.error(f"Error creating report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hmmer-tools/tools")
async def list_available_tools():
    """List all available HMMER and specialized tools"""
    try:
        result = await hmmer_tools_service.get_supported_tools()
        return {
            "status": "success",
            "tools": result
        }
        
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hmmer-tools/{tool_name}/parameters")
async def get_tool_parameters(tool_name: str):
    """Get parameter definitions for a specific tool"""
    try:
        if tool_name not in hmmer_tools_service.supported_tools:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
        
        parameter_definitions = {
            "deseq2": {
                "alpha": {
                    "type": "float",
                    "default": 0.05,
                    "description": "Significance threshold for adjusted p-values",
                    "range": [0.001, 0.1]
                },
                "lfc_threshold": {
                    "type": "float",
                    "default": 0,
                    "description": "Log2 fold change threshold",
                    "range": [0, 5]
                },
                "filter_low_counts": {
                    "type": "boolean",
                    "default": True,
                    "description": "Filter genes with low counts"
                }
            },
            "kallisto": {
                "bootstrap_samples": {
                    "type": "integer",
                    "default": 100,
                    "description": "Number of bootstrap samples",
                    "range": [0, 1000]
                },
                "fragment_length": {
                    "type": "integer",
                    "default": 200,
                    "description": "Average fragment length (for single-end reads)",
                    "range": [50, 1000]
                },
                "fragment_sd": {
                    "type": "integer",
                    "default": 20,
                    "description": "Standard deviation of fragment length",
                    "range": [1, 100]
                },
                "single_end": {
                    "type": "boolean",
                    "default": False,
                    "description": "Single-end reads mode"
                }
            },
            "hmmer_search": {
                "evalue_threshold": {
                    "type": "float",
                    "default": 1e-5,
                    "description": "E-value threshold for significant hits",
                    "range": [1e-10, 1]
                },
                "max_hits": {
                    "type": "integer",
                    "default": 1000,
                    "description": "Maximum number of hits to report",
                    "range": [1, 10000]
                }
            },
            "salmon": {
                "lib_type": {
                    "type": "select",
                    "default": "A",
                    "description": "Library type",
                    "options": ["A", "IU", "ISF", "ISR", "OU", "OSF", "OSR"]
                },
                "bootstrap_samples": {
                    "type": "integer",
                    "default": 100,
                    "description": "Number of bootstrap samples",
                    "range": [0, 1000]
                },
                "bias_correction": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable bias correction"
                }
            }
        }
        
        return {
            "status": "success",
            "tool_name": tool_name,
            "parameters": parameter_definitions.get(tool_name, {}),
            "description": hmmer_tools_service.supported_tools[tool_name]["description"]
        }
        
    except Exception as e:
        logger.error(f"Error getting tool parameters: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hmmer-tools/upload-hmm-profile")
async def upload_hmm_profile(
    file: UploadFile = File(...),
    profile_name: Optional[str] = None
):
    """Upload HMM profile file"""
    try:
        # Validate file type
        if not file.filename.endswith(('.hmm', '.hmmer')):
            raise HTTPException(status_code=400, detail="File must be .hmm or .hmmer format")
        
        # Read file content
        content = await file.read()
        
        # Basic validation of HMM format
        content_str = content.decode('utf-8')
        if not content_str.startswith('HMMER'):
            raise HTTPException(status_code=400, detail="Invalid HMM file format")
        
        # Generate profile ID
        profile_id = profile_name or f"profile_{file.filename.split('.')[0]}"
        
        # In production, store the profile file
        # For now, return success with profile info
        
        return {
            "status": "success",
            "profile_id": profile_id,
            "filename": file.filename,
            "size": len(content),
            "message": "HMM profile uploaded successfully"
        }
        
    except Exception as e:
        logger.error(f"Error uploading HMM profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hmmer-tools/analysis/{analysis_id}/status")
async def get_analysis_status(
    analysis_id: str,
    db_manager: DatabaseManager = Depends()
):
    """Get status of a running analysis"""
    try:
        # In production, check analysis status in database/task queue
        # For now, return mock status
        
        status_info = {
            "analysis_id": analysis_id,
            "status": "completed",
            "progress": 100,
            "started_at": "2024-01-01T10:00:00Z",
            "completed_at": "2024-01-01T10:15:00Z",
            "duration": "15 minutes"
        }
        
        return {
            "status": "success",
            "analysis_status": status_info
        }
        
    except Exception as e:
        logger.error(f"Error getting analysis status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hmmer-tools/compare-results")
async def compare_analysis_results(
    analysis_ids: List[str],
    comparison_type: str = "overlap",
    db_manager: DatabaseManager = Depends()
):
    """Compare results from multiple analyses"""
    try:
        if len(analysis_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 analyses required for comparison")
        
        # Retrieve analysis results
        results = []
        for analysis_id in analysis_ids:
            result = await db_manager.get_analysis_result(analysis_id)
            if result:
                results.append(result)
        
        if len(results) < 2:
            raise HTTPException(status_code=404, detail="Insufficient analysis results found")
        
        # Perform comparison based on type
        if comparison_type == "overlap":
            comparison = await self._compare_gene_overlap(results)
        elif comparison_type == "correlation":
            comparison = await self._compare_expression_correlation(results)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown comparison type: {comparison_type}")
        
        return {
            "status": "success",
            "comparison_type": comparison_type,
            "analyses_compared": len(results),
            "comparison_results": comparison
        }
        
    except Exception as e:
        logger.error(f"Error comparing results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def _compare_gene_overlap(results: List[Dict]) -> Dict:
    """Compare gene overlap between analyses"""
    # Mock implementation for gene overlap comparison
    return {
        "total_unique_genes": 15000,
        "common_genes": 12000,
        "analysis_specific": {
            "analysis_1": 1500,
            "analysis_2": 1500
        },
        "overlap_percentage": 80.0
    }

async def _compare_expression_correlation(results: List[Dict]) -> Dict:
    """Compare expression correlation between analyses"""
    # Mock implementation for correlation comparison
    return {
        "pearson_correlation": 0.85,
        "spearman_correlation": 0.82,
        "significant_correlations": 0.78,
        "comparison_plot_data": {
            "x": [1, 2, 3, 4, 5],
            "y": [1.1, 2.2, 2.9, 4.1, 5.2]
        }
    }