# backend/app/api/data_flow.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import List, Dict, Any, Optional, Union
import logging
from datetime import datetime
from pydantic import BaseModel, Field, validator

from ..services.data_flow import DataFlowService
from ..database.database_setup import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data-flow", tags=["Data Flow"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SequenceFilterRequest(BaseModel):
    """Request model for sequence filtering"""
    sequences: List[Dict[str, Any]]
    criteria: Dict[str, Any] = Field(
        ...,
        example={
            "min_length": 100,
            "max_length": 10000,
            "min_gc": 30,
            "max_gc": 70,
            "contains_pattern": "ATG",
            "min_quality": 20
        }
    )

class SequenceGroupRequest(BaseModel):
    """Request model for sequence grouping"""
    sequences: List[Dict[str, Any]]
    group_by: str = Field(..., regex="^(length_range|gc_content|organism|sequence_type|similarity)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)

class SequenceSortRequest(BaseModel):
    """Request model for sequence sorting"""
    sequences: List[Dict[str, Any]]
    sort_by: str = Field(..., regex="^(length|gc_content|name|quality)$")
    reverse: bool = False

class DataSplitRequest(BaseModel):
    """Request model for data splitting"""
    data: List[Dict[str, Any]]
    split_criteria: Dict[str, Any] = Field(
        ...,
        example={
            "type": "count",
            "items_per_group": 100
        }
    )

class MultiplexRequest(BaseModel):
    """Request model for data multiplexing"""
    data_sources: List[List[Dict[str, Any]]]
    operation: str = Field(..., regex="^(merge|concatenate|interleave|deduplicate)$")

class ValidationRulesRequest(BaseModel):
    """Request model for data validation"""
    data: List[Dict[str, Any]]
    validation_rules: Dict[str, Any] = Field(
        ...,
        example={
            "required_fields": ["id", "sequence"],
            "sequence_constraints": {
                "min_length": 10,
                "max_length": 50000,
                "allowed_characters": "ATCGN"
            }
        }
    )

class BatchProcessRequest(BaseModel):
    """Request model for batch processing"""
    data: List[Dict[str, Any]]
    batch_size: int = Field(100, ge=1, le=1000)
    operation: str = Field("identity", regex="^(identity|shuffle|sort)$")

# ============================================================================
# SEQUENCE FILTERING ENDPOINTS
# ============================================================================

@router.post("/filter-sequences")
async def filter_sequences(request: SequenceFilterRequest):
    """Filter sequences based on various criteria"""
    try:
        filtered_sequences = await DataFlowService.filter_sequences(
            sequences=request.sequences,
            criteria=request.criteria
        )
        
        return {
            "status": "success",
            "filtering_criteria": request.criteria,
            "input_count": len(request.sequences),
            "output_count": len(filtered_sequences),
            "filtered_sequences": filtered_sequences,
            "filter_efficiency": len(filtered_sequences) / len(request.sequences) * 100 if request.sequences else 0
        }
        
    except Exception as e:
        logger.error(f"Sequence filtering error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Filtering failed: {str(e)}")

@router.post("/filter-by-quality")
async def filter_sequences_by_quality(
    sequences: List[Dict[str, Any]],
    min_quality: float = Query(20.0, ge=0, le=40),
    quality_metric: str = Query("average", regex="^(average|minimum|median)$")
):
    """Filter sequences based on quality scores"""
    try:
        quality_criteria = {
            "min_quality": min_quality,
            "quality_metric": quality_metric
        }
        
        filtered_sequences = await DataFlowService.filter_sequences(
            sequences=sequences,
            criteria=quality_criteria
        )
        
        return {
            "status": "success",
            "quality_threshold": min_quality,
            "quality_metric": quality_metric,
            "input_count": len(sequences),
            "passed_quality": len(filtered_sequences),
            "filtered_sequences": filtered_sequences
        }
        
    except Exception as e:
        logger.error(f"Quality filtering error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Quality filtering failed: {str(e)}")

# ============================================================================
# SEQUENCE GROUPING ENDPOINTS
# ============================================================================

@router.post("/group-sequences")
async def group_sequences(request: SequenceGroupRequest):
    """Group sequences by specified criteria"""
    try:
        grouped_sequences = await DataFlowService.group_sequences(
            sequences=request.sequences,
            group_by=request.group_by,
            parameters=request.parameters
        )
        
        # Calculate group statistics
        group_stats = {
            group_name: {
                "count": len(group_sequences),
                "avg_length": sum(len(seq.get("sequence", "")) for seq in group_sequences) / len(group_sequences) if group_sequences else 0
            }
            for group_name, group_sequences in grouped_sequences.items()
        }
        
        return {
            "status": "success",
            "grouping_method": request.group_by,
            "total_groups": len(grouped_sequences),
            "group_statistics": group_stats,
            "grouped_sequences": grouped_sequences
        }
        
    except Exception as e:
        logger.error(f"Sequence grouping error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Grouping failed: {str(e)}")

# ============================================================================
# SEQUENCE SORTING ENDPOINTS
# ============================================================================

@router.post("/sort-sequences")
async def sort_sequences(request: SequenceSortRequest):
    """Sort sequences by specified criteria"""
    try:
        sorted_sequences = await DataFlowService.sort_sequences(
            sequences=request.sequences,
            sort_by=request.sort_by,
            reverse=request.reverse
        )
        
        return {
            "status": "success",
            "sort_criteria": request.sort_by,
            "reverse_order": request.reverse,
            "sequence_count": len(sorted_sequences),
            "sorted_sequences": sorted_sequences
        }
        
    except Exception as e:
        logger.error(f"Sequence sorting error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Sorting failed: {str(e)}")

# ============================================================================
# DATA SPLITTING ENDPOINTS
# ============================================================================

@router.post("/split-data")
async def split_data(request: DataSplitRequest):
    """Split data into multiple groups"""
    try:
        split_groups = await DataFlowService.split_data(
            data=request.data,
            split_criteria=request.split_criteria
        )
        
        group_sizes = [len(group) for group in split_groups]
        
        return {
            "status": "success",
            "split_criteria": request.split_criteria,
            "input_size": len(request.data),
            "total_groups": len(split_groups),
            "group_sizes": group_sizes,
            "split_groups": split_groups
        }
        
    except Exception as e:
        logger.error(f"Data splitting error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Data splitting failed: {str(e)}")

@router.post("/split-for-parallel")
async def split_for_parallel_processing(
    data: List[Dict[str, Any]],
    num_chunks: int = Query(..., ge=2, le=100),
    chunk_method: str = Query("equal", regex="^(equal|adaptive)$")
):
    """Split data for parallel processing"""
    try:
        if chunk_method == "equal":
            split_criteria = {
                "type": "count",
                "items_per_group": len(data) // num_chunks
            }
        else:  # adaptive
            split_criteria = {
                "type": "percentage",
                "percentages": [100 // num_chunks] * num_chunks
            }
        
        chunks = await DataFlowService.split_data(
            data=data,
            split_criteria=split_criteria
        )
        
        return {
            "status": "success",
            "chunk_method": chunk_method,
            "requested_chunks": num_chunks,
            "actual_chunks": len(chunks),
            "chunk_sizes": [len(chunk) for chunk in chunks],
            "chunks": chunks
        }
        
    except Exception as e:
        logger.error(f"Parallel splitting error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Parallel splitting failed: {str(e)}")

# ============================================================================
# DATA MULTIPLEXING ENDPOINTS
# ============================================================================

@router.post("/multiplex-data")
async def multiplex_data(request: MultiplexRequest):
    """Combine multiple data sources using various strategies"""
    try:
        result = await DataFlowService.multiplex_data(
            data_sources=request.data_sources,
            operation=request.operation
        )
        
        input_totals = [len(source) for source in request.data_sources]
        
        return {
            "status": "success",
            "operation": request.operation,
            "input_sources": len(request.data_sources),
            "input_totals": input_totals,
            "output_count": len(result),
            "multiplexed_data": result
        }
        
    except Exception as e:
        logger.error(f"Data multiplexing error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Multiplexing failed: {str(e)}")

# ============================================================================
# DATA VALIDATION ENDPOINTS
# ============================================================================

@router.post("/validate-data-integrity")
async def validate_data_integrity(request: ValidationRulesRequest):
    """Validate data integrity based on specified rules"""
    try:
        validation_result = await DataFlowService.validate_data_integrity(
            data=request.data,
            validation_rules=request.validation_rules
        )
        
        return {
            "status": "success",
            "validation_rules": request.validation_rules,
            "validation_result": validation_result,
            "data_quality_score": (validation_result["validation_summary"]["valid_count"] / 
                                 validation_result["validation_summary"]["total_items"] * 100) if validation_result["validation_summary"]["total_items"] > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Data validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Data validation failed: {str(e)}")

# ============================================================================
# BATCH PROCESSING ENDPOINTS
# ============================================================================

@router.post("/batch-process")
async def batch_process_data(request: BatchProcessRequest):
    """Process data in batches with specified operations"""
    try:
        batches = await DataFlowService.batch_process(
            data=request.data,
            batch_size=request.batch_size,
            operation=request.operation
        )
        
        return {
            "status": "success",
            "operation": request.operation,
            "batch_size": request.batch_size,
            "input_size": len(request.data),
            "total_batches": len(batches),
            "batches": batches
        }
        
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Batch processing failed: {str(e)}")

# ============================================================================
# DATA AGGREGATION ENDPOINTS
# ============================================================================

@router.post("/aggregate-data")
async def aggregate_data(
    data: List[Dict[str, Any]],
    aggregation_method: str = Query(..., regex="^(count|statistics|summary)$")
):
    """Aggregate data using various methods"""
    try:
        aggregation_result = await DataFlowService.aggregate_data(
            data=data,
            aggregation_method=aggregation_method
        )
        
        return {
            "status": "success",
            "aggregation_method": aggregation_method,
            "input_size": len(data),
            "aggregation_result": aggregation_result
        }
        
    except Exception as e:
        logger.error(f"Data aggregation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Data aggregation failed: {str(e)}")

# ============================================================================
# SEQUENCE MARKING AND TAGGING ENDPOINTS
# ============================================================================

@router.post("/mark-sequences")
async def mark_sequences(
    sequences: List[Dict[str, Any]],
    markers: Dict[str, Any] = Field(
        ...,
        example={
            "add_length_info": True,
            "add_gc_info": True,
            "add_composition_info": True,
            "add_timestamp": True,
            "custom_markers": {"project": "genome_study_2024"}
        }
    )
):
    """Add markers/tags to sequences"""
    try:
        marked_sequences = await DataFlowService.mark_sequences(
            sequences=sequences,
            markers=markers
        )
        
        return {
            "status": "success",
            "markers_applied": markers,
            "sequence_count": len(marked_sequences),
            "marked_sequences": marked_sequences
        }
        
    except Exception as e:
        logger.error(f"Sequence marking error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Sequence marking failed: {str(e)}")

# ============================================================================
# WORKFLOW DATA MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/validate-workflow-data")
async def validate_workflow_data_flow(
    workflow_definition: Dict[str, Any],
    input_data: Optional[Dict[str, Any]] = None
):
    """Validate data flow compatibility in workflow"""
    try:
        # Extract nodes and connections from workflow
        nodes = workflow_definition.get("nodes", [])
        connections = workflow_definition.get("connections", [])
        
        validation_errors = []
        validation_warnings = []
        
        # Check data type compatibility between connected nodes
        for connection in connections:
            from_node_id = connection.get("from")
            to_node_id = connection.get("to")
            
            from_node = next((n for n in nodes if n.get("id") == from_node_id), None)
            to_node = next((n for n in nodes if n.get("id") == to_node_id), None)
            
            if not from_node or not to_node:
                validation_errors.append(f"Invalid connection: node not found")
                continue
            
            # Check output/input type compatibility
            from_output_type = from_node.get("output_type", "unknown")
            to_input_type = to_node.get("input_type", "unknown")
            
            if from_output_type != "unknown" and to_input_type != "unknown":
                if from_output_type != to_input_type:
                    validation_warnings.append(
                        f"Potential type mismatch: {from_node.get('name')} ({from_output_type}) → {to_node.get('name')} ({to_input_type})"
                    )
        
        return {
            "status": "success",
            "workflow_valid": len(validation_errors) == 0,
            "validation_errors": validation_errors,
            "validation_warnings": validation_warnings,
            "node_count": len(nodes),
            "connection_count": len(connections)
        }
        
    except Exception as e:
        logger.error(f"Workflow validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Workflow validation failed: {str(e)}")

@router.post("/transform-data-between-nodes")
async def transform_data_between_nodes(
    data: Any,
    source_node_type: str,
    target_node_type: str,
    mapping: Dict[str, Any] = {}
):
    """Transform data structure between workflow nodes"""
    try:
        # Use DataFlowService to transform data
        transformed_data = await DataFlowService.transform_data_between_nodes(
            data=data,
            mapping={
                "source_type": source_node_type,
                "target_type": target_node_type,
                **mapping
            }
        )
        
        return {
            "status": "success",
            "transformation": f"{source_node_type} → {target_node_type}",
            "transformed_data": transformed_data
        }
        
    except Exception as e:
        logger.error(f"Data transformation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Data transformation failed: {str(e)}")

# ============================================================================
# PARALLEL PROCESSING ENDPOINTS
# ============================================================================

@router.post("/merge-analysis-results")
async def merge_analysis_results(
    results: List[Dict[str, Any]],
    merge_strategy: str = Query("combine", regex="^(combine|average|union|intersection)$")
):
    """Merge results from parallel analysis branches"""
    try:
        merged_result = await DataFlowService.merge_analysis_results(results)
        
        return {
            "status": "success",
            "merge_strategy": merge_strategy,
            "input_results": len(results),
            "merged_result": merged_result,
            "merge_summary": {
                "total_input_items": sum(len(r.get("data", [])) for r in results if isinstance(r.get("data"), list)),
                "merged_items": len(merged_result.get("data", [])) if isinstance(merged_result.get("data"), list) else 1
            }
        }
        
    except Exception as e:
        logger.error(f"Results merging error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Results merging failed: {str(e)}")

@router.post("/split-for-parallel-processing")
async def split_for_parallel_processing(
    data: List[Dict[str, Any]],
    chunks: int = Query(..., ge=2, le=50)
):
    """Split data for parallel processing across multiple workers"""
    try:
        split_data = await DataFlowService.split_data_for_parallel_processing(
            data=data,
            chunks=chunks
        )
        
        return {
            "status": "success",
            "input_size": len(data),
            "requested_chunks": chunks,
            "actual_chunks": len(split_data),
            "chunk_sizes": [len(chunk) for chunk in split_data],
            "chunks": split_data
        }
        
    except Exception as e:
        logger.error(f"Parallel splitting error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Parallel splitting failed: {str(e)}")

# ============================================================================
# DATA QUALITY AND ANALYSIS ENDPOINTS
# ============================================================================

@router.post("/calculate-sequence-statistics")
async def calculate_sequence_statistics(sequences: List[Dict[str, Any]]):
    """Calculate comprehensive statistics for sequence collections"""
    try:
        aggregated_stats = await DataFlowService.aggregate_data(
            data=sequences,
            aggregation_method="statistics"
        )
        
        # Add additional sequence-specific statistics
        sequence_lengths = [len(seq.get("sequence", "")) for seq in sequences]
        gc_contents = []
        
        for seq in sequences:
            sequence_data = seq.get("sequence", "")
            if sequence_data:
                gc_count = sequence_data.upper().count('G') + sequence_data.upper().count('C')
                gc_content = (gc_count / len(sequence_data)) * 100
                gc_contents.append(gc_content)
        
        enhanced_stats = {
            **aggregated_stats,
            "sequence_analysis": {
                "total_sequences": len(sequences),
                "total_nucleotides": sum(sequence_lengths),
                "length_distribution": {
                    "shortest": min(sequence_lengths) if sequence_lengths else 0,
                    "longest": max(sequence_lengths) if sequence_lengths else 0,
                    "average": sum(sequence_lengths) / len(sequence_lengths) if sequence_lengths else 0
                },
                "gc_content_analysis": {
                    "average_gc": sum(gc_contents) / len(gc_contents) if gc_contents else 0,
                    "gc_range": {
                        "min": min(gc_contents) if gc_contents else 0,
                        "max": max(gc_contents) if gc_contents else 0
                    }
                }
            }
        }
        
        return {
            "status": "success",
            "statistics": enhanced_stats
        }
        
    except Exception as e:
        logger.error(f"Statistics calculation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Statistics calculation failed: {str(e)}")

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.get("/supported-operations")
async def get_supported_operations():
    """Get list of all supported data flow operations"""
    return {
        "filtering_criteria": [
            "min_length", "max_length", "min_gc", "max_gc",
            "contains_pattern", "excludes_pattern", "min_quality", "max_n_percent"
        ],
        "grouping_methods": [
            "length_range", "gc_content", "organism", "sequence_type", "similarity"
        ],
        "sorting_methods": [
            "length", "gc_content", "name", "quality"
        ],
        "split_types": [
            "count", "percentage"
        ],
        "multiplex_operations": [
            "merge", "concatenate", "interleave", "deduplicate"
        ],
        "batch_operations": [
            "identity", "shuffle", "sort"
        ],
        "aggregation_methods": [
            "count", "statistics", "summary"
        ]
    }

@router.post("/estimate-processing-time")
async def estimate_processing_time(
    data_size: int,
    operation_type: str,
    complexity_factors: Dict[str, Any] = {}
):
    """Estimate processing time for data flow operations"""
    try:
        # Simple time estimation based on data size and operation
        base_times = {
            "filter": 0.001,    # seconds per item
            "group": 0.002,
            "sort": 0.003,
            "split": 0.0005,
            "multiplex": 0.002,
            "validate": 0.001,
            "aggregate": 0.0015
        }
        
        base_time = base_times.get(operation_type, 0.001)
        estimated_seconds = data_size * base_time
        
        # Apply complexity factors
        complexity_multiplier = 1.0
        if "sequence_analysis" in complexity_factors:
            complexity_multiplier *= 1.5
        if "parallel_processing" in complexity_factors:
            complexity_multiplier *= 0.6  # Parallel processing reduces time
        
        final_estimate = estimated_seconds * complexity_multiplier
        
        return {
            "status": "success",
            "operation_type": operation_type,
            "data_size": data_size,
            "estimated_time_seconds": round(final_estimate, 2),
            "estimated_time_human": _format_duration(final_estimate),
            "complexity_factors": complexity_factors
        }
        
    except Exception as e:
        logger.error(f"Time estimation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Time estimation failed: {str(e)}")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes:.0f}m {remaining_seconds:.0f}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours:.0f}h {remaining_minutes:.0f}m"