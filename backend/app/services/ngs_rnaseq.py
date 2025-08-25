# backend/app/services/ngs_rnaseq.py
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import logging
import uuid
from datetime import datetime
import math

logger = logging.getLogger(__name__)

@dataclass
class ExpressionQuantification:
    """Result from expression quantification"""
    analysis_id: str
    gene_expression: pd.DataFrame
    transcript_expression: pd.DataFrame
    mapping_stats: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    parameters_used: Dict[str, Any]

@dataclass
class DifferentialExpressionResult:
    """Result from differential expression analysis"""
    analysis_id: str
    results_table: pd.DataFrame
    significant_genes: List[Dict[str, Any]]
    summary_stats: Dict[str, Any]
    plots_data: Dict[str, Any]
    comparison_info: Dict[str, Any]

class NGSRnaSeqService:
    """Service for comprehensive RNA-seq analysis"""
    
    def __init__(self):
        self.quantification_methods = {
            'featurecounts': {
                'description': 'FeatureCounts - Fast and accurate read counting',
                'suitable_for': 'General purpose gene quantification',
                'output_level': 'gene'
            },
            'htseq': {
                'description': 'HTSeq - Python-based read counting',
                'suitable_for': 'Flexible counting with custom rules',
                'output_level': 'gene'
            },
            'stringtie': {
                'description': 'StringTie - Transcript assembly and quantification',
                'suitable_for': 'Novel transcript discovery',
                'output_level': 'transcript'
            },
            'cufflinks': {
                'description': 'Cufflinks - Transcript assembly and quantification',
                'suitable_for': 'Legacy transcript analysis',
                'output_level': 'transcript'
            },
            'mock': {
                'description': 'Mock quantification for testing',
                'suitable_for': 'Development and testing',
                'output_level': 'both'
            }
        }
        
        self.differential_methods = {
            'deseq2': {
                'description': 'DESeq2 - Robust differential expression analysis',
                'statistical_method': 'Negative binomial',
                'recommended_for': 'Most RNA-seq experiments'
            },
            'edger': {
                'description': 'EdgeR - Empirical analysis of digital gene expression',
                'statistical_method': 'Negative binomial',
                'recommended_for': 'Tag-based sequencing'
            },
            'limma_voom': {
                'description': 'Limma-voom - Linear modeling with variance modeling',
                'statistical_method': 'Linear modeling',
                'recommended_for': 'Microarray-like analysis'
            },
            'mock': {
                'description': 'Mock differential expression for testing',
                'statistical_method': 'Simulated',
                'recommended_for': 'Development and testing'
            }
        }
        
        # Default parameters
        self.default_quantification_params = {
            'featurecounts': {
                'feature_type': 'exon',
                'attribute_type': 'gene_id',
                'min_mapping_quality': 10,
                'count_multi_mapping': False,
                'count_fractional': False
            },
            'stringtie': {
                'min_isoform_abundance': 0.1,
                'min_coverage': 2.5,
                'junction_base': 10,
                'min_read_coverage': 1
            }
        }
        
        self.default_differential_params = {
            'deseq2': {
                'alpha': 0.05,
                'lfc_threshold': 0,
                'filter_low_counts': True,
                'independent_filtering': True,
                'cook_cutoff': True
            },
            'edger': {
                'fdr': 0.05,
                'lfc_threshold': 1,
                'filter_low_counts': True,
                'normalization': 'TMM'
            }
        }
    
    async def quantify_expression(
        self, 
        mapped_reads: List[Dict], 
        gtf_file: str, 
        method: str = "featurecounts",
        parameters: Dict = None
    ) -> Dict:
        """Quantify gene expression from mapped reads"""
        
        if not mapped_reads or not gtf_file:
            return {"error": "Mapped reads and GTF annotation file are required"}
        
        if method not in self.quantification_methods:
            return {"error": f"Unsupported quantification method: {method}"}
        
        if parameters is None:
            parameters = self.default_quantification_params.get(method, {})
        
        analysis_id = str(uuid.uuid4())
        
        try:
            if method == 'mock':
                result = await self._mock_expression_quantification(mapped_reads, gtf_file, parameters)
            else:
                result = await self._run_external_quantification(mapped_reads, gtf_file, method, parameters)
            
            return {
                "status": "success",
                "analysis_id": analysis_id,
                "method": method,
                "results": result,
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"Error in expression quantification: {str(e)}")
            return {"error": f"Expression quantification failed: {str(e)}"}
    
    async def differential_expression(
        self, 
        expression_data: Dict, 
        sample_groups: Dict,
        method: str = "deseq2",
        parameters: Dict = None
    ) -> Dict:
        """Perform differential expression analysis"""
        
        if not expression_data or not sample_groups:
            return {"error": "Expression data and sample group information are required"}
        
        if method not in self.differential_methods:
            return {"error": f"Unsupported differential expression method: {method}"}
        
        if parameters is None:
            parameters = self.default_differential_params.get(method, {})
        
        analysis_id = str(uuid.uuid4())
        
        try:
            # Validate input data
            validation = await self._validate_differential_input(expression_data, sample_groups)
            if not validation["valid"]:
                return {"error": "Input validation failed", "details": validation["errors"]}
            
            if method == 'mock':
                result = await self._mock_differential_expression(expression_data, sample_groups, parameters)
            else:
                result = await self._run_external_differential_analysis(expression_data, sample_groups, method, parameters)
            
            return {
                "status": "success",
                "analysis_id": analysis_id,
                "method": method,
                "results": result,
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"Error in differential expression: {str(e)}")
            return {"error": f"Differential expression analysis failed: {str(e)}"}
    
    async def _mock_expression_quantification(self, mapped_reads: List[Dict], gtf_file: str, parameters: Dict) -> ExpressionQuantification:
        """Mock expression quantification for demonstration"""
        
        analysis_id = str(uuid.uuid4())
        
        # Generate mock gene expression data
        num_genes = 20000
        num_samples = len(mapped_reads)
        
        gene_ids = [f"ENSG{i:011d}" for i in range(num_genes)]
        sample_ids = [read.get('sample_id', f'sample_{i}') for i, read in enumerate(mapped_reads)]
        
        np.random.seed(42)
        
        # Generate realistic expression data (negative binomial-like)
        expression_matrix = np.random.negative_binomial(
            n=5, p=0.3, size=(num_genes, num_samples)
        ).astype(float)
        
        # Add some highly expressed genes
        high_expr_genes = np.random.choice(num_genes, size=int(num_genes * 0.1), replace=False)
        expression_matrix[high_expr_genes] *= np.random.exponential(10, size=(len(high_expr_genes), num_samples))
        
        # Create gene expression DataFrame
        gene_expression = pd.DataFrame(
            expression_matrix,
            index=[f"gene_{i}" for i in range(num_genes)],
            columns=sample_ids
        )
        
        # Add gene metadata
        gene_expression['gene_id'] = gene_ids
        gene_expression['gene_name'] = [f"Gene_{i}" for i in range(num_genes)]
        gene_expression['gene_biotype'] = np.random.choice(
            ['protein_coding', 'lncRNA', 'miRNA', 'pseudogene'], 
            size=num_genes,
            p=[0.7, 0.15, 0.05, 0.1]
        )
        
        # Generate mock transcript data
        num_transcripts = int(num_genes * 1.5)  # ~1.5 transcripts per gene on average
        transcript_expression = pd.DataFrame(
            np.random.negative_binomial(n=3, p=0.4, size=(num_transcripts, num_samples)),
            index=[f"transcript_{i}" for i in range(num_transcripts)],
            columns=sample_ids
        )
        
        # Mock mapping statistics
        mapping_stats = {
            "total_reads": sum([read.get('read_count', np.random.randint(1000000, 5000000)) for read in mapped_reads]),
            "mapped_reads": int(sum([read.get('read_count', np.random.randint(1000000, 5000000)) for read in mapped_reads]) * 0.85),
            "uniquely_mapped": int(sum([read.get('read_count', np.random.randint(1000000, 5000000)) for read in mapped_reads]) * 0.75),
            "multi_mapped": int(sum([read.get('read_count', np.random.randint(1000000, 5000000)) for read in mapped_reads]) * 0.10),
            "unmapped": int(sum([read.get('read_count', np.random.randint(1000000, 5000000)) for read in mapped_reads]) * 0.15)
        }
        
        mapping_stats["mapping_rate"] = (mapping_stats["mapped_reads"] / mapping_stats["total_reads"]) * 100
        mapping_stats["unique_mapping_rate"] = (mapping_stats["uniquely_mapped"] / mapping_stats["total_reads"]) * 100
        
        # Quality metrics
        quality_metrics = {
            "genes_detected": int(np.sum(gene_expression.iloc[:, :num_samples].sum(axis=1) > 0)),
            "median_gene_count": float(np.median(gene_expression.iloc[:, :num_samples].sum(axis=1))),
            "genes_high_expression": int(np.sum(gene_expression.iloc[:, :num_samples].mean(axis=1) > 100)),
            "sample_correlation": float(np.corrcoef(expression_matrix.T).mean()) if num_samples > 1 else 1.0
        }
        
        return ExpressionQuantification(
            analysis_id=analysis_id,
            gene_expression=gene_expression,
            transcript_expression=transcript_expression,
            mapping_stats=mapping_stats,
            quality_metrics=quality_metrics,
            parameters_used=parameters
        )
    
    async def _mock_differential_expression(self, expression_data: Dict, sample_groups: Dict, parameters: Dict) -> DifferentialExpressionResult:
        """Mock differential expression analysis"""
        
        analysis_id = str(uuid.uuid4())
        
        # Extract expression matrix
        if 'gene_expression' in expression_data:
            expr_df = pd.DataFrame(expression_data['gene_expression'])
        else:
            # Generate mock expression data
            num_genes = 15000
            samples = sample_groups.get('samples', [])
            
            np.random.seed(42)
            expr_matrix = np.random.negative_binomial(n=5, p=0.3, size=(num_genes, len(samples)))
            expr_df = pd.DataFrame(
                expr_matrix,
                index=[f"gene_{i:05d}" for i in range(num_genes)],
                columns=[s.get('name', f'sample_{i}') for i, s in enumerate(samples)]
            )
        
        # Get comparison groups
        group1_samples = [s['name'] for s in sample_groups.get('group1', [])]
        group2_samples = [s['name'] for s in sample_groups.get('group2', [])]
        
        if not group1_samples or not group2_samples:
            raise ValueError("Both comparison groups must have at least one sample")
        
        # Perform mock differential analysis
        results_data = []
        gene_count = len(expr_df)
        
        np.random.seed(42)
        
        for i, gene_id in enumerate(expr_df.index):
            # Calculate mock statistics
            group1_expr = expr_df.loc[gene_id, group1_samples].values if len(group1_samples) > 0 else [0]
            group2_expr = expr_df.loc[gene_id, group2_samples].values if len(group2_samples) > 0 else [0]
            
            mean1 = np.mean(group1_expr)
            mean2 = np.mean(group2_expr)
            
            # Mock log2 fold change
            log2fc = np.log2((mean2 + 1) / (mean1 + 1))
            
            # Add some biological realism - most genes not DE
            if np.random.random() > 0.15:  # 85% of genes not differentially expressed
                log2fc += np.random.normal(0, 0.2)  # Small random variation
            else:  # 15% truly differentially expressed
                log2fc += np.random.normal(0, 1.5)  # Larger changes
            
            # Mock statistics
            base_mean = np.mean([mean1, mean2])
            lfc_se = abs(np.random.normal(0.3, 0.1))
            stat = log2fc / lfc_se if lfc_se > 0 else 0
            pvalue = 2 * (1 - stats.norm.cdf(abs(stat))) if 'stats' in locals() else np.random.beta(2, 8)
            
            # Simple mock p-value based on effect size
            pvalue = min(1.0, abs(log2fc) / 3.0 + np.random.exponential(0.1))
            
            result_row = {
                'gene_id': gene_id,
                'gene_name': f"Gene_{i:05d}",
                'baseMean': base_mean,
                'log2FoldChange': log2fc,
                'lfcSE': lfc_se,
                'stat': stat,
                'pvalue': pvalue,
                'padj': min(1.0, pvalue * gene_count)  # Simple Bonferroni correction
            }
            
            results_data.append(result_row)
        
        results_df = pd.DataFrame(results_data)
        
        # Identify significant genes
        alpha = parameters.get('alpha', 0.05)
        lfc_threshold = parameters.get('lfc_threshold', 0)
        
        significant_mask = (
            (results_df['padj'] < alpha) & 
            (abs(results_df['log2FoldChange']) > lfc_threshold) &
            (~results_df['padj'].isna())
        )
        
        significant_genes = results_df[significant_mask].to_dict('records')
        
        # Summary statistics
        summary_stats = {
            "total_genes": len(results_df),
            "significant_genes": int(significant_mask.sum()),
            "upregulated": int(((results_df['log2FoldChange'] > lfc_threshold) & significant_mask).sum()),
            "downregulated": int(((results_df['log2FoldChange'] < -lfc_threshold) & significant_mask).sum()),
            "alpha_used": alpha,
            "lfc_threshold_used": lfc_threshold,
            "mean_expression": float(results_df['baseMean'].mean())
        }
        
        # Generate plot data
        plots_data = {
            "volcano_plot": {
                "x": results_df['log2FoldChange'].tolist(),
                "y": (-np.log10(results_df['pvalue'] + 1e-300)).tolist(),
                "significant": significant_mask.tolist(),
                "gene_names": results_df['gene_name'].tolist()
            },
            "ma_plot": {
                "x": np.log10(results_df['baseMean'] + 1).tolist(),
                "y": results_df['log2FoldChange'].tolist(),
                "significant": significant_mask.tolist(),
                "gene_names": results_df['gene_name'].tolist()
            },
            "pvalue_histogram": {
                "bins": np.histogram(results_df['pvalue'], bins=20)[1].tolist(),
                "counts": np.histogram(results_df['pvalue'], bins=20)[0].tolist()
            }
        }
        
        # Comparison info
        comparison_info = {
            "group1": {
                "name": sample_groups.get('group1_name', 'Group1'),
                "samples": group1_samples,
                "sample_count": len(group1_samples)
            },
            "group2": {
                "name": sample_groups.get('group2_name', 'Group2'),
                "samples": group2_samples,
                "sample_count": len(group2_samples)
            },
            "comparison": f"{sample_groups.get('group2_name', 'Group2')} vs {sample_groups.get('group1_name', 'Group1')}"
        }
        
        return DifferentialExpressionResult(
            analysis_id=analysis_id,
            results_table=results_df,
            significant_genes=significant_genes,
            summary_stats=summary_stats,
            plots_data=plots_data,
            comparison_info=comparison_info
        )
    
    async def _validate_differential_input(self, expression_data: Dict, sample_groups: Dict) -> Dict:
        """Validate input for differential expression analysis"""
        
        errors = []
        warnings = []
        
        # Check expression data
        if 'gene_expression' not in expression_data and 'count_matrix' not in expression_data:
            errors.append("Expression data must contain 'gene_expression' or 'count_matrix'")
        
        # Check sample groups
        if 'group1' not in sample_groups or 'group2' not in sample_groups:
            errors.append("Sample groups must contain 'group1' and 'group2'")
        else:
            group1 = sample_groups['group1']
            group2 = sample_groups['group2']
            
            if len(group1) < 2:
                warnings.append("Group1 has fewer than 2 samples - results may be unreliable")
            if len(group2) < 2:
                warnings.append("Group2 has fewer than 2 samples - results may be unreliable")
            
            # Check for sample overlap
            group1_names = set(s.get('name', '') for s in group1)
            group2_names = set(s.get('name', '') for s in group2)
            
            if group1_names & group2_names:
                errors.append("Sample groups cannot have overlapping samples")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def perform_pathway_analysis(self, differential_results: Dict, pathway_database: str = "mock") -> Dict:
        """Perform pathway enrichment analysis on differential expression results"""
        
        if 'significant_genes' not in differential_results:
            return {"error": "Differential expression results with significant genes required"}
        
        significant_genes = differential_results['significant_genes']
        
        if not significant_genes:
            return {"error": "No significant genes found for pathway analysis"}
        
        try:
            # Mock pathway analysis
            # In production, this would query KEGG, GO, Reactome, etc.
            
            mock_pathways = [
                {"id": "hsa04110", "name": "Cell cycle", "database": "KEGG"},
                {"id": "hsa04115", "name": "p53 signaling pathway", "database": "KEGG"},
                {"id": "hsa04210", "name": "Apoptosis", "database": "KEGG"},
                {"id": "GO:0008283", "name": "cell proliferation", "database": "GO"},
                {"id": "GO:0006915", "name": "apoptotic process", "database": "GO"},
                {"id": "R-HSA-69278", "name": "Cell Cycle, Mitotic", "database": "Reactome"}
            ]
            
            enriched_pathways = []
            
            np.random.seed(hash(str(significant_genes)))
            
            for pathway in mock_pathways:
                # Mock enrichment statistics
                genes_in_pathway = np.random.randint(5, 50)
                significant_in_pathway = np.random.randint(1, min(genes_in_pathway, len(significant_genes)))
                
                # Calculate mock p-value (hypergeometric-like)
                pvalue = np.random.beta(1, 10)  # Skewed toward significant
                
                # Adjust p-value based on overlap
                overlap_ratio = significant_in_pathway / genes_in_pathway
                pvalue *= (1 - overlap_ratio)
                
                enriched_pathways.append({
                    "pathway_id": pathway["id"],
                    "pathway_name": pathway["name"],
                    "database": pathway["database"],
                    "genes_in_pathway": genes_in_pathway,
                    "significant_genes_in_pathway": significant_in_pathway,
                    "pvalue": pvalue,
                    "padj": min(1.0, pvalue * len(mock_pathways)),
                    "fold_enrichment": overlap_ratio * np.random.uniform(1.5, 4.0),
                    "genes": [g['gene_id'] for g in significant_genes[:significant_in_pathway]]
                })
            
            # Sort by p-value
            enriched_pathways.sort(key=lambda x: x['pvalue'])
            
            # Filter significant pathways
            significant_pathways = [p for p in enriched_pathways if p['padj'] < 0.05]
            
            return {
                "status": "success",
                "pathway_database": pathway_database,
                "input_genes": len(significant_genes),
                "pathways_tested": len(mock_pathways),
                "significant_pathways": len(significant_pathways),
                "enriched_pathways": enriched_pathways,
                "top_pathways": significant_pathways[:10]
            }
            
        except Exception as e:
            logger.error(f"Error in pathway analysis: {str(e)}")
            return {"error": f"Pathway analysis failed: {str(e)}"}
    
    async def perform_gene_set_analysis(self, expression_data: Dict, gene_sets: List[Dict]) -> Dict:
        """Perform gene set enrichment analysis"""
        
        try:
            # Mock GSEA-like analysis
            results = []
            
            for gene_set in gene_sets:
                set_name = gene_set.get('name', 'Unknown')
                set_genes = gene_set.get('genes', [])
                
                if not set_genes:
                    continue
                
                # Mock enrichment score
                np.random.seed(hash(set_name))
                enrichment_score = np.random.normal(0, 0.5)
                pvalue = 2 * (1 - stats.norm.cdf(abs(enrichment_score))) if 'stats' in locals() else np.random.beta(2, 8)
                
                results.append({
                    "gene_set_name": set_name,
                    "gene_set_size": len(set_genes),
                    "enrichment_score": enrichment_score,
                    "pvalue": pvalue,
                    "padj": min(1.0, pvalue * len(gene_sets)),
                    "leading_edge_genes": set_genes[:min(10, len(set_genes))]
                })
            
            # Sort by enrichment score
            results.sort(key=lambda x: abs(x['enrichment_score']), reverse=True)
            
            return {
                "status": "success",
                "gene_sets_tested": len(gene_sets),
                "enrichment_results": results,
                "significant_sets": [r for r in results if r['padj'] < 0.05]
            }
            
        except Exception as e:
            logger.error(f"Error in gene set analysis: {str(e)}")
            return {"error": f"Gene set analysis failed: {str(e)}"}
    
    async def create_expression_heatmap_data(self, expression_data: Dict, top_genes: int = 50) -> Dict:
        """Create data for expression heatmap visualization"""
        
        try:
            if 'gene_expression' in expression_data:
                expr_df = pd.DataFrame(expression_data['gene_expression'])
            else:
                return {"error": "Gene expression data not found"}
            
            # Get top variable genes
            numeric_cols = expr_df.select_dtypes(include=[np.number]).columns
            gene_variances = expr_df[numeric_cols].var(axis=1)
            top_variable_genes = gene_variances.nlargest(top_genes).index
            
            # Extract data for heatmap
            heatmap_data = expr_df.loc[top_variable_genes, numeric_cols]
            
            # Log transform and center
            log_data = np.log2(heatmap_data + 1)
            centered_data = log_data.subtract(log_data.mean(axis=1), axis=0)
            
            return {
                "status": "success",
                "heatmap_data": {
                    "values": centered_data.values.tolist(),
                    "gene_names": centered_data.index.tolist(),
                    "sample_names": centered_data.columns.tolist(),
                    "colorscale": "RdBu_r"
                },
                "parameters": {
                    "top_genes": top_genes,
                    "transformation": "log2",
                    "centering": "row_mean"
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating heatmap data: {str(e)}")
            return {"error": f"Heatmap data creation failed: {str(e)}"}
    
    async def calculate_sample_correlation(self, expression_data: Dict) -> Dict:
        """Calculate sample correlation matrix"""
        
        try:
            if 'gene_expression' in expression_data:
                expr_df = pd.DataFrame(expression_data['gene_expression'])
            else:
                return {"error": "Gene expression data not found"}
            
            # Get numeric columns (sample data)
            numeric_cols = expr_df.select_dtypes(include=[np.number]).columns
            sample_data = expr_df[numeric_cols]
            
            # Calculate correlation matrix
            correlation_matrix = sample_data.corr()
            
            return {
                "status": "success",
                "correlation_matrix": {
                    "values": correlation_matrix.values.tolist(),
                    "sample_names": correlation_matrix.columns.tolist(),
                    "method": "pearson"
                },
                "summary": {
                    "mean_correlation": float(correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].mean()),
                    "min_correlation": float(correlation_matrix.min().min()),
                    "max_correlation": float(correlation_matrix.max().max())
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating sample correlation: {str(e)}")
            return {"error": f"Sample correlation calculation failed: {str(e)}"}
    
    async def perform_pca_analysis(self, expression_data: Dict, top_genes: int = 1000) -> Dict:
        """Perform Principal Component Analysis on expression data"""
        
        try:
            if 'gene_expression' in expression_data:
                expr_df = pd.DataFrame(expression_data['gene_expression'])
            else:
                return {"error": "Gene expression data not found"}
            
            # Get numeric columns and top variable genes
            numeric_cols = expr_df.select_dtypes(include=[np.number]).columns
            gene_variances = expr_df[numeric_cols].var(axis=1)
            top_variable_genes = gene_variances.nlargest(top_genes).index
            
            # Prepare data for PCA
            pca_data = expr_df.loc[top_variable_genes, numeric_cols].T  # Samples as rows
            
            # Log transform and standardize
            log_data = np.log2(pca_data + 1)
            standardized_data = (log_data - log_data.mean()) / log_data.std()
            
            # Mock PCA (in production, use sklearn)
            np.random.seed(42)
            n_samples = len(numeric_cols)
            
            # Generate mock PCA results
            pc1_variance = 0.35
            pc2_variance = 0.20
            pc3_variance = 0.15
            
            pca_coords = {
                "PC1": np.random.normal(0, 1, n_samples).tolist(),
                "PC2": np.random.normal(0, 0.8, n_samples).tolist(),
                "PC3": np.random.normal(0, 0.6, n_samples).tolist()
            }
            
            return {
                "status": "success",
                "pca_results": {
                    "coordinates": pca_coords,
                    "sample_names": numeric_cols.tolist(),
                    "variance_explained": {
                        "PC1": pc1_variance,
                        "PC2": pc2_variance,
                        "PC3": pc3_variance,
                        "total_top3": pc1_variance + pc2_variance + pc3_variance
                    }
                },
                "parameters": {
                    "top_genes_used": top_genes,
                    "transformation": "log2",
                    "standardization": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error in PCA analysis: {str(e)}")
            return {"error": f"PCA analysis failed: {str(e)}"}
    
    async def export_expression_data(self, expression_result: Dict, format_type: str = "csv") -> str:
        """Export expression data in various formats"""
        
        try:
            if 'gene_expression' in expression_result:
                expr_df = pd.DataFrame(expression_result['gene_expression'])
            else:
                raise ValueError("Gene expression data not found in results")
            
            if format_type == "csv":
                return expr_df.to_csv()
            elif format_type == "tsv":
                return expr_df.to_csv(sep='\t')
            elif format_type == "excel":
                # Mock Excel export (would use pandas.to_excel in production)
                return "Excel export not implemented in mock service"
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
                
        except Exception as e:
            logger.error(f"Error exporting expression data: {str(e)}")
            return f"Export failed: {str(e)}"
    
    async def get_supported_methods(self) -> Dict:
        """Get supported quantification and differential expression methods"""
        
        return {
            "quantification_methods": self.quantification_methods,
            "differential_methods": self.differential_methods,
            "recommended_workflows": [
                {
                    "name": "Standard RNA-seq",
                    "quantification": "featurecounts",
                    "differential": "deseq2",
                    "description": "Standard workflow for bulk RNA-seq"
                },
                {
                    "name": "Transcript-level analysis", 
                    "quantification": "stringtie",
                    "differential": "deseq2",
                    "description": "For novel transcript discovery"
                },
                {
                    "name": "Quick analysis",
                    "quantification": "htseq",
                    "differential": "edger",
                    "description": "Fast workflow for initial exploration"
                }
            ]
        }

# Add scipy.stats for proper statistical calculations
try:
    from scipy import stats
except ImportError:
    logger.warning("SciPy not available, using mock statistical functions")
    
    class MockStats:
        @staticmethod
        def norm_cdf(x):
            return 0.5 + 0.5 * np.tanh(x / np.sqrt(2))
    
    stats = MockStats()

# Global service instance
ngs_rnaseq_service = NGSRnaSeqService()