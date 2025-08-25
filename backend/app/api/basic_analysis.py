# backend/app/api/basic_analysis.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any, Optional
from ..services.basic_analysis import basic_analysis_service
from ..models.enhanced_models import SequenceData, SequenceAnalysisRequest
from ..database.database_setup import DatabaseManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/analysis/statistics")
async def calculate_sequence_statistics(
    request: SequenceAnalysisRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Calculate comprehensive statistics for sequences"""
    try:
        # Fetch sequences from database
        sequences = []
        for seq_id in request.sequence_ids:
            seq_data = await db_manager.get_sequence(seq_id)
            if seq_data:
                sequences.append(seq_data)
        
        if not sequences:
            raise HTTPException(status_code=404, detail="No sequences found")
        
        # Determine analysis types from parameters
        analysis_types = request.parameters.get('analysis_types', ['basic', 'composition'])
        
        # Calculate statistics
        results = await basic_analysis_service.calculate_statistics(sequences, analysis_types)
        
        # Store results in database
        background_tasks.add_task(
            db_manager.store_analysis_result,
            request.analysis_type,
            results,
            {"sequence_ids": request.sequence_ids}
        )
        
        return {
            "status": "success",
            "results": results,
            "sequence_count": len(sequences)
        }
        
    except Exception as e:
        logger.error(f"Error calculating statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/summary")
async def generate_data_summary(
    sequences: List[SequenceData],
    summary_type: str = "basic"
):
    """Generate data summary for sequences"""
    try:
        # Convert SequenceData objects to dicts
        sequence_dicts = [seq.dict() for seq in sequences]
        
        results = await basic_analysis_service.summarize_data(sequence_dicts, summary_type)
        
        return {
            "status": "success",
            "summary_type": summary_type,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/consensus")
async def calculate_consensus_sequence(
    sequences: List[SequenceData],
    threshold: float = 0.5
):
    """Calculate consensus sequence from aligned sequences"""
    try:
        # Convert to dict format
        sequence_dicts = [seq.dict() for seq in sequences]
        
        results = await basic_analysis_service.calculate_consensus_sequence(sequence_dicts, threshold)
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error calculating consensus: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/motifs")
async def analyze_sequence_motifs(
    sequences: List[SequenceData],
    motif_length: int = 6,
    max_results: int = 20
):
    """Find common motifs in sequences"""
    try:
        # Convert to dict format
        sequence_dicts = [seq.dict() for seq in sequences]
        
        results = await basic_analysis_service.analyze_motifs(sequence_dicts, motif_length)
        
        # Limit results if requested
        if "top_motifs" in results:
            results["top_motifs"] = results["top_motifs"][:max_results]
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error analyzing motifs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/diversity")
async def calculate_sequence_diversity(
    sequences: List[SequenceData]
):
    """Calculate sequence diversity metrics"""
    try:
        # Convert to dict format
        sequence_dicts = [seq.dict() for seq in sequences]
        
        results = await basic_analysis_service.calculate_sequence_diversity(sequence_dicts)
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error calculating diversity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/gc-content")
async def analyze_gc_content(
    sequences: List[SequenceData]
):
    """Analyze GC content for DNA sequences"""
    try:
        # Filter for DNA sequences only
        dna_sequences = [
            seq for seq in sequences 
            if seq.sequence_type == "DNA" or "DNA" in str(seq.sequence_type)
        ]
        
        if not dna_sequences:
            raise HTTPException(status_code=400, detail="No DNA sequences provided")
        
        # Convert to dict format
        sequence_dicts = [seq.dict() for seq in dna_sequences]
        
        results = await basic_analysis_service._calculate_gc_content(sequence_dicts)
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error analyzing GC content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analysis/codon-usage")
async def analyze_codon_usage(
    sequences: List[SequenceData]
):
    """Analyze codon usage patterns"""
    try:
        # Convert to dict format
        sequence_dicts = [seq.dict() for seq in sequences]
        
        results = await basic_analysis_service.analyze_codon_usage(sequence_dicts)
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error analyzing codon usage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/supported-types")
async def get_supported_analysis_types():
    """Get list of supported analysis types"""
    return {
        "supported_types": basic_analysis_service.supported_analyses,
        "descriptions": {
            "length_distribution": "Analyze sequence length distribution",
            "composition_analysis": "Nucleotide/amino acid composition",
            "gc_content": "GC content analysis for DNA sequences",
            "quality_metrics": "Quality score analysis for FASTQ data",
            "consensus_sequence": "Generate consensus from aligned sequences",
            "sequence_diversity": "Calculate diversity metrics",
            "motif_analysis": "Find common sequence motifs",
            "codon_usage": "Analyze codon usage patterns"
        }
    }