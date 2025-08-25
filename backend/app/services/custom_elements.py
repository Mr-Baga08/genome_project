# backend/app/services/custom_elements.py
import asyncio
import subprocess
import tempfile
import os
import json
import uuid
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import logging
import sys
import importlib.util
import ast
import traceback

logger = logging.getLogger(__name__)

@dataclass
class ScriptExecution:
    """Result of script execution"""
    script_id: str
    success: bool
    output: Any
    logs: List[str]
    errors: List[str]
    execution_time: float
    memory_usage: Optional[float] = None

@dataclass
class CustomElement:
    """Definition of a custom workflow element"""
    element_id: str
    name: str
    description: str
    script_content: str
    script_type: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    parameters: Dict[str, Any]
    created_by: str
    created_at: str

class CustomElementsService:
    """Service for custom workflow elements with script support"""
    
    def __init__(self):
        self.supported_script_types = {
            'python': {
                'description': 'Python scripts for custom analysis',
                'file_extension': '.py',
                'execution_method': self._execute_python_script
            },
            'r': {
                'description': 'R scripts for statistical analysis',
                'file_extension': '.R',
                'execution_method': self._execute_r_script
            },
            'bash': {
                'description': 'Bash scripts for system operations',
                'file_extension': '.sh',
                'execution_method': self._execute_bash_script
            }
        }
        
        # Security settings
        self.allowed_imports = {
            'numpy', 'pandas', 'scipy', 'matplotlib', 'seaborn', 
            'biopython', 'Bio', 'sklearn', 'statsmodels',
            'json', 'csv', 'math', 'statistics', 're', 'collections'
        }
        
        self.forbidden_imports = {
            'os', 'subprocess', 'sys', 'eval', 'exec', 'compile',
            'open', '__import__', 'globals', 'locals', 'vars'
        }
        
        # Custom element registry
        self.custom_elements = {}
    
    async def execute_custom_script(
        self, 
        script_content: str, 
        input_data: Any, 
        script_type: str = "python",
        parameters: Dict = None,
        timeout: int = 300
    ) -> Dict:
        """Execute custom user-defined scripts safely"""
        
        if script_type not in self.supported_script_types:
            return {"error": f"Unsupported script type: {script_type}"}
        
        if parameters is None:
            parameters = {}
        
        script_id = str(uuid.uuid4())
        
        try:
            # Security validation
            security_check = await self._validate_script_security(script_content, script_type)
            if not security_check["safe"]:
                return {
                    "error": "Script failed security validation",
                    "security_issues": security_check["issues"]
                }
            
            # Execute script based on type
            execution_method = self.supported_script_types[script_type]['execution_method']
            
            start_time = asyncio.get_event_loop().time()
            
            result = await asyncio.wait_for(
                execution_method(script_content, input_data, parameters),
                timeout=timeout
            )
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            return {
                "status": "success",
                "script_id": script_id,
                "execution_time": execution_time,
                "result": result,
                "script_type": script_type
            }
            
        except asyncio.TimeoutError:
            return {"error": f"Script execution timed out after {timeout} seconds"}
        except Exception as e:
            logger.error(f"Error executing script: {str(e)}")
            return {"error": f"Script execution failed: {str(e)}"}
    
    async def _execute_python_script(self, script_content: str, input_data: Any, parameters: Dict) -> ScriptExecution:
        """Execute Python script in controlled environment"""
        
        script_id = str(uuid.uuid4())
        logs = []
        errors = []
        output = None
        
        try:
            # Create secure execution environment
            safe_globals = {
                '__builtins__': {
                    'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
                    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
                    'min': min, 'max': max, 'sum': sum, 'abs': abs,
                    'round': round, 'sorted': sorted, 'reversed': reversed,
                    'enumerate': enumerate, 'zip': zip, 'range': range,
                    'print': lambda *args: logs.append(' '.join(str(arg) for arg in args))
                }
            }
            
            # Add allowed imports
            try:
                import numpy as np
                import pandas as pd
                import json
                import re
                import math
                from collections import defaultdict, Counter
                
                safe_globals.update({
                    'np': np, 'pd': pd, 'json': json, 're': re, 'math': math,
                    'defaultdict': defaultdict, 'Counter': Counter
                })
            except ImportError as e:
                logs.append(f"Warning: Some libraries not available: {e}")
            
            # Add input data and parameters to globals
            safe_globals['input_data'] = input_data
            safe_globals['parameters'] = parameters
            safe_globals['output'] = None
            
            # Execute script
            start_time = asyncio.get_event_loop().time()
            exec(script_content, safe_globals)
            end_time = asyncio.get_event_loop().time()
            
            # Get output
            output = safe_globals.get('output')
            
            return ScriptExecution(
                script_id=script_id,
                success=True,
                output=output,
                logs=logs,
                errors=errors,
                execution_time=end_time - start_time
            )
            
        except Exception as e:
            errors.append(f"Execution error: {str(e)}")
            errors.append(traceback.format_exc())
            
            return ScriptExecution(
                script_id=script_id,
                success=False,
                output=None,
                logs=logs,
                errors=errors,
                execution_time=0.0
            )
    
    async def _execute_r_script(self, script_content: str, input_data: Any, parameters: Dict) -> ScriptExecution:
        """Execute R script using subprocess (requires R installation)"""
        
        script_id = str(uuid.uuid4())
        
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as script_file:
                # Prepare R script with input data
                r_script = f"""
# Load input data and parameters
input_data <- {self._convert_to_r_format(input_data)}
parameters <- {self._convert_to_r_format(parameters)}

# User script
{script_content}

# Output results as JSON
if (exists('output')) {{
    cat(jsonlite::toJSON(output, auto_unbox = TRUE))
}} else {{
    cat('{{"error": "No output variable defined"}}')
}}
"""
                script_file.write(r_script)
                script_file_path = script_file.name
            
            try:
                # Execute R script
                start_time = asyncio.get_event_loop().time()
                
                process = await asyncio.create_subprocess_exec(
                    'Rscript', script_file_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                end_time = asyncio.get_event_loop().time()
                
                # Parse output
                if process.returncode == 0:
                    try:
                        output = json.loads(stdout.decode())
                        return ScriptExecution(
                            script_id=script_id,
                            success=True,
                            output=output,
                            logs=[],
                            errors=[],
                            execution_time=end_time - start_time
                        )
                    except json.JSONDecodeError:
                        return ScriptExecution(
                            script_id=script_id,
                            success=False,
                            output=None,
                            logs=[stdout.decode()],
                            errors=["Failed to parse R script output as JSON"],
                            execution_time=end_time - start_time
                        )
                else:
                    return ScriptExecution(
                        script_id=script_id,
                        success=False,
                        output=None,
                        logs=[],
                        errors=[stderr.decode()],
                        execution_time=end_time - start_time
                    )
                    
            finally:
                # Clean up temporary file
                os.unlink(script_file_path)
                
        except Exception as e:
            return ScriptExecution(
                script_id=script_id,
                success=False,
                output=None,
                logs=[],
                errors=[f"R script execution failed: {str(e)}"],
                execution_time=0.0
            )
    
    async def _execute_bash_script(self, script_content: str, input_data: Any, parameters: Dict) -> ScriptExecution:
        """Execute bash script with security restrictions"""
        
        script_id = str(uuid.uuid4())
        
        try:
            # Create temporary files for input/output
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as script_file:
                # Add safety header and input data
                safe_script = f"""#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Input data (as JSON)
INPUT_DATA='{json.dumps(input_data)}'
PARAMETERS='{json.dumps(parameters)}'

# User script (sandboxed)
{script_content}
"""
                script_file.write(safe_script)
                script_file_path = script_file.name
                os.chmod(script_file_path, 0o755)
            
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Execute with restricted environment
                restricted_env = {
                    'PATH': '/usr/bin:/bin',
                    'INPUT_DATA': json.dumps(input_data),
                    'PARAMETERS': json.dumps(parameters)
                }
                
                process = await asyncio.create_subprocess_exec(
                    'bash', script_file_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=restricted_env
                )
                
                stdout, stderr = await process.communicate()
                
                end_time = asyncio.get_event_loop().time()
                
                success = process.returncode == 0
                logs = [stdout.decode()] if stdout else []
                errors = [stderr.decode()] if stderr else []
                
                return ScriptExecution(
                    script_id=script_id,
                    success=success,
                    output=stdout.decode() if success else None,
                    logs=logs,
                    errors=errors,
                    execution_time=end_time - start_time
                )
                
            finally:
                os.unlink(script_file_path)
                
        except Exception as e:
            return ScriptExecution(
                script_id=script_id,
                success=False,
                output=None,
                logs=[],
                errors=[f"Bash script execution failed: {str(e)}"],
                execution_time=0.0
            )
    
    async def _validate_script_security(self, script_content: str, script_type: str) -> Dict:
        """Validate script for security issues"""
        
        issues = []
        
        if script_type == 'python':
            # Check for forbidden imports and functions
            try:
                tree = ast.parse(script_content)
                
                for node in ast.walk(tree):
                    # Check imports
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name in self.forbidden_imports:
                                issues.append(f"Forbidden import: {alias.name}")
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module in self.forbidden_imports:
                            issues.append(f"Forbidden import: {node.module}")
                    
                    # Check function calls
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            if node.func.id in ['eval', 'exec', 'compile']:
                                issues.append(f"Forbidden function: {node.func.id}")
                
            except SyntaxError as e:
                issues.append(f"Syntax error: {str(e)}")
        
        elif script_type == 'bash':
            # Check for dangerous bash commands
            dangerous_commands = [
                'rm ', 'rmdir', 'mv ', 'cp ', 'chmod', 'chown',
                'sudo', 'su ', 'kill', 'killall', 'pkill',
                'wget', 'curl', 'nc ', 'netcat', 'ssh', 'scp',
                'dd ', 'mkfs', 'fdisk', 'parted'
            ]
            
            for cmd in dangerous_commands:
                if cmd in script_content:
                    issues.append(f"Potentially dangerous command: {cmd.strip()}")
        
        return {
            "safe": len(issues) == 0,
            "issues": issues
        }
    
    def _convert_to_r_format(self, data: Any) -> str:
        """Convert Python data to R format"""
        if isinstance(data, dict):
            r_items = []
            for key, value in data.items():
                r_value = self._convert_to_r_format(value)
                r_items.append(f'"{key}" = {r_value}')
            return f"list({', '.join(r_items)})"
        
        elif isinstance(data, list):
            r_values = [self._convert_to_r_format(item) for item in data]
            return f"c({', '.join(r_values)})"
        
        elif isinstance(data, str):
            return f'"{data}"'
        
        elif isinstance(data, (int, float)):
            return str(data)
        
        elif isinstance(data, bool):
            return "TRUE" if data else "FALSE"
        
        else:
            return "NULL"
    
    async def create_custom_element(self, element_definition: Dict) -> Dict:
        """Create a custom workflow element"""
        
        try:
            # Validate element definition
            validation = await self._validate_element_definition(element_definition)
            if not validation["valid"]:
                return {"error": "Invalid element definition", "details": validation["errors"]}
            
            # Create custom element object
            element = CustomElement(
                element_id=str(uuid.uuid4()),
                name=element_definition['name'],
                description=element_definition.get('description', ''),
                script_content=element_definition['script_content'],
                script_type=element_definition['script_type'],
                input_schema=element_definition.get('input_schema', {}),
                output_schema=element_definition.get('output_schema', {}),
                parameters=element_definition.get('parameters', {}),
                created_by=element_definition.get('created_by', 'unknown'),
                created_at=str(asyncio.get_event_loop().time())
            )
            
            # Test element with sample data
            test_result = await self._test_custom_element(element)
            
            if test_result["success"]:
                # Store element in registry
                self.custom_elements[element.element_id] = element
                
                return {
                    "status": "success",
                    "element_id": element.element_id,
                    "message": "Custom element created successfully",
                    "test_result": test_result
                }
            else:
                return {
                    "error": "Element failed testing",
                    "test_result": test_result
                }
            
        except Exception as e:
            logger.error(f"Error creating custom element: {str(e)}")
            return {"error": f"Failed to create element: {str(e)}"}
    
    async def _validate_element_definition(self, definition: Dict) -> Dict:
        """Validate custom element definition"""
        errors = []
        
        # Required fields
        required_fields = ['name', 'script_content', 'script_type']
        for field in required_fields:
            if field not in definition:
                errors.append(f"Missing required field: {field}")
        
        # Validate script type
        script_type = definition.get('script_type')
        if script_type and script_type not in self.supported_script_types:
            errors.append(f"Unsupported script type: {script_type}")
        
        # Validate name
        name = definition.get('name', '')
        if not name or len(name) < 3:
            errors.append("Element name must be at least 3 characters")
        
        # Validate script content
        script_content = definition.get('script_content', '')
        if not script_content.strip():
            errors.append("Script content cannot be empty")
        
        # Security validation for script content
        if script_content and script_type:
            security_check = await self._validate_script_security(script_content, script_type)
            if not security_check["safe"]:
                errors.extend(security_check["issues"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _test_custom_element(self, element: CustomElement) -> Dict:
        """Test custom element with sample data"""
        
        # Generate sample test data based on input schema
        sample_data = self._generate_sample_data(element.input_schema)
        
        try:
            # Execute element script with sample data
            result = await self.execute_custom_script(
                element.script_content,
                sample_data,
                element.script_type,
                element.parameters,
                timeout=30  # Short timeout for testing
            )
            
            return {
                "success": "status" in result and result["status"] == "success",
                "result": result,
                "sample_data_used": sample_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sample_data_used": sample_data
            }
    
    def _generate_sample_data(self, input_schema: Dict) -> Any:
        """Generate sample data based on input schema"""
        
        if not input_schema:
            # Default sample data for bioinformatics
            return {
                "sequences": [
                    {
                        "id": "sample_seq_1",
                        "name": "Sample Sequence 1",
                        "sequence": "ATCGATCGATCGATCG",
                        "sequence_type": "DNA"
                    },
                    {
                        "id": "sample_seq_2", 
                        "name": "Sample Sequence 2",
                        "sequence": "GCTAGCTAGCTAGCTA",
                        "sequence_type": "DNA"
                    }
                ]
            }
        
        # Generate data based on schema
        sample_data = {}
        for field, schema in input_schema.items():
            field_type = schema.get('type', 'string')
            
            if field_type == 'string':
                sample_data[field] = schema.get('default', 'sample_string')
            elif field_type == 'integer':
                sample_data[field] = schema.get('default', 42)
            elif field_type == 'number':
                sample_data[field] = schema.get('default', 3.14)
            elif field_type == 'array':
                sample_data[field] = schema.get('default', ['item1', 'item2'])
            elif field_type == 'object':
                sample_data[field] = schema.get('default', {})
            else:
                sample_data[field] = None
        
        return sample_data
    
    async def execute_element(self, element_id: str, input_data: Any) -> Dict:
        """Execute a registered custom element"""
        
        if element_id not in self.custom_elements:
            return {"error": f"Custom element not found: {element_id}"}
        
        element = self.custom_elements[element_id]
        
        try:
            # Execute the element's script
            result = await self.execute_custom_script(
                element.script_content,
                input_data,
                element.script_type,
                element.parameters
            )
            
            return {
                "status": "success",
                "element_id": element_id,
                "element_name": element.name,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error executing custom element {element_id}: {str(e)}")
            return {"error": f"Element execution failed: {str(e)}"}
    
    async def get_custom_elements(self) -> Dict:
        """Get list of all custom elements"""
        
        elements_info = {}
        for element_id, element in self.custom_elements.items():
            elements_info[element_id] = {
                "name": element.name,
                "description": element.description,
                "script_type": element.script_type,
                "created_by": element.created_by,
                "created_at": element.created_at,
                "input_schema": element.input_schema,
                "output_schema": element.output_schema
            }
        
        return {
            "custom_elements": elements_info,
            "total_count": len(self.custom_elements)
        }
    
    async def delete_custom_element(self, element_id: str) -> Dict:
        """Delete a custom element"""
        
        if element_id not in self.custom_elements:
            return {"error": f"Custom element not found: {element_id}"}
        
        element_name = self.custom_elements[element_id].name
        del self.custom_elements[element_id]
        
        return {
            "status": "success",
            "message": f"Custom element '{element_name}' deleted successfully"
        }
    
    async def export_custom_element(self, element_id: str) -> Dict:
        """Export custom element definition"""
        
        if element_id not in self.custom_elements:
            return {"error": f"Custom element not found: {element_id}"}
        
        element = self.custom_elements[element_id]
        
        export_data = {
            "name": element.name,
            "description": element.description,
            "script_content": element.script_content,
            "script_type": element.script_type,
            "input_schema": element.input_schema,
            "output_schema": element.output_schema,
            "parameters": element.parameters,
            "export_version": "1.0",
            "exported_at": str(asyncio.get_event_loop().time())
        }
        
        return {
            "status": "success",
            "export_data": export_data,
            "format": "json"
        }
    
    async def import_custom_element(self, import_data: Dict, created_by: str = "unknown") -> Dict:
        """Import custom element from export data"""
        
        try:
            # Validate import data
            if "name" not in import_data or "script_content" not in import_data:
                return {"error": "Invalid import data: missing required fields"}
            
            # Create element definition
            element_definition = {
                **import_data,
                "created_by": created_by
            }
            
            # Create the element
            result = await self.create_custom_element(element_definition)
            
            return result
            
        except Exception as e:
            logger.error(f"Error importing custom element: {str(e)}")
            return {"error": f"Import failed: {str(e)}"}
    
    async def get_script_templates(self) -> Dict:
        """Get templates for different script types"""
        
        templates = {
            "python": {
                "basic_analysis": """
# Basic sequence analysis template
import json

def analyze_sequences(sequences):
    results = []
    for seq in sequences:
        analysis = {
            'name': seq['name'],
            'length': len(seq['sequence']),
            'gc_content': (seq['sequence'].count('G') + seq['sequence'].count('C')) / len(seq['sequence']) * 100
        }
        results.append(analysis)
    return results

# Process input data
if 'sequences' in input_data:
    output = analyze_sequences(input_data['sequences'])
else:
    output = {'error': 'No sequences provided'}
""",
                "statistical_analysis": """
# Statistical analysis template
import numpy as np
import pandas as pd

def calculate_statistics(data):
    if isinstance(data, list):
        array = np.array(data)
        return {
            'mean': float(np.mean(array)),
            'median': float(np.median(array)),
            'std': float(np.std(array)),
            'min': float(np.min(array)),
            'max': float(np.max(array))
        }
    return {'error': 'Invalid data format'}

# Process input
if 'values' in input_data:
    output = calculate_statistics(input_data['values'])
else:
    output = {'error': 'No values provided'}
"""
            },
            "r": {
                "basic_statistics": """
# Basic statistics in R
library(jsonlite)

# Analyze data
if ('values' %in% names(input_data)) {
    values <- as.numeric(input_data$values)
    
    output <- list(
        mean = mean(values, na.rm = TRUE),
        median = median(values, na.rm = TRUE),
        sd = sd(values, na.rm = TRUE),
        min = min(values, na.rm = TRUE),
        max = max(values, na.rm = TRUE)
    )
} else {
    output <- list(error = "No values provided")
}
""",
                "sequence_analysis": """
# Sequence analysis in R
library(seqinr)
library(jsonlite)

if ('sequences' %in% names(input_data)) {
    sequences <- input_data$sequences
    results <- list()
    
    for (i in 1:length(sequences)) {
        seq <- sequences[[i]]$sequence
        seq_chars <- strsplit(seq, "")[[1]]
        
        analysis <- list(
            name = sequences[[i]]$name,
            length = nchar(seq),
            composition = table(seq_chars)
        )
        results[[i]] <- analysis
    }
    
    output <- list(analyses = results)
} else {
    output <- list(error = "No sequences provided")
}
"""
            },
            "bash": {
                "file_processing": """
#!/bin/bash

# File processing template
echo "Processing input data..."

# Parse JSON input (requires jq)
if command -v jq >/dev/null 2>&1; then
    echo "$INPUT_DATA" | jq '.sequences | length'
    echo "Sequence count: $(echo "$INPUT_DATA" | jq '.sequences | length')"
else
    echo "jq not available for JSON parsing"
fi

echo "Processing complete"
""",
                "data_conversion": """
#!/bin/bash

# Data conversion template
echo "Converting data format..."

# Example: Convert sequences to uppercase
# This is a mock implementation
echo "Data conversion complete"
echo '{"status": "converted", "format": "uppercase"}'
"""
            }
        }
        
        return {
            "templates": templates,
            "supported_types": list(self.supported_script_types.keys())
        }

# Global service instance
custom_elements_service = CustomElementsService()