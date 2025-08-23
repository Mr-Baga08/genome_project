# backend/app/models/workflow_elements.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum

class ElementType(str, Enum):
    READER = "reader"
    WRITER = "writer" 
    ALIGNER = "aligner"
    ANALYZER = "analyzer"
    CONVERTER = "converter"
    FILTER = "filter"
    ASSEMBLER = "assembler"
    TREE_BUILDER = "tree"
    BLAST = "blast"
    FLOW = "flow"

class WorkflowElement(BaseModel):
    id: int
    name: str
    type: ElementType
    position: Dict[str, float]
    parameters: Optional[Dict[str, Any]] = {}
    input_formats: Optional[List[str]] = []
    output_formats: Optional[List[str]] = []
    description: Optional[str] = ""

class WorkflowConnection(BaseModel):
    from_node: int = Field(alias="from")
    to_node: int = Field(alias="to")
    
    class Config:
        allow_population_by_field_name = True

class WorkflowDefinition(BaseModel):
    nodes: List[WorkflowElement]
    connections: List[WorkflowConnection]
    name: Optional[str] = "Untitled Workflow"
    description: Optional[str] = ""
    created_by: Optional[str] = ""