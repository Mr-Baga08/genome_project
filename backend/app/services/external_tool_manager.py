# backend/app/services/external_tool_manager.py - FIXED VERSION
import tempfile
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor
import subprocess
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class ExternalToolManager:
    """Manages integration with external bioinformatics tools using Docker with lazy initialization"""
    
    def __init__(self):
        self.docker_client = None
        self._docker_available = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # BioContainer image mappings
        self.tool_images = {
            'blast': 'biocontainers/blast:2.12.0_cv1',
            'muscle': 'biocontainers/muscle:3.8.31_cv2',
            'clustalw': 'biocontainers/clustalw:2.1_cv1',
            'mafft': 'biocontainers/mafft:7.471_cv1',
            'iqtree': 'biocontainers/iqtree:2.1.2_cv1',
            'hmmer': 'biocontainers/hmmer:3.3_cv1',
            'diamond': 'biocontainers/diamond:2.0.15_cv1',
            'prodigal': 'biocontainers/prodigal:2.6.3_cv1',
            'augustus': 'biocontainers/augustus:3.4.0_cv1',
            'samtools': 'biocontainers/samtools:1.15_cv1',
            'bwa': 'biocontainers/bwa:0.7.17_cv1'
        }
    
    def _init_docker_client(self):
        """Lazy initialization of Docker client with better error handling"""
        if self.docker_client is None:
            try:
                import docker
                
                # Try different Docker connection methods
                try:
                    # Method 1: Default from_env
                    self.docker_client = docker.from_env(timeout=10)
                except Exception:
                    try:
                        # Method 2: Unix socket directly
                        self.docker_client = docker.DockerClient(
                            base_url='unix://var/run/docker.sock',
                            timeout=10
                        )
                    except Exception:
                        # Method 3: TCP connection (for some environments)
                        self.docker_client = docker.DockerClient(
                            base_url='tcp://localhost:2375',
                            timeout=10
                        )
                
                # Test connection
                self.docker_client.ping()
                self._docker_available = True
                logger.info("✅ Docker client initialized successfully")
                
                # Log available images
                try:
                    images = self.docker_client.images.list()
                    logger.info(f"📦 Found {len(images)} Docker images available")
                except Exception as e:
                    logger.warning(f"Could not list Docker images: {str(e)}")
                
            except Exception as e:
                logger.warning(f"⚠️  Docker client initialization failed: {str(e)}")
                logger.warning("🔄 Falling back to mock analysis results")
                self.docker_client = None
                self._docker_available = False
    
    def _is_docker_available(self) -> bool:
        """Check if Docker is available"""
        if self._docker_available is None:
            self._init_docker_client()
        return self._docker_available
    
    async def execute_blast_search(self, sequence: str, database: str, 
                                 parameters: Dict = None) -> Dict:
        """Execute BLAST search using BioContainers or mock"""
        if parameters is None:
            parameters = {"evalue": "1e-5", "outfmt": "6", "max_hits": 10}
        
        logger.info(f"🔍 Starting BLAST search (Docker available: {self._is_docker_available()})")
        
        if self._is_docker_available():
            try:
                return await self._execute_blast_docker(sequence, database, parameters)
            except Exception as e:
                logger.warning(f"Docker BLAST failed, using mock: {str(e)}")
                return await self._execute_blast_mock(sequence, database, parameters)
        else:
            return await self._execute_blast_mock(sequence, database, parameters)
    
    async def _execute_blast_docker(self, sequence: str, database: str, parameters: Dict) -> Dict:
        """Execute BLAST using Docker"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write query sequence
            query_file = temp_path / "query.fasta"
            with open(query_file, 'w') as f:
                f.write(f">query\n{sequence}\n")
            
            # Prepare output file
            output_file = temp_path / "blast_results.txt"
            
            # Build BLAST command
            blast_program = "blastn" if self._is_nucleotide(sequence) else "blastp"
            blast_cmd = [
                blast_program,
                "-query", "/data/query.fasta",
                "-db", f"/databases/{database}",
                "-out", "/data/blast_results.txt",
                "-outfmt", str(parameters.get("outfmt", "6")),
                "-evalue", str(parameters.get("evalue", "1e-5")),
                "-max_target_seqs", str(parameters.get("max_hits", 10))
            ]
            
            # Execute in container
            container = await self._run_container(
                self.tool_images['blast'],
                command=" ".join(blast_cmd),
                volumes={
                    str(temp_path): {"bind": "/data", "mode": "rw"},
                    "/opt/blast_databases": {"bind": "/databases", "mode": "ro"}
                },
                working_dir="/data"
            )
            
            # Parse results
            if output_file.exists():
                results = self._parse_blast_results(output_file, parameters.get("outfmt", "6"))
                return {
                    "results": results,
                    "parameters": parameters,
                    "database": database,
                    "query_length": len(sequence),
                    "method": "docker"
                }
            else:
                raise RuntimeError("BLAST execution failed - no output generated")
    
    async def _execute_blast_mock(self, sequence: str, database: str, parameters: Dict) -> Dict:
        """Mock BLAST execution for development/testing"""
        import random
        
        hits = []
        max_hits = int(parameters.get("max_hits", 10))
        
        for i in range(min(max_hits, 5)):  # Generate up to 5 mock hits
            hits.append({
                "query_id": "query",
                "subject_id": f"mock_hit_{i}",
                "identity": random.uniform(0.3, 0.95),
                "alignment_length": random.randint(50, min(len(sequence), 200)),
                "mismatches": random.randint(1, 20),
                "gap_opens": random.randint(0, 5),
                "query_start": 1,
                "query_end": len(sequence),
                "subject_start": random.randint(1, 50),
                "subject_end": random.randint(100, 500),
                "evalue": random.uniform(1e-10, float(parameters.get("evalue", "1e-5"))),
                "bit_score": random.uniform(50, 200),
                "accession": f"MOCK_{random.randint(100000, 999999)}",
                "description": f"Mock protein {i+1} [simulated organism]"
            })
        
        return {
            "results": [{"query_id": "query", "hits": hits}],
            "parameters": parameters,
            "database": database,
            "query_length": len(sequence),
            "method": "mock"
        }
    
    async def execute_multiple_alignment(self, sequences: List[str], tool: str = "muscle", 
                                       parameters: Dict = None) -> Dict:
        """Execute multiple sequence alignment"""
        if parameters is None:
            parameters = {}
        
        if tool not in ['muscle', 'clustalw', 'mafft']:
            raise ValueError(f"Unsupported alignment tool: {tool}")
        
        logger.info(f"📊 Starting {tool} alignment (Docker available: {self._is_docker_available()})")
        
        if self._is_docker_available():
            try:
                return await self._execute_alignment_docker(sequences, tool, parameters)
            except Exception as e:
                logger.warning(f"Docker alignment failed, using mock: {str(e)}")
                return await self._execute_alignment_mock(sequences, tool, parameters)
        else:
            return await self._execute_alignment_mock(sequences, tool, parameters)
    
    async def _execute_alignment_docker(self, sequences: List[str], tool: str, parameters: Dict) -> Dict:
        """Execute alignment using Docker"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write input sequences
            input_file = temp_path / "sequences.fasta"
            with open(input_file, 'w') as f:
                for i, seq in enumerate(sequences):
                    f.write(f">seq_{i}\n{seq}\n")
            
            # Prepare output file
            output_file = temp_path / "alignment.fasta"
            
            # Build command based on tool
            if tool == "muscle":
                cmd = f"muscle -in /data/sequences.fasta -out /data/alignment.fasta"
            elif tool == "clustalw":
                cmd = f"clustalw2 -infile=/data/sequences.fasta -outfile=/data/alignment.fasta -output=FASTA"
            elif tool == "mafft":
                cmd = f"mafft --auto /data/sequences.fasta > /data/alignment.fasta"
            
            container = await self._run_container(
                self.tool_images[tool],
                command=cmd,
                volumes={str(temp_path): {"bind": "/data", "mode": "rw"}}
            )
            
            if output_file.exists():
                aligned_sequences = self._parse_fasta_file(output_file)
                alignment_stats = self._calculate_alignment_statistics(aligned_sequences)
                
                return {
                    "aligned_sequences": aligned_sequences,
                    "alignment_statistics": alignment_stats,
                    "tool": tool,
                    "parameters": parameters,
                    "method": "docker"
                }
            else:
                raise RuntimeError(f"{tool} alignment failed - no output generated")
    
    async def _execute_alignment_mock(self, sequences: List[str], tool: str, parameters: Dict) -> Dict:
        """Mock alignment execution"""
        import random
        
        # Simulate alignment by adding gaps
        max_length = max(len(seq) for seq in sequences) if sequences else 0
        aligned_sequences = []
        
        for i, seq in enumerate(sequences):
            # Add random gaps to simulate alignment
            gaps_needed = max_length - len(seq)
            gap_positions = sorted([random.randint(0, len(seq)) for _ in range(gaps_needed // 3)])
            
            aligned_seq = seq
            for pos in reversed(gap_positions):
                aligned_seq = aligned_seq[:pos] + '-' + aligned_seq[pos:]
            
            # Pad to max length
            aligned_seq = aligned_seq.ljust(max_length, '-')
            
            aligned_sequences.append({
                "id": f"seq_{i}",
                "sequence": aligned_seq,
                "length": len(aligned_seq)
            })
        
        alignment_stats = self._calculate_alignment_statistics(aligned_sequences)
        
        return {
            "aligned_sequences": aligned_sequences,
            "alignment_statistics": alignment_stats,
            "tool": f"{tool} (mock)",
            "parameters": parameters,
            "method": "mock"
        }
    
    async def _run_container(self, image: str, command: str, volumes: Dict = None, 
                           working_dir: str = None, timeout: int = 3600) -> Dict:
        """Run Docker container with timeout and error handling"""
        if not self._is_docker_available():
            raise RuntimeError("Docker is not available")
        
        def run_sync():
            try:
                container = self.docker_client.containers.run(
                    image,
                    command=command,
                    volumes=volumes or {},
                    working_dir=working_dir,
                    detach=True,
                    remove=True,
                    mem_limit="2g",
                    cpu_count=2,
                    network_mode="bridge"
                )
                
                # Wait for completion
                result = container.wait(timeout=timeout)
                logs = container.logs().decode('utf-8')
                
                return {
                    "status_code": result['StatusCode'],
                    "logs": logs
                }
                
            except Exception as e:
                logger.error(f"Container execution failed: {str(e)}")
                raise RuntimeError(f"Container execution failed: {e}")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, run_sync)
    
    def _is_nucleotide(self, sequence: str) -> bool:
        """Check if sequence is nucleotide (DNA/RNA)"""
        if not sequence:
            return True
        
        nucleotide_chars = set('ATCGUN')
        seq_chars = set(sequence.upper())
        if not seq_chars:
            return True
        
        nucleotide_ratio = len(seq_chars.intersection(nucleotide_chars)) / len(seq_chars)
        return nucleotide_ratio > 0.8
    
    def _parse_blast_results(self, results_file: Path, outfmt: str) -> List[Dict]:
        """Parse BLAST results file"""
        results = []
        
        try:
            if outfmt == "6":  # Tabular format
                with open(results_file, 'r') as f:
                    for line in f:
                        if line.startswith('#'):
                            continue
                        
                        fields = line.strip().split('\t')
                        if len(fields) >= 12:
                            results.append({
                                "query_id": fields[0],
                                "subject_id": fields[1],
                                "identity": float(fields[2]),
                                "alignment_length": int(fields[3]),
                                "mismatches": int(fields[4]),
                                "gap_opens": int(fields[5]),
                                "query_start": int(fields[6]),
                                "query_end": int(fields[7]),
                                "subject_start": int(fields[8]),
                                "subject_end": int(fields[9]),
                                "evalue": float(fields[10]),
                                "bit_score": float(fields[11])
                            })
        except Exception as e:
            logger.error(f"Failed to parse BLAST results: {str(e)}")
        
        return results
    
    def _parse_fasta_file(self, fasta_file: Path) -> List[Dict]:
        """Parse FASTA file"""
        sequences = []
        current_seq = None
        current_sequence = []
        
        try:
            with open(fasta_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('>'):
                        if current_seq:
                            sequences.append({
                                "id": current_seq,
                                "sequence": ''.join(current_sequence),
                                "length": len(''.join(current_sequence))
                            })
                        current_seq = line[1:]
                        current_sequence = []
                    else:
                        current_sequence.append(line)
            
            # Add last sequence
            if current_seq:
                sequences.append({
                    "id": current_seq,
                    "sequence": ''.join(current_sequence),
                    "length": len(''.join(current_sequence))
                })
        except Exception as e:
            logger.error(f"Failed to parse FASTA file: {str(e)}")
        
        return sequences
    
    def _calculate_alignment_statistics(self, aligned_sequences: List[Dict]) -> Dict:
        """Calculate alignment statistics"""
        if not aligned_sequences:
            return {}
        
        alignment_length = len(aligned_sequences[0]["sequence"])
        num_sequences = len(aligned_sequences)
        
        # Calculate conservation and gap statistics
        total_gaps = 0
        conserved_positions = 0
        
        for pos in range(alignment_length):
            column = [seq["sequence"][pos] for seq in aligned_sequences]
            gaps = column.count('-')
            total_gaps += gaps
            
            # Position is conserved if all non-gap characters are the same
            non_gaps = [c for c in column if c != '-']
            if non_gaps and all(c == non_gaps[0] for c in non_gaps):
                conserved_positions += 1
        
        gap_percentage = (total_gaps / (alignment_length * num_sequences)) * 100
        conservation_percentage = (conserved_positions / alignment_length) * 100
        
        return {
            "alignment_length": alignment_length,
            "num_sequences": num_sequences,
            "conserved_positions": conserved_positions,
            "conservation_percentage": conservation_percentage,
            "gap_percentage": gap_percentage,
            "average_identity": self._calculate_average_identity(aligned_sequences)
        }
    
    def _calculate_average_identity(self, aligned_sequences: List[Dict]) -> float:
        """Calculate average pairwise identity"""
        if len(aligned_sequences) < 2:
            return 100.0
        
        total_identity = 0
        comparisons = 0
        
        for i in range(len(aligned_sequences)):
            for j in range(i + 1, len(aligned_sequences)):
                seq1 = aligned_sequences[i]["sequence"]
                seq2 = aligned_sequences[j]["sequence"]
                
                matches = sum(1 for a, b in zip(seq1, seq2) if a == b and a != '-')
                total_length = len([1 for a, b in zip(seq1, seq2) if a != '-' or b != '-'])
                
                if total_length > 0:
                    identity = (matches / total_length) * 100
                    total_identity += identity
                    comparisons += 1
        
        return total_identity / comparisons if comparisons > 0 else 0.0
    
    # Mock implementations for when Docker is unavailable
    async def execute_phylogenetic_analysis(self, alignment_file: str, method: str = "iqtree",
                                          parameters: Dict = None) -> Dict:
        """Execute phylogenetic tree construction (mock for now)"""
        if parameters is None:
            parameters = {"model": "AUTO", "bootstrap": 1000}
        
        # Mock phylogenetic tree
        import random
        
        # Extract sequence names from alignment
        seq_names = []
        for line in alignment_file.split('\n'):
            if line.startswith('>'):
                seq_names.append(line[1:].split()[0])
        
        # Generate mock Newick tree
        if len(seq_names) >= 2:
            if len(seq_names) == 2:
                newick_tree = f"({seq_names[0]}:0.1,{seq_names[1]}:0.1);"
            else:
                # Simple mock tree structure
                newick_tree = f"(({seq_names[0]}:0.1,{seq_names[1]}:0.1):0.05,{seq_names[2] if len(seq_names) > 2 else 'seq_3'}:0.15);"
        else:
            newick_tree = "(single_sequence:0.0);"
        
        return {
            "newick_tree": newick_tree,
            "method": f"{method} (mock)",
            "parameters": parameters,
            "log_file": f"Mock {method} execution completed successfully"
        }
    
    async def execute_gene_prediction(self, sequence: str, organism_type: str = "bacteria",
                                    parameters: Dict = None) -> Dict:
        """Execute gene prediction (mock for now)"""
        if parameters is None:
            parameters = {"mode": "single" if len(sequence) < 20000 else "meta"}
        
        # Mock gene prediction results
        import random
        
        genes = []
        proteins = []
        
        # Generate mock genes (roughly 1 gene per 1000 bp)
        seq_length = len(sequence)
        num_genes = max(1, seq_length // 1000)
        
        for i in range(num_genes):
            start = random.randint(i * 1000, (i + 1) * 1000 - 300)
            length = random.randint(300, 1500)
            end = min(start + length, seq_length)
            strand = random.choice(['+', '-'])
            
            gene = {
                "seqid": "genome",
                "source": "prodigal",
                "type": "CDS",
                "start": start,
                "end": end,
                "score": random.uniform(10, 100),
                "strand": strand,
                "phase": "0",
                "attributes": {
                    "ID": f"gene_{i+1}",
                    "partial": "00",
                    "start_type": "ATG"
                }
            }
            genes.append(gene)
            
            # Mock protein sequence
            protein_length = (end - start) // 3
            protein_seq = ''.join(random.choices('ACDEFGHIKLMNPQRSTVWY', k=protein_length))
            proteins.append({
                "id": f"protein_{i+1}",
                "sequence": protein_seq,
                "length": len(protein_seq)
            })
        
        return {
            "predicted_genes": genes,
            "predicted_proteins": proteins,
            "statistics": {
                "total_genes": len(genes),
                "total_proteins": len(proteins),
                "average_gene_length": sum(g["end"] - g["start"] for g in genes) / len(genes) if genes else 0
            },
            "parameters": parameters,
            "method": "mock"
        }
    
    async def execute_domain_search(self, protein_sequences: List[str], 
                                  database: str = "pfam", parameters: Dict = None) -> Dict:
        """Execute protein domain search (mock for now)"""
        if parameters is None:
            parameters = {"evalue": "1e-3", "domtblout": True}
        
        # Mock domain search results
        import random
        
        domains = []
        domain_families = ['PF00001', 'PF00002', 'PF00003', 'PF00004', 'PF00005']
        
        for i, protein_seq in enumerate(protein_sequences):
            # Generate 1-3 domains per protein
            num_domains = random.randint(1, 3)
            
            for j in range(num_domains):
                domain_start = random.randint(1, max(1, len(protein_seq) - 100))
                domain_end = min(domain_start + random.randint(50, 200), len(protein_seq))
                
                domains.append({
                    "target_name": random.choice(domain_families),
                    "accession": f"{random.choice(domain_families)}.1",
                    "query_name": f"protein_{i}",
                    "full_sequence_evalue": random.uniform(1e-10, 1e-3),
                    "full_sequence_score": random.uniform(20, 100),
                    "domain_evalue": random.uniform(1e-8, 1e-2),
                    "domain_score": random.uniform(15, 80),
                    "hmm_from": random.randint(1, 50),
                    "hmm_to": random.randint(100, 300),
                    "ali_from": domain_start,
                    "ali_to": domain_end,
                    "description": f"Mock domain family {j+1}"
                })
        
        return {
            "domains": domains,
            "database": database,
            "parameters": parameters,
            "statistics": {
                "total_domains": len(domains),
                "unique_families": len(set(d["target_name"] for d in domains))
            },
            "method": "mock"
        }