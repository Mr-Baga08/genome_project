# backend/app/api/workflow_elements.py - New API endpoint
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from ..utils.ugene_commands import UgeneCommandBuilder

router = APIRouter()

@router.get("/elements", response_model=Dict[str, Any])
async def get_supported_elements():
    """Get all supported workflow elements and their capabilities"""
    builder = UgeneCommandBuilder()
    
    supported_elements = {}
    for element_name in builder.get_supported_elements():
        element_info = builder.get_element_info(element_name)
        supported_elements[element_name] = element_info
    
    return {
        "supported_elements": supported_elements,
        "total_count": len(supported_elements),
        "categories": _group_elements_by_category(supported_elements)
    }

@router.post("/elements/validate")
async def validate_workflow_elements(workflow: Dict[str, Any]):
    """Validate a workflow against supported elements"""
    builder = UgeneCommandBuilder()
    validation_result = builder.validate_workflow(workflow)
    
    return validation_result

@router.get("/elements/{element_name}")
async def get_element_details(element_name: str):
    """Get detailed information about a specific element"""
    builder = UgeneCommandBuilder()
    
    if not builder.is_element_supported(element_name):
        raise HTTPException(status_code=404, detail=f"Element '{element_name}' not found")
    
    element_info = builder.get_element_info(element_name)
    return {
        "name": element_name,
        "details": element_info,
        "supported": True
    }

def _group_elements_by_category(elements: Dict[str, Any]) -> Dict[str, List[str]]:
    """Group elements by category based on their names"""
    categories = {
        "Data Readers": [],
        "Data Writers": [],
        "Alignment Tools": [],
        "Analysis Tools": [],
        "Data Converters": [],
        "NGS Tools": [],
        "Other": []
    }
    
    for element_name in elements.keys():
        if "Read" in element_name:
            categories["Data Readers"].append(element_name)
        elif "Write" in element_name:
            categories["Data Writers"].append(element_name)
        elif "Align" in element_name:
            categories["Alignment Tools"].append(element_name)
        elif any(term in element_name for term in ["Statistics", "Summarize", "DESeq2", "Kallisto"]):
            categories["Analysis Tools"].append(element_name)
        elif any(term in element_name for term in ["Convert", "Parser"]):
            categories["Data Converters"].append(element_name)
        elif "NGS" in element_name or any(term in element_name for term in ["Splitter", "Merger"]):
            categories["NGS Tools"].append(element_name)
        else:
            categories["Other"].append(element_name)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}