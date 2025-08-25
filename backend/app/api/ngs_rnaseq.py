# backend/app/api/ngs_rnaseq.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Response
from typing import List, Dict, Any, Optional
from ..services.ngs_rnaseq import ngs_rnaseq_service
from ..models.enhanced_models import SequenceData
from ..database.database_setup import DatabaseManager
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ExpressionQuantificationRequest(BaseModel):
    mapped_reads: List[Dict[str, Any]]
    gtf_file: str
    method: str = "featurecounts"
    parameters: Optional[Dict[str, Any]] = {}

class DifferentialExpressionRequest(BaseModel):
    expression_data: Dict[str, Any]
    sample_groups: Dict[str, Any]
    method: str = "deseq2"
    parameters: Optional[Dict[str, Any]] = {}

class PathwayAnalysisRequest(BaseModel):
    differential_results: Dict[str, Any]
    pathway_database: str = "mock"
    significance_threshold: Optional[float] = 0.05

class GeneSetAnalysisRequest(BaseModel):
    expression_data: Dict[str, Any]
    gene_sets: List[Dict[str, Any]]
    method: str = "gsea"

@router.post("/rnaseq/quantify")
async def quantify_expression(
    request: ExpressionQuantificationRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Quantify gene expression from mapped reads"""
    try:
        results = await ngs_rnaseq_service.quantify_expression(
            request.mapped_reads,
            request.gtf_file,
            request.method,
            request.parameters
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        # Store results in database
        background_tasks.add_task(
            db_manager.store_analysis_result,
            "expression_quantification",
            results,
            {
                "method": request.method,
                "read_files": len(request.mapped_reads),
                "parameters": request.parameters
            }
        )
        
        return {
            "status": "success",
            "quantification_id": results["analysis_id"],
            "method_used": results["method"],
            "summary": {
                "genes_quantified": len(results["results"].gene_expression),
                "samples_processed": len(request.mapped_reads),
                "mapping_rate": results["results"].mapping_stats.get("mapping_rate", 0)
            },
            "download_links": {
                "gene_counts": f"/api/v1/rnaseq/{results['analysis_id']}/gene-counts",
                "transcript_counts": f"/api/v1/rnaseq/{results['analysis_id']}/transcript-counts"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in expression quantification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rnaseq/differential")
async def differential_expression_analysis(
    request: DifferentialExpressionRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Perform differential expression analysis"""
    try:
        results = await ngs_rnaseq_service.differential_expression(
            request.expression_data,
            request.sample_groups,
            request.method,
            request.parameters
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        # Store results in database
        background_tasks.add_task(
            db_manager.store_analysis_result,
            "differential_expression",
            results,
            {
                "method": request.method,
                "comparison": results["results"].comparison_info,
                "parameters": request.parameters
            }
        )
        
        return {
            "status": "success",
            "analysis_id": results["analysis_id"],
            "method_used": results["method"],
            "summary": results["results"].summary_stats,
            "significant_genes": len(results["results"].significant_genes),
            "plot_data": results["results"].plots_data,
            "download_links": {
                "full_results": f"/api/v1/rnaseq/differential/{results['analysis_id']}/results",
                "significant_genes": f"/api/v1/rnaseq/differential/{results['analysis_id']}/significant"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in differential expression: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rnaseq/pathway-analysis")
async def pathway_enrichment_analysis(
    request: PathwayAnalysisRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Perform pathway enrichment analysis"""
    try:
        results = await ngs_rnaseq_service.perform_pathway_analysis(
            request.differential_results,
            request.pathway_database
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        # Store results in database
        background_tasks.add_task(
            db_manager.store_analysis_result,
            "pathway_analysis",
            results,
            {
                "database": request.pathway_database,
                "input_genes": results.get("input_genes", 0)
            }
        )
        
        return {
            "status": "success",
            "pathway_analysis_id": f"pathway_{hash(str(results))}",
            "summary": {
                "pathways_tested": results.get("pathways_tested", 0),
                "significant_pathways": results.get("significant_pathways", 0),
                "database_used": request.pathway_database
            },
            "results": {
                "top_pathways": results.get("top_pathways", []),
                "all_pathways": results.get("enriched_pathways", [])
            }
        }
        
    except Exception as e:
        logger.error(f"Error in pathway analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rnaseq/gene-set-analysis")
async def gene_set_enrichment_analysis(
    request: GeneSetAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """Perform gene set enrichment analysis"""
    try:
        results = await ngs_rnaseq_service.perform_gene_set_analysis(
            request.expression_data,
            request.gene_sets
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        return {
            "status": "success",
            "gsea_id": f"gsea_{hash(str(results))}",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in gene set analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rnaseq/heatmap-data")
async def create_expression_heatmap(
    expression_data: Dict[str, Any],
    top_genes: int = 50,
    gene_selection: str = "variance"
):
    """Create heatmap data for expression visualization"""
    try:
        results = await ngs_rnaseq_service.create_expression_heatmap_data(
            expression_data,
            top_genes
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        return {
            "status": "success",
            "heatmap_data": results["heatmap_data"],
            "parameters": results["parameters"]
        }
        
    except Exception as e:
        logger.error(f"Error creating heatmap data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rnaseq/sample-correlation")
async def calculate_sample_correlation(
    expression_data: Dict[str, Any]
):
    """Calculate sample correlation matrix"""
    try:
        results = await ngs_rnaseq_service.calculate_sample_correlation(expression_data)
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        return {
            "status": "success",
            "correlation_data": results
        }
        
    except Exception as e:
        logger.error(f"Error calculating sample correlation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rnaseq/pca")
async def perform_pca_analysis(
    expression_data: Dict[str, Any],
    top_genes: int = 1000
):
    """Perform Principal Component Analysis"""
    try:
        results = await ngs_rnaseq_service.perform_pca_analysis(
            expression_data,
            top_genes
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        return {
            "status": "success",
            "pca_results": results
        }
        
    except Exception as e:
        logger.error(f"Error in PCA analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rnaseq/methods")
async def get_supported_methods():
    """Get supported RNA-seq analysis methods"""
    try:
        methods = await ngs_rnaseq_service.get_supported_methods()
        return {
            "status": "success",
            "methods": methods
        }
        
    except Exception as e:
        logger.error(f"Error getting methods: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rnaseq/{analysis_id}/gene-counts")
async def download_gene_counts(
    analysis_id: str,
    format_type: str = "csv",
    db_manager: DatabaseManager = Depends()
):
    """Download gene count data"""
    try:
        # In production, retrieve from database
        # For now, return mock download info
        
        mock_data = "gene_id,sample1,sample2,sample3\nENSG001,100,150,120\nENSG002,50,75,60"
        
        media_type_map = {
            "csv": "text/csv",
            "tsv": "text/tab-separated-values",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        
        return Response(
            content=mock_data,
            media_type=media_type_map.get(format_type, "text/csv"),
            headers={
                "Content-Disposition": f"attachment; filename=gene_counts_{analysis_id}.{format_type}"
            }
        )
        
    except Exception as e:
        logger.error(f"Error downloading gene counts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rnaseq/differential/{analysis_id}/results")
async def download_differential_results(
    analysis_id: str,
    format_type: str = "csv",
    include_plots: bool = False,
    db_manager: DatabaseManager = Depends()
):
    """Download differential expression results"""
    try:
        # In production, retrieve from database
        # Mock differential expression results
        
        mock_results = """gene_id,gene_name,baseMean,log2FoldChange,lfcSE,stat,pvalue,padj
ENSG001,Gene_001,150.5,2.3,0.4,5.75,8.9e-09,1.2e-06
ENSG002,Gene_002,89.2,-1.8,0.3,-6.0,2.0e-09,3.5e-07
ENSG003,Gene_003,45.1,0.2,0.5,0.4,0.69,0.85"""
        
        return Response(
            content=mock_results,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=differential_results_{analysis_id}.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"Error downloading differential results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rnaseq/workflows")
async def get_rnaseq_workflows():
    """Get predefined RNA-seq analysis workflows"""
    return {
        "workflows": [
            {
                "id": "standard_bulk_rnaseq",
                "name": "Standard Bulk RNA-seq",
                "description": "Complete bulk RNA-seq analysis pipeline",
                "steps": [
                    "quality_control",
                    "read_mapping", 
                    "expression_quantification",
                    "differential_expression",
                    "pathway_analysis"
                ],
                "estimated_time": "2-4 hours",
                "suitable_for": "Most bulk RNA-seq experiments"
            },
            {
                "id": "transcript_discovery",
                "name": "Transcript Discovery",
                "description": "Novel transcript discovery and quantification",
                "steps": [
                    "quality_control",
                    "read_mapping",
                    "transcript_assembly",
                    "transcript_quantification",
                    "differential_expression"
                ],
                "estimated_time": "4-8 hours", 
                "suitable_for": "Studies focusing on alternative splicing"
            },
            {
                "id": "quick_analysis",
                "name": "Quick Expression Analysis",
                "description": "Fast expression analysis for preliminary results",
                "steps": [
                    "read_mapping",
                    "expression_quantification", 
                    "basic_statistics"
                ],
                "estimated_time": "1-2 hours",
                "suitable_for": "Initial data exploration"
            }
        ]
    }

@router.post("/rnaseq/validate-design")
async def validate_experimental_design(
    sample_info: Dict[str, Any],
    comparison_groups: List[Dict[str, Any]]
):
    """Validate experimental design for RNA-seq analysis"""
    try:
        samples = sample_info.get('samples', [])
        
        if len(samples) < 2:
            raise HTTPException(status_code=400, detail="At least 2 samples required")
        
        validation_results = {
            "valid": True,
            "warnings": [],
            "recommendations": [],
            "sample_summary": {
                "total_samples": len(samples),
                "groups": len(comparison_groups)
            }
        }
        
        # Check replication
        for group in comparison_groups:
            group_samples = group.get('samples', [])
            if len(group_samples) < 3:
                validation_results["warnings"].append(
                    f"Group '{group.get('name', 'unnamed')}' has fewer than 3 replicates"
                )
            elif len(group_samples) >= 6:
                validation_results["recommendations"].append(
                    f"Group '{group.get('name', 'unnamed')}' has good replication (n={len(group_samples)})"
                )
        
        # Check for batch effects
        batch_info = set(s.get('batch', 'unknown') for s in samples)
        if len(batch_info) > 1 and 'unknown' not in batch_info:
            validation_results["recommendations"].append(
                "Multiple batches detected - consider including batch as a covariate"
            )
        
        return {
            "status": "success",
            "validation": validation_results
        }
        
    except Exception as e:
        logger.error(f"Error validating design: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rnaseq/quality-control")
async def perform_quality_control(
    expression_data: Dict[str, Any],
    sample_metadata: Dict[str, Any]
):
    """Perform quality control analysis on RNA-seq data"""
    try:
        # Mock QC analysis
        np.random.seed(42)
        
        samples = sample_metadata.get('samples', [])
        sample_names = [s.get('name', f'sample_{i}') for i, s in enumerate(samples)]
        
        qc_results = {
            "sample_qc": [],
            "overall_qc": {
                "total_samples": len(samples),
                "passed_qc": len(samples) - np.random.randint(0, max(1, len(samples) // 10)),
                "median_reads": np.random.randint(20000000, 50000000),
                "median_genes_detected": np.random.randint(15000, 18000)
            },
            "outlier_detection": {
                "method": "PCA + correlation",
                "outlier_samples": []
            }
        }
        
        # Generate per-sample QC metrics
        for sample_name in sample_names:
            sample_qc = {
                "sample_name": sample_name,
                "total_reads": np.random.randint(15000000, 60000000),
                "mapped_reads": np.random.randint(12000000, 55000000),
                "genes_detected": np.random.randint(14000, 19000),
                "mapping_rate": np.random.uniform(75, 95),
                "duplicate_rate": np.random.uniform(5, 25),
                "gc_content": np.random.uniform(40, 60),
                "qc_status": np.random.choice(["PASS", "WARNING", "FAIL"], p=[0.8, 0.15, 0.05])
            }
            
            # Flag potential outliers
            if (sample_qc["mapping_rate"] < 80 or 
                sample_qc["genes_detected"] < 15000 or
                sample_qc["duplicate_rate"] > 20):
                qc_results["outlier_detection"]["outlier_samples"].append(sample_name)
            
            qc_results["sample_qc"].append(sample_qc)
        
        return {
            "status": "success",
            "qc_results": qc_results,
            "recommendations": [
                "Remove samples with mapping rate < 70%",
                "Consider batch correction if needed",
                "Filter genes with low counts across samples"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in quality control: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rnaseq/normalization")
async def normalize_expression_data(
    expression_data: Dict[str, Any],
    normalization_method: str = "TPM",
    log_transform: bool = True
):
    """Normalize expression data using various methods"""
    try:
        if 'gene_expression' not in expression_data:
            raise HTTPException(status_code=400, detail="Gene expression data not found")
        
        expr_df = pd.DataFrame(expression_data['gene_expression'])
        numeric_cols = expr_df.select_dtypes(include=[np.number]).columns
        
        # Mock normalization
        if normalization_method == "TPM":
            # Mock TPM calculation
            normalized_data = expr_df[numeric_cols] * 1000000 / expr_df[numeric_cols].sum()
        elif normalization_method == "RPKM":
            # Mock RPKM calculation
            gene_lengths = np.random.randint(500, 5000, len(expr_df))
            normalized_data = expr_df[numeric_cols].div(gene_lengths, axis=0) * 1000000000 / expr_df[numeric_cols].sum()
        elif normalization_method == "CPM":
            # Counts per million
            normalized_data = expr_df[numeric_cols] * 1000000 / expr_df[numeric_cols].sum()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported normalization method: {normalization_method}")
        
        # Log transformation
        if log_transform:
            normalized_data = np.log2(normalized_data + 1)
        
        # Reconstruct DataFrame
        result_df = expr_df.copy()
        result_df[numeric_cols] = normalized_data
        
        return {
            "status": "success",
            "normalized_expression": result_df.to_dict(),
            "normalization_info": {
                "method": normalization_method,
                "log_transformed": log_transform,
                "genes_normalized": len(result_df),
                "samples_normalized": len(numeric_cols)
            }
        }
        
    except Exception as e:
        logger.error(f"Error normalizing expression data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rnaseq/create-report")
async def create_rnaseq_report(
    analyses: List[Dict[str, Any]],
    report_type: str = "comprehensive"
):
    """Create comprehensive RNA-seq analysis report"""
    try:
        report = {
            "report_type": report_type,
            "generated_at": datetime.utcnow().isoformat(),
            "analyses_included": len(analyses),
            "summary": {}
        }
        
        # Categorize analyses
        analysis_types = defaultdict(list)
        for analysis in analyses:
            analysis_type = analysis.get('type', 'unknown')
            analysis_types[analysis_type].append(analysis)
        
        # Generate summary for each analysis type
        for analysis_type, type_analyses in analysis_types.items():
            if analysis_type == 'differential_expression':
                # Summarize DE results
                total_significant = sum(
                    len(a.get('significant_genes', [])) 
                    for a in type_analyses
                )
                
                report["summary"][analysis_type] = {
                    "analyses_count": len(type_analyses),
                    "total_significant_genes": total_significant,
                    "average_significant_per_analysis": total_significant / len(type_analyses) if type_analyses else 0
                }
            
            elif analysis_type == 'pathway_analysis':
                # Summarize pathway results
                total_pathways = sum(
                    a.get('significant_pathways', 0)
                    for a in type_analyses
                )
                
                report["summary"][analysis_type] = {
                    "analyses_count": len(type_analyses),
                    "total_significant_pathways": total_pathways
                }
        
        # Add recommendations
        report["recommendations"] = [
            "Validate top differentially expressed genes with qPCR",
            "Consider functional validation of pathway findings",
            "Check for batch effects in PCA plots",
            "Review quality control metrics for outlier samples"
        ]
        
        return {
            "status": "success",
            "report": report
        }
        
    except Exception as e:
        logger.error(f"Error creating RNA-seq report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rnaseq/export-formats")
async def get_export_formats():
    """Get available export formats for RNA-seq data"""
    return {
        "expression_data": [
            {"format": "csv", "description": "Comma-separated values"},
            {"format": "tsv", "description": "Tab-separated values"},
            {"format": "excel", "description": "Excel spreadsheet"},
            {"format": "h5", "description": "HDF5 format for large datasets"}
        ],
        "differential_results": [
            {"format": "csv", "description": "Standard CSV format"},
            {"format": "xlsx", "description": "Excel with multiple sheets"},
            {"format": "gct", "description": "Gene Cluster Text format"},
            {"format": "rnk", "description": "Ranked gene list for GSEA"}
        ],
        "plots": [
            {"format": "png", "description": "Portable Network Graphics"},
            {"format": "pdf", "description": "Portable Document Format"},
            {"format": "svg", "description": "Scalable Vector Graphics"}
        ]
    }