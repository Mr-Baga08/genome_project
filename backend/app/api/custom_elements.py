# backend/app/api/custom_elements.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, File, UploadFile
from typing import List, Dict, Any, Optional
from ..services.custom_elements import custom_elements_service
from ..models.enhanced_models import SequenceData
from ..database.database_setup import DatabaseManager
from pydantic import BaseModel
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter()

class CustomElementDefinition(BaseModel):
    name: str
    description: Optional[str] = ""
    script_content: str
    script_type: str = "python"
    input_schema: Optional[Dict[str, Any]] = {}
    output_schema: Optional[Dict[str, Any]] = {}
    parameters: Optional[Dict[str, Any]] = {}
    created_by: Optional[str] = "unknown"

class ScriptExecutionRequest(BaseModel):
    script_content: str
    input_data: Any
    script_type: str = "python"
    parameters: Optional[Dict[str, Any]] = {}
    timeout: Optional[int] = 300

class ElementExecutionRequest(BaseModel):
    element_id: str
    input_data: Any

@router.post("/custom-elements/create")
async def create_custom_element(
    element_def: CustomElementDefinition,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends()
):
    """Create a new custom workflow element"""
    try:
        # Convert to dict
        element_dict = element_def.dict()
        
        # Create the element
        result = await custom_elements_service.create_custom_element(element_dict)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Store in database
        background_tasks.add_task(
            db_manager.store_custom_element,
            result["element_id"],
            element_dict
        )
        
        return {
            "status": "success",
            "element_id": result["element_id"],
            "message": result["message"],
            "test_result": result.get("test_result")
        }
        
    except Exception as e:
        logger.error(f"Error creating custom element: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/custom-elements/execute-script")
async def execute_custom_script(
    request: ScriptExecutionRequest
):
    """Execute a custom script directly (for testing/development)"""
    try:
        result = await custom_elements_service.execute_custom_script(
            request.script_content,
            request.input_data,
            request.script_type,
            request.parameters,
            request.timeout
        )
        
        if "error" in result:
            # Return error as 200 OK but with error field for better UX
            return {
                "status": "error",
                "error": result["error"],
                "details": result.get("security_issues", [])
            }
        
        return {
            "status": "success",
            "execution_result": result
        }
        
    except Exception as e:
        logger.error(f"Error executing custom script: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/custom-elements/{element_id}/execute")
async def execute_custom_element(
    element_id: str,
    request: ElementExecutionRequest,
    background_tasks: BackgroundTasks
):
    """Execute a registered custom element"""
    try:
        result = await custom_elements_service.execute_element(element_id, request.input_data)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "execution_result": result
        }
        
    except Exception as e:
        logger.error(f"Error executing custom element: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/custom-elements")
async def list_custom_elements():
    """Get list of all custom elements"""
    try:
        result = await custom_elements_service.get_custom_elements()
        
        return {
            "status": "success",
            "elements": result["custom_elements"],
            "total_count": result["total_count"]
        }
        
    except Exception as e:
        logger.error(f"Error listing custom elements: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/custom-elements/{element_id}")
async def get_custom_element(element_id: str):
    """Get details of a specific custom element"""
    try:
        if element_id not in custom_elements_service.custom_elements:
            raise HTTPException(status_code=404, detail="Custom element not found")
        
        element = custom_elements_service.custom_elements[element_id]
        
        return {
            "status": "success",
            "element": {
                "id": element.element_id,
                "name": element.name,
                "description": element.description,
                "script_content": element.script_content,
                "script_type": element.script_type,
                "input_schema": element.input_schema,
                "output_schema": element.output_schema,
                "parameters": element.parameters,
                "created_by": element.created_by,
                "created_at": element.created_at
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting custom element: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/custom-elements/{element_id}")
async def delete_custom_element(
    element_id: str,
    db_manager: DatabaseManager = Depends()
):
    """Delete a custom element"""
    try:
        result = await custom_elements_service.delete_custom_element(element_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        # Remove from database
        await db_manager.delete_custom_element(element_id)
        
        return {
            "status": "success",
            "message": result["message"]
        }
        
    except Exception as e:
        logger.error(f"Error deleting custom element: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/custom-elements/validate")
async def validate_element_definition(
    element_def: CustomElementDefinition
):
    """Validate a custom element definition before creation"""
    try:
        element_dict = element_def.dict()
        
        validation_result = await custom_elements_service._validate_element_definition(element_dict)
        
        return {
            "status": "success",
            "validation": validation_result
        }
        
    except Exception as e:
        logger.error(f"Error validating element definition: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/custom-elements/templates")
async def get_script_templates():
    """Get script templates for different languages"""
    try:
        templates = await custom_elements_service.get_script_templates()
        
        return {
            "status": "success",
            "templates": templates["templates"],
            "supported_types": templates["supported_types"]
        }
        
    except Exception as e:
        logger.error(f"Error getting script templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/custom-elements/{element_id}/export")
async def export_custom_element(element_id: str):
    """Export custom element definition"""
    try:
        result = await custom_elements_service.export_custom_element(element_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "status": "success",
            "export_data": result["export_data"],
            "format": result["format"]
        }
        
    except Exception as e:
        logger.error(f"Error exporting custom element: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/custom-elements/import")
async def import_custom_element(
    import_data: Dict[str, Any],
    created_by: str = "unknown",
    db_manager: DatabaseManager = Depends()
):
    """Import custom element from export data"""
    try:
        result = await custom_elements_service.import_custom_element(import_data, created_by)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "success",
            "element_id": result["element_id"],
            "message": "Custom element imported successfully"
        }
        
    except Exception as e:
        logger.error(f"Error importing custom element: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/custom-elements/supported-types")
async def get_supported_script_types():
    """Get supported script types and their capabilities"""
    return {
        "supported_types": custom_elements_service.supported_script_types,
        "security_info": {
            "python": {
                "allowed_imports": list(custom_elements_service.allowed_imports),
                "forbidden_imports": list(custom_elements_service.forbidden_imports),
                "sandbox_mode": True
            },
            "r": {
                "required_packages": ["jsonlite"],
                "recommended_packages": ["seqinr", "Biostrings", "GenomicRanges"]
            },
            "bash": {
                "restricted_environment": True,
                "available_commands": "Standard Unix utilities only"
            }
        }
    }

@router.post("/custom-elements/validate-script")
async def validate_script_security(
    script_content: str,
    script_type: str = "python"
):
    """Validate script for security issues"""
    try:
        validation_result = await custom_elements_service._validate_script_security(script_content, script_type)
        
        return {
            "status": "success",
            "validation": validation_result
        }
        
    except Exception as e:
        logger.error(f"Error validating script security: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/custom-elements/test")
async def test_custom_script(
    script_content: str,
    script_type: str = "python",
    sample_data: Optional[Any] = None
):
    """Test a custom script with sample data"""
    try:
        # Use provided sample data or generate default
        if sample_data is None:
            sample_data = {
                "sequences": [
                    {
                        "id": "test_seq_1",
                        "name": "Test Sequence 1", 
                        "sequence": "ATCGATCGATCGATCG",
                        "sequence_type": "DNA"
                    }
                ]
            }
        
        # Execute script
        result = await custom_elements_service.execute_custom_script(
            script_content,
            sample_data,
            script_type,
            {},
            timeout=30  # Short timeout for testing
        )
        
        return {
            "status": "success" if "error" not in result else "error",
            "test_result": result,
            "sample_data_used": sample_data
        }
        
    except Exception as e:
        logger.error(f"Error testing custom script: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))