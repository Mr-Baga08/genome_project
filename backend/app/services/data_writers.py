# backend/app/services/data_writers.py
import io
import json
import csv
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from Bio import SeqIO
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
import tempfile
from pathlib import Path

class DataWriterService:
    """Service for writing various biological data formats"""
    
    @staticmethod
    async def write_alignment(sequences: List[Dict], format_type: str = "fasta") -> str:
        """Write alignment to various formats"""
        try:
            output = io.StringIO()
            
            if format_type.lower() == "fasta":
                for seq in sequences:
                    output.write(f">{seq['id']}\n{seq['sequence']}\n")
            elif format_type.lower() == "clustal":
                # Write Clustal format
                output.write("CLUSTAL W (1.83) multiple sequence alignment\n\n")
                max_name_len = max(len(seq['id']) for seq in sequences)
                
                # Write sequences in blocks
                seq_length = len(sequences[0]['sequence']) if sequences else 0
                block_size = 60
                
                for start in range(0, seq_length, block_size):
                    for seq in sequences:
                        name = seq['id'].ljust(max_name_len)
                        sequence_block = seq['sequence'][start:start + block_size]
                        output.write(f"{name} {sequence_block}\n")
                    output.write("\n")
            elif format_type.lower() == "phylip":
                # Write PHYLIP format
                output.write(f"{len(sequences)} {len(sequences[0]['sequence']) if sequences else 0}\n")
                for seq in sequences:
                    # PHYLIP format: 10 characters for name, then sequence
                    name = seq['id'][:10].ljust(10)
                    output.write(f"{name}{seq['sequence']}\n")
            
            return output.getvalue()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error writing alignment: {str(e)}")

    @staticmethod
    async def write_annotations(annotations: List[Dict], format_type: str = "gff3") -> str:
        """Write annotations to various formats"""
        try:
            output = io.StringIO()
            
            if format_type.lower() == "gff3":
                output.write("##gff-version 3\n")
                for ann in annotations:
                    attributes = ";".join([f"{k}={v}" for k, v in ann.get('attributes', {}).items()])
                    line = f"{ann['seqid']}\t{ann['source']}\t{ann['type']}\t{ann['start']}\t{ann['end']}\t{ann.get('score', '.')}\t{ann['strand']}\t{ann.get('phase', '.')}\t{attributes}\n"
                    output.write(line)
            elif format_type.lower() == "bed":
                for ann in annotations:
                    line = f"{ann['chrom']}\t{ann['start']}\t{ann['end']}"
                    if 'name' in ann and ann['name']:
                        line += f"\t{ann['name']}"
                    if 'score' in ann and ann['score'] is not None:
                        line += f"\t{ann['score']}"
                    if 'strand' in ann and ann['strand']:
                        line += f"\t{ann['strand']}"
                    line += "\n"
                    output.write(line)
            elif format_type.lower() == "gtf":
                for ann in annotations:
                    attributes = " ".join([f'{k} "{v}";' for k, v in ann.get('attributes', {}).items()])
                    line = f"{ann['seqid']}\t{ann['source']}\t{ann['type']}\t{ann['start']}\t{ann['end']}\t{ann.get('score', '.')}\t{ann['strand']}\t{ann.get('phase', '.')}\t{attributes}\n"
                    output.write(line)
            
            return output.getvalue()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error writing annotations: {str(e)}")

    @staticmethod
    async def write_fasta(sequences: List[Dict]) -> str:
        """Write sequences in FASTA format"""
        try:
            output = io.StringIO()
            for seq in sequences:
                header = f">{seq['id']}"
                if 'description' in seq and seq['description']:
                    header += f" {seq['description']}"
                output.write(f"{header}\n{seq['sequence']}\n")
            return output.getvalue()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error writing FASTA: {str(e)}")

    @staticmethod
    async def write_ngs_assembly(contigs: List[Dict]) -> str:
        """Write NGS assembly in FASTA format"""
        try:
            return await DataWriterService.write_fasta(contigs)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error writing assembly: {str(e)}")

    @staticmethod
    async def write_variants(variants: List[Dict], format_type: str = "vcf") -> str:
        """Write variants to file formats"""
        try:
            output = io.StringIO()
            
            if format_type.lower() == "vcf":
                # Write VCF header
                output.write("##fileformat=VCFv4.2\n")
                output.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
                
                for var in variants:
                    alt_str = ",".join(var['alt']) if isinstance(var['alt'], list) else var['alt']
                    info_str = ";".join([f"{k}={v}" if v is not True else k for k, v in var.get('info', {}).items()])
                    
                    line = f"{var['chrom']}\t{var['pos']}\t{var.get('id', '.')}\t{var['ref']}\t{alt_str}\t{var.get('qual', '.')}\t{var.get('filter', 'PASS')}\t{info_str}\n"
                    output.write(line)
            
            return output.getvalue()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error writing variants: {str(e)}")

    @staticmethod
    async def write_plain_text(data: Any) -> str:
        """Write data as plain text"""
        try:
            if isinstance(data, str):
                return data
            elif isinstance(data, dict):
                return json.dumps(data, indent=2)
            elif isinstance(data, list):
                return "\n".join(str(item) for item in data)
            else:
                return str(data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error writing plain text: {str(e)}")

    @staticmethod
    async def write_csv(data: List[Dict], filename: str = "output.csv") -> str:
        """Write data to CSV format"""
        try:
            if not data:
                return ""
            
            output = io.StringIO()
            fieldnames = data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            
            return output.getvalue()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error writing CSV: {str(e)}")

    @staticmethod
    async def write_excel(data: Dict, filename: str = "output.xlsx") -> bytes:
        """Write data to Excel format"""
        try:
            # This would use openpyxl in real implementation
            # For now, return CSV-like content as bytes
            csv_content = ""
            if isinstance(data, dict):
                for sheet_name, sheet_data in data.items():
                    csv_content += f"Sheet: {sheet_name}\n"
                    if isinstance(sheet_data, list) and sheet_data:
                        fieldnames = sheet_data[0].keys()
                        csv_content += ",".join(fieldnames) + "\n"
                        for row in sheet_data:
                            csv_content += ",".join(str(row.get(field, "")) for field in fieldnames) + "\n"
                    csv_content += "\n"
            
            return csv_content.encode('utf-8')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error writing Excel: {str(e)}")

    @staticmethod
    async def write_json(data: Any, filename: str = "output.json") -> str:
        """Write data to JSON format"""
        try:
            return json.dumps(data, indent=2, default=str)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error writing JSON: {str(e)}")

    @staticmethod
    def _convert_sequences_to_seqrecords(sequences: List[Dict]) -> List[SeqRecord]:
        """Convert sequence dictionaries to BioPython SeqRecord objects"""
        records = []
        for seq in sequences:
            record = SeqRecord(
                Seq(seq['sequence']),
                id=seq['id'],
                description=seq.get('description', '')
            )
            records.append(record)
        return records