# backend/app/builders/sequence_builder.py
import re
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from ..models.enhanced_models import SequenceData, SequenceType, Annotation

class SequenceBuilder:
    """Builder pattern for creating sequence objects with validation"""
    
    def __init__(self):
        self._sequence = None
        self._name = None
        self._sequence_type = None
        self._annotations = []
        self._description = None
        self._organism_id = None
        self._user_id = None
        self._source = None
        self._accession_number = None
        self._is_public = False
    
    def sequence(self, seq: str) -> 'SequenceBuilder':
        """Set sequence string with validation"""
        # Clean sequence - remove whitespace and convert to uppercase
        self._sequence = re.sub(r'\s+', '', seq.upper())
        
        # Auto-detect sequence type if not set
        if not self._sequence_type:
            self._sequence_type = self._detect_sequence_type(self._sequence)
        
        return self
    
    def name(self, name: str) -> 'SequenceBuilder':
        """Set sequence name"""
        self._name = name
        return self
    
    def description(self, desc: str) -> 'SequenceBuilder':
        """Set sequence description"""
        self._description = desc
        return self
    
    def organism(self, organism_id: int) -> 'SequenceBuilder':
        """Set organism ID"""
        self._organism_id = organism_id
        return self
    
    def user(self, user_id: str) -> 'SequenceBuilder':
        """Set user ID"""
        self._user_id = user_id
        return self
    
    def source(self, source: str) -> 'SequenceBuilder':
        """Set sequence source"""
        self._source = source
        return self
    
    def accession(self, accession: str) -> 'SequenceBuilder':
        """Set accession number"""
        self._accession_number = accession
        return self
    
    def public(self, is_public: bool = True) -> 'SequenceBuilder':
        """Set public visibility"""
        self._is_public = is_public
        return self
    
    def annotation(self, feature_type: str, start: int, end: int, 
                   strand: str = '.', **attributes) -> 'SequenceBuilder':
        """Add annotation to sequence"""
        self._annotations.append({
            'feature_type': feature_type,
            'start_position': start,
            'end_position': end,
            'strand': strand,
            'attributes': attributes
        })
        return self
    
    def multiple_annotations(self, annotations: List[Dict]) -> 'SequenceBuilder':
        """Add multiple annotations"""
        self._annotations.extend(annotations)
        return self
    
    def from_fasta(self, fasta_content: str) -> 'SequenceBuilder':
        """Build from FASTA format"""
        lines = fasta_content.strip().split('\n')
        if lines and lines[0].startswith('>'):
            # Parse header
            header = lines[0][1:]  # Remove '>'
            parts = header.split(' ', 1)
            self._name = parts[0]
            if len(parts) > 1:
                self._description = parts[1]
            
            # Parse sequence
            sequence = ''.join(lines[1:])
            self.sequence(sequence)
        
        return self
    
    def build(self) -> SequenceData:
        """Build and validate sequence object"""
        if not self._sequence or not self._name:
            raise ValueError("Sequence and name are required")
        
        # Validate sequence content
        if not self._validate_sequence_content(self._sequence, self._sequence_type):
            raise ValueError(f"Invalid sequence content for type {self._sequence_type}")
        
        # Calculate additional properties
        length = len(self._sequence)
        gc_content = self._calculate_gc_content(self._sequence, self._sequence_type)
        checksum = hashlib.md5(self._sequence.encode()).hexdigest()
        
        return SequenceData(
            name=self._name,
            description=self._description,
            sequence=self._sequence,
            sequence_type=self._sequence_type,
            organism_id=self._organism_id,
            user_id=self._user_id,
            length=length,
            gc_content=gc_content,
            checksum=checksum,
            source=self._source,
            accession_number=self._accession_number,
            is_public=self._is_public
        )
    
    def _detect_sequence_type(self, seq: str) -> SequenceType:
        """Auto-detect sequence type based on content"""
        seq_upper = seq.upper()
        
        # Define character sets
        dna_chars = set('ATCG')
        rna_chars = set('AUCG')
        protein_chars = set('ACDEFGHIKLMNPQRSTVWY')
        
        seq_chars = set(seq_upper)
        
        # Remove common ambiguity codes
        ambiguity_chars = set('NRYWSKMBDHV')
        core_chars = seq_chars - ambiguity_chars
        
        if core_chars.issubset(dna_chars) and 'T' in seq_chars:
            return SequenceType.DNA
        elif core_chars.issubset(rna_chars) and 'U' in seq_chars:
            return SequenceType.RNA
        elif core_chars.issubset(protein_chars):
            return SequenceType.PROTEIN
        else:
            # Default to DNA if unclear
            return SequenceType.DNA
    
    def _validate_sequence_content(self, seq: str, seq_type: SequenceType) -> bool:
        """Validate sequence content matches declared type"""
        if not seq:
            return False
        
        seq_upper = seq.upper()
        
        if seq_type == SequenceType.DNA:
            valid_chars = set('ATCGNRYWSKMBDHV')
            return set(seq_upper).issubset(valid_chars)
        elif seq_type == SequenceType.RNA:
            valid_chars = set('AUCGNRYWSKMBDHV')
            return set(seq_upper).issubset(valid_chars)
        elif seq_type == SequenceType.PROTEIN:
            valid_chars = set('ACDEFGHIKLMNPQRSTVWYUBZXJ*')
            return set(seq_upper).issubset(valid_chars)
        
        return False
    
    def _calculate_gc_content(self, seq: str, seq_type: SequenceType) -> Optional[float]:
        """Calculate GC content for nucleotide sequences"""
        if seq_type in [SequenceType.DNA, SequenceType.RNA]:
            seq_upper = seq.upper()
            gc_count = seq_upper.count('G') + seq_upper.count('C')
            return (gc_count / len(seq)) * 100 if seq else 0.0
        return None


class AnalysisPipelineBuilder:
    """Builder for creating bioinformatics analysis pipelines"""
    
    def __init__(self):
        self.steps = []
        self.parameters = {}
        self.name = None
        self.description = None
    
    def pipeline_name(self, name: str) -> 'AnalysisPipelineBuilder':
        """Set pipeline name"""
        self.name = name
        return self
    
    def pipeline_description(self, description: str) -> 'AnalysisPipelineBuilder':
        """Set pipeline description"""
        self.description = description
        return self
    
    def add_blast_search(self, database: str = 'nr', evalue: float = 1e-5, 
                        max_hits: int = 10) -> 'AnalysisPipelineBuilder':
        """Add BLAST search step"""
        self.steps.append({
            'type': 'blast_search',
            'parameters': {
                'database': database,
                'evalue': evalue,
                'max_hits': max_hits
            }
        })
        return self
    
    def add_multiple_alignment(self, method: str = 'muscle') -> 'AnalysisPipelineBuilder':
        """Add multiple sequence alignment step"""
        self.steps.append({
            'type': 'multiple_alignment',
            'parameters': {'method': method}
        })
        return self
    
    def add_phylogeny(self, method: str = 'neighbor_joining') -> 'AnalysisPipelineBuilder':
        """Add phylogenetic analysis step"""
        self.steps.append({
            'type': 'phylogenetic_analysis',
            'parameters': {'method': method}
        })
        return self
    
    def add_structure_prediction(self, method: str = 'alphafold') -> 'AnalysisPipelineBuilder':
        """Add protein structure prediction step"""
        self.steps.append({
            'type': 'structure_prediction',
            'parameters': {'method': method}
        })
        return self
    
    def add_gene_finding(self, organism_type: str = 'prokaryote') -> 'AnalysisPipelineBuilder':
        """Add gene finding step"""
        self.steps.append({
            'type': 'gene_finding',
            'parameters': {'organism_type': organism_type}
        })
        return self
    
    def add_motif_search(self, motif_database: str = 'pfam') -> 'AnalysisPipelineBuilder':
        """Add motif search step"""
        self.steps.append({
            'type': 'motif_search',
            'parameters': {'database': motif_database}
        })
        return self
    
    def add_custom_step(self, step_type: str, parameters: Dict[str, Any]) -> 'AnalysisPipelineBuilder':
        """Add custom analysis step"""
        self.steps.append({
            'type': step_type,
            'parameters': parameters
        })
        return self
    
    def build_workflow(self) -> Dict:
        """Build workflow definition"""
        return {
            'name': self.name or f"Pipeline_{int(datetime.now().timestamp())}",
            'description': self.description or "Auto-generated analysis pipeline",
            'steps': self.steps,
            'created_at': datetime.utcnow().isoformat(),
            'version': '1.0'
        }

# Usage examples:
def create_sample_sequences():
    """Create sample sequences using builder pattern"""
    
    # DNA sequence with annotations
    dna_sequence = (SequenceBuilder()
        .name("Sample Gene")
        .description("A sample gene sequence for testing")
        .sequence("ATGAAACGCATTAGCACCACCATTACCACCACCATCACCATTACCACAGGTAACGGTGCGGGCTGA")
        .annotation("gene", 1, 63, gene="sampleGene", product="sample protein")
        .annotation("CDS", 1, 63, gene="sampleGene")
        .annotation("promoter", -50, -1, type="TATA_box")
        .public(True)
        .build())
    
    # Protein sequence
    protein_sequence = (SequenceBuilder()
        .name("Sample Protein")
        .sequence("MKRLATTPLTTTPSPLTTSKTNTKSAPVKKGRLQVFHHVQEQVKSVQSLQ")
        .description("A sample protein sequence")
        .annotation("domain", 10, 30, name="DNA_binding")
        .build())
    
    return dna_sequence, protein_sequence

def create_sample_pipeline():
    """Create a comprehensive analysis pipeline"""
    
    pipeline = (AnalysisPipelineBuilder()
        .pipeline_name("Comprehensive Gene Analysis")
        .pipeline_description("Complete analysis including BLAST, alignment, and phylogeny")
        .add_blast_search('nr', evalue=1e-10)
        .add_multiple_alignment('muscle')
        .add_phylogeny('maximum_likelihood')
        .add_gene_finding('prokaryote')
        .add_motif_search('pfam')
        .build_workflow())
    
    # Corrected line
    return pipeline