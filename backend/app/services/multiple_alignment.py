# backend/app/services/multiple_alignment.py
import asyncio
import subprocess
import tempfile
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class AlignmentResult:
    """Result of multiple sequence alignment"""
    aligned_sequences: List[Dict[str, str]]
    alignment_length: int
    method_used: str
    parameters: Dict[str, Any]
    quality_metrics: Dict[str, float]
    execution_time: float

class MultipleAlignmentService:
    """Service for multiple sequence alignment using various algorithms"""
    
    def __init__(self):
        self.supported_methods = {
            'muscle': {
                'description': 'MUSCLE - Multiple Sequence Comparison by Log-Expectation',
                'suitable_for': 'General purpose, medium to large datasets',
                'parameters': ['gap_open', 'gap_extend', 'max_iterations']
            },
            'clustalw': {
                'description': 'ClustalW - Progressive alignment algorithm',
                'suitable_for': 'Small to medium datasets, well-studied',
                'parameters': ['gap_open', 'gap_extend', 'protein_matrix']
            },
            'mafft': {
                'description': 'MAFFT - Multiple Alignment using Fast Fourier Transform',
                'suitable_for': 'Large datasets, high accuracy',
                'parameters': ['strategy', 'gap_open', 'gap_extend']
            },
            'simple_progressive': {
                'description': 'Simple progressive alignment (built-in implementation)',
                'suitable_for': 'Small datasets, educational purposes',
                'parameters': ['gap_penalty', 'match_score', 'mismatch_penalty']
            }
        }
        
        # Scoring matrices
        self.blosum62 = self._load_blosum62()
        self.pam250 = self._load_pam250()
    
    async def run_alignment(
        self, 
        sequences: List[Dict], 
        method: str = "muscle", 
        parameters: Dict = None
    ) -> Dict:
        """Run multiple sequence alignment using specified method"""
        
        if not sequences:
            return {"error": "No sequences provided"}
        
        if len(sequences) < 2:
            return {"error": "At least 2 sequences required for alignment"}
        
        if method not in self.supported_methods:
            return {"error": f"Unsupported alignment method: {method}. Supported: {list(self.supported_methods.keys())}"}
        
        if parameters is None:
            parameters = {}
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Route to appropriate alignment method
            if method == "simple_progressive":
                result = await self._run_simple_progressive_alignment(sequences, parameters)
            elif method in ["muscle", "clustalw", "mafft"]:
                result = await self._run_external_alignment(sequences, method, parameters)
            else:
                return {"error": f"Method {method} not implemented"}
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            # Calculate alignment quality metrics
            quality_metrics = await self._calculate_alignment_quality(result.aligned_sequences)
            
            return {
                "status": "success",
                "method": method,
                "parameters_used": parameters,
                "execution_time": execution_time,
                "results": {
                    "aligned_sequences": result.aligned_sequences,
                    "alignment_length": result.alignment_length,
                    "sequence_count": len(sequences),
                    "quality_metrics": quality_metrics
                }
            }
            
        except Exception as e:
            logger.error(f"Error in alignment: {str(e)}")
            return {"error": f"Alignment failed: {str(e)}"}
    
    async def _run_simple_progressive_alignment(self, sequences: List[Dict], parameters: Dict) -> AlignmentResult:
        """Run simple progressive alignment (built-in implementation)"""
        
        # Default parameters
        gap_penalty = parameters.get('gap_penalty', -2)
        match_score = parameters.get('match_score', 2)
        mismatch_penalty = parameters.get('mismatch_penalty', -1)
        
        # Extract sequence data
        seq_data = []
        for seq in sequences:
            seq_data.append({
                'id': seq.get('id', seq.get('name', 'unknown')),
                'name': seq.get('name', 'Unknown'),
                'sequence': seq.get('sequence', '').upper()
            })
        
        # Perform progressive alignment
        aligned_seqs = await self._progressive_alignment(seq_data, gap_penalty, match_score, mismatch_penalty)
        
        # Calculate alignment length
        alignment_length = max(len(seq['sequence']) for seq in aligned_seqs) if aligned_seqs else 0
        
        return AlignmentResult(
            aligned_sequences=aligned_seqs,
            alignment_length=alignment_length,
            method_used="simple_progressive",
            parameters=parameters,
            quality_metrics={},
            execution_time=0.0
        )
    
    async def _progressive_alignment(self, sequences: List[Dict], gap_penalty: int, match_score: int, mismatch_penalty: int) -> List[Dict]:
        """Implement simple progressive alignment algorithm"""
        
        if len(sequences) < 2:
            return sequences
        
        # Start with first two sequences
        aligned = [sequences[0], sequences[1]]
        aligned_seqs = await self._pairwise_alignment(
            sequences[0]['sequence'], 
            sequences[1]['sequence'],
            gap_penalty, match_score, mismatch_penalty
        )
        
        aligned[0]['sequence'] = aligned_seqs[0]
        aligned[1]['sequence'] = aligned_seqs[1]
        
        # Progressively add remaining sequences
        for i in range(2, len(sequences)):
            new_seq = sequences[i]
            
            # Align new sequence to existing alignment
            consensus = self._get_consensus_from_alignment([seq['sequence'] for seq in aligned])
            
            aligned_pair = await self._pairwise_alignment(
                consensus,
                new_seq['sequence'],
                gap_penalty, match_score, mismatch_penalty
            )
            
            # Insert gaps in existing alignment based on new alignment
            aligned = self._insert_gaps_in_alignment(aligned, aligned_pair[0])
            
            # Add new sequence
            aligned.append({
                'id': new_seq.get('id', new_seq.get('name', 'unknown')),
                'name': new_seq.get('name', 'Unknown'),
                'sequence': aligned_pair[1]
            })
        
        return aligned
    
    async def _pairwise_alignment(self, seq1: str, seq2: str, gap_penalty: int, match_score: int, mismatch_penalty: int) -> Tuple[str, str]:
        """Perform pairwise sequence alignment using dynamic programming"""
        
        len1, len2 = len(seq1), len(seq2)
        
        # Initialize scoring matrix
        score_matrix = [[0 for _ in range(len2 + 1)] for _ in range(len1 + 1)]
        
        # Initialize first row and column
        for i in range(1, len1 + 1):
            score_matrix[i][0] = i * gap_penalty
        for j in range(1, len2 + 1):
            score_matrix[0][j] = j * gap_penalty
        
        # Fill scoring matrix
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                match = score_matrix[i-1][j-1] + (match_score if seq1[i-1] == seq2[j-1] else mismatch_penalty)
                delete = score_matrix[i-1][j] + gap_penalty
                insert = score_matrix[i][j-1] + gap_penalty
                
                score_matrix[i][j] = max(match, delete, insert)
        
        # Traceback to get alignment
        aligned_seq1, aligned_seq2 = "", ""
        i, j = len1, len2
        
        while i > 0 or j > 0:
            if i > 0 and j > 0 and score_matrix[i][j] == score_matrix[i-1][j-1] + (match_score if seq1[i-1] == seq2[j-1] else mismatch_penalty):
                aligned_seq1 = seq1[i-1] + aligned_seq1
                aligned_seq2 = seq2[j-1] + aligned_seq2
                i -= 1
                j -= 1
            elif i > 0 and score_matrix[i][j] == score_matrix[i-1][j] + gap_penalty:
                aligned_seq1 = seq1[i-1] + aligned_seq1
                aligned_seq2 = "-" + aligned_seq2
                i -= 1
            else:
                aligned_seq1 = "-" + aligned_seq1
                aligned_seq2 = seq2[j-1] + aligned_seq2
                j -= 1
        
        return aligned_seq1, aligned_seq2
    
    def _get_consensus_from_alignment(self, aligned_sequences: List[str]) -> str:
        """Get consensus sequence from multiple aligned sequences"""
        if not aligned_sequences:
            return ""
        
        length = len(aligned_sequences[0])
        consensus = ""
        
        for pos in range(length):
            chars = [seq[pos] for seq in aligned_sequences if pos < len(seq)]
            if chars:
                # Most common character (excluding gaps)
                non_gap_chars = [c for c in chars if c != '-']
                if non_gap_chars:
                    consensus += max(set(non_gap_chars), key=non_gap_chars.count)
                else:
                    consensus += '-'
            else:
                consensus += '-'
        
        return consensus
    
    def _insert_gaps_in_alignment(self, alignment: List[Dict], template: str) -> List[Dict]:
        """Insert gaps in existing alignment based on template sequence"""
        for seq_dict in alignment:
            old_seq = seq_dict['sequence']
            new_seq = ""
            old_index = 0
            
            for char in template:
                if char == '-':
                    new_seq += '-'
                else:
                    if old_index < len(old_seq):
                        new_seq += old_seq[old_index]
                        old_index += 1
                    else:
                        new_seq += '-'
            
            seq_dict['sequence'] = new_seq
        
        return alignment
    
    async def _run_external_alignment(self, sequences: List[Dict], method: str, parameters: Dict) -> AlignmentResult:
        """Run external alignment tool (MUSCLE, ClustalW, MAFFT)"""
        
        # In a production environment, this would use Docker containers
        # For now, implement a mock external tool execution
        
        logger.info(f"Mock execution of {method} alignment")
        
        # Extract sequences for mock alignment
        seq_strings = [seq.get('sequence', '') for seq in sequences]
        
        # Mock alignment by adding gaps randomly (for demonstration)
        aligned_sequences = []
        max_length = max(len(s) for s in seq_strings)
        
        for i, seq in enumerate(sequences):
            # Simple mock: just pad shorter sequences
            sequence_str = seq.get('sequence', '')
            padded_seq = sequence_str.ljust(max_length, '-')
            
            aligned_sequences.append({
                'id': seq.get('id', seq.get('name', f'seq_{i}')),
                'name': seq.get('name', f'Sequence {i+1}'),
                'sequence': padded_seq
            })
        
        return AlignmentResult(
            aligned_sequences=aligned_sequences,
            alignment_length=max_length,
            method_used=method,
            parameters=parameters,
            quality_metrics={},
            execution_time=0.0
        )
    
    async def _calculate_alignment_quality(self, aligned_sequences: List[Dict]) -> Dict[str, float]:
        """Calculate quality metrics for the alignment"""
        if not aligned_sequences:
            return {}
        
        sequences = [seq['sequence'] for seq in aligned_sequences]
        
        # Calculate conservation score
        conservation_score = self._calculate_conservation_score(sequences)
        
        # Calculate gap percentage
        gap_percentage = self._calculate_gap_percentage(sequences)
        
        # Calculate pairwise identity
        pairwise_identity = self._calculate_average_pairwise_identity(sequences)
        
        return {
            "conservation_score": conservation_score,
            "gap_percentage": gap_percentage,
            "average_pairwise_identity": pairwise_identity,
            "alignment_length": len(sequences[0]) if sequences else 0
        }
    
    def _calculate_conservation_score(self, sequences: List[str]) -> float:
        """Calculate conservation score across alignment"""
        if not sequences:
            return 0.0
        
        length = len(sequences[0])
        conserved_positions = 0
        
        for pos in range(length):
            chars = [seq[pos] for seq in sequences if pos < len(seq)]
            non_gap_chars = [c for c in chars if c != '-']
            
            if non_gap_chars:
                # Position is conserved if all non-gap characters are the same
                if len(set(non_gap_chars)) == 1:
                    conserved_positions += 1
        
        return conserved_positions / length if length > 0 else 0.0
    
    def _calculate_gap_percentage(self, sequences: List[str]) -> float:
        """Calculate percentage of positions that are gaps"""
        if not sequences:
            return 0.0
        
        total_positions = sum(len(seq) for seq in sequences)
        gap_positions = sum(seq.count('-') for seq in sequences)
        
        return (gap_positions / total_positions * 100) if total_positions > 0 else 0.0
    
    def _calculate_average_pairwise_identity(self, sequences: List[str]) -> float:
        """Calculate average pairwise sequence identity"""
        if len(sequences) < 2:
            return 100.0
        
        identities = []
        
        for i in range(len(sequences)):
            for j in range(i + 1, len(sequences)):
                identity = self._calculate_pairwise_identity(sequences[i], sequences[j])
                identities.append(identity)
        
        return sum(identities) / len(identities) if identities else 0.0
    
    def _calculate_pairwise_identity(self, seq1: str, seq2: str) -> float:
        """Calculate pairwise sequence identity"""
        if len(seq1) != len(seq2):
            min_len = min(len(seq1), len(seq2))
            seq1, seq2 = seq1[:min_len], seq2[:min_len]
        
        if len(seq1) == 0:
            return 0.0
        
        matches = sum(1 for c1, c2 in zip(seq1, seq2) if c1 == c2 and c1 != '-')
        non_gap_positions = sum(1 for c1, c2 in zip(seq1, seq2) if c1 != '-' or c2 != '-')
        
        return (matches / non_gap_positions * 100) if non_gap_positions > 0 else 0.0
    
    async def validate_alignment_input(self, sequences: List[Dict]) -> Dict:
        """Validate input sequences for alignment"""
        if not sequences:
            return {"valid": False, "errors": ["No sequences provided"]}
        
        if len(sequences) < 2:
            return {"valid": False, "errors": ["At least 2 sequences required"]}
        
        errors = []
        warnings = []
        
        # Check sequence validity
        for i, seq in enumerate(sequences):
            sequence_str = seq.get('sequence', '')
            
            if not sequence_str:
                errors.append(f"Sequence {i+1} is empty")
                continue
            
            # Check for invalid characters
            valid_chars = set('ACGTRYKMSWBDHVN-')  # Including ambiguous nucleotides
            invalid_chars = set(sequence_str.upper()) - valid_chars
            if invalid_chars:
                errors.append(f"Sequence {i+1} contains invalid characters: {invalid_chars}")
            
            # Check sequence length
            if len(sequence_str) < 10:
                warnings.append(f"Sequence {i+1} is very short ({len(sequence_str)} bp)")
            
            if len(sequence_str) > 10000:
                warnings.append(f"Sequence {i+1} is very long ({len(sequence_str)} bp) - alignment may be slow")
        
        # Check sequence type consistency
        sequence_types = set()
        for seq in sequences:
            seq_type = self._detect_sequence_type(seq.get('sequence', ''))
            sequence_types.add(seq_type)
        
        if len(sequence_types) > 1:
            warnings.append(f"Mixed sequence types detected: {sequence_types}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "sequence_count": len(sequences),
            "detected_type": list(sequence_types)[0] if len(sequence_types) == 1 else "mixed"
        }
    
    def _detect_sequence_type(self, sequence: str) -> str:
        """Detect if sequence is DNA, RNA, or protein"""
        sequence = sequence.upper()
        
        dna_chars = set('ATCG')
        rna_chars = set('AUCG') 
        protein_chars = set('ACDEFGHIKLMNPQRSTVWY')
        
        seq_chars = set(sequence)
        
        if seq_chars.issubset(dna_chars):
            return 'DNA'
        elif seq_chars.issubset(rna_chars):
            return 'RNA'
        elif seq_chars.issubset(protein_chars):
            return 'PROTEIN'
        else:
            return 'UNKNOWN'
    
    async def export_alignment(self, aligned_sequences: List[Dict], format_type: str = "fasta") -> str:
        """Export alignment in various formats"""
        
        if format_type == "fasta":
            return self._export_fasta(aligned_sequences)
        elif format_type == "clustal":
            return self._export_clustal(aligned_sequences)
        elif format_type == "phylip":
            return self._export_phylip(aligned_sequences)
        elif format_type == "stockholm":
            return self._export_stockholm(aligned_sequences)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_fasta(self, sequences: List[Dict]) -> str:
        """Export alignment in FASTA format"""
        fasta_lines = []
        for seq in sequences:
            fasta_lines.append(f">{seq['name']}")
            fasta_lines.append(seq['sequence'])
        return '\n'.join(fasta_lines)
    
    def _export_clustal(self, sequences: List[Dict]) -> str:
        """Export alignment in Clustal format"""
        clustal_lines = []
        clustal_lines.append("CLUSTAL W (1.83) multiple sequence alignment")
        clustal_lines.append("")
        
        # Calculate max name length for formatting
        max_name_len = max(len(seq['name']) for seq in sequences)
        
        # Split sequences into blocks of 60 characters
        seq_length = len(sequences[0]['sequence']) if sequences else 0
        block_size = 60
        
        for start in range(0, seq_length, block_size):
            for seq in sequences:
                name = seq['name'].ljust(max_name_len)
                sequence_block = seq['sequence'][start:start + block_size]
                clustal_lines.append(f"{name} {sequence_block}")
            
            # Add conservation line
            conservation = self._generate_conservation_line(
                [seq['sequence'][start:start + block_size] for seq in sequences]
            )
            clustal_lines.append(" " * (max_name_len + 1) + conservation)
            clustal_lines.append("")
        
        return '\n'.join(clustal_lines)
    
    def _export_phylip(self, sequences: List[Dict]) -> str:
        """Export alignment in PHYLIP format"""
        phylip_lines = []
        
        # Header line
        seq_count = len(sequences)
        seq_length = len(sequences[0]['sequence']) if sequences else 0
        phylip_lines.append(f"{seq_count} {seq_length}")
        
        # Sequence lines
        for seq in sequences:
            name = seq['name'][:10].ljust(10)  # PHYLIP name limit
            phylip_lines.append(f"{name} {seq['sequence']}")
        
        return '\n'.join(phylip_lines)
    
    def _export_stockholm(self, sequences: List[Dict]) -> str:
        """Export alignment in Stockholm format"""
        stockholm_lines = []
        stockholm_lines.append("# STOCKHOLM 1.0")
        stockholm_lines.append("")
        
        # Calculate max name length
        max_name_len = max(len(seq['name']) for seq in sequences)
        
        # Sequence lines
        for seq in sequences:
            name = seq['name'].ljust(max_name_len)
            stockholm_lines.append(f"{name} {seq['sequence']}")
        
        stockholm_lines.append("//")
        
        return '\n'.join(stockholm_lines)
    
    def _generate_conservation_line(self, sequence_blocks: List[str]) -> str:
        """Generate conservation line for Clustal format"""
        if not sequence_blocks:
            return ""
        
        conservation = ""
        block_length = len(sequence_blocks[0]) if sequence_blocks else 0
        
        for pos in range(block_length):
            chars = [block[pos] for block in sequence_blocks if pos < len(block)]
            non_gap_chars = [c for c in chars if c != '-']
            
            if len(set(non_gap_chars)) == 1 and non_gap_chars:
                conservation += "*"  # Fully conserved
            elif len(set(non_gap_chars)) <= 2 and non_gap_chars:
                conservation += ":"  # Strongly similar
            elif non_gap_chars:
                conservation += "."  # Weakly similar
            else:
                conservation += " "  # No conservation
        
        return conservation
    
    def _load_blosum62(self) -> Dict:
        """Load BLOSUM62 scoring matrix (simplified version)"""
        # Simplified BLOSUM62 matrix for demonstration
        return {
            ('A', 'A'): 4, ('A', 'R'): -1, ('A', 'N'): -2, ('A', 'D'): -2,
            ('R', 'R'): 5, ('R', 'N'): 0, ('R', 'D'): -2,
            ('N', 'N'): 6, ('N', 'D'): 1,
            ('D', 'D'): 6,
            # ... (full matrix would be much larger)
        }
    
    def _load_pam250(self) -> Dict:
        """Load PAM250 scoring matrix (simplified version)"""
        # Simplified PAM250 matrix for demonstration
        return {
            ('A', 'A'): 2, ('A', 'R'): -2, ('A', 'N'): 0, ('A', 'D'): 0,
            ('R', 'R'): 6, ('R', 'N'): 0, ('R', 'D'): -1,
            ('N', 'N'): 2, ('N', 'D'): 2,
            ('D', 'D'): 4,
            # ... (full matrix would be much larger)
        }
    
    async def get_alignment_recommendations(self, sequences: List[Dict]) -> Dict:
        """Get recommendations for alignment method and parameters"""
        
        if not sequences:
            return {"error": "No sequences provided"}
        
        # Analyze sequence characteristics
        seq_count = len(sequences)
        seq_lengths = [len(seq.get('sequence', '')) for seq in sequences]
        avg_length = sum(seq_lengths) / len(seq_lengths) if seq_lengths else 0
        max_length = max(seq_lengths) if seq_lengths else 0
        
        # Detect sequence type
        seq_type = self._detect_sequence_type(sequences[0].get('sequence', ''))
        
        recommendations = {
            "sequence_analysis": {
                "count": seq_count,
                "average_length": avg_length,
                "max_length": max_length,
                "type": seq_type
            },
            "method_recommendations": []
        }
        
        # Recommend methods based on characteristics
        if seq_count <= 10 and avg_length <= 1000:
            recommendations["method_recommendations"].append({
                "method": "simple_progressive",
                "priority": "high",
                "reason": "Small dataset, good for educational purposes"
            })
        
        if seq_count <= 50:
            recommendations["method_recommendations"].append({
                "method": "muscle",
                "priority": "high",
                "reason": "Good general-purpose method for medium datasets"
            })
        
        if seq_count > 50 or max_length > 5000:
            recommendations["method_recommendations"].append({
                "method": "mafft",
                "priority": "high", 
                "reason": "Best for large datasets or long sequences"
            })
        
        if seq_count <= 20 and avg_length <= 2000:
            recommendations["method_recommendations"].append({
                "method": "clustalw",
                "priority": "medium",
                "reason": "Classic method, good for small to medium datasets"
            })
        
        return recommendations

# Global service instance
multiple_alignment_service = MultipleAlignmentService()