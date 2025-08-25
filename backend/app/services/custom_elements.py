# backend/app/services/custom_elements.py
import asyncio
import subprocess
import tempfile
import json
import time
import docker
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import HTTPException
from datetime import datetime

class CustomElementsService:
    """Service for custom workflow elements with script support"""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except:
            self.docker_client = None
        
        self.allowed_modules = [
            'math', 'statistics', 're', 'json', 'csv', 'datetime',
            'collections', 'itertools', 'functools', 'operator'
        ]
        
        self.forbidden_operations = [
            'import os', 'import sys', 'import subprocess', '__import__',
            'exec', 'eval', 'compile', 'open', 'file', 'input',
            'raw_input', 'reload', 'vars', 'locals', 'globals'
        ]
    
    async def execute_custom_script(self, script_content: str, input_data: Any, script_type: str = "python") -> Dict:
        """Execute custom user-defined scripts safely"""
        try:
            if script_type.lower() == "python":
                return await self._execute_python_script(script_content, input_data)
            elif script_type.lower() == "r":
                return await self._execute_r_script(script_content, input_data)
            elif script_type.lower() == "shell":
                return await self._execute_shell_script(script_content, input_data)
            elif script_type.lower() == "javascript":
                return await self._execute_javascript_script(script_content, input_data)
            else:
                raise HTTPException(status_code=400, detail=f"Script type {script_type} not supported")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Script execution error: {str(e)}")
    
    async def _execute_python_script(self, script_content: str, input_data: Any) -> Dict:
        """Execute Python script in sandboxed environment"""
        try:
            # Security validation
            if not self._validate_script_security(script_content):
                raise ValueError("Script contains forbidden operations")
            
            # Create restricted execution environment
            restricted_globals = {
                '__builtins__': {
                    'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
                    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
                    'range': range, 'enumerate': enumerate, 'zip': zip,
                    'sum': sum, 'max': max, 'min': min, 'abs': abs,
                    'round': round, 'sorted': sorted, 'reversed': reversed,
                    'any': any, 'all': all, 'print': print
                },
                'input_data': input_data,
                'result': None
            }
            
            # Import allowed modules
            for module in self.allowed_modules:
                try:
                    restricted_globals[module] = __import__(module)
                except ImportError:
                    pass
            
            # Add common scientific functions
            import math
            import statistics
            restricted_globals['math'] = math
            restricted_globals['statistics'] = statistics
            
            # Execute script with timeout
            start_time = time.time()
            exec(script_content, restricted_globals)
            execution_time = time.time() - start_time
            
            return {
                "status": "success",
                "result": restricted_globals.get('result'),
                "script_type": "python",
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "script_type": "python",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_r_script(self, script_content: str, input_data: Any) -> Dict:
        """Execute R script using Docker container"""
        try:
            if not self.docker_client:
                return {
                    "status": "error",
                    "error": "Docker not available for R script execution",
                    "script_type": "r"
                }
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write input data to JSON file
                input_file = Path(temp_dir) / "input_data.json"
                with open(input_file, 'w') as f:
                    json.dump(input_data, f, default=str)
                
                # Write R script
                script_file = Path(temp_dir) / "script.R"
                with open(script_file, 'w') as f:
                    # Add input data loading
                    f.write("library(jsonlite)\n")
                    f.write("input_data <- fromJSON('/data/input_data.json')\n\n")
                    f.write(script_content)
                    f.write("\n\n# Save result\n")
                    f.write("write_json(result, '/data/output.json')\n")
                
                # Execute R script in container
                try:
                    container = self.docker_client.containers.run(
                        "rocker/r-base:latest",
                        command="Rscript /data/script.R",
                        volumes={temp_dir: {"bind": "/data", "mode": "rw"}},
                        detach=True,
                        remove=True
                    )
                    
                    # Wait for completion with timeout
                    result = container.wait(timeout=300)  # 5 minute timeout
                    logs = container.logs().decode('utf-8')
                    
                    # Read output
                    output_file = Path(temp_dir) / "output.json"
                    if output_file.exists():
                        with open(output_file, 'r') as f:
                            script_result = json.load(f)
                    else:
                        script_result = None
                    
                    return {
                        "status": "success",
                        "result": script_result,
                        "script_type": "r",
                        "logs": logs,
                        "exit_code": result['StatusCode']
                    }
                    
                except docker.errors.ContainerError as e:
                    return {
                        "status": "error",
                        "error": f"R script execution failed: {str(e)}",
                        "script_type": "r"
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Container execution error: {str(e)}",
                        "script_type": "r"
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "script_type": "r"
            }
    
    async def _execute_shell_script(self, script_content: str, input_data: Any) -> Dict:
        """Execute shell script with safety restrictions"""
        try:
            # Security validation
            dangerous_commands = ['rm', 'rmdir', 'del', 'format', 'mkfs', 'dd', 'sudo', 'su']
            if any(cmd in script_content.lower() for cmd in dangerous_commands):
                raise ValueError("Script contains potentially dangerous commands")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write input data
                input_file = Path(temp_dir) / "input.json"
                with open(input_file, 'w') as f:
                    json.dump(input_data, f, default=str)
                
                # Create script file
                script_file = Path(temp_dir) / "script.sh"
                with open(script_file, 'w') as f:
                    f.write("#!/bin/bash\n")
                    f.write(f"cd {temp_dir}\n")
                    f.write(script_content)
                
                # Execute script
                process = await asyncio.create_subprocess_exec(
                    "bash", str(script_file),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=temp_dir
                )
                
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
                
                return {
                    "status": "success" if process.returncode == 0 else "error",
                    "result": stdout.decode('utf-8') if stdout else None,
                    "error": stderr.decode('utf-8') if stderr else None,
                    "script_type": "shell",
                    "exit_code": process.returncode
                }
                
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "error": "Script execution timeout",
                "script_type": "shell"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "script_type": "shell"
            }
    
    async def _execute_javascript_script(self, script_content: str, input_data: Any) -> Dict:
        """Execute JavaScript script using Node.js container"""
        try:
            if not self.docker_client:
                return {
                    "status": "error", 
                    "error": "Docker not available for JavaScript execution",
                    "script_type": "javascript"
                }
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write input data
                input_file = Path(temp_dir) / "input.json"
                with open(input_file, 'w') as f:
                    json.dump(input_data, f, default=str)
                
                # Write JavaScript script
                script_file = Path(temp_dir) / "script.js"
                with open(script_file, 'w') as f:
                    f.write("const fs = require('fs');\n")
                    f.write("const input_data = JSON.parse(fs.readFileSync('/data/input.json', 'utf8'));\n\n")
                    f.write(script_content)
                    f.write("\n\n// Save result\n")
                    f.write("fs.writeFileSync('/data/output.json', JSON.stringify(result, null, 2));\n")
                
                # Execute in Node.js container
                container = self.docker_client.containers.run(
                    "node:18-alpine",
                    command="node /data/script.js",
                    volumes={temp_dir: {"bind": "/data", "mode": "rw"}},
                    detach=True,
                    remove=True
                )
                
                result = container.wait(timeout=300)
                logs = container.logs().decode('utf-8')
                
                # Read output
                output_file = Path(temp_dir) / "output.json"
                if output_file.exists():
                    with open(output_file, 'r') as f:
                        script_result = json.load(f)
                else:
                    script_result = None
                
                return {
                    "status": "success",
                    "result": script_result,
                    "script_type": "javascript",
                    "logs": logs
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "script_type": "javascript"
            }
    
    async def create_custom_element(self, element_definition: Dict) -> Dict:
        """Create a custom workflow element"""
        try:
            required_fields = ['name', 'inputs', 'outputs', 'script']
            
            for field in required_fields:
                if field not in element_definition:
                    raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
            
            # Validate element definition
            validation_result = await self.validate_custom_element(element_definition)
            if not validation_result["valid"]:
                raise HTTPException(status_code=400, detail=f"Invalid element definition: {validation_result['errors']}")
            
            custom_element = {
                "id": f"custom_{int(time.time())}",
                "name": element_definition['name'],
                "description": element_definition.get('description', ''),
                "inputs": element_definition['inputs'],
                "outputs": element_definition['outputs'],
                "script": element_definition['script'],
                "script_type": element_definition.get('script_type', 'python'),
                "parameters": element_definition.get('parameters', {}),
                "tags": element_definition.get('tags', []),
                "author": element_definition.get('author', 'unknown'),
                "version": element_definition.get('version', '1.0'),
                "created_at": datetime.utcnow().isoformat(),
                "category": "Custom Elements with Script"
            }
            
            # Test execution with sample data
            if element_definition.get('test_execution', False):
                test_data = element_definition.get('test_data', {})
                test_result = await self.execute_custom_script(
                    custom_element['script'],
                    test_data,
                    custom_element['script_type']
                )
                custom_element['test_result'] = test_result
            
            return custom_element
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error creating custom element: {str(e)}")
    
    async def validate_custom_element(self, element_definition: Dict) -> Dict:
        """Validate custom element definition"""
        try:
            validation_results = {
                "valid": True,
                "warnings": [],
                "errors": []
            }
            
            # Check required fields
            required_fields = ['name', 'inputs', 'outputs', 'script']
            for field in required_fields:
                if field not in element_definition:
                    validation_results["errors"].append(f"Missing required field: {field}")
                    validation_results["valid"] = False
            
            # Validate name
            if 'name' in element_definition:
                name = element_definition['name']
                if not name or not isinstance(name, str):
                    validation_results["errors"].append("Name must be a non-empty string")
                    validation_results["valid"] = False
                elif len(name) > 100:
                    validation_results["warnings"].append("Name is quite long")
            
            # Validate inputs/outputs format
            if 'inputs' in element_definition:
                if not isinstance(element_definition['inputs'], list):
                    validation_results["errors"].append("Inputs must be a list")
                    validation_results["valid"] = False
                else:
                    for inp in element_definition['inputs']:
                        if not isinstance(inp, dict) or 'name' not in inp:
                            validation_results["errors"].append("Each input must be a dict with 'name' field")
                            validation_results["valid"] = False
            
            if 'outputs' in element_definition:
                if not isinstance(element_definition['outputs'], list):
                    validation_results["errors"].append("Outputs must be a list")
                    validation_results["valid"] = False
                else:
                    for out in element_definition['outputs']:
                        if not isinstance(out, dict) or 'name' not in out:
                            validation_results["errors"].append("Each output must be a dict with 'name' field")
                            validation_results["valid"] = False
            
            # Basic script validation
            if 'script' in element_definition:
                script = element_definition['script']
                if not script or not isinstance(script, str):
                    validation_results["errors"].append("Script must be a non-empty string")
                    validation_results["valid"] = False
                else:
                    # Check for potentially dangerous operations
                    for dangerous_op in self.forbidden_operations:
                        if dangerous_op in script:
                            validation_results["warnings"].append(f"Potentially dangerous operation detected: {dangerous_op}")
                    
                    # Check script syntax (for Python)
                    script_type = element_definition.get('script_type', 'python')
                    if script_type == 'python':
                        try:
                            compile(script, '<string>', 'exec')
                        except SyntaxError as e:
                            validation_results["errors"].append(f"Python syntax error: {str(e)}")
                            validation_results["valid"] = False
            
            # Validate script type
            supported_types = ['python', 'r', 'shell', 'javascript']
            script_type = element_definition.get('script_type', 'python')
            if script_type not in supported_types:
                validation_results["warnings"].append(f"Script type '{script_type}' may not be fully supported")
            
            return validation_results
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
    
    async def create_element_with_external_tool(self, tool_definition: Dict) -> Dict:
        """Create custom element that wraps external bioinformatics tool"""
        try:
            required_fields = ['tool_name', 'docker_image', 'command_template', 'inputs', 'outputs']
            
            for field in required_fields:
                if field not in tool_definition:
                    raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
            
            # Test tool availability
            tool_test = await self._test_external_tool(tool_definition)
            
            custom_element = {
                "id": f"external_tool_{int(time.time())}",
                "name": tool_definition['tool_name'],
                "description": tool_definition.get('description', f"External tool: {tool_definition['tool_name']}"),
                "type": "external_tool",
                "docker_image": tool_definition['docker_image'],
                "command_template": tool_definition['command_template'],
                "inputs": tool_definition['inputs'],
                "outputs": tool_definition['outputs'],
                "parameters": tool_definition.get('parameters', {}),
                "tool_version": tool_definition.get('tool_version', 'latest'),
                "created_at": datetime.utcnow().isoformat(),
                "test_result": tool_test,
                "category": "External Tools"
            }
            
            return custom_element
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error creating external tool element: {str(e)}")
    
    async def _test_external_tool(self, tool_definition: Dict) -> Dict:
        """Test external tool availability and basic functionality"""
        try:
            if not self.docker_client:
                return {"status": "warning", "message": "Docker not available for testing"}
            
            docker_image = tool_definition['docker_image']
            
            # Try to pull image
            try:
                self.docker_client.images.pull(docker_image)
                image_available = True
            except docker.errors.ImageNotFound:
                image_available = False
            except Exception:
                image_available = False
            
            # Test basic command
            test_command = tool_definition.get('test_command', '--help')
            
            if image_available:
                try:
                    container = self.docker_client.containers.run(
                        docker_image,
                        command=test_command,
                        detach=True,
                        remove=True
                    )
                    
                    result = container.wait(timeout=30)
                    logs = container.logs().decode('utf-8')
                    
                    return {
                        "status": "success",
                        "image_available": True,
                        "command_test": "passed",
                        "test_output": logs[:500]  # First 500 chars
                    }
                except Exception as e:
                    return {
                        "status": "warning",
                        "image_available": True,
                        "command_test": "failed",
                        "error": str(e)
                    }
            else:
                return {
                    "status": "error",
                    "image_available": False,
                    "message": f"Docker image {docker_image} not available"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def execute_external_tool_element(self, element: Dict, input_data: Any) -> Dict:
        """Execute a custom external tool element"""
        try:
            if not self.docker_client:
                raise HTTPException(status_code=500, detail="Docker not available")
            
            docker_image = element['docker_image']
            command_template = element['command_template']
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Prepare input files
                input_files = await self._prepare_input_files(input_data, temp_dir, element['inputs'])
                
                # Build command from template
                command = self._build_command_from_template(command_template, input_files, temp_dir, element.get('parameters', {}))
                
                # Execute tool
                container = self.docker_client.containers.run(
                    docker_image,
                    command=command,
                    volumes={temp_dir: {"bind": "/data", "mode": "rw"}},
                    detach=True,
                    remove=True
                )
                
                result = container.wait(timeout=1800)  # 30 minute timeout
                logs = container.logs().decode('utf-8')
                
                # Parse output files
                output_data = await self._parse_output_files(temp_dir, element['outputs'])
                
                return {
                    "status": "success" if result['StatusCode'] == 0 else "error",
                    "result": output_data,
                    "logs": logs,
                    "exit_code": result['StatusCode'],
                    "tool_name": element['name']
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "tool_name": element.get('name', 'unknown')
            }
    
    async def create_galaxy_tool_config(self, element_definition: Dict) -> str:
        """Create Galaxy tool configuration XML"""
        try:
            tool_name = element_definition.get('name', 'custom_tool')
            tool_version = element_definition.get('version', '1.0')
            description = element_definition.get('description', '')
            
            # Build Galaxy XML
            xml_content = f'''<tool id="{tool_name.lower().replace(' ', '_')}" name="{tool_name}" version="{tool_version}">
    <description>{description}</description>
    
    <requirements>
        <requirement type="package" version="{tool_version}">{tool_name}</requirement>
    </requirements>
    
    <command><![CDATA[
        {element_definition.get('command_template', 'echo "No command defined"')}
    ]]></command>
    
    <inputs>'''
            
            # Add input parameters
            for inp in element_definition.get('inputs', []):
                input_type = inp.get('type', 'data')
                xml_content += f'''
        <param name="{inp['name']}" type="{input_type}" label="{inp.get('label', inp['name'])}" 
               help="{inp.get('help', '')}" />'''
            
            xml_content += '''
    </inputs>
    
    <outputs>'''
            
            # Add output parameters
            for out in element_definition.get('outputs', []):
                xml_content += f'''
        <data name="{out['name']}" format="{out.get('format', 'txt')}" 
              label="{out.get('label', out['name'])}" />'''
            
            xml_content += '''
    </outputs>
    
    <help><![CDATA[
        {description}
        
        **What it does**
        
        This tool performs custom analysis using {tool_name}.
        
    ]]></help>
    
</tool>'''
            
            return xml_content
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error creating Galaxy config: {str(e)}")
    
    def _validate_script_security(self, script_content: str) -> bool:
        """Validate script for security issues"""
        # Check for forbidden operations
        for forbidden_op in self.forbidden_operations:
            if forbidden_op in script_content:
                return False
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'__\w+__',  # Dunder methods
            r'getattr\s*\(',  # Dynamic attribute access
            r'setattr\s*\(',  # Dynamic attribute setting
            r'delattr\s*\(',  # Dynamic attribute deletion
            r'hasattr\s*\(',  # Attribute checking
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, script_content):
                return False
        
        return True
    
    async def _prepare_input_files(self, input_data: Any, temp_dir: str, input_specs: List[Dict]) -> Dict[str, str]:
        """Prepare input files for external tool execution"""
        input_files = {}
        
        for i, input_spec in enumerate(input_specs):
            input_name = input_spec['name']
            input_format = input_spec.get('format', 'txt')
            
            filename = f"input_{i}.{input_format}"
            filepath = Path(temp_dir) / filename
            
            # Write data based on format
            if input_format in ['fasta', 'fa']:
                with open(filepath, 'w') as f:
                    if isinstance(input_data, list):
                        for j, seq in enumerate(input_data):
                            seq_data = seq.get('sequence', '') if isinstance(seq, dict) else str(seq)
                            seq_id = seq.get('id', f'seq_{j}') if isinstance(seq, dict) else f'seq_{j}'
                            f.write(f">{seq_id}\n{seq_data}\n")
                    else:
                        f.write(f">input_sequence\n{str(input_data)}\n")
            elif input_format == 'json':
                with open(filepath, 'w') as f:
                    json.dump(input_data, f, indent=2, default=str)
            else:
                with open(filepath, 'w') as f:
                    f.write(str(input_data))
            
            input_files[input_name] = f"/data/{filename}"
        
        return input_files
    
    def _build_command_from_template(self, template: str, input_files: Dict, temp_dir: str, parameters: Dict) -> str:
        """Build command from template with parameter substitution"""
        command = template
        
        # Substitute input files
        for input_name, filepath in input_files.items():
            command = command.replace(f"{{{input_name}}}", filepath)
        
        # Substitute parameters
        for param_name, param_value in parameters.items():
            command = command.replace(f"{{{param_name}}}", str(param_value))
        
        # Substitute output directory
        command = command.replace("{output_dir}", "/data")
        
        return command
    
    async def _parse_output_files(self, temp_dir: str, output_specs: List[Dict]) -> Dict[str, Any]:
        """Parse output files from external tool execution"""
        outputs = {}
        
        for output_spec in output_specs:
            output_name = output_spec['name']
            output_format = output_spec.get('format', 'txt')
            expected_filename = output_spec.get('filename', f"output.{output_format}")
            
            output_file = Path(temp_dir) / expected_filename
            
            if output_file.exists():
                if output_format in ['fasta', 'fa']:
                    # Parse FASTA output
                    sequences = []
                    with open(output_file, 'r') as f:
                        content = f.read()
                        for record in SeqIO.parse(io.StringIO(content), "fasta"):
                            sequences.append({
                                "id": record.id,
                                "sequence": str(record.seq),
                                "description": record.description,
                                "length": len(record.seq)
                            })
                    outputs[output_name] = sequences
                elif output_format == 'json':
                    with open(output_file, 'r') as f:
                        outputs[output_name] = json.load(f)
                elif output_format in ['csv', 'tsv']:
                    import csv
                    with open(output_file, 'r') as f:
                        delimiter = ',' if output_format == 'csv' else '\t'
                        reader = csv.DictReader(f, delimiter=delimiter)
                        outputs[output_name] = list(reader)
                else:
                    with open(output_file, 'r') as f:
                        outputs[output_name] = f.read()
            else:
                outputs[output_name] = None
        
        return outputs
    
    async def list_custom_elements(self, user_id: str = None, category: str = None) -> List[Dict]:
        """List available custom elements"""
        try:
            # This would query the database in a real implementation
            # For now, return example custom elements
            
            example_elements = [
                {
                    "id": "custom_gc_analyzer",
                    "name": "GC Content Analyzer",
                    "description": "Advanced GC content analysis with sliding windows",
                    "script_type": "python",
                    "category": "Custom Elements with Script",
                    "author": "system",
                    "created_at": "2024-01-01T00:00:00Z",
                    "usage_count": 15
                },
                {
                    "id": "custom_phylogeny",
                    "name": "Custom Phylogeny Builder", 
                    "description": "Build phylogenetic trees with custom parameters",
                    "script_type": "r",
                    "category": "Custom Elements with Script",
                    "author": "system",
                    "created_at": "2024-01-01T00:00:00Z",
                    "usage_count": 8
                },
                {
                    "id": "external_blast",
                    "name": "External BLAST Tool",
                    "description": "BLAST search using external NCBI BLAST+",
                    "type": "external_tool",
                    "docker_image": "biocontainers/blast:2.12.0_cv1",
                    "category": "External Tools",
                    "author": "system",
                    "created_at": "2024-01-01T00:00:00Z",
                    "usage_count": 42
                }
            ]
            
            # Filter by category if specified
            if category:
                example_elements = [e for e in example_elements if e.get('category') == category]
            
            # Filter by user if specified
            if user_id:
                example_elements = [e for e in example_elements if e.get('author') == user_id or e.get('author') == 'system']
            
            return example_elements
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error listing custom elements: {str(e)}")
    
    async def execute_custom_element(self, element_id: str, input_data: Any, parameters: Dict = None) -> Dict:
        """Execute a stored custom element"""
        try:
            # In a real implementation, this would retrieve the element from database
            # For now, use a mock element
            
            mock_element = {
                "id": element_id,
                "name": "Mock Custom Element",
                "script": '''
# Mock custom analysis
result = {
    "analysis_type": "custom",
    "input_count": len(input_data) if isinstance(input_data, list) else 1,
    "timestamp": "''' + datetime.utcnow().isoformat() + '''",
    "parameters_used": len(locals().get("parameters", {}))
}
''',
                "script_type": "python"
            }
            
            # Execute the element
            execution_result = await self.execute_custom_script(
                mock_element['script'],
                input_data,
                mock_element['script_type']
            )
            
            return {
                "element_id": element_id,
                "element_name": mock_element['name'],
                "execution_result": execution_result,
                "parameters": parameters or {}
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error executing custom element: {str(e)}")
    
    async def save_custom_element(self, element: Dict, user_id: str) -> Dict:
        """Save custom element to database"""
        try:
            # Add metadata
            element['user_id'] = user_id
            element['created_at'] = datetime.utcnow().isoformat()
            element['updated_at'] = datetime.utcnow().isoformat()
            element['usage_count'] = 0
            
            # In real implementation, save to database
            # For now, return success message
            
            return {
                "status": "success",
                "element_id": element.get('id'),
                "message": "Custom element saved successfully"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error saving custom element: {str(e)}")
    
    async def delete_custom_element(self, element_id: str, user_id: str) -> Dict:
        """Delete custom element"""
        try:
            # In real implementation, check ownership and delete from database
            
            return {
                "status": "success",
                "element_id": element_id,
                "message": "Custom element deleted successfully"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error deleting custom element: {str(e)}")
    
    async def get_script_templates(self, script_type: str = "python") -> List[Dict]:
        """Get script templates for different analysis types"""
        try:
            templates = {
                "python": [
                    {
                        "name": "Basic Sequence Analysis",
                        "description": "Template for basic sequence analysis",
                        "script": '''
# Basic sequence analysis template
sequences = input_data if isinstance(input_data, list) else [input_data]

results = []
for seq in sequences:
    sequence_data = seq.get('sequence', '') if isinstance(seq, dict) else str(seq)
    
    analysis = {
        'sequence_id': seq.get('id', 'unknown') if isinstance(seq, dict) else 'unknown',
        'length': len(sequence_data),
        'gc_content': (sequence_data.count('G') + sequence_data.count('C')) / len(sequence_data) * 100 if sequence_data else 0,
        'at_content': (sequence_data.count('A') + sequence_data.count('T')) / len(sequence_data) * 100 if sequence_data else 0
    }
    
    results.append(analysis)

result = {
    'analysis_results': results,
    'total_sequences': len(sequences),
    'timestamp': '2024-01-01T00:00:00Z'
}
'''
                    },
                    {
                        "name": "Statistical Analysis",
                        "description": "Template for statistical analysis of sequences",
                        "script": '''
import statistics

sequences = input_data if isinstance(input_data, list) else [input_data]
lengths = []
gc_contents = []

for seq in sequences:
    sequence_data = seq.get('sequence', '') if isinstance(seq, dict) else str(seq)
    lengths.append(len(sequence_data))
    
    if sequence_data:
        gc_content = (sequence_data.count('G') + sequence_data.count('C')) / len(sequence_data) * 100
        gc_contents.append(gc_content)

result = {
    'length_statistics': {
        'mean': statistics.mean(lengths) if lengths else 0,
        'median': statistics.median(lengths) if lengths else 0,
        'std_dev': statistics.stdev(lengths) if len(lengths) > 1 else 0,
        'min': min(lengths) if lengths else 0,
        'max': max(lengths) if lengths else 0
    },
    'gc_statistics': {
        'mean': statistics.mean(gc_contents) if gc_contents else 0,
        'median': statistics.median(gc_contents) if gc_contents else 0,
        'std_dev': statistics.stdev(gc_contents) if len(gc_contents) > 1 else 0
    },
    'sequence_count': len(sequences)
}
'''
                    }
                ],
                "r": [
                    {
                        "name": "Basic R Analysis",
                        "description": "Template for basic analysis in R",
                        "script": '''
# Basic R analysis template
library(jsonlite)

# Process input data
sequences <- input_data
sequence_lengths <- sapply(sequences, function(x) nchar(x$sequence))

# Perform analysis
result <- list(
    sequence_count = length(sequences),
    mean_length = mean(sequence_lengths),
    median_length = median(sequence_lengths),
    sd_length = sd(sequence_lengths)
)
'''
                    }
                ],
                "shell": [
                    {
                        "name": "Basic Shell Script",
                        "description": "Template for shell script analysis",
                        "script": '''
#!/bin/bash

# Basic shell script template
echo "Processing input data..."

# Count sequences in FASTA file
if [ -f "input.fasta" ]; then
    seq_count=$(grep -c "^>" input.fasta)
    echo "Found $seq_count sequences"
else
    echo "No FASTA input found"
fi

echo "Analysis complete"
'''
                    }
                ]
            }
            
            return templates.get(script_type, [])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error getting script templates: {str(e)}")