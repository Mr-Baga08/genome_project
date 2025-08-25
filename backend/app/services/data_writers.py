# backend/app/services/data_writers.py
import asyncio
import os
import json
import csv
import tempfile
from typing import Dict, List, Any, Optional, Union, TextIO
from dataclasses import dataclass
from pathlib import Path
import logging
import uuid
from datetime import datetime
import pandas as pd
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

@dataclass
class WriteOperation:
    """Data write operation result"""
    operation_id: str
    success: bool
    output_path: str
    format_type: str
    record_count: int
    file_size_bytes: int
    duration: float
    error_message: Optional[str] = None

class DataWritersService:
    """Service for writing biological data to various formats"""
    
    def __init__(self, output_directory: str = "/tmp/ugene_outputs"):
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        self.supported_formats = {
            'fasta': {
                'description': 'FASTA sequence format',
                'extensions': ['.fasta', '.fa', '.fas'],
                'writer_method': self._write_fasta
            },
            'fastq': {
                'description': 'FASTQ sequence format with quality scores',
                'extensions': ['.fastq', '.fq'],
                'writer_method': self._write_fastq
            },
            'gff3': {
                'description': 'General Feature Format version 3',
                'extensions': ['.gff3', '.gff'],
                'writer_method': self._write_gff3
            },
            'gtf': {
                'description': 'Gene Transfer Format',
                'extensions': ['.gtf'],
                'writer_method': self._write_gtf
            },
            'bed': {
                'description': 'Browser Extensible Data format',
                'extensions': ['.bed'],
                'writer_method': self._write_bed
            },
            'vcf': {
                'description': 'Variant Call Format',
                'extensions': ['.vcf'],
                'writer_method': self._write_vcf
            },
            'sam': {
                'description': 'Sequence Alignment/Map format',
                'extensions': ['.sam'],
                'writer_method': self._write_sam
            },
            'clustal': {
                'description': 'Clustal alignment format',
                'extensions': ['.aln', '.clustal'],
                'writer_method': self._write_clustal
            },
            'phylip': {
                'description': 'PHYLIP format',
                'extensions': ['.phy', '.phylip'],
                'writer_method': self._write_phylip
            },
            'stockholm': {
                'description': 'Stockholm alignment format',
                'extensions': ['.sto', '.stockholm'],
                'writer_method': self._write_stockholm
            },
            'csv': {
                'description': 'Comma-separated values',
                'extensions': ['.csv'],
                'writer_method': self._write_csv
            },
            'tsv': {
                'description': 'Tab-separated values',
                'extensions': ['.tsv', '.txt'],
                'writer_method': self._write_tsv
            },
            'json': {
                'description': 'JavaScript Object Notation',
                'extensions': ['.json'],
                'writer_method': self._write_json
            },
            'xml': {
                'description': 'Extensible Markup Language',
                'extensions': ['.xml'],
                'writer_method': self._write_xml
            }
        }
    
    async def write_sequences(
        self, 
        sequences: List[Dict], 
        format_type: str, 
        filename: str = None,
        parameters: Dict = None
    ) -> Dict:
        """Write sequences to specified format"""
        
        if format_type not in self.supported_formats:
            return {"error": f"Unsupported format: {format_type}"}
        
        if not sequences:
            return {"error": "No sequences provided"}
        
        if parameters is None:
            parameters = {}
        
        try:
            start_time = asyncio.get_event_loop().time()
            operation_id = str(uuid.uuid4())
            
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                extension = self.supported_formats[format_type]['extensions'][0]
                filename = f"sequences_{timestamp}_{operation_id[:8]}{extension}"
            
            # Ensure filename has correct extension
            if not any(filename.endswith(ext) for ext in self.supported_formats[format_type]['extensions']):
                extension = self.supported_formats[format_type]['extensions'][0]
                filename = f"{filename}{extension}"
            
            output_path = self.output_directory / filename
            
            # Get writer method
            writer_method = self.supported_formats[format_type]['writer_method']
            
            # Write data
            await writer_method(sequences, output_path, parameters)
            
            # Calculate metrics
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            file_size = output_path.stat().st_size if output_path.exists() else 0
            
            operation = WriteOperation(
                operation_id=operation_id,
                success=True,
                output_path=str(output_path),
                format_type=format_type,
                record_count=len(sequences),
                file_size_bytes=file_size,
                duration=duration
            )
            
            return {
                "status": "success",
                "operation": asdict(operation),
                "download_url": f"/download/{filename}",
                "file_info": {
                    "filename": filename,
                    "format": format_type,
                    "size_bytes": file_size,
                    "record_count": len(sequences)
                }
            }
            
        except Exception as e:
            logger.error(f"Error writing sequences to {format_type}: {str(e)}")
            return {"error": f"Write operation failed: {str(e)}"}
    
    async def _write_fasta(self, sequences: List[Dict], output_path: Path, parameters: Dict):
        """Write sequences in FASTA format"""
        
        line_length = parameters.get('line_length', 80)
        include_description = parameters.get('include_description', True)
        
        with open(output_path, 'w') as f:
            for seq in sequences:
                # Header line
                seq_id = seq.get('id', seq.get('name', 'unknown'))
                if include_description and seq.get('description'):
                    header = f">{seq_id} {seq['description']}"
                else:
                    header = f">{seq_id}"
                
                f.write(header + '\n')
                
                # Sequence lines (wrapped)
                sequence = seq.get('sequence', '')
                for i in range(0, len(sequence), line_length):
                    f.write(sequence[i:i + line_length] + '\n')
    
    async def _write_fastq(self, sequences: List[Dict], output_path: Path, parameters: Dict):
        """Write sequences in FASTQ format"""
        
        default_quality = parameters.get('default_quality', 'I' * 40)  # Default quality
        
        with open(output_path, 'w') as f:
            for seq in sequences:
                seq_id = seq.get('id', seq.get('name', 'unknown'))
                sequence = seq.get('sequence', '')
                quality = seq.get('quality', default_quality)
                
                # Ensure quality string matches sequence length
                if len(quality) != len(sequence):
                    quality = default_quality[:len(sequence)] or 'I' * len(sequence)
                
                # Write FASTQ record
                f.write(f"@{seq_id}\n")
                f.write(f"{sequence}\n")
                f.write("+\n")
                f.write(f"{quality}\n")
    
    async def _write_gff3(self, features: List[Dict], output_path: Path, parameters: Dict):
        """Write features in GFF3 format"""
        
        with open(output_path, 'w') as f:
            # GFF3 header
            f.write("##gff-version 3\n")
            
            # Add reference sequences if provided
            if 'reference_sequences' in parameters:
                for ref in parameters['reference_sequences']:
                    f.write(f"##sequence-region {ref['id']} 1 {ref['length']}\n")
            
            # Write features
            for feature in features:
                seqid = feature.get('seqid', feature.get('chromosome', 'unknown'))
                source = feature.get('source', 'ugene')
                feature_type = feature.get('type', feature.get('feature_type', 'feature'))
                start = feature.get('start', 1)
                end = feature.get('end', 1)
                score = feature.get('score', '.')
                strand = feature.get('strand', '.')
                phase = feature.get('phase', '.')
                
                # Build attributes
                attributes = []
                if 'id' in feature:
                    attributes.append(f"ID={feature['id']}")
                if 'name' in feature:
                    attributes.append(f"Name={feature['name']}")
                if 'parent' in feature:
                    attributes.append(f"Parent={feature['parent']}")
                
                # Add custom attributes
                for key, value in feature.get('attributes', {}).items():
                    if key not in ['ID', 'Name', 'Parent']:
                        attributes.append(f"{key}={value}")
                
                attributes_str = ';'.join(attributes) if attributes else '.'
                
                # Write GFF3 line
                f.write(f"{seqid}\t{source}\t{feature_type}\t{start}\t{end}\t{score}\t{strand}\t{phase}\t{attributes_str}\n")
    
    async def _write_gtf(self, features: List[Dict], output_path: Path, parameters: Dict):
        """Write features in GTF format"""
        
        with open(output_path, 'w') as f:
            for feature in features:
                seqname = feature.get('seqname', feature.get('chromosome', 'unknown'))
                source = feature.get('source', 'ugene')
                feature_type = feature.get('feature', feature.get('type', 'exon'))
                start = feature.get('start', 1)
                end = feature.get('end', 1)
                score = feature.get('score', '.')
                strand = feature.get('strand', '.')
                frame = feature.get('frame', '.')
                
                # Build attributes (GTF format)
                attributes = []
                if 'gene_id' in feature:
                    attributes.append(f'gene_id "{feature["gene_id"]}"')
                if 'transcript_id' in feature:
                    attributes.append(f'transcript_id "{feature["transcript_id"]}"')
                
                # Add other attributes
                for key, value in feature.get('attributes', {}).items():
                    if key not in ['gene_id', 'transcript_id']:
                        attributes.append(f'{key} "{value}"')
                
                attributes_str = '; '.join(attributes) if attributes else ''
                
                # Write GTF line
                f.write(f"{seqname}\t{source}\t{feature_type}\t{start}\t{end}\t{score}\t{strand}\t{frame}\t{attributes_str}\n")
    
    async def _write_bed(self, features: List[Dict], output_path: Path, parameters: Dict):
        """Write features in BED format"""
        
        track_name = parameters.get('track_name', 'UGENE_Features')
        track_description = parameters.get('track_description', 'Features from UGENE')
        
        with open(output_path, 'w') as f:
            # Track header
            f.write(f'track name="{track_name}" description="{track_description}"\n')
            
            for feature in features:
                chrom = feature.get('chrom', feature.get('chromosome', 'chr1'))
                start = feature.get('chromStart', feature.get('start', 1)) - 1  # BED is 0-based
                end = feature.get('chromEnd', feature.get('end', 1))
                name = feature.get('name', f"feature_{uuid.uuid4()}")
                score = feature.get('score', 0)
                strand = feature.get('strand', '.')
                
                # Basic BED format (3-6 columns)
                bed_line = f"{chrom}\t{start}\t{end}"
                
                if name:
                    bed_line += f"\t{name}"
                    
                    if score is not None:
                        bed_line += f"\t{score}"
                        
                        if strand:
                            bed_line += f"\t{strand}"
                
                f.write(bed_line + '\n')
    
    async def _write_vcf(self, variants: List[Dict], output_path: Path, parameters: Dict):
        """Write variants in VCF format"""
        
        with open(output_path, 'w') as f:
            # VCF header
            f.write("##fileformat=VCFv4.3\n")
            f.write("##source=UGENE Web Platform\n")
            f.write(f"##fileDate={datetime.utcnow().strftime('%Y%m%d')}\n")
            
            # INFO field definitions
            f.write("##INFO=<ID=DP,Number=1,Type=Integer,Description=\"Total Depth\">\n")
            f.write("##INFO=<ID=AF,Number=A,Type=Float,Description=\"Allele Frequency\">\n")
            
            # FORMAT field definitions
            f.write("##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n")
            f.write("##FORMAT=<ID=GQ,Number=1,Type=Integer,Description=\"Genotype Quality\">\n")
            
            # Column header
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")
            
            # Variant records
            for variant in variants:
                chrom = variant.get('chromosome', 'chr1')
                pos = variant.get('position', 1)
                var_id = variant.get('id', '.')
                ref = variant.get('ref_allele', 'A')
                alt = variant.get('alt_allele', 'T')
                qual = variant.get('quality', 30)
                filter_status = variant.get('filter', 'PASS')
                
                # Build INFO field
                info_parts = []
                if 'depth' in variant:
                    info_parts.append(f"DP={variant['depth']}")
                if 'allele_frequency' in variant:
                    info_parts.append(f"AF={variant['allele_frequency']:.4f}")
                info_str = ';'.join(info_parts) if info_parts else '.'
                
                # FORMAT and sample data
                format_str = "GT:GQ"
                sample_data = variant.get('genotype', {})
                sample_str = f"{sample_data.get('GT', '0/1')}:{sample_data.get('GQ', 30)}"
                
                f.write(f"{chrom}\t{pos}\t{var_id}\t{ref}\t{alt}\t{qual}\t{filter_status}\t{info_str}\t{format_str}\t{sample_str}\n")
    
    async def _write_sam(self, alignments: List[Dict], output_path: Path, parameters: Dict):
        """Write alignments in SAM format"""
        
        with open(output_path, 'w') as f:
            # SAM header
            f.write("@HD\tVN:1.6\tSO:unsorted\n")
            f.write("@PG\tID:ugene\tPN:UGENE Web Platform\tVN:1.0\n")
            
            # Reference sequences
            if 'reference_sequences' in parameters:
                for ref in parameters['reference_sequences']:
                    f.write(f"@SQ\tSN:{ref['name']}\tLN:{ref['length']}\n")
            
            # Alignment records
            for alignment in alignments:
                qname = alignment.get('query_name', 'unknown')
                flag = alignment.get('flag', 0)
                rname = alignment.get('reference_name', '*')
                pos = alignment.get('position', 0)
                mapq = alignment.get('mapping_quality', 60)
                cigar = alignment.get('cigar', '*')
                rnext = alignment.get('mate_reference', '*')
                pnext = alignment.get('mate_position', 0)
                tlen = alignment.get('template_length', 0)
                seq = alignment.get('sequence', '*')
                qual = alignment.get('quality', '*')
                
                f.write(f"{qname}\t{flag}\t{rname}\t{pos}\t{mapq}\t{cigar}\t{rnext}\t{pnext}\t{tlen}\t{seq}\t{qual}\n")
    
    async def _write_clustal(self, aligned_sequences: List[Dict], output_path: Path, parameters: Dict):
        """Write multiple sequence alignment in Clustal format"""
        
        with open(output_path, 'w') as f:
            f.write("CLUSTAL W (1.83) multiple sequence alignment\n\n")
            
            if not aligned_sequences:
                return
            
            # Calculate maximum name length for formatting
            max_name_length = max(len(seq.get('name', '')) for seq in aligned_sequences)
            max_name_length = max(max_name_length, 10)
            
            # Get alignment length
            alignment_length = len(aligned_sequences[0].get('sequence', '')) if aligned_sequences else 0
            
            # Write alignment in blocks
            block_size = parameters.get('block_size', 60)
            
            for start in range(0, alignment_length, block_size):
                for seq in aligned_sequences:
                    name = seq.get('name', 'unknown')[:max_name_length].ljust(max_name_length)
                    sequence_block = seq.get('sequence', '')[start:start + block_size]
                    f.write(f"{name} {sequence_block}\n")
                
                # Add conservation line
                conservation = self._calculate_conservation_line(
                    [seq.get('sequence', '')[start:start + block_size] for seq in aligned_sequences]
                )
                f.write(' ' * (max_name_length + 1) + conservation + '\n\n')
    
    async def _write_phylip(self, aligned_sequences: List[Dict], output_path: Path, parameters: Dict):
        """Write multiple sequence alignment in PHYLIP format"""
        
        with open(output_path, 'w') as f:
            if not aligned_sequences:
                f.write("0 0\n")
                return
            
            seq_count = len(aligned_sequences)
            seq_length = len(aligned_sequences[0].get('sequence', ''))
            
            # Header
            f.write(f"{seq_count} {seq_length}\n")
            
            # Sequences
            for seq in aligned_sequences:
                name = seq.get('name', 'unknown')[:10].ljust(10)  # PHYLIP name limit
                sequence = seq.get('sequence', '')
                f.write(f"{name} {sequence}\n")
    
    async def _write_stockholm(self, aligned_sequences: List[Dict], output_path: Path, parameters: Dict):
        """Write multiple sequence alignment in Stockholm format"""
        
        with open(output_path, 'w') as f:
            f.write("# STOCKHOLM 1.0\n")
            
            if aligned_sequences:
                max_name_length = max(len(seq.get('name', '')) for seq in aligned_sequences)
                
                for seq in aligned_sequences:
                    name = seq.get('name', 'unknown').ljust(max_name_length)
                    sequence = seq.get('sequence', '')
                    f.write(f"{name} {sequence}\n")
            
            f.write("//\n")
    
    async def _write_csv(self, data: List[Dict], output_path: Path, parameters: Dict):
        """Write data in CSV format"""
        
        if not data:
            # Write empty CSV
            with open(output_path, 'w') as f:
                f.write("")
            return
        
        # Get all possible field names
        fieldnames = set()
        for record in data:
            fieldnames.update(record.keys())
        
        fieldnames = sorted(fieldnames)
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    
    async def _write_tsv(self, data: List[Dict], output_path: Path, parameters: Dict):
        """Write data in TSV format"""
        
        if not data:
            with open(output_path, 'w') as f:
                f.write("")
            return
        
        fieldnames = set()
        for record in data:
            fieldnames.update(record.keys())
        
        fieldnames = sorted(fieldnames)
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()
            writer.writerows(data)
    
    async def _write_json(self, data: List[Dict], output_path: Path, parameters: Dict):
        """Write data in JSON format"""
        
        pretty_print = parameters.get('pretty_print', True)
        
        with open(output_path, 'w') as f:
            if pretty_print:
                json.dump(data, f, indent=2, default=str)
            else:
                json.dump(data, f, default=str)
    
    async def _write_xml(self, data: List[Dict], output_path: Path, parameters: Dict):
        """Write data in XML format"""
        
        root_element = parameters.get('root_element', 'data')
        record_element = parameters.get('record_element', 'record')
        
        # Create XML structure
        root = ET.Element(root_element)
        
        for record in data:
            record_elem = ET.SubElement(root, record_element)
            
            for key, value in record.items():
                child_elem = ET.SubElement(record_elem, key)
                child_elem.text = str(value)
        
        # Write XML
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
    
    def _calculate_conservation_line(self, sequence_blocks: List[str]) -> str:
        """Calculate conservation line for Clustal format"""
        
        if not sequence_blocks:
            return ""
        
        conservation = ""
        block_length = len(sequence_blocks[0]) if sequence_blocks else 0
        
        for pos in range(block_length):
            chars = [block[pos] for block in sequence_blocks if pos < len(block)]
            non_gap_chars = [c for c in chars if c != '-']
            
            if len(set(non_gap_chars)) == 1 and non_gap_chars:
                conservation += "*"  # Fully conserved
            elif len(set(non_gap_chars)) <= 2 and len(non_gap_chars) > 1:
                conservation += ":"  # Strongly similar
            elif len(non_gap_chars) > 1:
                conservation += "."  # Weakly similar
            else:
                conservation += " "  # No conservation
        
        return conservation
    
    async def write_analysis_results(
        self, 
        analysis_results: Dict, 
        format_type: str = "json",
        filename: str = None
    ) -> Dict:
        """Write analysis results to file"""
        
        try:
            if filename is None:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                analysis_type = analysis_results.get('analysis_type', 'analysis')
                filename = f"{analysis_type}_results_{timestamp}.{format_type}"
            
            output_path = self.output_directory / filename
            
            if format_type == "json":
                with open(output_path, 'w') as f:
                    json.dump(analysis_results, f, indent=2, default=str)
            
            elif format_type == "csv":
                # Convert results to tabular format
                if 'results' in analysis_results and isinstance(analysis_results['results'], list):
                    df = pd.DataFrame(analysis_results['results'])
                    df.to_csv(output_path, index=False)
                else:
                    # Flatten dictionary for CSV
                    flattened = self._flatten_dict(analysis_results)
                    df = pd.DataFrame([flattened])
                    df.to_csv(output_path, index=False)
            
            elif format_type == "excel":
                if 'results' in analysis_results:
                    # Create Excel file with multiple sheets
                    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                        # Summary sheet
                        summary_data = {k: v for k, v in analysis_results.items() if k != 'results'}
                        summary_df = pd.DataFrame([self._flatten_dict(summary_data)])
                        summary_df.to_excel(writer, sheet_name='Summary', index=False)
                        
                        # Results sheet
                        if isinstance(analysis_results['results'], list):
                            results_df = pd.DataFrame(analysis_results['results'])
                            results_df.to_excel(writer, sheet_name='Results', index=False)
                else:
                    df = pd.DataFrame([self._flatten_dict(analysis_results)])
                    df.to_excel(output_path, index=False)
            
            else:
                return {"error": f"Unsupported format for analysis results: {format_type}"}
            
            file_size = output_path.stat().st_size
            
            return {
                "status": "success",
                "filename": filename,
                "file_path": str(output_path),
                "file_size": file_size,
                "format": format_type,
                "download_url": f"/download/{filename}"
            }
            
        except Exception as e:
            logger.error(f"Error writing analysis results: {str(e)}")
            return {"error": f"Failed to write analysis results: {str(e)}"}
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dictionary for tabular formats"""
        
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                # Convert list of dicts to summary statistics
                items.append((f"{new_key}_count", len(v)))
                if all(isinstance(item, (int, float)) for item in v):
                    items.append((f"{new_key}_mean", np.mean(v)))
                    items.append((f"{new_key}_std", np.std(v)))
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    async def get_supported_formats(self) -> Dict:
        """Get list of supported output formats"""
        
        return {
            "formats": {
                name: {
                    "description": info["description"],
                    "extensions": info["extensions"],
                    "suitable_for": self._get_format_use_cases(name)
                }
                for name, info in self.supported_formats.items()
            }
        }
    
    def _get_format_use_cases(self, format_name: str) -> List[str]:
        """Get use cases for specific format"""
        
        use_cases = {
            'fasta': ['Sequence storage', 'Database submission', 'Tool input'],
            'fastq': ['Raw sequencing data', 'Quality-aware analysis'],
            'gff3': ['Genome annotation', 'Feature visualization'],
            'gtf': ['Gene annotation', 'RNA-seq analysis'],
            'bed': ['Genome browser tracks', 'Region analysis'],
            'vcf': ['Variant calling results', 'Population genetics'],
            'sam': ['Read alignments', 'Mapping results'],
            'clustal': ['Multiple sequence alignments', 'Phylogenetic analysis'],
            'phylip': ['Phylogenetic software input', 'Distance matrices'],
            'stockholm': ['Protein families', 'RNA structures'],
            'csv': ['Data analysis', 'Spreadsheet import'],
            'tsv': ['Bioinformatics tools', 'Database import'],
            'json': ['Web APIs', 'Data interchange'],
            'xml': ['Structured data', 'Database exchange']
        }
        
        return use_cases.get(format_name, ['General data storage'])
    
    async def batch_write_sequences(
        self, 
        sequence_batches: List[Dict], 
        format_configs: List[Dict]
    ) -> Dict:
        """Write multiple sequence sets to different formats"""
        
        if len(sequence_batches) != len(format_configs):
            return {"error": "Number of sequence batches must match number of format configurations"}
        
        results = []
        successful_writes = 0
        failed_writes = 0
        
        try:
            for i, (sequences, format_config) in enumerate(zip(sequence_batches, format_configs)):
                try:
                    result = await self.write_sequences(
                        sequences,
                        format_config.get('format', 'fasta'),
                        format_config.get('filename'),
                        format_config.get('parameters', {})
                    )
                    
                    results.append({
                        "batch_index": i,
                        "result": result
                    })
                    
                    if result.get("status") == "success":
                        successful_writes += 1
                    else:
                        failed_writes += 1
                        
                except Exception as e:
                    results.append({
                        "batch_index": i,
                        "result": {"error": str(e)}
                    })
                    failed_writes += 1
            
            return {
                "status": "completed",
                "total_batches": len(sequence_batches),
                "successful_writes": successful_writes,
                "failed_writes": failed_writes,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in batch write operation: {str(e)}")
            return {"error": f"Batch write failed: {str(e)}"}
    
    async def cleanup_old_files(self, max_age_hours: int = 24) -> Dict:
        """Clean up old output files"""
        
        try:
            cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
            
            cleaned_files = 0
            freed_space_bytes = 0
            
            for file_path in self.output_directory.iterdir():
                if file_path.is_file():
                    file_stat = file_path.stat()
                    
                    if file_stat.st_mtime < cutoff_time:
                        freed_space_bytes += file_stat.st_size
                        file_path.unlink()
                        cleaned_files += 1
            
            return {
                "status": "success",
                "cleaned_files": cleaned_files,
                "freed_space_mb": freed_space_bytes / (1024 * 1024),
                "max_age_hours": max_age_hours
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")
            return {"error": f"Cleanup failed: {str(e)}"}

# Global service instance
data_writers_service = DataWritersService()