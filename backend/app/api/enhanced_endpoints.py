# backend/app/api/enhanced_endpoints.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Dict, Any, Optional
import asyncio
import tempfile
import shutil
from pathlib import Path
import logging

from ..models.enhanced_models import *
from ..builders.sequence_builder import SequenceBuilder, AnalysisPipelineBuilder
from ..services.external_tool_manager import ExternalToolManager
from ..services.caching_manager import BioinformaticsCacheManager, cache_blast_search, cache_alignment
from ..database.database_setup import DatabaseManager
from ..utils.file_handlers import FileHandler
from ..websockets.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Enhanced Bioinformatics API"])

# Initialize services
external_tools = ExternalToolManager()
cache_manager = BioinformaticsCacheManager()
connection_manager = ConnectionManager()
file_handler = FileHandler()

# ============================================================================
# SEQUENCE MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/sequences/create", response_model=SequenceData)
async def create_sequence_enhanced(
    name: str = Form(...),
    sequence: str = Form(...),
    sequence_type: Optional[SequenceType] = Form(None),
    description: Optional[str] = Form(None),
    organism_id: Optional[int] = Form(None),
    annotations_file: Optional[UploadFile] = File(None),
    db_manager: DatabaseManager = Depends()
):
    """Create sequence using builder pattern with optional annotations upload"""
    try:
        builder = SequenceBuilder()
        builder.name(name).sequence(sequence)
        
        if description:
            builder.description(description)
        if organism_id:
            builder.organism(organism_id)
        
        # Parse annotations if provided
        if annotations_file:
            annotations_content = await annotations_file.read()
            annotations = await file_handler.parse_annotations_file(
                annotations_content, 
                annotations_file.filename
            )
            builder.multiple_annotations(annotations)
        
        sequence_data = builder.build()
        
        # Store in database
        sequences_collection = await db_manager.get_collection("sequences")
        result = await sequences_collection.insert_one(sequence_data.dict())
        
        if result.inserted_id:
            # Cache the sequence data
            await cache_manager.cache_sequence_data(
                str(result.inserted_id), 
                sequence_data.dict()
            )
            
            return sequence_data
        else:
            raise HTTPException(status_code=500, detail="Failed to create sequence")
            
    except Exception as e:
        logger.error(f"Sequence creation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sequences/batch-create", response_model=List[SequenceData])
async def create_sequences_batch(
    fasta_file: UploadFile = File(...),
    organism_id: Optional[int] = Form(None),
    is_public: bool = Form(False),
    db_manager: DatabaseManager = Depends()
):
    """Create multiple sequences from FASTA file"""
    try:
        fasta_content = await fasta_file.read()
        fasta_text = fasta_content.decode('utf-8')
        
        sequences = []
        current_sequence = None
        current_seq_data = []
        
        for line in fasta_text.split('\n'):
            line = line.strip()
            if line.startswith('>'):
                # Save previous sequence
                if current_sequence:
                    sequence_data = (SequenceBuilder()
                        .name(current_sequence)
                        .sequence(''.join(current_seq_data))
                        .organism(organism_id)
                        .public(is_public)
                        .build())
                    sequences.append(sequence_data)
                
                # Start new sequence
                current_sequence = line[1:]
                current_seq_data = []
            else:
                current_seq_data.append(line)
        
        # Don't forget the last sequence
        if current_sequence:
            sequence_data = (SequenceBuilder()
                .name(current_sequence)
                .sequence(''.join(current_seq_data))
                .organism(organism_id)
                .public(is_public)
                .build())
            sequences.append(sequence_data)
        
        # Batch insert to database
        sequences_collection = await db_manager.get_collection("sequences")
        sequence_dicts = [seq.dict() for seq in sequences]
        result = await sequences_collection.insert_many(sequence_dicts)
        
        if result.inserted_ids:
            # Cache all sequences
            for i, seq_id in enumerate(result.inserted_ids):
                await cache_manager.cache_sequence_data(
                    str(seq_id), 
                    sequences[i].dict()
                )
        
        return sequences
        
    except Exception as e:
        logger.error(f"Batch sequence creation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================

@router.post("/analysis/blast-search")
@cache_blast_search()
async def run_blast_analysis(
    request: BlastSearchRequest,
    background_tasks: BackgroundTasks
):
    """Execute BLAST search with caching"""
    try:
        result = await external_tools.execute_blast_search(
            sequence=request.sequences[0],  # For single sequence
            database=request.database,
            parameters={
                "evalue": str(request.evalue),
                "max_hits": request.max_hits,
                "word_size": request.word_size
            }
        )
        
        # Notify connected clients
        background_tasks.add_task(
            connection_manager.broadcast_to_room,
            "analysis_updates",
            {"type": "blast_complete", "result": result}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"BLAST search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/multiple-alignment")
@cache_alignment()
async def run_multiple_alignment_analysis(
    request: MultipleAlignmentRequest,
    background_tasks: BackgroundTasks
):
    """Execute multiple sequence alignment"""
    try:
        sequences = [seq.sequence for seq in request.sequences]
        
        result = await external_tools.execute_multiple_alignment(
            sequences=sequences,
            tool=request.method,
            parameters=request.parameters
        )
        
        # Notify clients
        background_tasks.add_task(
            connection_manager.broadcast_to_room,
            "analysis_updates",
            {"type": "alignment_complete", "result": result}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Multiple alignment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/phylogeny")
async def run_phylogenetic_analysis(
    background_tasks: BackgroundTasks,
    alignment_data: str = Form(...),
    method: str = Form("iqtree"),
    model: str = Form("AUTO"),
    bootstrap: int = Form(1000)
):
    """Execute phylogenetic analysis"""
    try:
        result = await external_tools.execute_phylogenetic_analysis(
            alignment_file=alignment_data,
            method=method,
            parameters={"model": model, "bootstrap": bootstrap}
        )
        
        background_tasks.add_task(
            connection_manager.broadcast_to_room,
            "analysis_updates",
            {"type": "phylogeny_complete", "result": result}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Phylogenetic analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/gene-prediction")
async def run_gene_prediction(
    background_tasks: BackgroundTasks, # <-- Moved to the front
    sequence: str = Form(...),
    organism_type: str = Form("bacteria"),
    mode: str = Form("single")
):
    """Execute gene prediction"""
    try:
        result = await external_tools.execute_gene_prediction(
            sequence=sequence,
            organism_type=organism_type,
            parameters={"mode": mode}
        )
        
        background_tasks.add_task(
            connection_manager.broadcast_to_room,
            "analysis_updates", 
            {"type": "gene_prediction_complete", "result": result}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Gene prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/domain-search")
async def run_domain_search(
    protein_sequences: List[str],
    background_tasks: BackgroundTasks,
    database: str = "pfam",
    evalue: float = 1e-3
):
    """Execute protein domain search"""
    try:
        result = await external_tools.execute_domain_search(
            protein_sequences=protein_sequences,
            database=database,
            parameters={"evalue": str(evalue)}
        )
        
        background_tasks.add_task(
            connection_manager.broadcast_to_room,
            "analysis_updates",
            {"type": "domain_search_complete", "result": result}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Domain search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# PIPELINE ENDPOINTS  
# ============================================================================

@router.post("/pipelines/create")
async def create_analysis_pipeline(
    pipeline_name: str = Form(...),
    description: str = Form(""),
    steps: List[str] = Form(...),  # JSON string of steps
    db_manager: DatabaseManager = Depends()
):
    """Create analysis pipeline using builder pattern"""
    try:
        builder = AnalysisPipelineBuilder()
        builder.pipeline_name(pipeline_name)
        builder.pipeline_description(description)
        
        # Parse and add steps
        import json
        step_configs = json.loads(steps[0]) if steps else []
        
        for step_config in step_configs:
            step_type = step_config.get("type")
            params = step_config.get("parameters", {})
            
            if step_type == "blast_search":
                builder.add_blast_search(
                    database=params.get("database", "nr"),
                    evalue=params.get("evalue", 1e-5)
                )
            elif step_type == "multiple_alignment":
                builder.add_multiple_alignment(method=params.get("method", "muscle"))
            elif step_type == "phylogeny":
                builder.add_phylogeny(method=params.get("method", "neighbor_joining"))
            elif step_type == "gene_finding":
                builder.add_gene_finding(organism_type=params.get("organism_type", "prokaryote"))
        
        pipeline_definition = builder.build_workflow()
        
        # Store in database
        pipelines_collection = await db_manager.get_collection("pipelines")
        result = await pipelines_collection.insert_one(pipeline_definition)
        
        if result.inserted_id:
            pipeline_definition["_id"] = str(result.inserted_id)
            return pipeline_definition
        else:
            raise HTTPException(status_code=500, detail="Failed to create pipeline")
            
    except Exception as e:
        logger.error(f"Pipeline creation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/pipelines/{pipeline_id}/execute")
async def execute_pipeline(
    pipeline_id: str,
    sequence_ids: List[str],
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Execute an analysis pipeline"""
    try:
        # Get pipeline definition
        pipelines_collection = await db_manager.get_collection("pipelines")
        pipeline = await pipelines_collection.find_one({"_id": pipeline_id})
        
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        # Get sequences
        sequences_collection = await db_manager.get_collection("sequences") 
        sequences = []
        for seq_id in sequence_ids:
            seq = await sequences_collection.find_one({"_id": seq_id})
            if seq:
                sequences.append(seq)
        
        if not sequences:
            raise HTTPException(status_code=400, detail="No valid sequences found")
        
        # Execute pipeline steps
        execution_id = f"pipeline_exec_{pipeline_id}_{len(sequence_ids)}"
        background_tasks.add_task(
            execute_pipeline_background,
            execution_id,
            pipeline,
            sequences,
            connection_manager
        )
        
        return {
            "execution_id": execution_id,
            "status": "started",
            "pipeline": pipeline["name"],
            "sequence_count": len(sequences)
        }
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_pipeline_background(
    execution_id: str, 
    pipeline: Dict, 
    sequences: List[Dict], 
    connection_manager: ConnectionManager
):
    """Background task to execute pipeline"""
    try:
        await connection_manager.broadcast_to_room(
            "pipeline_updates",
            {"execution_id": execution_id, "status": "running", "progress": 0}
        )
        
        results = {}
        total_steps = len(pipeline["steps"])
        
        for i, step in enumerate(pipeline["steps"]):
            step_type = step["type"]
            params = step["parameters"]
            
            await connection_manager.broadcast_to_room(
                "pipeline_updates",
                {
                    "execution_id": execution_id,
                    "status": "running", 
                    "current_step": step_type,
                    "progress": (i / total_steps) * 100
                }
            )
            
            if step_type == "blast_search":
                for seq in sequences:
                    result = await external_tools.execute_blast_search(
                        seq["sequence"], 
                        params["database"], 
                        params
                    )
                    results[f"{step_type}_{seq['_id']}"] = result
            
            elif step_type == "multiple_alignment":
                seq_list = [seq["sequence"] for seq in sequences]
                result = await external_tools.execute_multiple_alignment(
                    seq_list,
                    params["method"],
                    params
                )
                results[step_type] = result
            
            # Add more step types as needed...
        
        await connection_manager.broadcast_to_room(
            "pipeline_updates",
            {
                "execution_id": execution_id,
                "status": "completed",
                "progress": 100,
                "results": results
            }
        )
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        await connection_manager.broadcast_to_room(
            "pipeline_updates",
            {
                "execution_id": execution_id,
                "status": "failed",
                "error": str(e)
            }
        )

# ============================================================================
# CACHE MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/cache/stats")
async def get_cache_statistics():
    """Get cache performance statistics"""
    return await cache_manager.get_cache_stats()

@router.delete("/cache/invalidate")
async def invalidate_cache(pattern: str = Query(...)):
    """Invalidate cache entries matching pattern"""
    try:
        await cache_manager.invalidate_cache(pattern)
        return {"status": "success", "message": f"Cache invalidated for pattern: {pattern}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/warm")
async def warm_cache(
    sequence_ids: List[str],
    analysis_types: List[str],
    background_tasks: BackgroundTasks
):
    """Pre-warm cache for frequently accessed data"""
    background_tasks.add_task(
        cache_manager.warm_cache,
        sequence_ids,
        analysis_types
    )
    
    return {
        "status": "started",
        "message": "Cache warming started in background"
    }

# ============================================================================
# FILE HANDLING ENDPOINTS
# ============================================================================

@router.post("/files/upload-fasta")
async def upload_fasta_file(
    file: UploadFile = File(...),
    organism_id: Optional[int] = Form(None)
):
    """Upload and parse FASTA file"""
    try:
        content = await file.read()
        sequences = await file_handler.parse_fasta_content(content.decode('utf-8'))
        
        # Create sequence objects using builder
        sequence_objects = []
        for seq_data in sequences:
            sequence_obj = (SequenceBuilder()
                .name(seq_data["name"])
                .sequence(seq_data["sequence"])
                .description(seq_data.get("description", ""))
                .organism(organism_id)
                .build())
            sequence_objects.append(sequence_obj)
        
        return {
            "filename": file.filename,
            "sequence_count": len(sequence_objects),
            "sequences": [seq.dict() for seq in sequence_objects[:10]]  # Return first 10
        }
        
    except Exception as e:
        logger.error(f"FASTA upload failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/files/export-results/{execution_id}")
async def export_analysis_results(
    execution_id: str,
    format: str = "json"
):
    """Export analysis results in various formats"""
    try:
        # This would fetch results from database/cache
        # Implementation depends on your storage strategy
        
        if format == "json":
            return {"message": "JSON export not yet implemented"}
        elif format == "csv":
            return {"message": "CSV export not yet implemented"}
        elif format == "fasta":
            return {"message": "FASTA export not yet implemented"}
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SYSTEM ENDPOINTS
# ============================================================================

@router.get("/system/health")
async def system_health_check():
    """Comprehensive system health check"""
    try:
        health_status = {
            "status": "healthy",
            "services": {
                "database": "healthy",
                "redis_cache": "healthy", 
                "docker": "healthy"
            },
            "cache_stats": await cache_manager.get_cache_stats(),
            "docker_containers": len(external_tools.docker_client.containers.list())
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/system/tools")
async def list_available_tools():
    """List all available bioinformatics tools"""
    return {
        "tools": list(external_tools.tool_images.keys()),
        "tool_images": external_tools.tool_images
    }