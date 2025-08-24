# backend/app/services/advanced_analysis.py
import asyncio
import tempfile
import subprocess
import json
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np
from Bio import SeqIO, Phylo
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Align import MultipleSeqAlignment
import docker
import logging
from ..models.enhanced_models import SequenceData, AnalysisResult

logger = logging.getLogger(__name__)

class AdvancedBioinformaticsTools:
    """Advanced bioinformatics analysis tools with external tool integration"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.temp_dir = Path("/tmp/bioinformatics_analysis")
        self.temp_dir.mkdir(exist_ok=True)
    
    async def run_phylogenetic_analysis(self, sequences: List[SequenceData], method: str = "neighbor_joining", parameters: Dict = None) -> Dict:
        """Perform phylogenetic analysis using various methods"""
        if parameters is None:
            parameters = {"bootstrap": 100, "model": "GTR+I+G"}
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write sequences to FASTA file
                fasta_file = Path(temp_dir) / "sequences.fasta"
                with open(fasta_file, 'w') as f:
                    for seq in sequences:
                        f.write(f">{seq.id}\n{seq.sequence}\n")
                
                # Perform multiple sequence alignment first
                alignment_file = await self._run_multiple_alignment(fasta_file, temp_dir)
                
                # Run phylogenetic analysis
                tree_result = await self._run_phylogeny(alignment_file, method, parameters, temp_dir)
                
                return {
                    "method": method,
                    "parameters": parameters,
                    "tree": tree_result["newick_tree"],
                    "bootstrap_values": tree_result.get("bootstrap_values", []),
                    "log_likelihood": tree_result.get("log_likelihood"),
                    "alignment_length": tree_result.get("alignment_length"),
                    "statistics": tree_result.get("statistics", {})
                }
        
        except Exception as e:
            logger.error(f"Phylogenetic analysis failed: {str(e)}")
            raise ValueError(f"Phylogenetic analysis failed: {str(e)}")
    
    async def _run_multiple_alignment(self, fasta_file: Path, temp_dir: str) -> Path:
        """Run multiple sequence alignment using MUSCLE"""
        alignment_file = Path(temp_dir) / "alignment.fasta"
        
        # Use Docker to run MUSCLE
        container = self.docker_client.containers.run(
            "biocontainers/muscle:3.8.31_cv2",
            command=f"muscle -in /data/sequences.fasta -out /data/alignment.fasta",
            volumes={temp_dir: {"bind": "/data", "mode": "rw"}},
            detach=True,
            remove=True
        )
        
        # Wait for completion
        result = container.wait()
        if result['StatusCode'] != 0:
            raise ValueError("Multiple sequence alignment failed")
        
        return alignment_file
    
    async def _run_phylogeny(self, alignment_file: Path, method: str, parameters: Dict, temp_dir: str) -> Dict:
        """Run phylogenetic tree construction"""
        if method == "neighbor_joining":
            return await self._run_neighbor_joining(alignment_file, parameters, temp_dir)
        elif method == "maximum_likelihood":
            return await self._run_iqtree(alignment_file, parameters, temp_dir)
        elif method == "maximum_parsimony":
            return await self._run_paup(alignment_file, parameters, temp_dir)
        else:
            raise ValueError(f"Unsupported phylogenetic method: {method}")
    
    async def _run_iqtree(self, alignment_file: Path, parameters: Dict, temp_dir: str) -> Dict:
        """Run IQ-TREE for maximum likelihood phylogeny"""
        container = self.docker_client.containers.run(
            "staphb/iqtree:2.2.0",
            command=f"iqtree -s /data/alignment.fasta -m {parameters.get('model', 'GTR+I+G')} -bb {parameters.get('bootstrap', 1000)} -nt AUTO",
            volumes={temp_dir: {"bind": "/data", "mode": "rw"}},
            detach=True,
            remove=True
        )
        
        result = container.wait()
        if result['StatusCode'] != 0:
            raise ValueError("IQ-TREE analysis failed")
        
        # Parse results
        tree_file = Path(temp_dir) / "alignment.fasta.treefile"
        log_file = Path(temp_dir) / "alignment.fasta.log"
        
        newick_tree = ""
        if tree_file.exists():
            newick_tree = tree_file.read_text().strip()
        
        # Parse log for statistics
        statistics = {}
        if log_file.exists():
            log_content = log_file.read_text()
            statistics = self._parse_iqtree_log(log_content)
        
        return {
            "newick_tree": newick_tree,
            "statistics": statistics
        }
    
    async def run_genome_annotation(self, sequence: SequenceData, parameters: Dict = None) -> Dict:
        """Perform genome annotation using Prokka"""
        if parameters is None:
            parameters = {"kingdom": "Bacteria", "genus": "Unknown"}
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write sequence to file
                input_file = Path(temp_dir) / "genome.fasta"
                with open(input_file, 'w') as f:
                    f.write(f">{sequence.name}\n{sequence.sequence}\n")
                
                # Run Prokka annotation
                container = self.docker_client.containers.run(
                    "staphb/prokka:1.14.6",
                    command=f"prokka --kingdom {parameters['kingdom']} --genus {parameters['genus']} --outdir /data/annotation --prefix genome /data/genome.fasta",
                    volumes={temp_dir: {"bind": "/data", "mode": "rw"}},
                    detach=True,
                    remove=True
                )
                
                result = container.wait()
                if result['StatusCode'] != 0:
                    raise ValueError("Genome annotation failed")
                
                # Parse annotation results
                annotation_dir = Path(temp_dir) / "annotation"
                gff_file = annotation_dir / "genome.gff"
                faa_file = annotation_dir / "genome.faa"
                txt_file = annotation_dir / "genome.txt"
                
                annotations = []
                if gff_file.exists():
                    annotations = self._parse_gff_file(gff_file)
                
                proteins = []
                if faa_file.exists():
                    proteins = self._parse_fasta_file(faa_file)
                
                statistics = {}
                if txt_file.exists():
                    statistics = self._parse_prokka_stats(txt_file)
                
                return {
                    "annotations": annotations,
                    "proteins": proteins,
                    "statistics": statistics,
                    "parameters": parameters
                }
        
        except Exception as e:
            logger.error(f"Genome annotation failed: {str(e)}")
            raise ValueError(f"Genome annotation failed: {str(e)}")
    
    async def run_variant_calling(self, reads_r1: str, reads_r2: str, reference: str, parameters: Dict = None) -> Dict:
        """Perform variant calling using BWA + GATK pipeline"""
        if parameters is None:
            parameters = {"min_quality": 30, "min_depth": 10}
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write input files
                r1_file = Path(temp_dir) / "reads_R1.fastq"
                r2_file = Path(temp_dir) / "reads_R2.fastq"
                ref_file = Path(temp_dir) / "reference.fasta"
                
                with open(r1_file, 'w') as f:
                    f.write(reads_r1)
                with open(r2_file, 'w') as f:
                    f.write(reads_r2)
                with open(ref_file, 'w') as f:
                    f.write(reference)
                
                # Run variant calling pipeline
                variants = await self._run_variant_pipeline(temp_dir, parameters)
                
                return {
                    "variants": variants,
                    "parameters": parameters,
                    "statistics": self._calculate_variant_stats(variants)
                }
        
        except Exception as e:
            logger.error(f"Variant calling failed: {str(e)}")
            raise ValueError(f"Variant calling failed: {str(e)}")
    
    async def run_differential_expression(self, count_data: List[Dict], sample_info: Dict, parameters: Dict = None) -> Dict:
        """Run differential expression analysis using DESeq2"""
        if parameters is None:
            parameters = {"alpha": 0.05, "lfc_threshold": 1.0}
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Prepare count matrix
                count_matrix_file = Path(temp_dir) / "counts.csv"
                sample_info_file = Path(temp_dir) / "samples.csv"
                
                # Write count data
                df_counts = pd.DataFrame(count_data)
                df_counts.to_csv(count_matrix_file, index=False)
                
                # Write sample information
                df_samples = pd.DataFrame(sample_info)
                df_samples.to_csv(sample_info_file, index=False)
                
                # Run DESeq2 analysis
                results = await self._run_deseq2_analysis(temp_dir, parameters)
                
                return {
                    "results": results,
                    "parameters": parameters,
                    "summary": self._summarize_de_results(results, parameters["alpha"])
                }
        
        except Exception as e:
            logger.error(f"Differential expression analysis failed: {str(e)}")
            raise ValueError(f"Differential expression analysis failed: {str(e)}")
    
    async def run_protein_structure_prediction(self, protein_sequence: str, parameters: Dict = None) -> Dict:
        """Predict protein structure using ChimeraX/AlphaFold"""
        if parameters is None:
            parameters = {"method": "alphafold", "confidence_threshold": 0.7}
        
        try:
            # For demonstration, return mock structure prediction results
            # In production, integrate with actual structure prediction tools
            
            prediction_result = {
                "sequence": protein_sequence,
                "structure_format": "PDB",
                "confidence_scores": [np.random.uniform(0.5, 1.0) for _ in range(len(protein_sequence))],
                "secondary_structure": self._predict_secondary_structure(protein_sequence),
                "domains": self._predict_protein_domains(protein_sequence),
                "parameters": parameters
            }
            
            return prediction_result
        
        except Exception as e:
            logger.error(f"Protein structure prediction failed: {str(e)}")
            raise ValueError(f"Protein structure prediction failed: {str(e)}")
    
    async def run_metabolic_pathway_analysis(self, gene_ids: List[str], organism: str, parameters: Dict = None) -> Dict:
        """Analyze metabolic pathways using KEGG/Reactome"""
        if parameters is None:
            parameters = {"database": "kegg", "p_value_threshold": 0.05}
        
        try:
            # Mock pathway analysis - integrate with KEGG/Reactome APIs in production
            enriched_pathways = []
            
            # Simulate pathway enrichment
            mock_pathways = [
                {"pathway_id": "ko00010", "name": "Glycolysis / Gluconeogenesis", "p_value": 0.001},
                {"pathway_id": "ko00020", "name": "Citrate cycle (TCA cycle)", "p_value": 0.015},
                {"pathway_id": "ko00030", "name": "Pentose phosphate pathway", "p_value": 0.032}
            ]
            
            for pathway in mock_pathways:
                if pathway["p_value"] <= parameters["p_value_threshold"]:
                    enriched_pathways.append(pathway)
            
            return {
                "enriched_pathways": enriched_pathways,
                "input_genes": gene_ids,
                "organism": organism,
                "parameters": parameters,
                "statistics": {
                    "total_pathways_tested": len(mock_pathways),
                    "significant_pathways": len(enriched_pathways)
                }
            }
        
        except Exception as e:
            logger.error(f"Metabolic pathway analysis failed: {str(e)}")
            raise ValueError(f"Metabolic pathway analysis failed: {str(e)}")
    
    # Helper methods
    def _parse_gff_file(self, gff_file: Path) -> List[Dict]:
        """Parse GFF annotation file"""
        annotations = []
        with open(gff_file, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                
                parts = line.strip().split('\t')
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
                        "attributes": self._parse_gff_attributes(parts[8])
                    })
        
        return annotations
    
    def _parse_gff_attributes(self, attr_string: str) -> Dict:
        """Parse GFF attributes string"""
        attributes = {}
        for attr in attr_string.split(';'):
            if '=' in attr:
                key, value = attr.split('=', 1)
                attributes[key] = value
        return attributes
    
    def _parse_fasta_file(self, fasta_file: Path) -> List[Dict]:
        """Parse FASTA file and return sequences"""
        sequences = []
        for record in SeqIO.parse(fasta_file, "fasta"):
            sequences.append({
                "id": record.id,
                "description": record.description,
                "sequence": str(record.seq),
                "length": len(record.seq)
            })
        return sequences
    
    def _predict_secondary_structure(self, sequence: str) -> List[str]:
        """Simple secondary structure prediction (mock implementation)"""
        # This would integrate with actual prediction tools like PSIPRED
        structures = ['H', 'E', 'C']  # Helix, Beta sheet, Coil
        return [np.random.choice(structures) for _ in sequence]
    
    def _predict_protein_domains(self, sequence: str) -> List[Dict]:
        """Predict protein domains (mock implementation)"""
        # This would integrate with domain databases like Pfam
        domains = []
        if len(sequence) > 100:
            domains.append({
                "name": "ATP_binding",
                "start": 10,
                "end": 80,
                "score": 45.2,
                "database": "Pfam"
            })
        return domains
    
    async def _run_deseq2_analysis(self, temp_dir: str, parameters: Dict) -> List[Dict]:
        """Run DESeq2 analysis using R container"""
        # This would run actual DESeq2 analysis in R container
        # For now, return mock results
        mock_results = []
        for i in range(1000):
            log2fc = np.random.normal(0, 2)
            pvalue = np.random.uniform(0, 1)
            padj = pvalue * 1.1  # Simplified FDR correction
            
            mock_results.append({
                "gene_id": f"gene_{i:04d}",
                "baseMean": np.random.uniform(10, 1000),
                "log2FoldChange": log2fc,
                "lfcSE": abs(log2fc) * 0.1,
                "stat": log2fc / (abs(log2fc) * 0.1) if log2fc != 0 else 0,
                "pvalue": pvalue,
                "padj": padj
            })
        
        return mock_results
    
    def _summarize_de_results(self, results: List[Dict], alpha: float) -> Dict:
        """Summarize differential expression results"""
        significant = [r for r in results if r["padj"] <= alpha]
        upregulated = [r for r in significant if r["log2FoldChange"] > 0]
        downregulated = [r for r in significant if r["log2FoldChange"] < 0]
        
        return {
            "total_genes": len(results),
            "significant_genes": len(significant),
            "upregulated": len(upregulated),
            "downregulated": len(downregulated),
            "significance_threshold": alpha
        }