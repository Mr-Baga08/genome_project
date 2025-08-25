# backend/app/services/external_tool_manager.py
import asyncio
import docker
import subprocess
import tempfile
import os
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
import shutil
import tarfile
import io

logger = logging.getLogger(__name__)

@dataclass
class ToolExecution:
    """Result of external tool execution"""
    tool_name: str
    execution_id: str
    success: bool
    output_files: List[str]
    logs: str
    errors: str
    execution_time: float
    container_id: Optional[str] = None
    exit_code: Optional[int] = None

@dataclass
class BioContainer:
    """BioContainer configuration"""
    name: str
    image: str
    version: str
    description: str
    parameters: Dict[str, Any]
    input_formats: List[str]
    output_formats: List[str]

class ExternalToolManager:
    """Complete manager for external bioinformatics tools integration"""
    
    def __init__(self):
        self.docker_client = None
        self.biocontainers = self._initialize_biocontainers()
        self.execution_history = {}
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.warning(f"Docker client initialization failed: {e}")
            self.docker_client = None
    
    def _initialize_biocontainers(self) -> Dict[str, BioContainer]:
        """Initialize available BioContainers"""
        
        containers = {
            'blast': BioContainer(
                name='blast',
                image='biocontainers/blast:v2.12.0_cv1',
                version='2.12.0',
                description='BLAST+ suite for sequence similarity searching',
                parameters={
                    'evalue': {'type': 'float', 'default': 1e-5},
                    'word_size': {'type': 'int', 'default': 11},
                    'max_target_seqs': {'type': 'int', 'default': 10}
                },
                input_formats=['fasta'],
                output_formats=['xml', 'tsv', 'json']
            ),
            
            'muscle': BioContainer(
                name='muscle',
                image='biocontainers/muscle:v3.8.1551_cv3',
                version='3.8.1551',
                description='Multiple sequence alignment with MUSCLE',
                parameters={
                    'maxiters': {'type': 'int', 'default': 16},
                    'diags': {'type': 'bool', 'default': False}
                },
                input_formats=['fasta'],
                output_formats=['fasta', 'clustal']
            ),
            
            'clustalw': BioContainer(
                name='clustalw',
                image='biocontainers/clustalw:v2.1_cv2',
                version='2.1',
                description='Multiple sequence alignment with ClustalW',
                parameters={
                    'type': {'type': 'select', 'options': ['DNA', 'PROTEIN'], 'default': 'DNA'},
                    'output': {'type': 'select', 'options': ['CLUSTAL', 'FASTA'], 'default': 'CLUSTAL'}
                },
                input_formats=['fasta'],
                output_formats=['aln', 'fasta']
            ),
            
            'mafft': BioContainer(
                name='mafft',
                image='biocontainers/mafft:v7.475_cv1',
                version='7.475',
                description='Multiple sequence alignment with MAFFT',
                parameters={
                    'auto': {'type': 'bool', 'default': True},
                    'reorder': {'type': 'bool', 'default': False}
                },
                input_formats=['fasta'],
                output_formats=['fasta']
            ),
            
            'fastp': BioContainer(
                name='fastp',
                image='biocontainers/fastp:v0.23.2_cv1',
                version='0.23.2',
                description='Fast FASTQ preprocessing tool',
                parameters={
                    'trim_front1': {'type': 'int', 'default': 0},
                    'trim_tail1': {'type': 'int', 'default': 0},
                    'cut_mean_quality': {'type': 'int', 'default': 20}
                },
                input_formats=['fastq'],
                output_formats=['fastq', 'html', 'json']
            ),
            
            'hisat2': BioContainer(
                name='hisat2',
                image='biocontainers/hisat2:v2.2.1_cv1',
                version='2.2.1',
                description='Fast and sensitive alignment for RNA-seq',
                parameters={
                    'min_intronlen': {'type': 'int', 'default': 20},
                    'max_intronlen': {'type': 'int', 'default': 500000},
                    'dta': {'type': 'bool', 'default': False}
                },
                input_formats=['fastq'],
                output_formats=['sam', 'bam']
            ),
            
            'featurecounts': BioContainer(
                name='featurecounts',
                image='biocontainers/subread:v2.0.1_cv1',
                version='2.0.1',
                description='Feature counting for RNA-seq data',
                parameters={
                    'feature_type': {'type': 'str', 'default': 'exon'},
                    'attribute_type': {'type': 'str', 'default': 'gene_id'},
                    'min_mapping_quality': {'type': 'int', 'default': 10}
                },
                input_formats=['bam', 'sam'],
                output_formats=['txt', 'summary']
            )
        }
        
        return containers
    
    def _is_docker_available(self) -> bool:
        """Check if Docker is available"""
        return self.docker_client is not None
    
    async def execute_blast_search(
        self, 
        sequence: str, 
        database: str, 
        parameters: dict = None
    ) -> Dict:
        """Execute BLAST search using BioContainers"""
        
        if not self._is_docker_available():
            return await self._mock_blast_execution(sequence, database, parameters)
        
        if parameters is None:
            parameters = {}
        
        execution_id = str(uuid.uuid4())
        
        try:
            # Prepare input files
            with tempfile.TemporaryDirectory() as temp_dir:
                input_file = os.path.join(temp_dir, "query.fasta")
                output_file = os.path.join(temp_dir, "blast_results.xml")
                
                # Write sequence to FASTA file
                with open(input_file, 'w') as f:
                    f.write(f">query_sequence\n{sequence}\n")
                
                # Prepare BLAST command
                blast_cmd = [
                    "blastn" if self._is_nucleotide_sequence(sequence) else "blastp",
                    "-query", "/data/query.fasta",
                    "-db", database,
                    "-out", "/data/blast_results.xml",
                    "-outfmt", "5",  # XML format
                    "-evalue", str(parameters.get('evalue', 1e-5)),
                    "-max_target_seqs", str(parameters.get('max_target_seqs', 10))
                ]
                
                # Add optional parameters
                if 'word_size' in parameters:
                    blast_cmd.extend(["-word_size", str(parameters['word_size'])])
                
                # Run BLAST container
                start_time = asyncio.get_event_loop().time()
                
                container = self.docker_client.containers.run(
                    self.biocontainers['blast'].image,
                    blast_cmd,
                    volumes={temp_dir: {'bind': '/data', 'mode': 'rw'}},
                    remove=False,
                    detach=True
                )
                
                # Wait for completion
                result = container.wait()
                logs = container.logs().decode('utf-8')
                
                end_time = asyncio.get_event_loop().time()
                
                # Read output
                output_content = ""
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        output_content = f.read()
                
                # Clean up container
                container.remove()
                
                return {
                    "status": "success",
                    "execution_id": execution_id,
                    "tool": "blast",
                    "execution_time": end_time - start_time,
                    "exit_code": result['StatusCode'],
                    "output": output_content,
                    "logs": logs,
                    "parameters_used": parameters
                }
                
        except Exception as e:
            logger.error(f"Error executing BLAST: {str(e)}")
            return {"error": f"BLAST execution failed: {str(e)}"}
    
    async def execute_multiple_alignment(
        self, 
        sequences: List[str], 
        tool: str, 
        parameters: dict = None
    ) -> str:
        """Execute multiple sequence alignment"""
        
        if tool not in ['muscle', 'clustalw', 'mafft']:
            return {"error": f"Unsupported alignment tool: {tool}"}
        
        if not self._is_docker_available():
            return await self._mock_alignment_execution(sequences, tool, parameters)
        
        if parameters is None:
            parameters = {}
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                input_file = os.path.join(temp_dir, "input.fasta")
                output_file = os.path.join(temp_dir, "alignment.fasta")
                
                # Write sequences to FASTA file
                with open(input_file, 'w') as f:
                    for i, seq in enumerate(sequences):
                        f.write(f">sequence_{i+1}\n{seq}\n")
                
                # Prepare command based on tool
                if tool == 'muscle':
                    cmd = [
                        "muscle",
                        "-in", "/data/input.fasta",
                        "-out", "/data/alignment.fasta"
                    ]
                    if 'maxiters' in parameters:
                        cmd.extend(["-maxiters", str(parameters['maxiters'])])
                
                elif tool == 'clustalw':
                    cmd = [
                        "clustalw",
                        "-INFILE=/data/input.fasta",
                        "-OUTFILE=/data/alignment.fasta",
                        "-OUTPUT=FASTA"
                    ]
                    if parameters.get('type'):
                        cmd.append(f"-TYPE={parameters['type']}")
                
                elif tool == 'mafft':
                    cmd = ["mafft"]
                    if parameters.get('auto', True):
                        cmd.append("--auto")
                    cmd.extend(["/data/input.fasta"])
                
                # Execute container
                container = self.docker_client.containers.run(
                    self.biocontainers[tool].image,
                    cmd,
                    volumes={temp_dir: {'bind': '/data', 'mode': 'rw'}},
                    remove=False,
                    detach=True
                )
                
                result = container.wait()
                logs = container.logs().decode('utf-8')
                
                # Read alignment result
                alignment_content = ""
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        alignment_content = f.read()
                elif tool == 'mafft':
                    # MAFFT outputs to stdout
                    alignment_content = logs
                
                container.remove()
                
                return {
                    "status": "success",
                    "tool": tool,
                    "alignment": alignment_content,
                    "logs": logs,
                    "exit_code": result['StatusCode']
                }
                
        except Exception as e:
            logger.error(f"Error executing {tool}: {str(e)}")
            return {"error": f"{tool} execution failed: {str(e)}"}
    
    async def _mock_blast_execution(self, sequence: str, database: str, parameters: dict) -> Dict:
        """Mock BLAST execution for testing when Docker unavailable"""
        
        logger.info("Running mock BLAST execution (Docker unavailable)")
        
        # Generate mock BLAST results
        mock_hits = []
        
        np.random.seed(hash(sequence) % 2**32)
        num_hits = min(parameters.get('max_target_seqs', 10), np.random.randint(3, 8))
        
        for i in range(num_hits):
            hit = {
                "hit_id": f"gi|{np.random.randint(100000, 999999)}|ref|{['NM_', 'XM_', 'NR_'][np.random.randint(0, 3)]}{np.random.randint(100000, 999999)}.1|",
                "hit_def": f"Homo sapiens {['gene', 'protein', 'sequence'][np.random.randint(0, 3)]} {i+1}",
                "hit_len": np.random.randint(200, 2000),
                "hsp_score": float(np.random.exponential(100) + 50),
                "hsp_evalue": float(np.random.exponential(1e-10)),
                "hsp_identity": np.random.randint(80, 100),
                "hsp_positive": np.random.randint(85, 100),
                "hsp_align_len": np.random.randint(100, len(sequence)),
                "hsp_query_from": 1,
                "hsp_query_to": min(len(sequence), np.random.randint(100, len(sequence))),
                "hsp_hit_from": np.random.randint(1, 50),
                "hsp_hit_to": np.random.randint(150, 500)
            }
            mock_hits.append(hit)
        
        # Sort by E-value
        mock_hits.sort(key=lambda x: x['hsp_evalue'])
        
        return {
            "status": "success",
            "execution_id": str(uuid.uuid4()),
            "tool": "blast",
            "results": {
                "query_length": len(sequence),
                "database": database,
                "hits": mock_hits,
                "search_stats": {
                    "total_hits": len(mock_hits),
                    "significant_hits": len([h for h in mock_hits if h['hsp_evalue'] < parameters.get('evalue', 1e-5)])
                }
            }
        }
    
    async def _mock_alignment_execution(self, sequences: List[str], tool: str, parameters: dict) -> Dict:
        """Mock alignment execution for testing"""
        
        logger.info(f"Running mock {tool} execution (Docker unavailable)")
        
        # Simple mock alignment - just pad sequences to same length
        max_length = max(len(seq) for seq in sequences)
        aligned_sequences = []
        
        for i, seq in enumerate(sequences):
            # Simple padding alignment
            aligned_seq = seq.ljust(max_length, '-')
            aligned_sequences.append(f">sequence_{i+1}\n{aligned_seq}")
        
        alignment_content = '\n'.join(aligned_sequences)
        
        return {
            "status": "success",
            "tool": tool,
            "alignment": alignment_content,
            "logs": f"Mock {tool} alignment completed",
            "exit_code": 0
        }
    
    def _is_nucleotide_sequence(self, sequence: str) -> bool:
        """Determine if sequence is nucleotide or protein"""
        nucleotide_chars = set('ATCGRYKMSWBDHVN')
        sequence_chars = set(sequence.upper())
        
        # If >90% of characters are valid nucleotides, consider it nucleotide
        valid_nuc_ratio = len(sequence_chars & nucleotide_chars) / len(sequence_chars)
        return valid_nuc_ratio > 0.9
    
    async def pull_container_image(self, container_name: str) -> Dict:
        """Pull container image from repository"""
        
        if not self._is_docker_available():
            return {"error": "Docker not available"}
        
        if container_name not in self.biocontainers:
            return {"error": f"Unknown container: {container_name}"}
        
        try:
            container_config = self.biocontainers[container_name]
            
            logger.info(f"Pulling container image: {container_config.image}")
            
            # Pull image
            image = self.docker_client.images.pull(container_config.image)
            
            return {
                "status": "success",
                "container_name": container_name,
                "image": container_config.image,
                "image_id": image.id,
                "size": image.attrs.get('Size', 0),
                "message": f"Successfully pulled {container_config.image}"
            }
            
        except Exception as e:
            logger.error(f"Error pulling container {container_name}: {str(e)}")
            return {"error": f"Failed to pull container: {str(e)}"}
    
    async def list_available_containers(self) -> Dict:
        """List all available BioContainers"""
        
        containers_info = {}
        
        for name, container in self.biocontainers.items():
            # Check if image is locally available
            image_available = False
            if self._is_docker_available():
                try:
                    self.docker_client.images.get(container.image)
                    image_available = True
                except:
                    image_available = False
            
            containers_info[name] = {
                "name": container.name,
                "description": container.description,
                "version": container.version,
                "image": container.image,
                "image_available": image_available,
                "input_formats": container.input_formats,
                "output_formats": container.output_formats,
                "parameters": container.parameters
            }
        
        return {
            "containers": containers_info,
            "total_count": len(containers_info),
            "docker_available": self._is_docker_available()
        }
    
    async def validate_tool_input(self, tool_name: str, input_data: Any, parameters: Dict = None) -> Dict:
        """Validate input data and parameters for a tool"""
        
        if tool_name not in self.biocontainers:
            return {"error": f"Unknown tool: {tool_name}"}
        
        container = self.biocontainers[tool_name]
        errors = []
        warnings = []
        
        # Validate parameters
        if parameters:
            for param_name, param_value in parameters.items():
                if param_name in container.parameters:
                    param_config = container.parameters[param_name]
                    param_type = param_config['type']
                    
                    # Type validation
                    if param_type == 'int' and not isinstance(param_value, int):
                        errors.append(f"Parameter {param_name} must be integer")
                    elif param_type == 'float' and not isinstance(param_value, (int, float)):
                        errors.append(f"Parameter {param_name} must be numeric")
                    elif param_type == 'bool' and not isinstance(param_value, bool):
                        errors.append(f"Parameter {param_name} must be boolean")
                    elif param_type == 'select':
                        valid_options = param_config.get('options', [])
                        if param_value not in valid_options:
                            errors.append(f"Parameter {param_name} must be one of: {valid_options}")
        
        # Tool-specific validation
        if tool_name == 'blast':
            if isinstance(input_data, str):
                if len(input_data) < 10:
                    warnings.append("Query sequence is very short - may not produce meaningful results")
                if len(input_data) > 10000:
                    warnings.append("Query sequence is very long - search may be slow")
        
        elif tool_name in ['muscle', 'clustalw', 'mafft']:
            if isinstance(input_data, list):
                if len(input_data) < 2:
                    errors.append("At least 2 sequences required for alignment")
                if len(input_data) > 1000:
                    warnings.append("Large number of sequences - alignment may be very slow")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "tool_info": {
                "name": container.name,
                "version": container.version,
                "image_available": self._is_docker_available()
            }
        }
    
    async def get_execution_status(self, execution_id: str) -> Dict:
        """Get status of a tool execution"""
        
        if execution_id in self.execution_history:
            return {
                "status": "success",
                "execution": self.execution_history[execution_id]
            }
        else:
            return {"error": f"Execution {execution_id} not found"}
    
    async def cleanup_old_executions(self, max_age_hours: int = 24) -> Dict:
        """Clean up old execution data"""
        
        try:
            current_time = asyncio.get_event_loop().time()
            max_age_seconds = max_age_hours * 3600
            
            cleaned_count = 0
            to_remove = []
            
            for execution_id, execution_data in self.execution_history.items():
                execution_time = execution_data.get('timestamp', current_time)
                age = current_time - execution_time
                
                if age > max_age_seconds:
                    to_remove.append(execution_id)
                    cleaned_count += 1
            
            # Remove old executions
            for execution_id in to_remove:
                del self.execution_history[execution_id]
            
            return {
                "status": "success",
                "cleaned_executions": cleaned_count,
                "remaining_executions": len(self.execution_history)
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up executions: {str(e)}")
            return {"error": f"Cleanup failed: {str(e)}"}
    
    async def get_container_logs(self, container_name: str, lines: int = 100) -> Dict:
        """Get logs from a running container"""
        
        if not self._is_docker_available():
            return {"error": "Docker not available"}
        
        try:
            # Find running containers for the tool
            containers = self.docker_client.containers.list(
                filters={"ancestor": self.biocontainers.get(container_name, {}).get('image', '')}
            )
            
            if not containers:
                return {"error": f"No running containers found for {container_name}"}
            
            # Get logs from first container
            container = containers[0]
            logs = container.logs(tail=lines).decode('utf-8')
            
            return {
                "status": "success",
                "container_id": container.id[:12],
                "container_name": container_name,
                "logs": logs,
                "lines_returned": len(logs.split('\n'))
            }
            
        except Exception as e:
            logger.error(f"Error getting container logs: {str(e)}")
            return {"error": f"Failed to get logs: {str(e)}"}
    
    async def execute_custom_container(
        self, 
        image: str, 
        command: List[str], 
        input_files: Dict[str, str],
        parameters: Dict = None
    ) -> Dict:
        """Execute custom container with specified image and command"""
        
        if not self._is_docker_available():
            return {"error": "Docker not available"}
        
        execution_id = str(uuid.uuid4())
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write input files
                for filename, content in input_files.items():
                    file_path = os.path.join(temp_dir, filename)
                    with open(file_path, 'w') as f:
                        f.write(content)
                
                # Execute container
                start_time = asyncio.get_event_loop().time()
                
                container = self.docker_client.containers.run(
                    image,
                    command,
                    volumes={temp_dir: {'bind': '/data', 'mode': 'rw'}},
                    working_dir='/data',
                    remove=False,
                    detach=True,
                    network_mode='none',  # Security: no network access
                    mem_limit='2g',       # Security: limit memory
                    cpu_quota=100000      # Security: limit CPU
                )
                
                # Wait for completion with timeout
                try:
                    result = container.wait(timeout=3600)  # 1 hour timeout
                    logs = container.logs().decode('utf-8')
                    
                    end_time = asyncio.get_event_loop().time()
                    
                    # Read output files
                    output_files = {}
                    for file in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, file)
                        if os.path.isfile(file_path) and file not in input_files:
                            with open(file_path, 'r') as f:
                                output_files[file] = f.read()
                    
                    # Clean up
                    container.remove()
                    
                    execution_result = {
                        "execution_id": execution_id,
                        "image": image,
                        "command": command,
                        "success": result['StatusCode'] == 0,
                        "exit_code": result['StatusCode'],
                        "execution_time": end_time - start_time,
                        "logs": logs,
                        "output_files": output_files,
                        "timestamp": end_time
                    }
                    
                    # Store in execution history
                    self.execution_history[execution_id] = execution_result
                    
                    return {
                        "status": "success",
                        "execution": execution_result
                    }
                
                except Exception as timeout_error:
                    # Handle timeout or other execution errors
                    try:
                        container.kill()
                        container.remove()
                    except:
                        pass
                    
                    return {"error": f"Container execution failed: {str(timeout_error)}"}
                
        except Exception as e:
            logger.error(f"Error executing custom container: {str(e)}")
            return {"error": f"Custom container execution failed: {str(e)}"}
    
    async def get_system_requirements(self) -> Dict:
        """Get system requirements for external tools"""
        
        return {
            "docker": {
                "required": True,
                "minimum_version": "20.10",
                "available": self._is_docker_available()
            },
            "system_resources": {
                "minimum_memory": "4GB",
                "recommended_memory": "16GB", 
                "minimum_disk": "10GB",
                "recommended_disk": "100GB"
            },
            "biocontainers": {
                "total_available": len(self.biocontainers),
                "images_pulled": len([
                    name for name, container in self.biocontainers.items()
                    if self._check_image_locally_available(container.image)
                ]) if self._is_docker_available() else 0
            }
        }
    
    def _check_image_locally_available(self, image: str) -> bool:
        """Check if Docker image is available locally"""
        if not self._is_docker_available():
            return False
        
        try:
            self.docker_client.images.get(image)
            return True
        except:
            return False
    
    async def monitor_container_resources(self, container_id: str) -> Dict:
        """Monitor resource usage of running container"""
        
        if not self._is_docker_available():
            return {"error": "Docker not available"}
        
        try:
            container = self.docker_client.containers.get(container_id)
            
            # Get container stats
            stats = container.stats(stream=False)
            
            # Parse memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            memory_percent = (memory_usage / memory_limit) * 100
            
            # Parse CPU usage
            cpu_stats = stats['cpu_stats']
            cpu_usage = 0
            if 'system_cpu_usage' in cpu_stats:
                cpu_delta = cpu_stats['cpu_usage']['total_usage']
                system_delta = cpu_stats['system_cpu_usage'] 
                cpu_usage = (cpu_delta / system_delta) * 100
            
            return {
                "status": "success",
                "container_id": container_id[:12],
                "resource_usage": {
                    "memory": {
                        "usage_bytes": memory_usage,
                        "limit_bytes": memory_limit,
                        "usage_percent": memory_percent
                    },
                    "cpu": {
                        "usage_percent": cpu_usage
                    }
                },
                "container_status": container.status
            }
            
        except Exception as e:
            logger.error(f"Error monitoring container resources: {str(e)}")
            return {"error": f"Resource monitoring failed: {str(e)}"}

# Global service instance
external_tool_manager = ExternalToolManager()