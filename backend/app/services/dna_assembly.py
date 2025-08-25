# backend/app/services/dna_assembly.py
import asyncio
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter
import docker
from fastapi import HTTPException
import random
import statistics

class DNAAssemblyService:
    """Service for DNA assembly operations"""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except:
            self.docker_client = None
    
    async def assembler_1(self, reads: List[Dict], parameters: Dict = None) -> Dict:
        """Overlap-layout-consensus assembly algorithm"""
        try:
            if parameters is None:
                parameters = {"min_overlap": 20, "min_identity": 0.95, "min_contig_length": 100}
            
            # Extract sequences from reads
            sequences = []
            for read in reads:
                if isinstance(read, dict):
                    if 'sequence' in read:
                        sequences.append(read['sequence'])
                    elif 'r1' in read and 'r2' in read:  # Paired-end
                        sequences.append(read['r1']['sequence'])
                        sequences.append(read['r2']['sequence'])
                else:
                    sequences.append(str(read))
            
            contigs = []
            used_reads = set()
            
            for i, seq1 in enumerate(sequences):
                if i in used_reads:
                    continue
                    
                contig_sequence = seq1
                current_reads = [i]
                
                # Find overlapping reads
                extended = True
                while extended:
                    extended = False
                    for j, seq2 in enumerate(sequences):
                        if j in used_reads or j in current_reads:
                            continue
                        
                        # Check for overlap at the end
                        overlap = self._find_overlap(
                            contig_sequence, seq2, parameters['min_overlap']
                        )
                        
                        if overlap >= parameters['min_overlap']:
                            # Extend contig
                            contig_sequence = contig_sequence + seq2[overlap:]
                            current_reads.append(j)
                            extended = True
                            break
                        
                        # Check for overlap at the beginning
                        overlap = self._find_overlap(
                            seq2, contig_sequence, parameters['min_overlap']
                        )
                        
                        if overlap >= parameters['min_overlap']:
                            # Prepend to contig
                            contig_sequence = seq2 + contig_sequence[overlap:]
                            current_reads.append(j)
                            extended = True
                            break
                
                # Mark reads as used
                for read_idx in current_reads:
                    used_reads.add(read_idx)
                
                # Only keep contigs above minimum length
                if len(contig_sequence) >= parameters.get('min_contig_length', 100):
                    contigs.append({
                        "id": f"contig_{len(contigs)+1}",
                        "sequence": contig_sequence,
                        "length": len(contig_sequence),
                        "coverage": len(current_reads),
                        "reads_used": current_reads,
                        "gc_content": self._calculate_gc_content(contig_sequence)
                    })
            
            return {
                "contigs": contigs,
                "stats": self._calculate_assembly_stats(contigs),
                "parameters": parameters,
                "algorithm": "overlap-layout-consensus",
                "input_reads": len(sequences),
                "reads_used": len(used_reads),
                "reads_unused": len(sequences) - len(used_reads)
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Assembly error: {str(e)}")

    async def assembler_2(self, reads: List[Dict], parameters: Dict = None) -> Dict:
        """Greedy k-mer based assembly algorithm"""
        try:
            if parameters is None:
                parameters = {"k_mer_size": 21, "min_coverage": 2, "min_contig_length": 100}
            
            # Extract sequences
            sequences = []
            for read in reads:
                if isinstance(read, dict):
                    if 'sequence' in read:
                        sequences.append(read['sequence'])
                    elif 'r1' in read and 'r2' in read:
                        sequences.append(read['r1']['sequence'])
                        sequences.append(read['r2']['sequence'])
                else:
                    sequences.append(str(read))
            
            # Build k-mer graph
            k = parameters['k_mer_size']
            k_mer_counts = Counter()
            
            # Count k-mers
            for sequence in sequences:
                for i in range(len(sequence) - k + 1):
                    k_mer = sequence[i:i+k]
                    k_mer_counts[k_mer] += 1
            
            # Filter by minimum coverage
            valid_k_mers = {kmer for kmer, count in k_mer_counts.items() if count >= parameters['min_coverage']}
            
            # Build overlap graph
            overlap_graph = defaultdict(list)
            for kmer in valid_k_mers:
                prefix = kmer[:-1]
                suffix = kmer[1:]
                
                # Find overlapping k-mers
                for other_kmer in valid_k_mers:
                    if kmer != other_kmer and suffix == other_kmer[:-1]:
                        overlap_graph[kmer].append(other_kmer)
            
            # Greedy assembly
            contigs = []
            used_k_mers = set()
            
            for k_mer in valid_k_mers:
                if k_mer in used_k_mers:
                    continue
                
                # Extend contig
                contig = self._extend_contig(k_mer, overlap_graph, used_k_mers)
                
                if len(contig) >= parameters.get('min_contig_length', 100):
                    contigs.append({
                        "id": f"contig_{len(contigs)+1}",
                        "sequence": contig,
                        "length": len(contig),
                        "algorithm": "greedy-k-mer",
                        "k_mer_coverage": self._calculate_kmer_coverage(contig, k_mer_counts, k),
                        "gc_content": self._calculate_gc_content(contig)
                    })
            
            return {
                "contigs": contigs,
                "stats": self._calculate_assembly_stats(contigs),
                "parameters": parameters,
                "algorithm": "greedy-k-mer",
                "k_mer_stats": {
                    "total_kmers": len(k_mer_counts),
                    "valid_kmers": len(valid_k_mers),
                    "used_kmers": len(used_k_mers)
                }
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"K-mer assembly error: {str(e)}")

    async def cap3_assembly(self, sequences: List[Dict], parameters: Dict = None) -> Dict:
        """CAP3 assembly algorithm using Docker container"""
        try:
            if parameters is None:
                parameters = {"overlap_length": 40, "overlap_percent_identity": 90}
            
            if not self.docker_client:
                raise HTTPException(status_code=500, detail="Docker not available for CAP3 assembly")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write sequences to FASTA file
                input_file = f"{temp_dir}/input.fasta"
                with open(input_file, 'w') as f:
                    for i, seq in enumerate(sequences):
                        seq_data = seq.get('sequence', '') if isinstance(seq, dict) else str(seq)
                        seq_id = seq.get('id', f'seq_{i}') if isinstance(seq, dict) else f'seq_{i}'
                        f.write(f">{seq_id}\n{seq_data}\n")
                
                # Run CAP3 in Docker container
                try:
                    container = self.docker_client.containers.run(
                        "biocontainers/cap3:latest",
                        command=f"cap3 /data/input.fasta -o {parameters['overlap_length']} -p {parameters['overlap_percent_identity']}",
                        volumes={temp_dir: {"bind": "/data", "mode": "rw"}},
                        detach=True,
                        remove=True
                    )
                    
                    # Wait for completion
                    result = container.wait()
                    logs = container.logs().decode('utf-8')
                    
                    # Parse results
                    contigs_file = f"{temp_dir}/input.fasta.cap.contigs"
                    singlets_file = f"{temp_dir}/input.fasta.cap.singlets"
                    
                    contigs = []
                    
                    # Read contigs if file exists
                    try:
                        with open(contigs_file, 'r') as f:
                            for record in SeqIO.parse(f, "fasta"):
                                contigs.append({
                                    "id": record.id,
                                    "sequence": str(record.seq),
                                    "length": len(record.seq),
                                    "type": "contig",
                                    "gc_content": self._calculate_gc_content(str(record.seq))
                                })
                    except FileNotFoundError:
                        pass
                    
                    # Read singlets if file exists
                    try:
                        with open(singlets_file, 'r') as f:
                            for record in SeqIO.parse(f, "fasta"):
                                contigs.append({
                                    "id": record.id,
                                    "sequence": str(record.seq),
                                    "length": len(record.seq),
                                    "type": "singlet",
                                    "gc_content": self._calculate_gc_content(str(record.seq))
                                })
                    except FileNotFoundError:
                        pass
                    
                    return {
                        "contigs": contigs,
                        "stats": self._calculate_assembly_stats(contigs),
                        "parameters": parameters,
                        "algorithm": "CAP3",
                        "logs": logs,
                        "input_sequences": len(sequences)
                    }
                    
                except docker.errors.DockerException as e:
                    # Fallback to simple assembly if Docker fails
                    return await self.assembler_1(sequences, parameters)
                    
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"CAP3 assembly error: {str(e)}")

    def _find_overlap(self, seq1: str, seq2: str, min_overlap: int) -> int:
        """Find overlap between two sequences"""
        max_overlap = 0
        
        # Check suffix of seq1 with prefix of seq2
        for i in range(min_overlap, min(len(seq1), len(seq2)) + 1):
            if seq1[-i:] == seq2[:i]:
                max_overlap = i
        
        return max_overlap
    
    def _extend_contig(self, start_kmer: str, overlap_graph: Dict, used_k_mers: set) -> str:
        """Extend contig from starting k-mer using overlap graph"""
        contig = start_kmer
        used_k_mers.add(start_kmer)
        
        # Extend forward
        current_kmer = start_kmer
        while current_kmer in overlap_graph:
            next_kmers = [k for k in overlap_graph[current_kmer] if k not in used_k_mers]
            if not next_kmers:
                break
            
            # Choose the k-mer with highest coverage (simplified: just take first)
            next_kmer = next_kmers[0]
            contig += next_kmer[-1]  # Add the last character
            used_k_mers.add(next_kmer)
            current_kmer = next_kmer
        
        return contig
    
    def _calculate_assembly_stats(self, contigs: List[Dict]) -> Dict:
        """Calculate comprehensive assembly statistics"""
        if not contigs:
            return {"error": "No contigs generated"}
        
        lengths = [contig['length'] for contig in contigs]
        total_length = sum(lengths)
        
        # Calculate N50
        n50 = self._calculate_n50(sorted(lengths, reverse=True), total_length)
        
        # Calculate L50 (number of contigs contributing to N50)
        l50 = self._calculate_l50(sorted(lengths, reverse=True), total_length)
        
        # GC content statistics
        gc_contents = [contig.get('gc_content', 0) for contig in contigs if contig.get('gc_content') is not None]
        
        stats = {
            "num_contigs": len(contigs),
            "total_length": total_length,
            "largest_contig": max(lengths),
            "smallest_contig": min(lengths),
            "mean_length": total_length / len(contigs),
            "median_length": statistics.median(lengths),
            "n50": n50,
            "l50": l50,
            "n90": self._calculate_n90(sorted(lengths, reverse=True), total_length)
        }
        
        if gc_contents:
            stats["gc_content"] = {
                "mean": statistics.mean(gc_contents),
                "median": statistics.median(gc_contents),
                "min": min(gc_contents),
                "max": max(gc_contents)
            }
        
        return stats
    
    def _calculate_n50(self, lengths: List[int], total_length: int) -> int:
        """Calculate N50 statistic"""
        target = total_length / 2
        cumulative = 0
        for length in lengths:
            cumulative += length
            if cumulative >= target:
                return length
        return 0
    
    def _calculate_l50(self, lengths: List[int], total_length: int) -> int:
        """Calculate L50 statistic (number of contigs in N50)"""
        target = total_length / 2
        cumulative = 0
        for i, length in enumerate(lengths):
            cumulative += length
            if cumulative >= target:
                return i + 1
        return len(lengths)
    
    def _calculate_n90(self, lengths: List[int], total_length: int) -> int:
        """Calculate N90 statistic"""
        target = total_length * 0.9
        cumulative = 0
        for length in lengths:
            cumulative += length
            if cumulative >= target:
                return length
        return 0
    
    def _calculate_gc_content(self, sequence: str) -> float:
        """Calculate GC content"""
        if not sequence:
            return 0.0
        gc_count = sequence.upper().count('G') + sequence.upper().count('C')
        return (gc_count / len(sequence)) * 100
    
    def _calculate_kmer_coverage(self, contig: str, kmer_counts: Counter, k: int) -> float:
        """Calculate average k-mer coverage for a contig"""
        if len(contig) < k:
            return 0.0
        
        total_coverage = 0
        kmer_count = 0
        
        for i in range(len(contig) - k + 1):
            kmer = contig[i:i+k]
            total_coverage += kmer_counts.get(kmer, 0)
            kmer_count += 1
        
        return total_coverage / kmer_count if kmer_count > 0 else 0.0

    async def spades_assembly(self, reads: List[Dict], parameters: Dict = None) -> Dict:
        """SPAdes assembly using Docker container"""
        try:
            if parameters is None:
                parameters = {"k_list": "21,33,55", "careful": True}
            
            if not self.docker_client:
                # Fallback to simple assembly
                return await self.assembler_2(reads, parameters)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Prepare input files
                pe_reads = []
                se_reads = []
                
                for read in reads:
                    if isinstance(read, dict):
                        if 'r1' in read and 'r2' in read:
                            pe_reads.append(read)
                        elif 'sequence' in read:
                            se_reads.append(read)
                
                # Write paired-end reads
                if pe_reads:
                    r1_file = f"{temp_dir}/reads_R1.fastq"
                    r2_file = f"{temp_dir}/reads_R2.fastq"
                    
                    with open(r1_file, 'w') as f1, open(r2_file, 'w') as f2:
                        for read in pe_reads:
                            r1_data = read['r1']
                            r2_data = read['r2']
                            
                            f1.write(f"@{r1_data['id']}\n{r1_data['sequence']}\n+\n")
                            f1.write("I" * len(r1_data['sequence']) + "\n")  # Mock quality
                            
                            f2.write(f"@{r2_data['id']}\n{r2_data['sequence']}\n+\n")
                            f2.write("I" * len(r2_data['sequence']) + "\n")  # Mock quality
                
                # Write single-end reads
                if se_reads:
                    se_file = f"{temp_dir}/reads_SE.fastq"
                    with open(se_file, 'w') as f:
                        for read in se_reads:
                            seq_data = read.get('sequence', '')
                            seq_id = read.get('id', f'read_{len(se_reads)}')
                            f.write(f"@{seq_id}\n{seq_data}\n+\n")
                            f.write("I" * len(seq_data) + "\n")  # Mock quality
                
                # Build SPAdes command
                spades_cmd = ["spades.py", "-o", "/data/output"]
                
                if pe_reads:
                    spades_cmd.extend(["-1", "/data/reads_R1.fastq", "-2", "/data/reads_R2.fastq"])
                if se_reads:
                    spades_cmd.extend(["-s", "/data/reads_SE.fastq"])
                
                spades_cmd.extend(["-k", parameters["k_list"]])
                
                if parameters.get("careful"):
                    spades_cmd.append("--careful")
                
                try:
                    # Run SPAdes
                    container = self.docker_client.containers.run(
                        "quay.io/biocontainers/spades:3.15.3--h95f258a_0",
                        command=" ".join(spades_cmd),
                        volumes={temp_dir: {"bind": "/data", "mode": "rw"}},
                        detach=True,
                        remove=True
                    )
                    
                    result = container.wait()
                    logs = container.logs().decode('utf-8')
                    
                    # Parse assembly results
                    contigs_file = f"{temp_dir}/output/contigs.fasta"
                    contigs = []
                    
                    try:
                        from Bio import SeqIO
                        for record in SeqIO.parse(contigs_file, "fasta"):
                            contigs.append({
                                "id": record.id,
                                "sequence": str(record.seq),
                                "length": len(record.seq),
                                "gc_content": self._calculate_gc_content(str(record.seq)),
                                "algorithm": "SPAdes"
                            })
                    except FileNotFoundError:
                        # No contigs generated, fallback
                        pass
                    
                    return {
                        "contigs": contigs,
                        "stats": self._calculate_assembly_stats(contigs),
                        "parameters": parameters,
                        "algorithm": "SPAdes",
                        "logs": logs
                    }
                    
                except docker.errors.DockerException:
                    # Fallback to k-mer assembly
                    return await self.assembler_2(reads, parameters)
                    
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"SPAdes assembly error: {str(e)}")

    async def evaluate_assembly_quality(self, contigs: List[Dict], reference_sequences: List[Dict] = None) -> Dict:
        """Evaluate assembly quality metrics"""
        try:
            if not contigs:
                return {"error": "No contigs to evaluate"}
            
            quality_metrics = {
                "basic_stats": self._calculate_assembly_stats(contigs),
                "contiguity": self._calculate_contiguity_metrics(contigs),
                "completeness": self._estimate_completeness(contigs),
                "correctness": {}
            }
            
            # If reference sequences provided, calculate correctness
            if reference_sequences:
                quality_metrics["correctness"] = await self._calculate_correctness(contigs, reference_sequences)
            
            return quality_metrics
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error evaluating assembly: {str(e)}")

    def _calculate_contiguity_metrics(self, contigs: List[Dict]) -> Dict:
        """Calculate contiguity metrics"""
        lengths = [contig['length'] for contig in contigs]
        total_length = sum(lengths)
        
        return {
            "total_contigs": len(contigs),
            "largest_contig": max(lengths) if lengths else 0,
            "contig_n50": self._calculate_n50(sorted(lengths, reverse=True), total_length),
            "contig_l50": self._calculate_l50(sorted(lengths, reverse=True), total_length),
            "gaps": len(contigs) - 1 if len(contigs) > 1 else 0
        }

    def _estimate_completeness(self, contigs: List[Dict]) -> Dict:
        """Estimate assembly completeness (simplified)"""
        total_length = sum(contig['length'] for contig in contigs)
        
        # Simple heuristics for completeness estimation
        return {
            "total_assembled_length": total_length,
            "estimated_coverage": "unknown",  # Would need more data
            "contig_distribution": {
                "short_contigs": len([c for c in contigs if c['length'] < 1000]),
                "medium_contigs": len([c for c in contigs if 1000 <= c['length'] < 10000]),
                "long_contigs": len([c for c in contigs if c['length'] >= 10000])
            }
        }

    async def _calculate_correctness(self, contigs: List[Dict], reference_sequences: List[Dict]) -> Dict:
        """Calculate assembly correctness by comparing to reference"""
        try:
            # Simplified correctness calculation
            # In reality, this would use sophisticated alignment algorithms
            
            total_aligned = 0
            total_mismatches = 0
            
            for contig in contigs:
                # Find best matching reference
                best_match = None
                best_score = 0
                
                for ref in reference_sequences:
                    score = self._simple_alignment_score(contig['sequence'], ref.get('sequence', ''))
                    if score > best_score:
                        best_score = score
                        best_match = ref
                
                if best_match:
                    total_aligned += 1
                    # Calculate mismatches (simplified)
                    mismatches = self._count_mismatches(contig['sequence'], best_match['sequence'])
                    total_mismatches += mismatches
            
            return {
                "aligned_contigs": total_aligned,
                "total_contigs": len(contigs),
                "alignment_rate": total_aligned / len(contigs) if contigs else 0,
                "estimated_accuracy": max(0, 1 - (total_mismatches / sum(c['length'] for c in contigs))) if contigs else 0
            }
        except Exception as e:
            return {"error": f"Error calculating correctness: {str(e)}"}

    def _simple_alignment_score(self, seq1: str, seq2: str) -> float:
        """Simple alignment scoring (placeholder)"""
        # Simplified: count matching k-mers
        k = 10
        if len(seq1) < k or len(seq2) < k:
            return 0.0
        
        kmers1 = set(seq1[i:i+k] for i in range(len(seq1) - k + 1))
        kmers2 = set(seq2[i:i+k] for i in range(len(seq2) - k + 1))
        
        intersection = len(kmers1.intersection(kmers2))
        union = len(kmers1.union(kmers2))
        
        return intersection / union if union > 0 else 0.0

    def _count_mismatches(self, seq1: str, seq2: str) -> int:
        """Count mismatches between two sequences"""
        min_len = min(len(seq1), len(seq2))
        return sum(1 for i in range(min_len) if seq1[i] != seq2[i])