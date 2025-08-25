# backend/app/api/ngs_variant.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Response
from typing import List, Dict, Any, Optional
from ..services.ngs_variant_analysis import ngs_variant_service
from ..models.enhanced_models import SequenceData
from ..database.database_setup import DatabaseManager
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class VariantCallingRequest(BaseModel):
    mapped_reads: List[Dict[str, Any]]
    reference_genome: str
    caller: str = "mock"
    min_quality: Optional[float] = 20
    min_depth: Optional[int] = 5
    min_allele_frequency: Optional[float] = 0.2

class VariantAnnotationRequest(BaseModel):
    variants: List[Dict[str, Any]]
    annotation_database: str = "mock_annotation"

class VariantFilterRequest(BaseModel):
    variants: List[Dict[str, Any]]
    filter_criteria: Dict[str, Any]

class VariantPrioritizationRequest(BaseModel):
    annotated_variants: List[Dict[str, Any]]
    prioritization_criteria: Optional[Dict[str, Any]] = None

@router.post("/ngs-variant/call-variants")
async def call_variants(
    request: VariantCallingRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Call variants from mapped reads"""
    try:
        # Prepare parameters
        parameters = {
            'caller': request.caller,
            'min_quality': request.min_quality,
            'min_depth': request.min_depth,
            'min_allele_frequency': request.min_allele_frequency
        }
        
        # Call variants
        results = await ngs_variant_service.call_variants(
            request.mapped_reads,
            request.reference_genome,
            parameters
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        # Store results in database
        background_tasks.add_task(
            db_manager.store_analysis_result,
            "variant_calling",
            results,
            {
                "caller": request.caller,
                "read_files": len(request.mapped_reads),
                "parameters": parameters
            }
        )
        
        return {
            "status": "success",
            "variant_calling_id": f"vc_{hash(str(results))}",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in variant calling: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ngs-variant/annotate")
async def annotate_variants(
    request: VariantAnnotationRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Annotate variants with functional information"""
    try:
        results = await ngs_variant_service.annotate_variants(
            request.variants,
            request.annotation_database
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        # Store results in database
        background_tasks.add_task(
            db_manager.store_analysis_result,
            "variant_annotation",
            results,
            {
                "database": request.annotation_database,
                "variant_count": len(request.variants)
            }
        )
        
        return {
            "status": "success",
            "annotation_id": f"anno_{hash(str(results))}",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in variant annotation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ngs-variant/filter")
async def filter_variants(
    request: VariantFilterRequest
):
    """Filter variants based on criteria"""
    try:
        results = await ngs_variant_service.filter_variants(
            request.variants,
            request.filter_criteria
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        return {
            "status": "success",
            "filter_results": results
        }
        
    except Exception as e:
        logger.error(f"Error filtering variants: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ngs-variant/prioritize")
async def prioritize_variants(
    request: VariantPrioritizationRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Prioritize variants based on clinical and functional criteria"""
    try:
        results = await ngs_variant_service.prioritize_variants(
            request.annotated_variants,
            request.prioritization_criteria
        )
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        # Store prioritization results
        background_tasks.add_task(
            db_manager.store_analysis_result,
            "variant_prioritization",
            results,
            {
                "criteria": request.prioritization_criteria,
                "variant_count": len(request.annotated_variants)
            }
        )
        
        return {
            "status": "success",
            "prioritization_id": f"prio_{hash(str(results))}",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error prioritizing variants: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ngs-variant/statistics")
async def calculate_variant_statistics(
    variants: List[Dict[str, Any]]
):
    """Calculate comprehensive statistics for variant set"""
    try:
        results = await ngs_variant_service.calculate_variant_statistics(variants)
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        return {
            "status": "success",
            "statistics": results
        }
        
    except Exception as e:
        logger.error(f"Error calculating variant statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ngs-variant/export-vcf")
async def export_variants_vcf(
    variants: List[Dict[str, Any]],
    include_annotations: bool = True
):
    """Export variants in VCF format"""
    try:
        vcf_content = await ngs_variant_service.export_variants_vcf(
            variants,
            include_annotations
        )
        
        return Response(
            content=vcf_content,
            media_type="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=variants.vcf"
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting VCF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ngs-variant/create-report")
async def create_variant_report(
    variants: List[Dict[str, Any]],
    report_type: str = "summary"
):
    """Create comprehensive variant analysis report"""
    try:
        results = await ngs_variant_service.create_variant_report(variants, report_type)
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        return {
            "status": "success",
            "report": results["report"]
        }
        
    except Exception as e:
        logger.error(f"Error creating variant report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ngs-variant/callers")
async def get_available_variant_callers():
    """Get available variant calling tools"""
    return {
        "callers": ngs_variant_service.variant_callers,
        "default_caller": "mock",
        "recommendations": {
            "general_purpose": "gatk",
            "speed_optimized": "bcftools", 
            "sensitivity_optimized": "freebayes",
            "testing": "mock"
        }
    }

@router.get("/ngs-variant/annotation-databases")
async def get_annotation_databases():
    """Get available annotation databases"""
    return {
        "databases": ngs_variant_service.annotation_databases,
        "default_database": "mock_annotation",
        "database_info": {
            "clinvar": {
                "description": "Clinical variant database",
                "variant_count": "~2M",
                "last_updated": "Monthly"
            },
            "dbsnp": {
                "description": "Short genetic variations database", 
                "variant_count": "~1B",
                "last_updated": "Regularly"
            },
            "gnomad": {
                "description": "Genome aggregation database",
                "variant_count": "~800M",
                "last_updated": "Annually"
            }
        }
    }

@router.get("/ngs-variant/consequence-types")
async def get_consequence_types():
    """Get available consequence types and their descriptions"""
    return {
        "consequence_types": ngs_variant_service.consequence_types,
        "impact_levels": {
            "HIGH": ["nonsense_variant", "frameshift_variant", "splice_site_variant"],
            "MODERATE": ["missense_variant", "inframe_deletion", "inframe_insertion"],
            "LOW": ["synonymous_variant"],
            "MODIFIER": ["intron_variant", "upstream_variant", "downstream_variant"]
        }
    }

@router.post("/ngs-variant/batch-process")
async def batch_process_variants(
    variant_files: List[Dict[str, Any]],
    processing_steps: List[str],
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Process multiple variant files through a pipeline"""
    try:
        batch_id = f"batch_variant_{hash(str(variant_files))}"
        batch_results = []
        
        for i, file_info in enumerate(variant_files):
            try:
                # Mock processing pipeline
                file_result = {
                    "file_index": i,
                    "filename": file_info.get('filename', f'file_{i}'),
                    "status": "success",
                    "steps_completed": processing_steps,
                    "variants_processed": np.random.randint(100, 1000),
                    "high_impact_variants": np.random.randint(5, 50)
                }
                
                batch_results.append(file_result)
                
            except Exception as e:
                batch_results.append({
                    "file_index": i,
                    "filename": file_info.get('filename', f'file_{i}'),
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
            "files_processed": len(variant_files),
            "successful_files": len([r for r in batch_results if r["status"] == "success"]),
            "failed_files": len([r for r in batch_results if r["status"] == "failed"]),
            "processing_steps": processing_steps,
            "results": batch_results
        }
        
    except Exception as e:
        logger.error(f"Error in batch variant processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))