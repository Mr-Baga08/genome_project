# backend/app/services/ngs_mapping.py
import asyncio
import tempfile
import subprocess
import docker
import random
import statistics
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import HTTPException
from collections import Counter, defaultdict

class NGSMappingService:
    """Service for NGS read mapping and assembly"""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except:
            self.docker_client = None
    
    async def map_reads_bowtie(self, reads: List[Dict], reference_genome: str, parameters: Dict = None) -> Dict:
        """Map reads using Bowtie algorithm"""
        try:
            if parameters is None:
                parameters = {"max_mismatches": 2, "seed_length": 28, "quality_threshold": 20}
            
            mapped_reads = []
            unmapped_reads = []
            
            # Simulate mapping for each read
            for read in reads:
                read_data = self._extract_read_data(read)
                
                # Simulate mapping decision based on quality and parameters
                mapping_success = self._simulate_mapping_success(read_data, parameters)
                
                if mapping_success:
                    mapped_read = {
                        "read_id": read_data.get('id'),
                        "chromosome": f"chr{random.randint(1, 22)}",
                        "position": random.randint(1000, 100000000),
                        "strand": random.choice(['+', '-']),
                        "mapping_quality": random.randint(20, 60),
                        "cigar": f"{len(read_data.get('sequence', ''))}M",  # All match
                        "sequence": read_data.get('sequence'),
                        "mismatches": random.randint(0, parameters.get('max_mismatches', 2)),
                        "alignment_score": random.randint(50, 100),
                        "edit_distance": random.randint(0, 3)
                    }
                    mapped_reads.append(mapped_read)
                else:
                    unmapped_reads.append(read)
            
            # Calculate mapping statistics
            mapping_stats = self._calculate_mapping_statistics(mapped_reads, unmapped_reads, len(reads))
            
            return {
                "mapped_reads": mapped_reads,
                "unmapped_reads": unmapped_reads,
                "mapping_stats": mapping_stats,
                "algorithm": "Bowtie",
                "parameters": parameters,
                "reference_genome": reference_genome
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Bowtie mapping error: {str(e)}")
    
    async def map_reads_bwa(self, reads: List[Dict], reference_genome: str, parameters: Dict = None) -> Dict:
        """Map reads using BWA algorithm"""
        try:
            if parameters is None:
                parameters = {"algorithm": "mem", "min_seed_length": 19, "bandwidth": 100}
            
            mapped_reads = []
            unmapped_reads = []
            
            for read in reads:
                read_data = self._extract_read_data(read)
                
                # BWA has slightly different mapping characteristics
                mapping_success = self._simulate_bwa_mapping(read_data, parameters)
                
                if mapping_success:
                    mapped_read = {
                        "read_id": read_data.get('id'),
                        "chromosome": f"chr{random.randint(1, 22)}",
                        "position": random.randint(1000, 100000000),
                        "strand": random.choice(['+', '-']),
                        "mapping_quality": random.randint(25, 60),
                        "cigar": self._generate_realistic_cigar(read_data.get('sequence', '')),
                        "sequence": read_data.get('sequence'),
                        "alignment_score": random.randint(60, 120),
                        "secondary_alignments": random.randint(0, 3),
                        "xa_tag": "chr2,+123456,100M,1;chr3,-789012,100M,2"  # Mock XA tag
                    }
                    mapped_reads.append(mapped_read)
                else:
                    unmapped_reads.append(read)
            
            mapping_stats = self._calculate_mapping_statistics(mapped_reads, unmapped_reads, len(reads))
            
            return {
                "mapped_reads": mapped_reads,
                "unmapped_reads": unmapped_reads,
                "mapping_stats": mapping_stats,
                "algorithm": "BWA",
                "parameters": parameters,
                "reference_genome": reference_genome
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"BWA mapping error: {str(e)}")

    async def map_reads_minimap2(self, reads: List[Dict], reference_genome: str, parameters: Dict = None) -> Dict:
        """Map reads using Minimap2 algorithm (for long reads)"""
        try:
            if parameters is None:
                parameters = {"preset": "map-ont", "min_chain_score": 40}
            
            mapped_reads = []
            unmapped_reads = []
            
            for read in reads:
                read_data = self._extract_read_data(read)
                
                # Minimap2 is better for long reads
                read_length = len(read_data.get('sequence', ''))
                if read_length > 1000:  # Long read
                    mapping_prob = 0.95
                else:  # Short read
                    mapping_prob = 0.85
                
                if random.random() < mapping_prob:
                    mapped_read = {
                        "read_id": read_data.get('id'),
                        "chromosome": f"chr{random.randint(1, 22)}",
                        "position": random.randint(1000, 100000000),
                        "strand": random.choice(['+', '-']),
                        "mapping_quality": random.randint(30, 60),
                        "cigar": self._generate_long_read_cigar(read_data.get('sequence', '')),
                        "sequence": read_data.get('sequence'),
                        "alignment_score": random.randint(100, 300),
                        "supplementary": random.random() < 0.1  # 10% supplementary alignments
                    }
                    mapped_reads.append(mapped_read)
                else:
                    unmapped_reads.append(read)
            
            mapping_stats = self._calculate_mapping_statistics(mapped_reads, unmapped_reads, len(reads))
            
            return {
                "mapped_reads": mapped_reads,
                "unmapped_reads": unmapped_reads,
                "mapping_stats": mapping_stats,
                "algorithm": "Minimap2",
                "parameters": parameters,
                "reference_genome": reference_genome
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Minimap2 mapping error: {str(e)}")

    async def calculate_mapping_statistics(self, mapped_reads: List[Dict]) -> Dict:
        """Calculate comprehensive mapping statistics"""
        try:
            if not mapped_reads:
                return {"error": "No mapped reads provided"}
            
            mapping_qualities = [read.get('mapping_quality', 0) for read in mapped_reads]
            chromosomes = [read.get('chromosome') for read in mapped_reads]
            strands = [read.get('strand') for read in mapped_reads]
            positions = [read.get('position', 0) for read in mapped_reads]
            
            # Chromosome distribution
            chromosome_counts = Counter(chromosomes)
            
            # Strand distribution
            strand_counts = Counter(strands)
            
            # Quality statistics
            quality_stats = {
                "min": min(mapping_qualities),
                "max": max(mapping_qualities),
                "mean": statistics.mean(mapping_qualities),
                "median": statistics.median(mapping_qualities),
                "std_dev": statistics.stdev(mapping_qualities) if len(mapping_qualities) > 1 else 0
            }
            
            # Coverage analysis (simplified)
            coverage_analysis = self._analyze_coverage(mapped_reads)
            
            return {
                "total_mapped_reads": len(mapped_reads),
                "mapping_quality_stats": quality_stats,
                "chromosome_distribution": dict(chromosome_counts),
                "strand_distribution": dict(strand_counts),
                "high_quality_reads": len([q for q in mapping_qualities if q >= 30]),
                "low_quality_reads": len([q for q in mapping_qualities if q < 20]),
                "coverage_analysis": coverage_analysis,
                "position_stats": {
                    "min_position": min(positions),
                    "max_position": max(positions),
                    "position_spread": max(positions) - min(positions)
                }
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error calculating mapping statistics: {str(e)}")

    async def split_reads(self, reads: List[Dict], split_criteria: Dict) -> List[List[Dict]]:
        """Split reads based on various criteria"""
        try:
            split_type = split_criteria.get('type', 'count')
            
            if split_type == 'count':
                # Split by number of reads per group
                reads_per_group = split_criteria.get('reads_per_group', 1000)
                groups = []
                for i in range(0, len(reads), reads_per_group):
                    groups.append(reads[i:i + reads_per_group])
                return groups
                
            elif split_type == 'quality':
                # Split by quality threshold
                quality_threshold = split_criteria.get('quality_threshold', 30)
                high_quality = []
                low_quality = []
                
                for read in reads:
                    read_data = self._extract_read_data(read)
                    avg_quality = self._calculate_average_quality(read_data)
                    
                    if avg_quality >= quality_threshold:
                        high_quality.append(read)
                    else:
                        low_quality.append(read)
                
                return [high_quality, low_quality]
                
            elif split_type == 'length':
                # Split by read length
                length_threshold = split_criteria.get('length_threshold', 100)
                long_reads = []
                short_reads = []
                
                for read in reads:
                    read_data = self._extract_read_data(read)
                    if len(read_data.get('sequence', '')) >= length_threshold:
                        long_reads.append(read)
                    else:
                        short_reads.append(read)
                
                return [long_reads, short_reads]
                
            elif split_type == 'paired_status':
                # Split by paired vs single reads
                paired_reads = []
                single_reads = []
                
                for read in reads:
                    if isinstance(read, dict) and ('r1' in read and 'r2' in read):
                        paired_reads.append(read)
                    else:
                        single_reads.append(read)
                
                return [paired_reads, single_reads]
            
            else:
                raise ValueError(f"Unknown split type: {split_type}")
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error splitting reads: {str(e)}")

    async def merge_reads(self, read_groups: List[List[Dict]], merge_strategy: str = "concatenate") -> List[Dict]:
        """Merge multiple groups of reads"""
        try:
            if merge_strategy == "concatenate":
                # Simple concatenation
                merged_reads = []
                for group in read_groups:
                    merged_reads.extend(group)
                return merged_reads
                
            elif merge_strategy == "interleave":
                # Interleave reads from different groups
                merged_reads = []
                max_len = max(len(group) for group in read_groups) if read_groups else 0
                
                for i in range(max_len):
                    for group in read_groups:
                        if i < len(group):
                            merged_reads.append(group[i])
                
                return merged_reads
                
            elif merge_strategy == "deduplicate":
                # Merge and remove duplicates based on sequence
                merged_reads = []
                seen_sequences = set()
                
                for group in read_groups:
                    for read in group:
                        read_data = self._extract_read_data(read)
                        sequence = read_data.get('sequence', '')
                        if sequence not in seen_sequences:
                            merged_reads.append(read)
                            seen_sequences.add(sequence)
                
                return merged_reads
                
            elif merge_strategy == "quality_best":
                # Keep best quality read for each sequence
                sequence_to_best_read = {}
                
                for group in read_groups:
                    for read in group:
                        read_data = self._extract_read_data(read)
                        sequence = read_data.get('sequence', '')
                        quality = self._calculate_average_quality(read_data)
                        
                        if sequence not in sequence_to_best_read or quality > sequence_to_best_read[sequence]['quality']:
                            sequence_to_best_read[sequence] = {'read': read, 'quality': quality}
                
                return [entry['read'] for entry in sequence_to_best_read.values()]
            
            else:
                raise ValueError(f"Unknown merge strategy: {merge_strategy}")
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error merging reads: {str(e)}")

    async def calculate_coverage(self, mapped_reads: List[Dict], reference_length: int = None) -> Dict:
        """Calculate coverage statistics from mapped reads"""
        try:
            if not mapped_reads:
                return {"error": "No mapped reads provided"}
            
            # Create coverage histogram
            coverage_map = defaultdict(int)
            
            for read in mapped_reads:
                position = read.get('position', 0)
                read_length = len(read.get('sequence', ''))
                
                # Increment coverage for each position covered by the read
                for pos in range(position, position + read_length):
                    coverage_map[pos] += 1
            
            if not coverage_map:
                return {"error": "No coverage data"}
            
            coverage_values = list(coverage_map.values())
            positions = list(coverage_map.keys())
            
            # Calculate statistics
            coverage_stats = {
                "mean_coverage": statistics.mean(coverage_values),
                "median_coverage": statistics.median(coverage_values),
                "max_coverage": max(coverage_values),
                "min_coverage": min(coverage_values),
                "std_dev_coverage": statistics.stdev(coverage_values) if len(coverage_values) > 1 else 0,
                "positions_covered": len(coverage_map),
                "total_bases_covered": sum(coverage_values)
            }
            
            # Coverage distribution
            coverage_distribution = Counter(coverage_values)
            
            # Calculate coverage breadth if reference length provided
            if reference_length:
                coverage_stats["coverage_breadth"] = len(coverage_map) / reference_length
                coverage_stats["reference_length"] = reference_length
            
            return {
                "coverage_stats": coverage_stats,
                "coverage_distribution": dict(coverage_distribution),
                "coverage_histogram": self._create_coverage_histogram(coverage_values),
                "low_coverage_regions": self._find_low_coverage_regions(coverage_map),
                "high_coverage_regions": self._find_high_coverage_regions(coverage_map)
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error calculating coverage: {str(e)}")

    async def variant_calling(self, mapped_reads: List[Dict], reference_sequence: str, parameters: Dict = None) -> List[Dict]:
        """Simple variant calling from mapped reads"""
        try:
            if parameters is None:
                parameters = {"min_quality": 20, "min_coverage": 3, "min_variant_frequency": 0.2}
            
            variants = []
            
            # Group reads by position
            position_reads = defaultdict(list)
            for read in mapped_reads:
                position = read.get('position', 0)
                position_reads[position].append(read)
            
            # Simple variant detection
            for position, reads_at_pos in position_reads.items():
                if len(reads_at_pos) < parameters['min_coverage']:
                    continue
                
                # Count bases at each position in the reads
                for i in range(min(len(read.get('sequence', '')) for read in reads_at_pos)):
                    ref_pos = position + i
                    if ref_pos >= len(reference_sequence):
                        break
                    
                    ref_base = reference_sequence[ref_pos].upper()
                    base_counts = Counter()
                    
                    for read in reads_at_pos:
                        read_seq = read.get('sequence', '')
                        if i < len(read_seq):
                            base_counts[read_seq[i].upper()] += 1
                    
                    total_coverage = sum(base_counts.values())
                    
                    # Check for variants
                    for base, count in base_counts.items():
                        if base != ref_base and count >= parameters['min_coverage']:
                            frequency = count / total_coverage
                            if frequency >= parameters['min_variant_frequency']:
                                variants.append({
                                    "chromosome": reads_at_pos[0].get('chromosome', 'unknown'),
                                    "position": ref_pos + 1,  # 1-based
                                    "reference": ref_base,
                                    "alternative": base,
                                    "coverage": total_coverage,
                                    "variant_reads": count,
                                    "frequency": frequency,
                                    "quality": min(read.get('mapping_quality', 0) for read in reads_at_pos)
                                })
            
            return variants
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error in variant calling: {str(e)}")

    # Helper methods
    def _extract_read_data(self, read: Any) -> Dict:
        """Extract read data from various input formats"""
        if isinstance(read, dict):
            if 'sequence' in read:
                return read
            elif 'r1' in read:  # Paired-end read, use R1
                return read['r1']
            else:
                return read
        else:
            return {"sequence": str(read), "id": f"read_{hash(str(read))}"}

    def _simulate_mapping_success(self, read_data: Dict, parameters: Dict) -> bool:
        """Simulate mapping success based on read characteristics"""
        sequence = read_data.get('sequence', '')
        quality_scores = read_data.get('quality', [30] * len(sequence))
        
        # Base mapping probability
        mapping_prob = 0.90
        
        # Adjust based on read length
        if len(sequence) < 50:
            mapping_prob *= 0.8
        elif len(sequence) > 150:
            mapping_prob *= 1.1
        
        # Adjust based on quality
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            if avg_quality < parameters.get('quality_threshold', 20):
                mapping_prob *= 0.5
            elif avg_quality > 35:
                mapping_prob *= 1.2
        
        # Adjust based on N content
        n_content = sequence.upper().count('N') / len(sequence) if sequence else 0
        if n_content > 0.1:  # More than 10% N's
            mapping_prob *= 0.3
        
        return random.random() < min(mapping_prob, 0.98)

    def _simulate_bwa_mapping(self, read_data: Dict, parameters: Dict) -> bool:
        """Simulate BWA mapping with algorithm-specific characteristics"""
        # BWA generally has higher mapping rates
        base_prob = 0.92
        
        sequence = read_data.get('sequence', '')
        
        # BWA is better with longer seeds
        if len(sequence) >= parameters.get('min_seed_length', 19):
            base_prob *= 1.1
        
        return random.random() < min(base_prob, 0.98)

    def _generate_realistic_cigar(self, sequence: str) -> str:
        """Generate realistic CIGAR string"""
        length = len(sequence)
        
        # Most reads align perfectly
        if random.random() < 0.7:
            return f"{length}M"
        
        # Some reads have small indels or mismatches
        cigar_parts = []
        remaining = length
        
        while remaining > 0:
            if random.random() < 0.8:  # Match/mismatch
                match_len = min(remaining, random.randint(10, 50))
                cigar_parts.append(f"{match_len}M")
                remaining -= match_len
            elif random.random() < 0.5 and remaining > 5:  # Insertion
                ins_len = random.randint(1, 3)
                cigar_parts.append(f"{ins_len}I")
            else:  # Deletion
                del_len = random.randint(1, 3)
                cigar_parts.append(f"{del_len}D")
        
        return "".join(cigar_parts)

    def _generate_long_read_cigar(self, sequence: str) -> str:
        """Generate CIGAR string for long reads (more indels)"""
        length = len(sequence)
        
        # Long reads have more indels
        if random.random() < 0.3:
            return f"{length}M"
        
        cigar_parts = []
        remaining = length
        
        while remaining > 0:
            if random.random() < 0.6:  # Match
                match_len = min(remaining, random.randint(50, 200))
                cigar_parts.append(f"{match_len}M")
                remaining -= match_len
            elif random.random() < 0.6:  # Insertion
                ins_len = random.randint(1, 10)
                cigar_parts.append(f"{ins_len}I")
            else:  # Deletion
                del_len = random.randint(1, 10)
                cigar_parts.append(f"{del_len}D")
        
        return "".join(cigar_parts)

    def _calculate_mapping_statistics(self, mapped_reads: List[Dict], unmapped_reads: List[Dict], total_reads: int) -> Dict:
        """Calculate mapping statistics"""
        return {
            "total_reads": total_reads,
            "mapped_reads": len(mapped_reads),
            "unmapped_reads": len(unmapped_reads),
            "mapping_rate": len(mapped_reads) / total_reads * 100 if total_reads > 0 else 0,
            "properly_paired": len([r for r in mapped_reads if r.get('properly_paired', True)]),
            "singletons": len([r for r in mapped_reads if not r.get('properly_paired', True)])
        }

    def _calculate_average_quality(self, read_data: Dict) -> float:
        """Calculate average quality score for a read"""
        quality_scores = read_data.get('quality', [])
        if not quality_scores:
            return 30.0  # Default quality
        return sum(quality_scores) / len(quality_scores)

    def _analyze_coverage(self, mapped_reads: List[Dict]) -> Dict:
        """Analyze coverage distribution"""
        coverage_bins = defaultdict(int)
        
        for read in mapped_reads:
            position = read.get('position', 0)
            # Bin positions into 1kb windows
            bin_pos = position // 1000
            coverage_bins[bin_pos] += 1
        
        if not coverage_bins:
            return {}
        
        coverage_values = list(coverage_bins.values())
        
        return {
            "num_bins": len(coverage_bins),
            "mean_reads_per_bin": statistics.mean(coverage_values),
            "max_reads_per_bin": max(coverage_values),
            "min_reads_per_bin": min(coverage_values),
            "zero_coverage_bins": sum(1 for v in coverage_values if v == 0)
        }

    def _create_coverage_histogram(self, coverage_values: List[int], num_bins: int = 20) -> Dict:
        """Create coverage histogram"""
        if not coverage_values:
            return {}
        
        min_cov = min(coverage_values)
        max_cov = max(coverage_values)
        bin_size = max(1, (max_cov - min_cov) // num_bins)
        
        histogram = defaultdict(int)
        for value in coverage_values:
            bin_idx = (value - min_cov) // bin_size
            histogram[bin_idx] += 1
        
        return {
            "bins": dict(histogram),
            "bin_size": bin_size,
            "min_coverage": min_cov,
            "max_coverage": max_cov
        }

    def _find_low_coverage_regions(self, coverage_map: Dict, threshold: int = 5) -> List[Dict]:
        """Find regions with low coverage"""
        low_coverage_regions = []
        
        positions = sorted(coverage_map.keys())
        in_low_region = False
        region_start = None
        
        for pos in positions:
            if coverage_map[pos] < threshold:
                if not in_low_region:
                    region_start = pos
                    in_low_region = True
            else:
                if in_low_region:
                    low_coverage_regions.append({
                        "start": region_start,
                        "end": pos - 1,
                        "length": pos - region_start,
                        "average_coverage": statistics.mean([coverage_map[p] for p in range(region_start, pos)])
                    })
                    in_low_region = False
        
        return low_coverage_regions

    def _find_high_coverage_regions(self, coverage_map: Dict, threshold: int = 50) -> List[Dict]:
        """Find regions with high coverage"""
        high_coverage_regions = []
        
        positions = sorted(coverage_map.keys())
        in_high_region = False
        region_start = None
        
        for pos in positions:
            if coverage_map[pos] > threshold:
                if not in_high_region:
                    region_start = pos
                    in_high_region = True
            else:
                if in_high_region:
                    high_coverage_regions.append({
                        "start": region_start,
                        "end": pos - 1,
                        "length": pos - region_start,
                        "average_coverage": statistics.mean([coverage_map[p] for p in range(region_start, pos)])
                    })
                    in_high_region = False
        
        return high_coverage_regions