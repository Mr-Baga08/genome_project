# backend/app/services/analysis_tools.py - FIXED VERSION
import random
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class AnalysisToolsService:
    """Service for bioinformatics analysis tools with lazy Docker initialization"""
    
    def __init__(self):
        self.docker_client = None
        self._docker_available = None
    
    def _init_docker_client(self):
        """Lazy initialization of Docker client"""
        if self.docker_client is None:
            try:
                import docker
                self.docker_client = docker.from_env(timeout=10)
                # Test connection
                self.docker_client.ping()
                self._docker_available = True
                logger.info("Docker client initialized successfully")
            except Exception as e:
                logger.warning(f"Docker client initialization failed: {str(e)}")
                logger.warning("Falling back to mock analysis results")
                self.docker_client = None
                self._docker_available = False
    
    def _is_docker_available(self) -> bool:
        """Check if Docker is available"""
        if self._docker_available is None:
            self._init_docker_client()
        return self._docker_available
    
    async def run_blast_search(self, sequences: List[str], database: str, parameters: Dict = None) -> Dict:
        """Execute BLAST search using BioContainers or mock results"""
        if parameters is None:
            parameters = {"evalue": "1e-5", "max_hits": 10}
        
        if self._is_docker_available():
            return await self._run_blast_with_docker(sequences, database, parameters)
        else:
            return await self._run_blast_mock(sequences, database, parameters)
    
    async def _run_blast_with_docker(self, sequences: List[str], database: str, parameters: Dict) -> Dict:
        """Run BLAST using Docker containers"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Write query sequences
                query_file = temp_path / "query.fasta"
                with open(query_file, 'w') as f:
                    for i, sequence in enumerate(sequences):
                        f.write(f">query_{i}\n{sequence}\n")
                
                # Prepare output file
                output_file = temp_path / "blast_results.txt"
                
                # Determine BLAST program based on sequence type
                blast_program = "blastn" if self._is_nucleotide(sequences[0]) else "blastp"
                
                # Build BLAST command
                blast_cmd = [
                    blast_program,
                    "-query", "/data/query.fasta",
                    "-db", f"/databases/{database}",
                    "-out", "/data/blast_results.txt",
                    "-outfmt", "6",
                    "-evalue", str(parameters.get("evalue", "1e-5")),
                    "-max_target_seqs", str(parameters.get("max_hits", 10))
                ]
                
                # Execute in container
                container = self.docker_client.containers.run(
                    "biocontainers/blast:2.12.0_cv1",
                    command=" ".join(blast_cmd),
                    volumes={
                        str(temp_path): {"bind": "/data", "mode": "rw"},
                        "/opt/blast_databases": {"bind": "/databases", "mode": "ro"}
                    },
                    detach=True,
                    remove=True,
                    mem_limit="1g"
                )
                
                # Wait for completion
                result = container.wait()
                logs = container.logs().decode('utf-8')
                
                if result['StatusCode'] == 0 and output_file.exists():
                    results = self._parse_blast_results(output_file)
                    return {
                        "results": results,
                        "parameters": parameters,
                        "database": database,
                        "method": "docker"
                    }
                else:
                    logger.warning(f"BLAST container failed, falling back to mock: {logs}")
                    return await self._run_blast_mock(sequences, database, parameters)
                    
        except Exception as e:
            logger.error(f"BLAST Docker execution failed: {str(e)}")
            return await self._run_blast_mock(sequences, database, parameters)
    
    async def _run_blast_mock(self, sequences: List[str], database: str, parameters: Dict) -> Dict:
        """Mock BLAST results when Docker is unavailable"""
        results = []
        for i, sequence in enumerate(sequences):
            hits = []
            for j in range(min(int(parameters.get("max_hits", 10)), 5)):
                hits.append({
                    "hit_id": f"hit_{i}_{j}",
                    "accession": f"NP_{random.randint(100000, 999999)}",
                    "description": f"Hypothetical protein {random.randint(1, 1000)} [mock organism]",
                    "score": random.uniform(50, 200),
                    "evalue": random.uniform(1e-10, float(parameters.get("evalue", "1e-5"))),
                    "identity": random.uniform(0.3, 0.95),
                    "length": random.randint(100, 500),
                    "query_start": 1,
                    "query_end": len(sequence),
                    "subject_start": random.randint(1, 50),
                    "subject_end": random.randint(len(sequence) - 50, len(sequence))
                })
            
            results.append({
                "query_id": f"seq_{i}",
                "hits": hits
            })
        
        return {
            "results": results,
            "parameters": parameters,
            "database": database,
            "method": "mock"
        }
    
    async def run_multiple_alignment(self, sequences: List[Dict], method: str = "muscle", parameters: Dict = None) -> Dict:
        """Execute multiple sequence alignment"""
        if parameters is None:
            parameters = {"gap_penalty": -10}
        
        if self._is_docker_available():
            return await self._run_alignment_with_docker(sequences, method, parameters)
        else:
            return await self._run_alignment_mock(sequences, method, parameters)
    
    async def _run_alignment_with_docker(self, sequences: List[Dict], method: str, parameters: Dict) -> Dict:
        """Run alignment using Docker containers"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Write input sequences
                input_file = temp_path / "sequences.fasta"
                with open(input_file, 'w') as f:
                    for i, seq in enumerate(sequences):
                        seq_id = seq.get('id', f'seq_{i}')
                        sequence = seq.get('sequence', '')
                        f.write(f">{seq_id}\n{sequence}\n")
                
                # Prepare output file
                output_file = temp_path / "alignment.fasta"
                
                # Build command based on method
                tool_images = {
                    "muscle": "biocontainers/muscle:3.8.31_cv2",
                    "clustalw": "biocontainers/clustalw:2.1_cv1",
                    "mafft": "biocontainers/mafft:7.471_cv1"
                }
                
                if method == "muscle":
                    cmd = "muscle -in /data/sequences.fasta -out /data/alignment.fasta"
                elif method == "clustalw":
                    cmd = "clustalw2 -infile=/data/sequences.fasta -outfile=/data/alignment.fasta -output=FASTA"
                elif method == "mafft":
                    cmd = "mafft --auto /data/sequences.fasta > /data/alignment.fasta"
                else:
                    raise ValueError(f"Unsupported alignment method: {method}")
                
                # Execute in container
                container = self.docker_client.containers.run(
                    tool_images[method],
                    command=cmd,
                    volumes={str(temp_path): {"bind": "/data", "mode": "rw"}},
                    detach=True,
                    remove=True,
                    mem_limit="1g"
                )
                
                result = container.wait()
                logs = container.logs().decode('utf-8')
                
                if result['StatusCode'] == 0 and output_file.exists():
                    aligned_sequences = self._parse_fasta_file(output_file)
                    alignment_stats = self._calculate_alignment_stats(aligned_sequences)
                    
                    return {
                        "aligned_sequences": aligned_sequences,
                        "alignment_stats": alignment_stats,
                        "method": method,
                        "parameters": parameters
                    }
                else:
                    logger.warning(f"{method} container failed, falling back to mock: {logs}")
                    return await self._run_alignment_mock(sequences, method, parameters)
                    
        except Exception as e:
            logger.error(f"{method} Docker execution failed: {str(e)}")
            return await self._run_alignment_mock(sequences, method, parameters)
    
    async def _run_alignment_mock(self, sequences: List[Dict], method: str, parameters: Dict) -> Dict:
        """Mock alignment results when Docker is unavailable"""
        aligned_sequences = []
        max_length = max(len(seq.get('sequence', '')) for seq in sequences) if sequences else 0
        
        for i, seq in enumerate(sequences):
            original_seq = seq.get('sequence', '')
            # Simulate alignment by padding with gaps
            gaps_to_add = max_length - len(original_seq)
            gap_positions = [random.randint(0, len(original_seq)) for _ in range(gaps_to_add // 4)]
            
            aligned_seq = original_seq
            for pos in sorted(gap_positions, reverse=True):
                aligned_seq = aligned_seq[:pos] + '-' + aligned_seq[pos:]
            
            aligned_seq = aligned_seq.ljust(max_length, '-')
            
            aligned_sequences.append({
                "id": seq.get('id', f'seq_{i}'),
                "sequence": aligned_seq,
                "original_length": len(original_seq),
                "aligned_length": len(aligned_seq)
            })
        
        return {
            "aligned_sequences": aligned_sequences,
            "alignment_stats": self._calculate_alignment_stats(aligned_sequences),
            "method": f"{method} (mock)",
            "parameters": parameters
        }
    
    def _calculate_alignment_stats(self, aligned_sequences: List[Dict]) -> Dict:
        """Calculate alignment statistics"""
        if not aligned_sequences:
            return {}
        
        alignment_length = len(aligned_sequences[0]["sequence"])
        num_sequences = len(aligned_sequences)
        
        # Calculate conservation and gaps
        total_gaps = 0
        conserved_positions = 0
        
        for pos in range(alignment_length):
            column = [seq["sequence"][pos] for seq in aligned_sequences]
            gaps = column.count('-')
            total_gaps += gaps
            
            # Position is conserved if all non-gap characters are the same
            non_gaps = [c for c in column if c != '-']
            if non_gaps and len(set(non_gaps)) == 1:
                conserved_positions += 1
        
        gap_percentage = (total_gaps / (alignment_length * num_sequences)) * 100
        conservation_percentage = (conserved_positions / alignment_length) * 100
        
        return {
            "alignment_length": alignment_length,
            "num_sequences": num_sequences,
            "conserved_positions": conserved_positions,
            "conservation_percentage": conservation_percentage,
            "gap_percentage": gap_percentage,
            "average_conservation": conservation_percentage
        }
    
    def _parse_blast_results(self, results_file: Path) -> List[Dict]:
        """Parse BLAST tabular results"""
        results = []
        
        try:
            with open(results_file, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    
                    fields = line.strip().split('\t')
                    if len(fields) >= 12:
                        results.append({
                            "query_id": fields[0],
                            "subject_id": fields[1],
                            "identity": float(fields[2]) / 100.0,
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
    
    def _is_nucleotide(self, sequence: str) -> bool:
        """Check if sequence is nucleotide (DNA/RNA)"""
        if not sequence:
            return True
        
        nucleotide_chars = set('ATCGUN')
        seq_chars = set(sequence.upper())
        nucleotide_ratio = len(seq_chars.intersection(nucleotide_chars)) / len(seq_chars)
        return nucleotide_ratio > 0.8