# backend/app/services/hmmer_tools.py
import asyncio
import subprocess
import tempfile
import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
import uuid

logger = logging.getLogger(__name__)

@dataclass
class DESeq2Result:
    """Result from DESeq2 differential expression analysis"""
    analysis_id: str
    gene_results: pd.DataFrame
    summary_stats: Dict[str, Any]
    plot_data: Dict[str, Any]
    significant_genes: List[Dict[str, Any]]
    parameters_used: Dict[str, Any]

@dataclass
class KallistoResult:
    """Result from Kallisto quantification"""
    analysis_id: str
    abundance_estimates: pd.DataFrame
    run_info: Dict[str, Any]
    bootstrap_samples: Optional[List[pd.DataFrame]]
    quality_metrics: Dict[str, Any]

class HMMERToolsService:
    """Service for HMMER and specialized analysis tools"""
    
    def __init__(self):
        self.supported_tools = {
            'deseq2': {
                'description': 'Differential gene expression analysis using DESeq2',
                'input_types': ['count_matrix', 'sample_info'],
                'output_types': ['differential_expression_results'],
                'container_image': 'bioconductor/bioconductor_docker:RELEASE_3_15'
            },
            'kallisto': {
                'description': 'Fast RNA-seq quantification',
                'input_types': ['fastq_files', 'transcriptome_index'],
                'output_types': ['abundance_estimates'],
                'container_image': 'biocontainers/kallisto:v0.46.1_cv1'
            },
            'hmmer_search': {
                'description': 'Profile HMM searching with HMMER',
                'input_types': ['sequences', 'hmm_profile'],
                'output_types': ['hmm_hits'],
                'container_image': 'biocontainers/hmmer:v3.3.2_cv1'
            },
            'salmon': {
                'description': 'Fast RNA-seq quantification with Salmon',
                'input_types': ['fastq_files', 'transcriptome_index'],
                'output_types': ['abundance_estimates'],
                'container_image': 'combinelab/salmon:latest'
            }
        }
        
        # Default parameters for each tool
        self.default_parameters = {
            'deseq2': {
                'alpha': 0.05,
                'lfc_threshold': 0,
                'filter_low_counts': True,
                'independent_filtering': True,
                'cook_cutoff': True
            },
            'kallisto': {
                'bootstrap_samples': 100,
                'fragment_length': 200,
                'fragment_sd': 20,
                'bias_correction': True,
                'single_end': False
            },
            'hmmer_search': {
                'evalue_threshold': 1e-5,
                'bit_score_threshold': None,
                'domain_evalue': 1e-3,
                'max_hits': 1000
            },
            'salmon': {
                'lib_type': 'A',  # Automatic library type detection
                'bootstrap_samples': 100,
                'bias_correction': True,
                'gc_bias': True
            }
        }
    
    async def run_deseq2(
        self, 
        count_data: List[Dict], 
        sample_info: Dict, 
        parameters: Dict = None
    ) -> Dict:
        """Run DESeq2 differential expression analysis"""
        
        if not count_data or not sample_info:
            return {"error": "Count data and sample information are required"}
        
        if parameters is None:
            parameters = self.default_parameters['deseq2'].copy()
        
        analysis_id = str(uuid.uuid4())
        
        try:
            # Convert count data to DataFrame
            count_df = pd.DataFrame(count_data)
            
            # Validate input data
            validation = await self._validate_deseq2_input(count_df, sample_info)
            if not validation["valid"]:
                return {"error": "Input validation failed", "details": validation["errors"]}
            
            # Run DESeq2 analysis (mock implementation)
            # In production, this would use rpy2 or Docker container with R/DESeq2
            result = await self._run_deseq2_analysis(count_df, sample_info, parameters)
            
            return {
                "status": "success",
                "analysis_id": analysis_id,
                "results": result,
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"Error in DESeq2 analysis: {str(e)}")
            return {"error": f"DESeq2 analysis failed: {str(e)}"}
    
    async def run_kallisto(
        self, 
        fastq_files: List[Dict], 
        transcriptome_index: str, 
        parameters: Dict = None
    ) -> Dict:
        """Run Kallisto quantification"""
        
        if not fastq_files or not transcriptome_index:
            return {"error": "FASTQ files and transcriptome index are required"}
        
        if parameters is None:
            parameters = self.default_parameters['kallisto'].copy()
        
        analysis_id = str(uuid.uuid4())
        
        try:
            # Validate input
            validation = await self._validate_kallisto_input(fastq_files, transcriptome_index)
            if not validation["valid"]:
                return {"error": "Input validation failed", "details": validation["errors"]}
            
            # Run Kallisto (mock implementation)
            # In production, this would use Docker container with Kallisto
            result = await self._run_kallisto_quantification(fastq_files, transcriptome_index, parameters)
            
            return {
                "status": "success",
                "analysis_id": analysis_id,
                "results": result,
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"Error in Kallisto analysis: {str(e)}")
            return {"error": f"Kallisto analysis failed: {str(e)}"}
    
    async def run_hmmer_search(
        self,
        sequences: List[Dict],
        hmm_profile: str,
        parameters: Dict = None
    ) -> Dict:
        """Run HMMER profile search"""
        
        if not sequences or not hmm_profile:
            return {"error": "Sequences and HMM profile are required"}
        
        if parameters is None:
            parameters = self.default_parameters['hmmer_search'].copy()
        
        analysis_id = str(uuid.uuid4())
        
        try:
            # Run HMMER search (mock implementation)
            result = await self._run_hmmer_profile_search(sequences, hmm_profile, parameters)
            
            return {
                "status": "success",
                "analysis_id": analysis_id,
                "results": result,
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"Error in HMMER search: {str(e)}")
            return {"error": f"HMMER search failed: {str(e)}"}
    
    async def _validate_deseq2_input(self, count_df: pd.DataFrame, sample_info: Dict) -> Dict:
        """Validate DESeq2 input data"""
        errors = []
        
        # Check count matrix
        if count_df.empty:
            errors.append("Count matrix is empty")
        
        # Check for negative counts
        if (count_df < 0).any().any():
            errors.append("Count matrix contains negative values")
        
        # Check sample information
        if 'samples' not in sample_info:
            errors.append("Sample information must contain 'samples' field")
        else:
            samples = sample_info['samples']
            
            # Check that sample names match count matrix columns
            sample_names = [s.get('name', '') for s in samples]
            count_columns = count_df.columns.tolist()
            
            missing_samples = set(sample_names) - set(count_columns)
            if missing_samples:
                errors.append(f"Sample names not found in count matrix: {missing_samples}")
            
            # Check for condition/group information
            conditions = [s.get('condition', '') for s in samples]
            if not any(conditions):
                errors.append("Sample information must include condition/group assignments")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _run_deseq2_analysis(self, count_df: pd.DataFrame, sample_info: Dict, parameters: Dict) -> DESeq2Result:
        """Run DESeq2 analysis (mock implementation)"""
        
        # Mock DESeq2 analysis - in production this would use rpy2 or R subprocess
        analysis_id = str(uuid.uuid4())
        
        # Generate mock differential expression results
        gene_count = len(count_df)
        genes = count_df.index.tolist() if hasattr(count_df, 'index') else [f"gene_{i}" for i in range(gene_count)]
        
        # Mock results with random but realistic values
        np.random.seed(42)  # For reproducible mock data
        
        log2_fold_changes = np.random.normal(0, 2, gene_count)
        p_values = np.random.beta(2, 8, gene_count)  # Skewed toward small p-values
        adjusted_p_values = p_values * gene_count  # Simple Bonferroni correction
        adjusted_p_values = np.minimum(adjusted_p_values, 1.0)
        
        # Create results DataFrame
        results_df = pd.DataFrame({
            'gene_id': genes,
            'baseMean': np.random.exponential(100, gene_count),
            'log2FoldChange': log2_fold_changes,
            'lfcSE': np.abs(np.random.normal(0.5, 0.2, gene_count)),
            'stat': log2_fold_changes / np.abs(np.random.normal(0.5, 0.2, gene_count)),
            'pvalue': p_values,
            'padj': adjusted_p_values
        })
        
        # Identify significant genes
        alpha = parameters.get('alpha', 0.05)
        significant_mask = (results_df['padj'] < alpha) & (~results_df['padj'].isna())
        significant_genes = results_df[significant_mask].to_dict('records')
        
        # Summary statistics
        summary_stats = {
            "total_genes": gene_count,
            "significant_genes": int(significant_mask.sum()),
            "upregulated": int(((results_df['log2FoldChange'] > 0) & significant_mask).sum()),
            "downregulated": int(((results_df['log2FoldChange'] < 0) & significant_mask).sum()),
            "alpha_threshold": alpha,
            "median_expression": float(results_df['baseMean'].median())
        }
        
        # Plot data for visualization
        plot_data = {
            "volcano_plot": {
                "x": log2_fold_changes.tolist(),
                "y": (-np.log10(p_values + 1e-300)).tolist(),  # Avoid log(0)
                "significant": significant_mask.tolist()
            },
            "ma_plot": {
                "x": np.log10(results_df['baseMean'] + 1).tolist(),
                "y": log2_fold_changes.tolist(),
                "significant": significant_mask.tolist()
            }
        }
        
        return DESeq2Result(
            analysis_id=analysis_id,
            gene_results=results_df,
            summary_stats=summary_stats,
            plot_data=plot_data,
            significant_genes=significant_genes,
            parameters_used=parameters
        )
    
    async def _validate_kallisto_input(self, fastq_files: List[Dict], transcriptome_index: str) -> Dict:
        """Validate Kallisto input data"""
        errors = []
        
        # Check FASTQ files
        if not fastq_files:
            errors.append("No FASTQ files provided")
        
        for i, file_info in enumerate(fastq_files):
            if 'path' not in file_info and 'content' not in file_info:
                errors.append(f"FASTQ file {i+1} missing path or content")
        
        # Check transcriptome index
        if not transcriptome_index:
            errors.append("Transcriptome index is required")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _run_kallisto_quantification(self, fastq_files: List[Dict], transcriptome_index: str, parameters: Dict) -> KallistoResult:
        """Run Kallisto quantification (mock implementation)"""
        
        analysis_id = str(uuid.uuid4())
        
        # Mock Kallisto results
        # In production, this would execute Kallisto in Docker container
        
        # Generate mock transcript abundance data
        transcript_count = 5000  # Mock number of transcripts
        transcripts = [f"transcript_{i:05d}" for i in range(transcript_count)]
        
        np.random.seed(42)
        
        # Mock abundance estimates
        abundance_df = pd.DataFrame({
            'target_id': transcripts,
            'length': np.random.randint(200, 5000, transcript_count),
            'eff_length': np.random.randint(150, 4800, transcript_count),
            'est_counts': np.random.exponential(50, transcript_count),
            'tpm': np.random.exponential(10, transcript_count)
        })
        
        # Run info
        run_info = {
            "n_targets": transcript_count,
            "n_bootstraps": parameters.get('bootstrap_samples', 100),
            "n_processed": len(fastq_files) * 1000000,  # Mock read count
            "n_pseudoaligned": int(len(fastq_files) * 1000000 * 0.85),  # 85% alignment rate
            "n_unique": int(len(fastq_files) * 1000000 * 0.75),
            "p_pseudoaligned": 85.0,
            "p_unique": 75.0
        }
        
        # Quality metrics
        quality_metrics = {
            "pseudoalignment_rate": run_info["p_pseudoaligned"],
            "unique_alignment_rate": run_info["p_unique"],
            "total_reads": run_info["n_processed"],
            "aligned_reads": run_info["n_pseudoaligned"]
        }
        
        return KallistoResult(
            analysis_id=analysis_id,
            abundance_estimates=abundance_df,
            run_info=run_info,
            bootstrap_samples=None,  # Would contain bootstrap data in real implementation
            quality_metrics=quality_metrics
        )
    
    async def _run_hmmer_profile_search(self, sequences: List[Dict], hmm_profile: str, parameters: Dict) -> Dict:
        """Run HMMER profile search (mock implementation)"""
        
        # Mock HMMER search results
        analysis_id = str(uuid.uuid4())
        
        # Generate mock hits
        hits = []
        evalue_threshold = parameters.get('evalue_threshold', 1e-5)
        max_hits = parameters.get('max_hits', 1000)
        
        np.random.seed(42)
        
        for i, seq in enumerate(sequences[:min(len(sequences), max_hits)]):
            # Mock hit with realistic parameters
            if np.random.random() < 0.3:  # 30% chance of hit
                evalue = np.random.exponential(1e-10)
                
                if evalue <= evalue_threshold:
                    hit = {
                        "target_name": seq.get('name', f'seq_{i}'),
                        "query_name": hmm_profile,
                        "evalue": float(evalue),
                        "bit_score": float(np.random.exponential(50) + 20),
                        "bias": float(np.random.exponential(2)),
                        "domain_number": int(np.random.randint(1, 4)),
                        "domain_count": int(np.random.randint(1, 4)),
                        "domain_evalue": float(evalue * np.random.uniform(0.1, 1.0)),
                        "domain_score": float(np.random.exponential(40) + 15),
                        "hmm_from": int(np.random.randint(1, 50)),
                        "hmm_to": int(np.random.randint(50, 200)),
                        "ali_from": int(np.random.randint(1, 100)),
                        "ali_to": int(np.random.randint(100, len(seq.get('sequence', 'A'*500)))),
                        "env_from": int(np.random.randint(1, 90)),
                        "env_to": int(np.random.randint(110, len(seq.get('sequence', 'A'*500)) + 10))
                    }
                    hits.append(hit)
        
        # Sort hits by E-value
        hits.sort(key=lambda x: x['evalue'])
        
        return {
            "analysis_id": analysis_id,
            "hmm_profile": hmm_profile,
            "total_sequences_searched": len(sequences),
            "total_hits": len(hits),
            "significant_hits": len([h for h in hits if h['evalue'] <= evalue_threshold]),
            "hits": hits,
            "parameters_used": parameters
        }
    
    async def run_salmon(
        self,
        fastq_files: List[Dict],
        transcriptome_index: str,
        parameters: Dict = None
    ) -> Dict:
        """Run Salmon quantification"""
        
        if not fastq_files or not transcriptome_index:
            return {"error": "FASTQ files and transcriptome index are required"}
        
        if parameters is None:
            parameters = self.default_parameters['salmon'].copy()
        
        analysis_id = str(uuid.uuid4())
        
        try:
            # Mock Salmon execution
            # In production, this would use Docker container
            
            # Generate mock quantification results
            transcript_count = 4500
            transcripts = [f"transcript_{i:05d}" for i in range(transcript_count)]
            
            np.random.seed(42)
            
            abundance_df = pd.DataFrame({
                'Name': transcripts,
                'Length': np.random.randint(200, 6000, transcript_count),
                'EffectiveLength': np.random.randint(150, 5800, transcript_count),
                'TPM': np.random.exponential(5, transcript_count),
                'NumReads': np.random.exponential(100, transcript_count)
            })
            
            # Mock run info
            run_info = {
                "salmon_version": "1.5.2",
                "library_type": parameters.get('lib_type', 'A'),
                "num_reads": int(np.sum(abundance_df['NumReads'])),
                "num_mapped": int(np.sum(abundance_df['NumReads']) * 0.88),
                "mapping_rate": 88.0,
                "num_targets": transcript_count
            }
            
            return {
                "analysis_id": analysis_id,
                "abundance_estimates": abundance_df.to_dict('records'),
                "run_info": run_info,
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"Error in Salmon analysis: {str(e)}")
            return {"error": f"Salmon analysis failed: {str(e)}"}
    
    async def get_tool_info(self, tool_name: str) -> Dict:
        """Get information about a specific tool"""
        
        if tool_name not in self.supported_tools:
            return {"error": f"Tool {tool_name} not supported"}
        
        tool_info = self.supported_tools[tool_name].copy()
        tool_info['default_parameters'] = self.default_parameters.get(tool_name, {})
        
        return {
            "tool_name": tool_name,
            "info": tool_info
        }
    
    async def validate_tool_parameters(self, tool_name: str, parameters: Dict) -> Dict:
        """Validate parameters for a specific tool"""
        
        if tool_name not in self.supported_tools:
            return {"error": f"Tool {tool_name} not supported"}
        
        errors = []
        warnings = []
        
        if tool_name == 'deseq2':
            # Validate DESeq2 parameters
            alpha = parameters.get('alpha', 0.05)
            if not 0 < alpha <= 1:
                errors.append("alpha must be between 0 and 1")
            
            lfc_threshold = parameters.get('lfc_threshold', 0)
            if lfc_threshold < 0:
                errors.append("lfc_threshold must be non-negative")
                
        elif tool_name == 'kallisto':
            # Validate Kallisto parameters
            bootstrap_samples = parameters.get('bootstrap_samples', 100)
            if bootstrap_samples < 0:
                errors.append("bootstrap_samples must be non-negative")
            
            fragment_length = parameters.get('fragment_length', 200)
            if fragment_length <= 0:
                errors.append("fragment_length must be positive")
                
        elif tool_name == 'hmmer_search':
            # Validate HMMER parameters
            evalue = parameters.get('evalue_threshold', 1e-5)
            if evalue <= 0:
                errors.append("evalue_threshold must be positive")
            
            max_hits = parameters.get('max_hits', 1000)
            if max_hits <= 0:
                errors.append("max_hits must be positive")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def get_supported_tools(self) -> Dict:
        """Get list of all supported tools"""
        
        tools_info = {}
        for tool_name, tool_config in self.supported_tools.items():
            tools_info[tool_name] = {
                "description": tool_config["description"],
                "input_types": tool_config["input_types"],
                "output_types": tool_config["output_types"],
                "container_available": await self._check_container_availability(tool_config["container_image"]),
                "default_parameters": list(self.default_parameters.get(tool_name, {}).keys())
            }
        
        return {
            "supported_tools": tools_info,
            "total_count": len(self.supported_tools)
        }
    
    async def _check_container_availability(self, container_image: str) -> bool:
        """Check if container image is available"""
        try:
            # In production, this would check Docker daemon
            # For now, return True for mock implementation
            return True
        except Exception:
            return False
    
    async def create_analysis_report(self, analysis_results: List[Dict], report_type: str = "summary") -> Dict:
        """Create analysis report from multiple tool results"""
        
        if not analysis_results:
            return {"error": "No analysis results provided"}
        
        try:
            if report_type == "summary":
                return await self._create_summary_report(analysis_results)
            elif report_type == "detailed":
                return await self._create_detailed_report(analysis_results)
            elif report_type == "comparative":
                return await self._create_comparative_report(analysis_results)
            else:
                return {"error": f"Unknown report type: {report_type}"}
                
        except Exception as e:
            logger.error(f"Error creating analysis report: {str(e)}")
            return {"error": f"Report generation failed: {str(e)}"}
    
    async def _create_summary_report(self, analysis_results: List[Dict]) -> Dict:
        """Create summary report from analysis results"""
        
        report = {
            "report_type": "summary",
            "generated_at": str(asyncio.get_event_loop().time()),
            "analyses_included": len(analysis_results),
            "summary": {}
        }
        
        # Summarize each analysis type
        analysis_types = {}
        for result in analysis_results:
            analysis_type = result.get('analysis_type', 'unknown')
            if analysis_type not in analysis_types:
                analysis_types[analysis_type] = []
            analysis_types[analysis_type].append(result)
        
        report["summary"] = {
            "analysis_types": list(analysis_types.keys()),
            "type_counts": {k: len(v) for k, v in analysis_types.items()}
        }
        
        return report

# Global service instance
hmmer_tools_service = HMMERToolsService()