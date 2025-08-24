# backend/app/services/data_readers.py
import io
import json
import tempfile
import requests
from typing import List, Dict, Any, Optional
from Bio import SeqIO
from Bio.SeqRecord import SeqRecord
import pandas as pd
import asyncio
from fastapi import HTTPException

class DataReaderService:
    """Service for reading various biological data formats"""
    
    @staticmethod
    async def read_alignment(file_content: str, format_type: str = "fasta") -> List[Dict]:
        """Read alignment files (FASTA, Clustal, Stockholm, etc.)"""
        try:
            sequences = []
            if format_type.lower() == "fasta":
                records = SeqIO.parse(io.StringIO(file_content), "fasta")
                for record in records:
                    sequences.append({
                        "id": record.id,
                        "description": record.description,
                        "sequence": str(record.seq),
                        "length": len(record.seq)
                    })
            elif format_type.lower() == "clustal":
                records = SeqIO.parse(io.StringIO(file_content), "clustal")
                for record in records:
                    sequences.append({
                        "id": record.id,
                        "sequence": str(record.seq),
                        "length": len(record.seq)
                    })
            return sequences
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading alignment: {str(e)}")

    @staticmethod
    async def read_annotations(file_content: str, format_type: str = "gff3") -> List[Dict]:
        """Read annotation files (GFF3, GTF, BED, etc.)"""
        annotations = []
        
        if format_type.lower() == "gff3":
            for line in file_content.strip().split('\n'):
                if line.startswith('#') or not line.strip():
                    continue
                    
                parts = line.split('\t')
                if len(parts) >= 9:
                    annotations.append({
                        "seqid": parts[0],
                        "source": parts[1],
                        "type": parts[2],
                        "start": int(parts[3]),
                        "end": int(parts[4]),
                        "score": parts[5] if parts[5] != '.' else None,
                        "strand": parts[6],
                        "phase": parts[7] if parts[7] != '.' else None,
                        "attributes": DataReaderService._parse_gff_attributes(parts[8])
                    })
        elif format_type.lower() == "bed":
            for line in file_content.strip().split('\n'):
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) >= 3:
                    annotations.append({
                        "chrom": parts[0],
                        "start": int(parts[1]),
                        "end": int(parts[2]),
                        "name": parts[3] if len(parts) > 3 else None,
                        "score": int(parts[4]) if len(parts) > 4 else None,
                        "strand": parts[5] if len(parts) > 5 else None
                    })
        
        return annotations

    @staticmethod
    async def read_fastq_se_reads(file_content: str) -> List[Dict]:
        """Read FASTQ files with Single-End reads"""
        reads = []
        records = SeqIO.parse(io.StringIO(file_content), "fastq")
        
        for record in records:
            reads.append({
                "id": record.id,
                "description": record.description,
                "sequence": str(record.seq),
                "quality": record.letter_annotations.get("phred_quality", []),
                "length": len(record.seq)
            })
        
        return reads

    @staticmethod
    async def read_fastq_pe_reads(r1_content: str, r2_content: str) -> List[Dict]:
        """Read FASTQ files with Paired-End reads"""
        r1_records = list(SeqIO.parse(io.StringIO(r1_content), "fastq"))
        r2_records = list(SeqIO.parse(io.StringIO(r2_content), "fastq"))
        
        paired_reads = []
        for r1, r2 in zip(r1_records, r2_records):
            paired_reads.append({
                "pair_id": r1.id.split('/')[0] if '/' in r1.id else r1.id,
                "r1": {
                    "id": r1.id,
                    "sequence": str(r1.seq),
                    "quality": r1.letter_annotations.get("phred_quality", []),
                    "length": len(r1.seq)
                },
                "r2": {
                    "id": r2.id,
                    "sequence": str(r2.seq),
                    "quality": r2.letter_annotations.get("phred_quality", []),
                    "length": len(r2.seq)
                }
            })
        
        return paired_reads

    @staticmethod
    async def read_file_urls(urls: List[str]) -> List[Dict]:
        """Read files from URLs"""
        results = []
        
        async def fetch_url(url: str):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                return {
                    "url": url,
                    "content": response.text,
                    "status": "success",
                    "size": len(response.content)
                }
            except Exception as e:
                return {
                    "url": url,
                    "error": str(e),
                    "status": "failed"
                }
        
        tasks = [fetch_url(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        return results

    @staticmethod
    def _parse_gff_attributes(attr_string: str) -> Dict:
        """Parse GFF3 attributes"""
        attributes = {}
        for attr in attr_string.split(';'):
            if '=' in attr:
                key, value = attr.split('=', 1)
                attributes[key] = value
        return attributes

    @staticmethod
    def _calculate_gc_content(sequence: str) -> float:
        """Calculate GC content of sequence"""
        gc_count = sequence.upper().count('G') + sequence.upper().count('C')
        return (gc_count / len(sequence)) * 100 if sequence else 0.0
