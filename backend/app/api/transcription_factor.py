# backend/app/api/transcription_factor.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, File, UploadFile
from typing import List, Dict, Any, Optional
from ..services.transcription_factor import transcription_factor_service
from ..models.enhanced_models import SequenceData
from ..database.database_setup import DatabaseManager
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class TFBSSearchRequest(BaseModel):
    sequence_ids: List[str]
    motif_database: str = "builtin"
    threshold: float = 0.8
    scan_both_strands: bool = True
    motif_ids: Optional[List[str]] = None

class CustomMotifRequest(BaseModel):
    sequences: List[SequenceData]
    motif_matrices: List[Dict[str, Any]]
    threshold: float = 0.8
    scan_both_strands: bool = True

class MotifCreationRequest(BaseModel):
    binding_sites: List[str]  # Aligned binding site sequences
    motif_name: str
    description: Optional[str] = None

@router.post("/tfbs/search")
async def search_binding_sites(
    request: TFBSSearchRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Search for transcription factor binding sites"""
    try:
        # Fetch sequences from database
        sequences = []
        for seq_id in request.sequence_ids:
            seq_data = await db_manager.get_sequence(seq_id)
            if seq_data:
                sequences.append(seq_data)
        
        if not sequences:
            raise HTTPException(status_code=404, detail="No sequences found")
        
        # Prepare parameters
        parameters = {
            'threshold': request.threshold,
            'scan_both_strands': request.scan_both_strands,
            'motif_ids': request.motif_ids
        }
        
        # Perform binding site search
        results = await transcription_factor_service.find_binding_sites(
            sequences, request.motif_database, parameters
        )
        
        # Store results in database
        background_tasks.add_task(
            db_manager.store_analysis_result,
            "tfbs_search",
            results,
            {"sequence_ids": request.sequence_ids, "parameters": parameters}
        )
        
        return {
            "status": "success",
            "results": results,
            "sequences_analyzed": len(sequences)
        }
        
    except Exception as e:
        logger.error(f"Error in TFBS search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tfbs/scan-custom-motifs")
async def scan_custom_motifs(
    request: CustomMotifRequest,
    background_tasks: BackgroundTasks
):
    """Scan sequences with custom motif matrices"""
    try:
        # Convert SequenceData to dict format
        sequence_dicts = [seq.dict() for seq in request.sequences]
        
        # Prepare parameters
        parameters = {
            'threshold': request.threshold,
            'scan_both_strands': request.scan_both_strands
        }
        
        # Perform motif scanning
        results = await transcription_factor_service.scan_motifs(
            sequence_dicts, request.motif_matrices, parameters
        )
        
        return {
            "status": "success",
            "results": results,
            "sequences_analyzed": len(request.sequences),
            "motifs_scanned": len(request.motif_matrices)
        }
        
    except Exception as e:
        logger.error(f"Error scanning custom motifs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tfbs/create-motif")
async def create_motif_from_sites(
    request: MotifCreationRequest,
    db_manager: DatabaseManager = Depends()
):
    """Create a position weight matrix from binding site sequences"""
    try:
        # Create PWM from binding sites
        pwm = await transcription_factor_service.create_custom_motif(
            request.binding_sites, request.motif_name
        )
        
        # Store motif in database
        motif_data = {
            "motif_id": pwm.motif_id,
            "matrix": pwm.matrix,
            "consensus": pwm.consensus,
            "length": pwm.length,
            "information_content": pwm.information_content,
            "description": request.description,
            "created_from": request.binding_sites
        }
        
        await db_manager.store_custom_motif(motif_data)
        
        return {
            "status": "success",
            "motif": {
                "id": pwm.motif_id,
                "consensus": pwm.consensus,
                "length": pwm.length,
                "information_content_sum": sum(pwm.information_content)
            },
            "message": f"Motif {request.motif_name} created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating motif: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tfbs/motifs")
async def get_available_motifs(
    database: str = "builtin"
):
    """Get available motifs from specified database"""
    try:
        results = await transcription_factor_service.get_available_motifs(database)
        return results
        
    except Exception as e:
        logger.error(f"Error getting motifs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tfbs/export")
async def export_tfbs_results(
    matches: List[Dict[str, Any]],
    format_type: str = "bed"
):
    """Export TFBS results in various formats"""
    try:
        # Convert dict matches to MotifMatch objects
        from ..services.transcription_factor import MotifMatch
        
        motif_matches = []
        for match_data in matches:
            match = MotifMatch(
                sequence_id=match_data['sequence_id'],
                motif_id=match_data['motif_id'],
                start_position=match_data['start_position'],
                end_position=match_data['end_position'],
                strand=match_data['strand'],
                score=match_data['score'],
                sequence_match=match_data['sequence_match'],
                p_value=match_data.get('p_value')
            )
            motif_matches.append(match)
        
        # Export in requested format
        export_content = await transcription_factor_service.export_motif_results(
            motif_matches, format_type
        )
        
        return {
            "status": "success",
            "format": format_type,
            "content": export_content,
            "matches_exported": len(motif_matches)
        }
        
    except Exception as e:
        logger.error(f"Error exporting TFBS results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tfbs/databases")
async def get_available_databases():
    """Get list of available motif databases"""
    return {
        "databases": [
            {
                "id": "builtin",
                "name": "Built-in Motifs",
                "description": "Core transcription factor motifs (p53, NF-kB, TATA)",
                "motif_count": 3
            },
            {
                "id": "jaspar",
                "name": "JASPAR",
                "description": "JASPAR transcription factor database (not implemented)",
                "motif_count": 0,
                "status": "planned"
            },
            {
                "id": "hocomoco",
                "name": "HOCOMOCO",
                "description": "HOCOMOCO human motif database (not implemented)",
                "motif_count": 0,
                "status": "planned"
            }
        ]
    }

@router.post("/tfbs/validate-motif")
async def validate_motif_matrix(
    motif_matrix: List[List[float]],
    motif_id: str
):
    """Validate a position weight matrix"""
    try:
        # Check matrix dimensions
        if not motif_matrix:
            raise ValueError("Empty motif matrix")
        
        # Check that all positions have 4 probabilities
        for i, position in enumerate(motif_matrix):
            if len(position) != 4:
                raise ValueError(f"Position {i} must have exactly 4 probabilities (A, C, G, T)")
            
            # Check probabilities sum to 1 (with tolerance)
            prob_sum = sum(position)
            if abs(prob_sum - 1.0) > 0.01:
                raise ValueError(f"Position {i} probabilities must sum to 1.0 (got {prob_sum})")
            
            # Check all probabilities are non-negative
            if any(p < 0 for p in position):
                raise ValueError(f"Position {i} contains negative probabilities")
        
        # Create PWM object to validate
        motif_data = {
            "id": motif_id,
            "matrix": motif_matrix
        }
        
        pwm = transcription_factor_service._create_pwm_from_matrix(motif_data)
        
        return {
            "status": "valid",
            "motif_id": motif_id,
            "length": pwm.length,
            "consensus": pwm.consensus,
            "information_content_sum": sum(pwm.information_content),
            "message": "Motif matrix is valid"
        }
        
    except Exception as e:
        return {
            "status": "invalid",
            "error": str(e),
            "message": "Motif matrix validation failed"
        }