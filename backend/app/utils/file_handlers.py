# backend/app/utils/file_handlers.py
import io
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FileHandler:
    """Handles parsing and writing of various bioinformatics file formats"""
    
    def __init__(self):
        self.supported_formats = {
            'fasta': ['.fasta', '.fa', '.fas', '.fna', '.ffn', '.faa'],
            'fastq': ['.fastq', '.fq'],
            'gff': ['.gff', '.gff3', '.gtf'],
            'sam': ['.sam'],
            'bed': ['.bed'],
            'vcf': ['.vcf'],
            'genbank': ['.gb', '.gbk', '.genbank'],
            'embl': ['.embl'],
            'phylip': ['.phy', '.phylip'],
            'nexus': ['.nex', '.nexus'],
            'newick': ['.newick', '.nwk', '.tree'],
            'clustal': ['.aln', '.clustal'],
            'stockholm': ['.sto', '.stockholm']
        }
    
    def detect_file_format(self, filename: str, content: Optional[str] = None) -> str:
        """Detect file format based on extension and content"""
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        
        # Try extension first
        for format_name, extensions in self.supported_formats.items():
            if extension in extensions:
                return format_name
        
        # Try content detection if available
        if content:
            return self._detect_format_by_content(content)
        
        return 'unknown'
    
    def _detect_format_by_content(self, content: str) -> str:
        """Detect format based on file content"""
        lines = content.strip().split('\n')
        if not lines:
            return 'unknown'
        
        first_line = lines[0].strip()
        
        if first_line.startswith('>'):
            return 'fasta'
        elif first_line.startswith('@') and len(lines) >= 4:
            return 'fastq'
        elif first_line.startswith('##gff-version'):
            return 'gff'
        elif first_line.startswith('##fileformat=VCF'):
            return 'vcf'
        elif first_line.startswith('@HD') or first_line.startswith('@SQ'):
            return 'sam'
        elif re.match(r'^chr\w+\s+\d+\s+\d+', first_line):
            return 'bed'
        elif 'LOCUS' in first_line and 'bp' in first_line:
            return 'genbank'
        elif first_line.startswith('ID   '):
            return 'embl'
        elif first_line.strip().split() and first_line.strip().split()[0].isdigit():
            return 'phylip'
        elif first_line.startswith('#NEXUS'):
            return 'nexus'
        elif re.match(r'^\(.*\);?$', first_line):
            return 'newick'
        elif 'CLUSTAL' in first_line.upper():
            return 'clustal'
        elif first_line.startswith('# STOCKHOLM'):
            return 'stockholm'
        
        return 'unknown'
    
    # FASTA Format Handlers
    async def parse_fasta_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse FASTA format content"""
        sequences = []
        current_header = None
        current_sequence = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('>'):
                # Save previous sequence
                if current_header is not None:
                    sequences.append({
                        'name': current_header.split()[0],
                        'description': ' '.join(current_header.split()[1:]) if len(current_header.split()) > 1 else '',
                        'sequence': ''.join(current_sequence),
                        'length': len(''.join(current_sequence))
                    })
                
                # Start new sequence
                current_header = line[1:]
                current_sequence = []
            else:
                current_sequence.append(line)
        
        # Don't forget the last sequence
        if current_header is not None:
            sequences.append({
                'name': current_header.split()[0],
                'description': ' '.join(current_header.split()[1:]) if len(current_header.split()) > 1 else '',
                'sequence': ''.join(current_sequence),
                'length': len(''.join(current_sequence))
            })
        
        return sequences
    
    def write_fasta_content(self, sequences: List[Dict[str, Any]], line_length: int = 80) -> str:
        """Write sequences to FASTA format"""
        output = []
        
        for seq_data in sequences:
            header = f">{seq_data['name']}"
            if seq_data.get('description'):
                header += f" {seq_data['description']}"
            
            output.append(header)
            
            # Break sequence into lines
            sequence = seq_data['sequence']
            for i in range(0, len(sequence), line_length):
                output.append(sequence[i:i + line_length])
        
        return '\n'.join(output)
    
    # FASTQ Format Handlers
    async def parse_fastq_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse FASTQ format content"""
        sequences = []
        lines = content.strip().split('\n')
        
        i = 0
        while i < len(lines):
            if lines[i].startswith('@'):
                if i + 3 < len(lines):
                    header = lines[i][1:]  # Remove @
                    sequence = lines[i + 1]
                    plus_line = lines[i + 2]
                    quality = lines[i + 3]
                    
                    if plus_line.startswith('+'):
                        sequences.append({
                            'name': header.split()[0],
                            'description': ' '.join(header.split()[1:]) if len(header.split()) > 1 else '',
                            'sequence': sequence,
                            'quality': quality,
                            'length': len(sequence),
                            'average_quality': self._calculate_average_quality(quality)
                        })
                    
                    i += 4
                else:
                    break
            else:
                i += 1
        
        return sequences
    
    def _calculate_average_quality(self, quality_string: str) -> float:
        """Calculate average quality score from FASTQ quality string"""
        if not quality_string:
            return 0.0
        
        # Convert ASCII to Phred scores (assuming Phred+33 encoding)
        quality_scores = [ord(char) - 33 for char in quality_string]
        return sum(quality_scores) / len(quality_scores)
    
    def write_fastq_content(self, sequences: List[Dict[str, Any]]) -> str:
        """Write sequences to FASTQ format"""
        output = []
        
        for seq_data in sequences:
            header = f"@{seq_data['name']}"
            if seq_data.get('description'):
                header += f" {seq_data['description']}"
            
            output.extend([
                header,
                seq_data['sequence'],
                '+',
                seq_data.get('quality', 'I' * len(seq_data['sequence']))  # Default high quality
            ])
        
        return '\n'.join(output)
    
    # GFF/GTF Format Handlers
    async def parse_gff_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse GFF/GTF format content"""
        features = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            fields = line.split('\t')
            if len(fields) >= 9:
                attributes = self._parse_gff_attributes(fields[8])
                
                features.append({
                    'seqid': fields[0],
                    'source': fields[1],
                    'type': fields[2],
                    'start': int(fields[3]),
                    'end': int(fields[4]),
                    'score': float(fields[5]) if fields[5] != '.' else None,
                    'strand': fields[6],
                    'phase': int(fields[7]) if fields[7] != '.' else None,
                    'attributes': attributes
                })
        
        return features
    
    def _parse_gff_attributes(self, attr_string: str) -> Dict[str, str]:
        """Parse GFF attributes string"""
        attributes = {}
        
        # Handle different attribute formats (GFF3 vs GTF)
        if '=' in attr_string:  # GFF3 format
            for attr in attr_string.split(';'):
                if '=' in attr:
                    key, value = attr.split('=', 1)
                    attributes[key.strip()] = value.strip()
        else:  # GTF format
            for attr in attr_string.split(';'):
                if attr.strip():
                    parts = attr.strip().split(' ', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip().strip('"')
                        attributes[key] = value
        
        return attributes
    
    def write_gff_content(self, features: List[Dict[str, Any]], version: str = "3") -> str:
        """Write features to GFF format"""
        output = [f"##gff-version {version}"]
        
        for feature in features:
            fields = [
                feature['seqid'],
                feature['source'],
                feature['type'],
                str(feature['start']),
                str(feature['end']),
                str(feature['score']) if feature.get('score') is not None else '.',
                feature['strand'],
                str(feature['phase']) if feature.get('phase') is not None else '.',
                self._format_gff_attributes(feature.get('attributes', {}))
            ]
            output.append('\t'.join(fields))
        
        return '\n'.join(output)
    
    def _format_gff_attributes(self, attributes: Dict[str, str]) -> str:
        """Format attributes for GFF output"""
        attr_strings = []
        for key, value in attributes.items():
            attr_strings.append(f"{key}={value}")
        return ';'.join(attr_strings)
    
    # BED Format Handlers
    async def parse_bed_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse BED format content"""
        features = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('track') or line.startswith('browser'):
                continue
            
            fields = line.split('\t')
            if len(fields) >= 3:
                feature = {
                    'chrom': fields[0],
                    'chromStart': int(fields[1]),
                    'chromEnd': int(fields[2])
                }
                
                # Optional BED fields
                if len(fields) > 3:
                    feature['name'] = fields[3]
                if len(fields) > 4:
                    feature['score'] = int(fields[4])
                if len(fields) > 5:
                    feature['strand'] = fields[5]
                if len(fields) > 6:
                    feature['thickStart'] = int(fields[6])
                if len(fields) > 7:
                    feature['thickEnd'] = int(fields[7])
                if len(fields) > 8:
                    feature['itemRgb'] = fields[8]
                if len(fields) > 9:
                    feature['blockCount'] = int(fields[9])
                if len(fields) > 10:
                    feature['blockSizes'] = [int(x) for x in fields[10].split(',') if x]
                if len(fields) > 11:
                    feature['blockStarts'] = [int(x) for x in fields[11].split(',') if x]
                
                features.append(feature)
        
        return features
    
    # VCF Format Handlers
    async def parse_vcf_content(self, content: str) -> Dict[str, Any]:
        """Parse VCF format content"""
        header_lines = []
        variants = []
        
        lines = content.split('\n')
        header_processed = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('##'):
                header_lines.append(line)
            elif line.startswith('#CHROM'):
                column_headers = line[1:].split('\t')
                header_processed = True
            elif header_processed:
                fields = line.split('\t')
                if len(fields) >= 8:
                    variant = {
                        'CHROM': fields[0],
                        'POS': int(fields[1]),
                        'ID': fields[2] if fields[2] != '.' else None,
                        'REF': fields[3],
                        'ALT': fields[4].split(','),
                        'QUAL': float(fields[5]) if fields[5] != '.' else None,
                        'FILTER': fields[6] if fields[6] != '.' else None,
                        'INFO': self._parse_vcf_info(fields[7])
                    }
                    
                    # Sample data if present
                    if len(fields) > 9:
                        variant['FORMAT'] = fields[8]
                        variant['SAMPLES'] = fields[9:]
                    
                    variants.append(variant)
        
        return {
            'header': header_lines,
            'variants': variants,
            'variant_count': len(variants)
        }
    
    def _parse_vcf_info(self, info_string: str) -> Dict[str, Any]:
        """Parse VCF INFO field"""
        info = {}
        if info_string and info_string != '.':
            for item in info_string.split(';'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    # Try to convert to appropriate type
                    try:
                        if '.' in value:
                            info[key] = float(value)
                        else:
                            info[key] = int(value)
                    except ValueError:
                        info[key] = value
                else:
                    info[item] = True
        return info
    
    # Alignment Format Handlers
    async def parse_clustal_content(self, content: str) -> Dict[str, Any]:
        """Parse Clustal alignment format"""
        lines = content.split('\n')
        if not lines or not lines[0].startswith('CLUSTAL'):
            raise ValueError("Not a valid Clustal format file")
        
        sequences = {}
        sequence_order = []
        
        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith('*') or line.startswith(':') or line.startswith('.'):
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                seq_name = parts[0]
                seq_data = parts[1]
                
                if seq_name not in sequences:
                    sequences[seq_name] = []
                    sequence_order.append(seq_name)
                
                sequences[seq_name].append(seq_data)
        
        # Convert to final format
        aligned_sequences = []
        for seq_name in sequence_order:
            aligned_sequences.append({
                'name': seq_name,
                'sequence': ''.join(sequences[seq_name]),
                'length': len(''.join(sequences[seq_name]))
            })
        
        return {
            'aligned_sequences': aligned_sequences,
            'alignment_length': len(aligned_sequences[0]['sequence']) if aligned_sequences else 0,
            'sequence_count': len(aligned_sequences)
        }
    
    # Newick Tree Format Handlers
    async def parse_newick_content(self, content: str) -> Dict[str, Any]:
        """Parse Newick tree format"""
        tree_string = content.strip()
        if not tree_string.endswith(';'):
            tree_string += ';'
        
        # Basic parsing - for full functionality, use a proper tree parser like Bio.Phylo
        node_count = tree_string.count('(') + tree_string.count(')')
        leaf_names = []
        
        # Extract leaf names (simplified)
        import re
        leaf_pattern = r'([A-Za-z0-9_]+)(?::\d*\.?\d*)?'
        matches = re.findall(leaf_pattern, tree_string)
        leaf_names = [match for match in matches if not match.isdigit()]
        
        return {
            'newick_string': tree_string,
            'leaf_names': leaf_names,
            'leaf_count': len(leaf_names),
            'node_count': node_count,
            'has_branch_lengths': ':' in tree_string
        }
    
    # Generic annotation parsing
    async def parse_annotations_file(self, content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Parse annotations from various file formats"""
        content_str = content.decode('utf-8')
        file_format = self.detect_file_format(filename, content_str)
        
        if file_format == 'gff':
            features = await self.parse_gff_content(content_str)
            return [self._gff_to_annotation(feature) for feature in features]
        elif file_format == 'bed':
            features = await self.parse_bed_content(content_str)
            return [self._bed_to_annotation(feature) for feature in features]
        else:
            # Try to parse as simple tab-delimited annotation file
            return await self._parse_simple_annotations(content_str)
    
    def _gff_to_annotation(self, gff_feature: Dict[str, Any]) -> Dict[str, Any]:
        """Convert GFF feature to standard annotation format"""
        return {
            'feature_type': gff_feature['type'],
            'start_position': gff_feature['start'],
            'end_position': gff_feature['end'],
            'strand': gff_feature['strand'],
            'score': gff_feature.get('score'),
            'attributes': gff_feature.get('attributes', {})
        }
    
    def _bed_to_annotation(self, bed_feature: Dict[str, Any]) -> Dict[str, Any]:
        """Convert BED feature to standard annotation format"""
        return {
            'feature_type': bed_feature.get('name', 'region'),
            'start_position': bed_feature['chromStart'] + 1,  # Convert to 1-based
            'end_position': bed_feature['chromEnd'],
            'strand': bed_feature.get('strand', '.'),
            'score': bed_feature.get('score'),
            'attributes': {
                'chrom': bed_feature['chrom'],
                'thick_start': bed_feature.get('thickStart'),
                'thick_end': bed_feature.get('thickEnd'),
                'item_rgb': bed_feature.get('itemRgb')
            }
        }
    
    async def _parse_simple_annotations(self, content: str) -> List[Dict[str, Any]]:
        """Parse simple tab-delimited annotation file"""
        annotations = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            fields = line.split('\t')
            if len(fields) >= 3:
                try:
                    annotations.append({
                        'feature_type': fields[0],
                        'start_position': int(fields[1]),
                        'end_position': int(fields[2]),
                        'strand': fields[3] if len(fields) > 3 else '.',
                        'attributes': {
                            'description': fields[4] if len(fields) > 4 else ''
                        }
                    })
                except ValueError:
                    continue  # Skip malformed lines
        
        return annotations
    
    # File validation
    def validate_file_format(self, content: str, expected_format: str) -> Tuple[bool, List[str]]:
        """Validate file content against expected format"""
        errors = []
        
        if expected_format == 'fasta':
            if not content.strip().startswith('>'):
                errors.append("FASTA files must start with '>'")
            
            # Check for proper FASTA structure
            lines = content.split('\n')
            in_sequence = False
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('>'):
                    in_sequence = True
                elif in_sequence:
                    if not re.match(r'^[ATCGRYSWKMBDHVN-]+$', line.upper()):
                        errors.append(f"Line {i+1}: Invalid characters in sequence")
        
        elif expected_format == 'fastq':
            lines = [line for line in content.split('\n') if line.strip()]
            if len(lines) % 4 != 0:
                errors.append("FASTQ files must have records in groups of 4 lines")
            
            for i in range(0, len(lines), 4):
                if i + 3 < len(lines):
                    if not lines[i].startswith('@'):
                        errors.append(f"Line {i+1}: Header line must start with '@'")
                    if not lines[i+2].startswith('+'):
                        errors.append(f"Line {i+3}: Plus line must start with '+'")
                    if len(lines[i+1]) != len(lines[i+3]):
                        errors.append(f"Line {i+1}: Sequence and quality lengths don't match")
        
        return len(errors) == 0, errors
    
    # Export functions
    def export_analysis_results(self, results: Dict[str, Any], format: str) -> str:
        """Export analysis results in specified format"""
        if format == 'json':
            return json.dumps(results, indent=2, default=str)
        elif format == 'csv':
            return self._results_to_csv(results)
        elif format == 'tsv':
            return self._results_to_tsv(results)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _results_to_csv(self, results: Dict[str, Any]) -> str:
        """Convert analysis results to CSV format"""
        output = io.StringIO()
        
        # This is a simplified implementation
        # Real implementation would depend on the specific result structure
        if 'results' in results and isinstance(results['results'], list):
            if results['results']:
                fieldnames = results['results'][0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results['results'])
        
        return output.getvalue()
    
    def _results_to_tsv(self, results: Dict[str, Any]) -> str:
        """Convert analysis results to TSV format"""
        csv_content = self._results_to_csv(results)
        return csv_content.replace(',', '\t')
    
    # Utility functions
    def get_file_statistics(self, content: str, file_format: str) -> Dict[str, Any]:
        """Get statistics about a file"""
        stats = {
            'file_size': len(content.encode('utf-8')),
            'line_count': len(content.split('\n')),
            'character_count': len(content)
        }
        
        if file_format == 'fasta':
            sequences = []
            current_seq = ""
            for line in content.split('\n'):
                if line.startswith('>'):
                    if current_seq:
                        sequences.append(current_seq)
                        current_seq = ""
                else:
                    current_seq += line.strip()
            if current_seq:
                sequences.append(current_seq)
            
            stats.update({
                'sequence_count': len(sequences),
                'total_bases': sum(len(seq) for seq in sequences),
                'average_length': sum(len(seq) for seq in sequences) / len(sequences) if sequences else 0,
                'min_length': min(len(seq) for seq in sequences) if sequences else 0,
                'max_length': max(len(seq) for seq in sequences) if sequences else 0
            })
        
        return stats