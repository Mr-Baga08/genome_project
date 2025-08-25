# backend/app/services/basic_analysis.py
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BasicAnalysisService:
    """Service for basic sequence analysis operations"""
    
    def __init__(self):
        self.supported_analyses = [
            'length_distribution',
            'composition_analysis', 
            'gc_content',
            'quality_metrics',
            'consensus_sequence',
            'sequence_diversity',
            'motif_analysis',
            'codon_usage'
        ]
    
    async def calculate_statistics(self, sequences: List[Dict], analysis_types: List[str] = None) -> Dict:
        """Calculate comprehensive statistics for sequences"""
        if not sequences:
            return {"error": "No sequences provided"}
        
        if analysis_types is None:
            analysis_types = ['basic', 'composition', 'quality']
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "sequence_count": len(sequences),
            "analyses": {}
        }
        
        try:
            # Basic statistics
            if 'basic' in analysis_types:
                results["analyses"]["basic"] = await self._calculate_basic_stats(sequences)
            
            # Composition analysis
            if 'composition' in analysis_types:
                results["analyses"]["composition"] = await self._calculate_composition_stats(sequences)
            
            # Quality metrics (for sequences with quality data)
            if 'quality' in analysis_types:
                results["analyses"]["quality"] = await self._calculate_quality_stats(sequences)
            
            # GC content analysis
            if 'gc_content' in analysis_types:
                results["analyses"]["gc_content"] = await self._calculate_gc_content(sequences)
            
            # Length distribution
            if 'length_distribution' in analysis_types:
                results["analyses"]["length_distribution"] = await self._calculate_length_distribution(sequences)
                
            return results
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {str(e)}")
            return {"error": f"Failed to calculate statistics: {str(e)}"}
    
    async def _calculate_basic_stats(self, sequences: List[Dict]) -> Dict:
        """Calculate basic sequence statistics"""
        lengths = []
        valid_sequences = 0
        
        for seq in sequences:
            sequence_str = seq.get('sequence', '')
            if sequence_str:
                lengths.append(len(sequence_str))
                valid_sequences += 1
        
        if not lengths:
            return {"error": "No valid sequences found"}
        
        return {
            "total_sequences": len(sequences),
            "valid_sequences": valid_sequences,
            "total_length": sum(lengths),
            "average_length": np.mean(lengths),
            "median_length": np.median(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "length_std": np.std(lengths)
        }
    
    async def _calculate_composition_stats(self, sequences: List[Dict]) -> Dict:
        """Calculate nucleotide/amino acid composition"""
        composition_counts = defaultdict(int)
        total_chars = 0
        sequence_type = None
        
        for seq in sequences:
            sequence_str = seq.get('sequence', '').upper()
            if not sequence_str:
                continue
                
            # Detect sequence type if not specified
            if sequence_type is None:
                sequence_type = self._detect_sequence_type(sequence_str)
            
            for char in sequence_str:
                if char.isalpha():
                    composition_counts[char] += 1
                    total_chars += 1
        
        if total_chars == 0:
            return {"error": "No valid sequence characters found"}
        
        # Convert to percentages
        composition_percentages = {
            char: (count / total_chars) * 100 
            for char, count in composition_counts.items()
        }
        
        result = {
            "sequence_type": sequence_type,
            "total_characters": total_chars,
            "composition_counts": dict(composition_counts),
            "composition_percentages": composition_percentages
        }
        
        # Add specific analysis based on sequence type
        if sequence_type == 'DNA':
            result["purine_pyrimidine"] = self._calculate_purine_pyrimidine(composition_counts)
        elif sequence_type == 'PROTEIN':
            result["amino_acid_properties"] = self._calculate_aa_properties(composition_counts)
            
        return result
    
    async def _calculate_quality_stats(self, sequences: List[Dict]) -> Dict:
        """Calculate quality statistics for sequences with quality data"""
        quality_scores = []
        
        for seq in sequences:
            quality_str = seq.get('quality', '')
            if quality_str:
                # Convert Phred quality scores from ASCII
                scores = [ord(char) - 33 for char in quality_str if ord(char) >= 33]
                quality_scores.extend(scores)
        
        if not quality_scores:
            return {"message": "No quality data available"}
        
        return {
            "average_quality": np.mean(quality_scores),
            "median_quality": np.median(quality_scores),
            "min_quality": min(quality_scores),
            "max_quality": max(quality_scores),
            "quality_std": np.std(quality_scores),
            "high_quality_ratio": len([q for q in quality_scores if q >= 30]) / len(quality_scores)
        }
    
    async def _calculate_gc_content(self, sequences: List[Dict]) -> Dict:
        """Calculate GC content for DNA sequences"""
        gc_contents = []
        
        for seq in sequences:
            sequence_str = seq.get('sequence', '').upper()
            if not sequence_str:
                continue
                
            gc_count = sequence_str.count('G') + sequence_str.count('C')
            at_count = sequence_str.count('A') + sequence_str.count('T')
            total_bases = gc_count + at_count
            
            if total_bases > 0:
                gc_content = (gc_count / total_bases) * 100
                gc_contents.append({
                    "sequence_name": seq.get('name', 'Unknown'),
                    "gc_content": gc_content,
                    "length": len(sequence_str)
                })
        
        if not gc_contents:
            return {"error": "No valid DNA sequences found for GC analysis"}
        
        overall_gc = np.mean([gc['gc_content'] for gc in gc_contents])
        
        return {
            "overall_gc_content": overall_gc,
            "gc_content_std": np.std([gc['gc_content'] for gc in gc_contents]),
            "individual_sequences": gc_contents,
            "gc_content_distribution": {
                "low_gc": len([gc for gc in gc_contents if gc['gc_content'] < 40]),
                "medium_gc": len([gc for gc in gc_contents if 40 <= gc['gc_content'] <= 60]),
                "high_gc": len([gc for gc in gc_contents if gc['gc_content'] > 60])
            }
        }
    
    async def _calculate_length_distribution(self, sequences: List[Dict]) -> Dict:
        """Calculate sequence length distribution"""
        lengths = [len(seq.get('sequence', '')) for seq in sequences if seq.get('sequence')]
        
        if not lengths:
            return {"error": "No valid sequences found"}
        
        # Create histogram bins
        bins = np.histogram(lengths, bins=10)
        
        return {
            "bins": bins[1].tolist(),
            "counts": bins[0].tolist(),
            "statistics": {
                "mean": np.mean(lengths),
                "median": np.median(lengths),
                "std": np.std(lengths),
                "range": max(lengths) - min(lengths)
            }
        }
    
    async def summarize_data(self, sequences: List[Dict], summary_type: str = "basic") -> Dict:
        """Generate various types of data summaries"""
        if not sequences:
            return {"error": "No sequences provided"}
        
        try:
            if summary_type == "basic":
                return await self._basic_summary(sequences)
            elif summary_type == "detailed":
                return await self._detailed_summary(sequences)
            elif summary_type == "comparative":
                return await self._comparative_summary(sequences)
            else:
                return {"error": f"Unknown summary type: {summary_type}"}
                
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return {"error": f"Failed to generate summary: {str(e)}"}
    
    async def _basic_summary(self, sequences: List[Dict]) -> Dict:
        """Generate basic sequence summary"""
        valid_sequences = [seq for seq in sequences if seq.get('sequence')]
        
        if not valid_sequences:
            return {"error": "No valid sequences found"}
        
        lengths = [len(seq['sequence']) for seq in valid_sequences]
        
        return {
            "summary_type": "basic",
            "total_sequences": len(sequences),
            "valid_sequences": len(valid_sequences),
            "length_stats": {
                "total": sum(lengths),
                "average": np.mean(lengths),
                "min": min(lengths),
                "max": max(lengths)
            },
            "sequence_types": self._get_sequence_type_distribution(valid_sequences)
        }
    
    async def _detailed_summary(self, sequences: List[Dict]) -> Dict:
        """Generate detailed sequence summary with composition analysis"""
        basic_summary = await self._basic_summary(sequences)
        
        if "error" in basic_summary:
            return basic_summary
        
        # Add composition analysis
        composition = await self._calculate_composition_stats(sequences)
        gc_content = await self._calculate_gc_content(sequences)
        
        return {
            **basic_summary,
            "summary_type": "detailed",
            "composition_analysis": composition,
            "gc_content_analysis": gc_content
        }
    
    async def _comparative_summary(self, sequences: List[Dict]) -> Dict:
        """Generate comparative summary between different sequence groups"""
        # Group sequences by type or other criteria
        groups = defaultdict(list)
        
        for seq in sequences:
            seq_type = seq.get('sequence_type', 'Unknown')
            groups[seq_type].append(seq)
        
        comparative_results = {}
        for group_name, group_sequences in groups.items():
            if group_sequences:
                comparative_results[group_name] = await self._basic_summary(group_sequences)
        
        return {
            "summary_type": "comparative",
            "groups": comparative_results,
            "group_counts": {name: len(seqs) for name, seqs in groups.items()}
        }
    
    def _detect_sequence_type(self, sequence: str) -> str:
        """Detect sequence type (DNA, RNA, PROTEIN)"""
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
    
    def _calculate_purine_pyrimidine(self, composition: Dict) -> Dict:
        """Calculate purine/pyrimidine ratios for DNA"""
        purines = composition.get('A', 0) + composition.get('G', 0)
        pyrimidines = composition.get('T', 0) + composition.get('C', 0)
        
        total = purines + pyrimidines
        if total == 0:
            return {"error": "No valid DNA bases found"}
        
        return {
            "purines": purines,
            "pyrimidines": pyrimidines,
            "purine_ratio": purines / total,
            "pyrimidine_ratio": pyrimidines / total
        }
    
    def _calculate_aa_properties(self, composition: Dict) -> Dict:
        """Calculate amino acid properties for proteins"""
        hydrophobic = {'A', 'V', 'I', 'L', 'M', 'F', 'Y', 'W'}
        hydrophilic = {'R', 'N', 'D', 'C', 'Q', 'E', 'G', 'H', 'K', 'P', 'S', 'T'}
        
        hydrophobic_count = sum(composition.get(aa, 0) for aa in hydrophobic)
        hydrophilic_count = sum(composition.get(aa, 0) for aa in hydrophilic)
        total = hydrophobic_count + hydrophilic_count
        
        if total == 0:
            return {"error": "No valid amino acids found"}
        
        return {
            "hydrophobic_count": hydrophobic_count,
            "hydrophilic_count": hydrophilic_count,
            "hydrophobic_ratio": hydrophobic_count / total,
            "hydrophilic_ratio": hydrophilic_count / total
        }
    
    def _get_sequence_type_distribution(self, sequences: List[Dict]) -> Dict:
        """Get distribution of sequence types"""
        type_counts = defaultdict(int)
        
        for seq in sequences:
            seq_type = seq.get('sequence_type')
            if not seq_type:
                seq_type = self._detect_sequence_type(seq.get('sequence', ''))
            type_counts[seq_type] += 1
        
        return dict(type_counts)
    
    async def calculate_consensus_sequence(self, sequences: List[Dict], threshold: float = 0.5) -> Dict:
        """Calculate consensus sequence from multiple aligned sequences"""
        if not sequences:
            return {"error": "No sequences provided"}
        
        # Extract sequence strings
        seq_strings = [seq.get('sequence', '') for seq in sequences if seq.get('sequence')]
        
        if not seq_strings:
            return {"error": "No valid sequences found"}
        
        # Check if sequences are aligned (same length)
        lengths = [len(seq) for seq in seq_strings]
        if len(set(lengths)) > 1:
            return {"error": "Sequences must be aligned (same length) for consensus calculation"}
        
        consensus_length = lengths[0]
        consensus = []
        
        for position in range(consensus_length):
            # Count characters at this position
            char_counts = Counter()
            for seq in seq_strings:
                if position < len(seq):
                    char = seq[position].upper()
                    if char != '-':  # Ignore gaps
                        char_counts[char] += 1
            
            # Determine consensus character
            if char_counts:
                most_common = char_counts.most_common(1)[0]
                char, count = most_common
                frequency = count / len(seq_strings)
                
                if frequency >= threshold:
                    consensus.append(char)
                else:
                    consensus.append('N')  # Ambiguous position
            else:
                consensus.append('-')  # Gap position
        
        return {
            "consensus_sequence": ''.join(consensus),
            "length": consensus_length,
            "threshold_used": threshold,
            "sequence_count": len(seq_strings)
        }
    
    async def analyze_motifs(self, sequences: List[Dict], motif_length: int = 6) -> Dict:
        """Find common motifs in sequences"""
        if not sequences:
            return {"error": "No sequences provided"}
        
        motif_counts = defaultdict(int)
        total_motifs = 0
        
        for seq in sequences:
            sequence_str = seq.get('sequence', '').upper()
            if not sequence_str:
                continue
            
            # Extract motifs of specified length
            for i in range(len(sequence_str) - motif_length + 1):
                motif = sequence_str[i:i + motif_length]
                if len(motif) == motif_length and motif.isalpha():
                    motif_counts[motif] += 1
                    total_motifs += 1
        
        if total_motifs == 0:
            return {"error": "No motifs found"}
        
        # Sort by frequency
        sorted_motifs = sorted(motif_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "motif_length": motif_length,
            "total_motifs_found": total_motifs,
            "unique_motifs": len(motif_counts),
            "top_motifs": [
                {
                    "motif": motif,
                    "count": count,
                    "frequency": count / total_motifs
                }
                for motif, count in sorted_motifs[:20]  # Top 20 motifs
            ]
        }
    
    async def calculate_sequence_diversity(self, sequences: List[Dict]) -> Dict:
        """Calculate sequence diversity metrics"""
        if not sequences:
            return {"error": "No sequences provided"}
        
        seq_strings = [seq.get('sequence', '') for seq in sequences if seq.get('sequence')]
        
        if len(seq_strings) < 2:
            return {"error": "Need at least 2 sequences for diversity calculation"}
        
        # Calculate pairwise distances
        distances = []
        for i in range(len(seq_strings)):
            for j in range(i + 1, len(seq_strings)):
                distance = self._calculate_hamming_distance(seq_strings[i], seq_strings[j])
                distances.append(distance)
        
        if not distances:
            return {"error": "Could not calculate distances"}
        
        return {
            "pairwise_distances": distances,
            "average_distance": np.mean(distances),
            "max_distance": max(distances),
            "min_distance": min(distances),
            "distance_std": np.std(distances),
            "diversity_index": np.mean(distances) / max(len(s) for s in seq_strings)
        }
    
    def _calculate_hamming_distance(self, seq1: str, seq2: str) -> float:
        """Calculate Hamming distance between two sequences"""
        if len(seq1) != len(seq2):
            # For unequal lengths, normalize by average length
            min_len = min(len(seq1), len(seq2))
            mismatches = sum(c1 != c2 for c1, c2 in zip(seq1[:min_len], seq2[:min_len]))
            length_diff = abs(len(seq1) - len(seq2))
            return (mismatches + length_diff) / max(len(seq1), len(seq2))
        else:
            mismatches = sum(c1 != c2 for c1, c2 in zip(seq1, seq2))
            return mismatches / len(seq1)
    
    async def analyze_codon_usage(self, sequences: List[Dict]) -> Dict:
        """Analyze codon usage for DNA/RNA sequences"""
        if not sequences:
            return {"error": "No sequences provided"}
        
        codon_counts = defaultdict(int)
        total_codons = 0
        
        for seq in sequences:
            sequence_str = seq.get('sequence', '').upper()
            if not sequence_str:
                continue
            
            # Extract codons (triplets)
            for i in range(0, len(sequence_str) - 2, 3):
                codon = sequence_str[i:i+3]
                if len(codon) == 3 and codon.isalpha():
                    codon_counts[codon] += 1
                    total_codons += 1
        
        if total_codons == 0:
            return {"error": "No valid codons found"}
        
        # Calculate frequencies
        codon_frequencies = {
            codon: count / total_codons 
            for codon, count in codon_counts.items()
        }
        
        # Sort by frequency
        sorted_codons = sorted(codon_frequencies.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total_codons": total_codons,
            "unique_codons": len(codon_counts),
            "codon_frequencies": codon_frequencies,
            "most_frequent_codons": sorted_codons[:10],
            "least_frequent_codons": sorted_codons[-10:] if len(sorted_codons) > 10 else []
        }

# Global service instance
basic_analysis_service = BasicAnalysisService()