# backend/app/services/data_flow.py
import asyncio
import random
from typing import List, Dict, Any, Optional, Union
from fastapi import HTTPException
from collections import defaultdict, Counter
import re
import statistics

class DataFlowService:
    """Service for workflow data flow control"""
    
    @staticmethod
    async def filter_sequences(sequences: List[Dict], criteria: Dict) -> List[Dict]:
        """Filter sequences based on various criteria"""
        try:
            filtered = []
            
            for seq in sequences:
                include = True
                sequence_data = seq.get('sequence', '')
                
                # Length filter
                if 'min_length' in criteria:
                    if len(sequence_data) < criteria['min_length']:
                        include = False
                
                if 'max_length' in criteria:
                    if len(sequence_data) > criteria['max_length']:
                        include = False
                
                # GC content filter
                if 'min_gc' in criteria or 'max_gc' in criteria:
                    gc_content = DataFlowService._calculate_gc_content(sequence_data)
                    if 'min_gc' in criteria and gc_content < criteria['min_gc']:
                        include = False
                    if 'max_gc' in criteria and gc_content > criteria['max_gc']:
                        include = False
                
                # Pattern filter
                if 'contains_pattern' in criteria:
                    pattern = criteria['contains_pattern']
                    if pattern not in sequence_data.upper():
                        include = False
                
                if 'excludes_pattern' in criteria:
                    pattern = criteria['excludes_pattern']
                    if pattern in sequence_data.upper():
                        include = False
                
                # Quality filter (for FASTQ data)
                if 'min_quality' in criteria and 'quality' in seq:
                    avg_quality = sum(seq['quality']) / len(seq['quality']) if seq['quality'] else 0
                    if avg_quality < criteria['min_quality']:
                        include = False
                
                # N content filter
                if 'max_n_percent' in criteria:
                    n_count = sequence_data.upper().count('N')
                    n_percent = (n_count / len(sequence_data)) * 100 if sequence_data else 0
                    if n_percent > criteria['max_n_percent']:
                        include = False
                
                if include:
                    filtered.append(seq)
            
            return filtered
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error filtering sequences: {str(e)}")

    @staticmethod
    async def group_sequences(sequences: List[Dict], group_by: str, parameters: Dict = None) -> Dict[str, List[Dict]]:
        """Group sequences by specified criteria"""
        try:
            if parameters is None:
                parameters = {}
                
            groups = defaultdict(list)
            
            for seq in sequences:
                if group_by == "length_range":
                    length = len(seq.get('sequence', ''))
                    if length < parameters.get('short_threshold', 100):
                        key = "short"
                    elif length < parameters.get('medium_threshold', 1000):
                        key = "medium"
                    elif length < parameters.get('long_threshold', 10000):
                        key = "long"
                    else:
                        key = "very_long"
                elif group_by == "gc_content":
                    gc = DataFlowService._calculate_gc_content(seq.get('sequence', ''))
                    if gc < parameters.get('low_gc_threshold', 40):
                        key = "low_gc"
                    elif gc < parameters.get('high_gc_threshold', 60):
                        key = "medium_gc"
                    else:
                        key = "high_gc"
                elif group_by == "organism":
                    key = seq.get('organism', 'unknown')
                elif group_by == "sequence_type":
                    key = seq.get('sequence_type', 'unknown')
                elif group_by == "similarity":
                    # Group by sequence similarity (simplified k-mer approach)
                    key = DataFlowService._get_similarity_group(seq, parameters)
                else:
                    key = seq.get(group_by, 'unknown')
                
                groups[key].append(seq)
            
            return dict(groups)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error grouping sequences: {str(e)}")

    @staticmethod
    async def multiplex_data(data_sources: List[Dict], operation: str = "merge") -> List[Dict]:
        """Multiplex multiple data sources"""
        try:
            if operation == "merge":
                result = []
                for source in data_sources:
                    if isinstance(source, list):
                        result.extend(source)
                    elif isinstance(source, dict) and 'sequences' in source:
                        result.extend(source['sequences'])
                    else:
                        result.append(source)
                return result
                
            elif operation == "interleave":
                result = []
                # Find the maximum length among all sources
                max_len = 0
                source_lists = []
                
                for source in data_sources:
                    if isinstance(source, list):
                        source_lists.append(source)
                        max_len = max(max_len, len(source))
                    elif isinstance(source, dict) and 'sequences' in source:
                        source_lists.append(source['sequences'])
                        max_len = max(max_len, len(source['sequences']))
                    else:
                        source_lists.append([source])
                        max_len = max(max_len, 1)
                
                # Interleave elements
                for i in range(max_len):
                    for source_list in source_lists:
                        if i < len(source_list):
                            result.append(source_list[i])
                
                return result
                
            elif operation == "deduplicate":
                result = []
                seen_sequences = set()
                
                for source in data_sources:
                    source_list = source if isinstance(source, list) else [source]
                    for item in source_list:
                        sequence = item.get('sequence', str(item))
                        if sequence not in seen_sequences:
                            result.append(item)
                            seen_sequences.add(sequence)
                
                return result
                
            elif operation == "union":
                # Union operation preserving unique IDs
                result = []
                seen_ids = set()
                
                for source in data_sources:
                    source_list = source if isinstance(source, list) else [source]
                    for item in source_list:
                        item_id = item.get('id', str(hash(str(item))))
                        if item_id not in seen_ids:
                            result.append(item)
                            seen_ids.add(item_id)
                
                return result
            
            else:
                raise ValueError(f"Unknown multiplexer operation: {operation}")
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error multiplexing data: {str(e)}")

    @staticmethod
    async def mark_sequences(sequences: List[Dict], markers: Dict) -> List[Dict]:
        """Add markers/tags to sequences"""
        try:
            marked_sequences = []
            
            for seq in sequences:
                marked_seq = seq.copy()
                
                # Add length marker
                if markers.get('add_length_info'):
                    marked_seq['length_category'] = DataFlowService._get_length_category(len(seq.get('sequence', '')))
                
                # Add GC content marker
                if markers.get('add_gc_info'):
                    marked_seq['gc_content'] = DataFlowService._calculate_gc_content(seq.get('sequence', ''))
                
                # Add composition markers
                if markers.get('add_composition_info'):
                    marked_seq['composition'] = DataFlowService._analyze_composition(seq.get('sequence', ''))
                
                # Add quality markers
                if markers.get('add_quality_info') and 'quality' in seq:
                    marked_seq['quality_stats'] = DataFlowService._analyze_quality(seq['quality'])
                
                # Add custom markers
                if 'custom_markers' in markers:
                    for marker_key, marker_value in markers['custom_markers'].items():
                        marked_seq[marker_key] = marker_value
                
                # Add timestamp marker
                if markers.get('add_timestamp'):
                    from datetime import datetime
                    marked_seq['processed_at'] = datetime.utcnow().isoformat()
                
                marked_sequences.append(marked_seq)
            
            return marked_sequences
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error marking sequences: {str(e)}")

    @staticmethod
    async def sort_sequences(sequences: List[Dict], sort_by: str, reverse: bool = False) -> List[Dict]:
        """Sort sequences by specified criteria"""
        try:
            if sort_by == "length":
                return sorted(sequences, key=lambda x: len(x.get('sequence', '')), reverse=reverse)
            elif sort_by == "gc_content":
                return sorted(sequences, key=lambda x: DataFlowService._calculate_gc_content(x.get('sequence', '')), reverse=reverse)
            elif sort_by == "name":
                return sorted(sequences, key=lambda x: x.get('id', ''), reverse=reverse)
            elif sort_by == "quality" and sequences and 'quality' in sequences[0]:
                return sorted(sequences, key=lambda x: sum(x.get('quality', [0])) / len(x.get('quality', [1])), reverse=reverse)
            else:
                return sorted(sequences, key=lambda x: x.get(sort_by, ''), reverse=reverse)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error sorting sequences: {str(e)}")

    @staticmethod
    async def split_data(data: List[Dict], split_criteria: Dict) -> List[List[Dict]]:
        """Split data into multiple groups"""
        try:
            split_type = split_criteria.get('type', 'count')
            
            if split_type == 'count':
                # Split by number of items per group
                items_per_group = split_criteria.get('items_per_group', 100)
                groups = []
                for i in range(0, len(data), items_per_group):
                    groups.append(data[i:i + items_per_group])
                return groups
                
            elif split_type == 'percentage':
                # Split by percentage
                percentages = split_criteria.get('percentages', [50, 50])
                percentages = [p / sum(percentages) for p in percentages]  # Normalize
                
                groups = []
                start_idx = 0
                
                for i, percentage in enumerate(percentages[:-1]):  # Skip last to avoid rounding errors
                    end_idx = start_idx + int(len(data) * percentage)
                    groups.append(data[start_idx:end_idx])
                    start_idx = end_idx
                
                # Add remaining items to last group
                groups.append(data[start_idx:])
                return groups
                
            elif split_type == 'random':
                # Random split
                import random
                shuffled_data = data.copy()
                random.shuffle(shuffled_data)
                
                num_groups = split_criteria.get('num_groups', 2)
                group_size = len(data) // num_groups
                
                groups = []
                for i in range(num_groups):
                    start_idx = i * group_size
                    end_idx = start_idx + group_size if i < num_groups - 1 else len(shuffled_data)
                    groups.append(shuffled_data[start_idx:end_idx])
                
                return groups
            
            else:
                raise ValueError(f"Unknown split type: {split_type}")
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error splitting data: {str(e)}")

    # Helper methods
    @staticmethod
    def _calculate_gc_content(sequence: str) -> float:
        """Calculate GC content of sequence"""
        if not sequence:
            return 0.0
        gc_count = sequence.upper().count('G') + sequence.upper().count('C')
        return (gc_count / len(sequence)) * 100

    @staticmethod
    def _get_length_category(length: int) -> str:
        """Categorize sequence length"""
        if length < 100:
            return "short"
        elif length < 1000:
            return "medium"
        elif length < 10000:
            return "long"
        else:
            return "very_long"

    @staticmethod
    def _analyze_composition(sequence: str) -> Dict[str, float]:
        """Analyze nucleotide/amino acid composition"""
        if not sequence:
            return {}
        
        composition = Counter(sequence.upper())
        total = len(sequence)
        
        return {base: (count / total) * 100 for base, count in composition.items()}

    @staticmethod
    def _analyze_quality(quality_scores: List[int]) -> Dict[str, float]:
        """Analyze quality score statistics"""
        if not quality_scores:
            return {}
        
        return {
            "mean_quality": statistics.mean(quality_scores),
            "median_quality": statistics.median(quality_scores),
            "min_quality": min(quality_scores),
            "max_quality": max(quality_scores),
            "std_dev": statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0
        }

    @staticmethod
    def _get_similarity_group(sequence: Dict, parameters: Dict) -> str:
        """Get similarity group for sequence using k-mer analysis"""
        k = parameters.get('k_mer_size', 3)
        sequence_data = sequence.get('sequence', '')
        
        if len(sequence_data) < k:
            return "too_short"
        
        # Simple k-mer based grouping
        kmers = []
        for i in range(len(sequence_data) - k + 1):
            kmers.append(sequence_data[i:i+k])
        
        # Use first k-mer as group identifier (simplified)
        return kmers[0] if kmers else "ungrouped"

    @staticmethod
    async def batch_process(data: List[Dict], batch_size: int = 100, operation: str = "identity") -> List[List[Dict]]:
        """Process data in batches"""
        try:
            batches = []
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                if operation == "identity":
                    # No processing, just batching
                    processed_batch = batch
                elif operation == "shuffle":
                    # Shuffle each batch
                    import random
                    processed_batch = batch.copy()
                    random.shuffle(processed_batch)
                elif operation == "sort":
                    # Sort each batch
                    processed_batch = sorted(batch, key=lambda x: x.get('id', ''))
                else:
                    processed_batch = batch
                
                batches.append(processed_batch)
            
            return batches
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error batch processing: {str(e)}")

    @staticmethod
    async def aggregate_data(data: List[Dict], aggregation_method: str = "count") -> Dict[str, Any]:
        """Aggregate data using various methods"""
        try:
            result = {}
            
            if aggregation_method == "count":
                result = {
                    "total_items": len(data),
                    "count_by_type": Counter(item.get('type', 'unknown') for item in data)
                }
            elif aggregation_method == "statistics":
                if data and 'sequence' in data[0]:
                    lengths = [len(item.get('sequence', '')) for item in data]
                    gc_contents = [DataFlowService._calculate_gc_content(item.get('sequence', '')) for item in data]
                    
                    result = {
                        "sequence_count": len(data),
                        "length_stats": {
                            "mean": statistics.mean(lengths) if lengths else 0,
                            "median": statistics.median(lengths) if lengths else 0,
                            "min": min(lengths) if lengths else 0,
                            "max": max(lengths) if lengths else 0,
                            "std_dev": statistics.stdev(lengths) if len(lengths) > 1 else 0
                        },
                        "gc_stats": {
                            "mean": statistics.mean(gc_contents) if gc_contents else 0,
                            "median": statistics.median(gc_contents) if gc_contents else 0,
                            "min": min(gc_contents) if gc_contents else 0,
                            "max": max(gc_contents) if gc_contents else 0
                        }
                    }
                else:
                    result = {"total_items": len(data)}
            elif aggregation_method == "summary":
                result = {
                    "total_items": len(data),
                    "item_types": list(set(item.get('type', 'unknown') for item in data)),
                    "has_sequences": any('sequence' in item for item in data),
                    "has_annotations": any('annotations' in item for item in data)
                }
            
            return result
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error aggregating data: {str(e)}")

    @staticmethod
    async def validate_data_integrity(data: List[Dict], validation_rules: Dict) -> Dict[str, Any]:
        """Validate data integrity based on specified rules"""
        try:
            results = {
                "valid_items": [],
                "invalid_items": [],
                "validation_summary": {
                    "total_items": len(data),
                    "valid_count": 0,
                    "invalid_count": 0,
                    "errors": []
                }
            }
            
            for i, item in enumerate(data):
                is_valid = True
                item_errors = []
                
                # Required fields validation
                if 'required_fields' in validation_rules:
                    for field in validation_rules['required_fields']:
                        if field not in item or not item[field]:
                            is_valid = False
                            item_errors.append(f"Missing required field: {field}")
                
                # Sequence validation
                if 'validate_sequences' in validation_rules and validation_rules['validate_sequences']:
                    if 'sequence' in item:
                        sequence = item['sequence'].upper()
                        # Check for valid DNA/RNA/Protein characters
                        valid_chars = set('ATCGRYSWKMBDHVN-')  # DNA with IUPAC codes
                        if not set(sequence).issubset(valid_chars):
                            is_valid = False
                            item_errors.append("Invalid sequence characters")
                
                # Length validation
                if 'min_sequence_length' in validation_rules:
                    if 'sequence' in item:
                        if len(item['sequence']) < validation_rules['min_sequence_length']:
                            is_valid = False
                            item_errors.append(f"Sequence too short: {len(item['sequence'])}")
                
                # Custom validation rules
                if 'custom_rules' in validation_rules:
                    for rule_name, rule_func in validation_rules['custom_rules'].items():
                        try:
                            if not rule_func(item):
                                is_valid = False
                                item_errors.append(f"Failed custom rule: {rule_name}")
                        except Exception as e:
                            is_valid = False
                            item_errors.append(f"Error in custom rule {rule_name}: {str(e)}")
                
                if is_valid:
                    results["valid_items"].append(item)
                    results["validation_summary"]["valid_count"] += 1
                else:
                    results["invalid_items"].append({
                        "item": item,
                        "index": i,
                        "errors": item_errors
                    })
                    results["validation_summary"]["invalid_count"] += 1
                    results["validation_summary"]["errors"].extend(item_errors)
            
            return results
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error validating data: {str(e)}")