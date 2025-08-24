# backend/app/api/sequences.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from ..models.enhanced_models import SequenceData, Annotation
from ..database.database_setup import DatabaseManager

router = APIRouter()

@router.post("/sequences", response_model=SequenceData)
async def create_sequence(sequence: SequenceData, db_manager: DatabaseManager = Depends()):
    """Create a new biological sequence"""
    try:
        sequences_collection = await db_manager.get_collection("sequences")
        
        # Insert sequence
        result = await sequences_collection.insert_one(sequence.dict())
        
        if result.inserted_id:
            # Return created sequence
            created_sequence = await sequences_collection.find_one({"_id": result.inserted_id})
            return SequenceData(**created_sequence)
        else:
            raise HTTPException(status_code=500, detail="Failed to create sequence")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sequences", response_model=List[SequenceData])
async def list_sequences(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    sequence_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    db_manager: DatabaseManager = Depends()
):
    """List sequences with filtering and pagination"""
    try:
        sequences_collection = await db_manager.get_collection("sequences")
        
        # Build query filter
        query_filter = {}
        if sequence_type:
            query_filter["sequence_type"] = sequence_type
        if user_id:
            query_filter["user_id"] = user_id
        
        # Execute query with pagination
        cursor = sequences_collection.find(query_filter).skip(skip).limit(limit)
        sequences = await cursor.to_list(length=limit)
        
        return [SequenceData(**seq) for seq in sequences]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sequences/{sequence_id}", response_model=SequenceData)
async def get_sequence(sequence_id: str, db_manager: DatabaseManager = Depends()):
    """Get a specific sequence by ID"""
    try:
        sequences_collection = await db_manager.get_collection("sequences")
        
        sequence = await sequences_collection.find_one({"id": sequence_id})
        if not sequence:
            raise HTTPException(status_code=404, detail="Sequence not found")
        
        return SequenceData(**sequence)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/sequences/{sequence_id}", response_model=SequenceData)
async def update_sequence(
    sequence_id: str, 
    sequence_update: Dict[str, Any],
    db_manager: DatabaseManager = Depends()
):
    """Update a sequence"""
    try:
        sequences_collection = await db_manager.get_collection("sequences")
        
        # Add updated_at timestamp
        sequence_update["updated_at"] = datetime.utcnow()
        
        result = await sequences_collection.update_one(
            {"id": sequence_id},
            {"$set": sequence_update}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Sequence not found")
        
        # Return updated sequence
        updated_sequence = await sequences_collection.find_one({"id": sequence_id})
        return SequenceData(**updated_sequence)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/sequences/{sequence_id}")
async def delete_sequence(sequence_id: str, db_manager: DatabaseManager = Depends()):
    """Delete a sequence"""
    try:
        sequences_collection = await db_manager.get_collection("sequences")
        
        result = await sequences_collection.delete_one({"id": sequence_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Sequence not found")
        
        return {"message": "Sequence deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/sequences/{sequence_id}/annotations", response_model=Annotation)
async def add_annotation(
    sequence_id: str,
    annotation: Annotation,
    db_manager: DatabaseManager = Depends()
):
    """Add annotation to a sequence"""
    try:
        annotations_collection = await db_manager.get_collection("annotations")
        
        # Set sequence_id
        annotation.sequence_id = sequence_id
        
        result = await annotations_collection.insert_one(annotation.dict())
        
        if result.inserted_id:
            created_annotation = await annotations_collection.find_one({"_id": result.inserted_id})
            return Annotation(**created_annotation)
        else:
            raise HTTPException(status_code=500, detail="Failed to create annotation")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sequences/{sequence_id}/annotations", response_model=List[Annotation])
async def get_sequence_annotations(sequence_id: str, db_manager: DatabaseManager = Depends()):
    """Get all annotations for a sequence"""
    try:
        annotations_collection = await db_manager.get_collection("annotations")
        
        cursor = annotations_collection.find({"sequence_id": sequence_id})
        annotations = await cursor.to_list(length=None)
        
        return [Annotation(**ann) for ann in annotations]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
