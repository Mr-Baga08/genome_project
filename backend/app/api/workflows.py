# backend/app/api/workflows.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any
from ..models.enhanced_models import WorkflowDefinition, WorkflowExecutionRequest, EnhancedTask
from ..services.workflow_engine import WorkflowEngine
from ..database.database_setup import DatabaseManager

router = APIRouter()

@router.post("/workflows/execute")
async def execute_workflow(
    request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    workflow_engine: WorkflowEngine = Depends(),
    db_manager: DatabaseManager = Depends()
):
    """Execute a workflow asynchronously"""
    try:
        workflow_id = await workflow_engine.execute_workflow(
            request.workflow_definition.dict(),
            request.input_data,
            user_id="current_user"  # Get from authentication
        )
        
        return {
            "workflow_id": workflow_id,
            "status": "started",
            "message": "Workflow execution started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/workflows/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str,
    workflow_engine: WorkflowEngine = Depends()
):
    """Get workflow execution status"""
    status = workflow_engine.get_workflow_status(workflow_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return status

@router.post("/workflows/validate")
async def validate_workflow(workflow_definition: WorkflowDefinition):
    """Validate workflow definition"""
    try:
        # Basic validation
        if not workflow_definition.nodes:
            raise ValueError("Workflow must contain at least one node")
        
        # Validate node types
        valid_types = ["read_alignment", "blast_search", "multiple_alignment", "statistics"]
        for node in workflow_definition.nodes:
            if node.get("type") not in valid_types:
                raise ValueError(f"Invalid node type: {node.get('type')}")
        
        return {"valid": True, "message": "Workflow definition is valid"}
        
    except ValueError as e:
        return {"valid": False, "errors": [str(e)]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/workflows/templates")
async def get_workflow_templates(db_manager: DatabaseManager = Depends()):
    """Get available workflow templates"""
    try:
        templates_collection = await db_manager.get_collection("workflow_templates")
        
        cursor = templates_collection.find({"is_public": True})
        templates = await cursor.to_list(length=None)
        
        return templates
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/workflows/templates")
async def create_workflow_template(
    template: WorkflowDefinition,
    db_manager: DatabaseManager = Depends()
):
    """Create a new workflow template"""
    try:
        templates_collection = await db_manager.get_collection("workflow_templates")
        
        template_dict = template.dict()
        template_dict["is_template"] = True
        
        result = await templates_collection.insert_one(template_dict)
        
        if result.inserted_id:
            return {"message": "Template created successfully", "template_id": template.id}
        else:
            raise HTTPException(status_code=500, detail="Failed to create template")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
