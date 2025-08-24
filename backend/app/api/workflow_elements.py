# backend/app/api/workflow_elements.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from typing import List, Dict, Any, Optional
from ..services.data_readers import DataReaderService
from ..services.analysis_tools import AnalysisToolsService
from ..services.workflow_engine import workflowengine
from ..models.enhanced_models import *
from ..database.database_setup import DatabaseManager

router = APIRouter()

# Initialize services (these would be dependency injected in production)
data_reader = DataReaderService()
analysis_tools = AnalysisToolsService()

# Workflow Elements Endpoints
@router.get("/workflow/elements")
async def get_workflow_elements():
    """Get all available workflow elements organized by category"""
    
    elements = {
        "Data Readers": [
            {
                "name": "read_alignment",
                "display_name": "Read Alignment",
                "description": "Read alignment files (FASTA, Clustal, Stockholm)",
                "input_ports": [],
                "output_ports": ["sequences"],
                "parameters": {
                    "format_type": {"type": "select", "options": ["fasta", "clustal", "stockholm"], "default": "fasta"}
                }
            },
            {
                "name": "read_annotations", 
                "display_name": "Read Annotations",
                "description": "Read annotation files (GFF3, GTF, BED)",
                "input_ports": [],
                "output_ports": ["annotations"],
                "parameters": {
                    "format_type": {"type": "select", "options": ["gff3", "gtf", "bed"], "default": "gff3"}
                }
            },
            {
                "name": "read_fastq_se",
                "display_name": "Read FASTQ SE",
                "description": "Read single-end FASTQ files",
                "input_ports": [],
                "output_ports": ["reads"],
                "parameters": {}
            },
            {
                "name": "read_fastq_pe",
                "display_name": "Read FASTQ PE", 
                "description": "Read paired-end FASTQ files",
                "input_ports": [],
                "output_ports": ["paired_reads"],
                "parameters": {}
            },
            {
                "name": "read_file_urls",
                "display_name": "Read File URLs",
                "description": "Read files from remote URLs",
                "input_ports": [],
                "output_ports": ["files"],
                "parameters": {
                    "urls": {"type": "text_array", "description": "List of URLs to fetch"}
                }
            },
            {
                "name": "read_sequence_remote",
                "display_name": "Read Sequence Remote",
                "description": "Fetch sequences from remote databases (NCBI, UniProt)",
                "input_ports": [],
                "output_ports": ["sequences"],
                "parameters": {
                    "accession": {"type": "text", "description": "Accession number"},
                    "database": {"type": "select", "options": ["ncbi", "uniprot"], "default": "ncbi"}
                }
            }
        ],
        
        "Data Writers": [
            {
                "name": "write_alignment",
                "display_name": "Write Alignment",
                "description": "Write sequences to alignment formats",
                "input_ports": ["sequences"],
                "output_ports": ["file"],
                "parameters": {
                    "format_type": {"type": "select", "options": ["fasta", "clustal", "phylip"], "default": "fasta"}
                }
            },
            {
                "name": "write_fasta",
                "display_name": "Write FASTA", 
                "description": "Write sequences in FASTA format",
                "input_ports": ["sequences"],
                "output_ports": ["file"],
                "parameters": {}
            },
            {
                "name": "write_annotations",
                "display_name": "Write Annotations",
                "description": "Write annotations to various formats",
                "input_ports": ["annotations"], 
                "output_ports": ["file"],
                "parameters": {
                    "format_type": {"type": "select", "options": ["gff3", "gtf", "bed"], "default": "gff3"}
                }
            }
        ],
        
        "Analysis Tools": [
            {
                "name": "blast_search",
                "display_name": "BLAST Search",
                "description": "Perform BLAST sequence similarity search",
                "input_ports": ["sequences"],
                "output_ports": ["results"],
                "parameters": {
                    "database": {"type": "select", "options": ["nr", "nt", "swissprot"], "default": "nr"},
                    "evalue": {"type": "float", "default": 1e-5},
                    "max_hits": {"type": "integer", "default": 10}
                }
            },
            {
                "name": "multiple_alignment",
                "display_name": "Multiple Alignment",
                "description": "Perform multiple sequence alignment",
                "input_ports": ["sequences"],
                "output_ports": ["alignment"],
                "parameters": {
                    "method": {"type": "select", "options": ["muscle", "clustalw", "mafft"], "default": "muscle"}
                }
            },
            {
                "name": "statistics",
                "display_name": "Statistics",
                "description": "Calculate sequence statistics",
                "input_ports": ["sequences"],
                "output_ports": ["statistics"],
                "parameters": {}
            }
        ],
        
        "Data Flow": [
            {
                "name": "filter_sequences",
                "display_name": "Filter Sequences",
                "description": "Filter sequences based on criteria",
                "input_ports": ["sequences"],
                "output_ports": ["filtered_sequences"],
                "parameters": {
                    "min_length": {"type": "integer", "default": 0},
                    "max_length": {"type": "integer", "default": 10000},
                    "min_gc": {"type": "float", "default": 0},
                    "max_gc": {"type": "float", "default": 100}
                }
            }
        ]
    }
    
    return elements


# Data Reader Endpoints
@router.post("/readers/alignment")
async def read_alignment_endpoint(file: UploadFile = File(...), format_type: str = "fasta"):
    content = await file.read()
    return await data_reader.read_alignment(content.decode('utf-8'), format_type)

@router.post("/readers/annotations") 
async def read_annotations_endpoint(file: UploadFile = File(...), format_type: str = "gff3"):
    content = await file.read()
    return await data_reader.read_annotations(content.decode('utf-8'), format_type)

@router.post("/readers/fastq-se")
async def read_fastq_se_endpoint(file: UploadFile = File(...)):
    content = await file.read()
    return await data_reader.read_fastq_se_reads(content.decode('utf-8'))

@router.post("/readers/fastq-pe")
async def read_fastq_pe_endpoint(r1_file: UploadFile = File(...), r2_file: UploadFile = File(...)):
    r1_content = await r1_file.read()
    r2_content = await r2_file.read()
    return await data_reader.read_fastq_pe_reads(
        r1_content.decode('utf-8'),
        r2_content.decode('utf-8')
    )

@router.post("/readers/file-urls")
async def read_file_urls_endpoint(urls: List[str]):
    return await data_reader.read_file_urls(urls)


# Analysis Tool Endpoints
@router.post("/analysis/blast")
async def blast_search_endpoint(request: BlastSearchRequest):
    return await analysis_tools.run_blast_search(
        request.sequences,
        request.database,
        {
            "evalue": str(request.evalue),
            "max_hits": request.max_hits,
            "word_size": request.word_size
        }
    )

@router.post("/analysis/alignment")
async def multiple_alignment_endpoint(request: MultipleAlignmentRequest):
    sequences = [seq.dict() for seq in request.sequences]
    return await analysis_tools.run_multiple_alignment(
        sequences,
        request.method,
        request.parameters
    )
