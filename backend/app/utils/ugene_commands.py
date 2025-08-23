# backend/app/utils/ugene_commands.py - COMPLETE VERSION
from typing import List, Dict, Any, Optional
import json

class UgeneCommandBuilder:
    """Build UGENE command line arguments from workflow definitions with complete element support"""
    
    # Complete mapping for ALL elements from your frontend
    COMMAND_MAPPINGS = {
        # =====================================
        # DATA READERS
        # =====================================
        'Read Alignment': {
            'command': 'read-alignment',
            'input_formats': ['.aln', '.clustal', '.msf', '.stockholm'],
            'output_format': 'alignment',
            'description': 'Read alignment from various formats'
        },
        'Read Annotations': {
            'command': 'read-annotations', 
            'input_formats': ['.gff', '.gtf', '.bed', '.gb'],
            'output_format': 'annotations',
            'description': 'Read genome annotations'
        },
        'Read FASTQ File with SE Reads': {
            'command': 'read-sequence',
            'parameters': '--format=fastq --type=single-end',
            'input_formats': ['.fastq', '.fq'],
            'output_format': 'sequence',
            'description': 'Read single-end FASTQ files'
        },
        'Read FASTQ File with PE Reads': {
            'command': 'read-sequence',
            'parameters': '--format=fastq --type=paired-end',
            'input_formats': ['.fastq', '.fq'],
            'output_format': 'sequence',
            'description': 'Read paired-end FASTQ files'
        },
        'Read File URL(s)': {
            'command': 'download-sequence',
            'parameters': '--source=url',
            'input_formats': ['url'],
            'output_format': 'sequence',
            'description': 'Download sequences from URLs'
        },
        'Read NGS Reads Assembly': {
            'command': 'read-assembly',
            'input_formats': ['.fasta', '.fa', '.contigs'],
            'output_format': 'assembly',
            'description': 'Read assembled NGS data'
        },
        'Read Plain Text': {
            'command': 'read-text',
            'input_formats': ['.txt'],
            'output_format': 'text',
            'description': 'Read plain text files'
        },
        'Read Sequence': {
            'command': 'read-sequence',
            'input_formats': ['.fasta', '.fa', '.seq'],
            'output_format': 'sequence',
            'description': 'Read sequence data'
        },
        'Read Sequence from Remote Database': {
            'command': 'fetch-sequence',
            'parameters': '--database=ncbi',
            'input_formats': ['accession'],
            'output_format': 'sequence',
            'description': 'Fetch sequences from remote databases'
        },
        'Read Variants': {
            'command': 'read-variants',
            'input_formats': ['.vcf', '.bcf'],
            'output_format': 'variants',
            'description': 'Read variant call format files'
        },

        # =====================================
        # DATA WRITERS  
        # =====================================
        'Write Alignment': {
            'command': 'write-alignment',
            'parameters': '--format=clustal',
            'output_formats': ['.aln', '.clustal'],
            'description': 'Write alignment in specified format'
        },
        'Write Annotations': {
            'command': 'write-annotations',
            'parameters': '--format=gff3',
            'output_formats': ['.gff', '.gff3'],
            'description': 'Write genome annotations'
        },
        'Write FASTA': {
            'command': 'write-sequence',
            'parameters': '--format=fasta',
            'output_formats': ['.fasta', '.fa'],
            'description': 'Write sequences in FASTA format'
        },
        'Write NGS Reads Assembly': {
            'command': 'write-assembly',
            'parameters': '--format=fasta',
            'output_formats': ['.fasta'],
            'description': 'Write assembled NGS data'
        },
        'Write Plain Text': {
            'command': 'write-text',
            'output_formats': ['.txt'],
            'description': 'Write plain text output'
        },
        'Write Sequence': {
            'command': 'write-sequence',
            'output_formats': ['.fasta', '.fa', '.seq'],
            'description': 'Write sequence data'
        },
        'Write Variants': {
            'command': 'write-variants',
            'parameters': '--format=vcf',
            'output_formats': ['.vcf'],
            'description': 'Write variant data'
        },

        # =====================================
        # DATA FLOW
        # =====================================
        'Filter': {
            'command': 'filter-sequences',
            'parameters': '--criteria=length',
            'description': 'Filter sequences based on criteria'
        },
        'Grouper': {
            'command': 'group-sequences',
            'parameters': '--method=similarity',
            'description': 'Group sequences by similarity'
        },
        'Multiplexer': {
            'command': 'multiplex-data',
            'description': 'Combine multiple data streams'
        },
        'Sequence Marker': {
            'command': 'mark-sequences',
            'parameters': '--marker-type=position',
            'description': 'Mark sequences with identifiers'
        },

        # =====================================
        # SEQUENCE ALIGNMENT TOOLS
        # =====================================
        'Align with ClustalW': {
            'command': 'align',
            'parameters': '--algorithm=clustalw --gap-open=10 --gap-extend=0.2',
            'description': 'Multiple sequence alignment with ClustalW'
        },
        'Align with ClustalO': {
            'command': 'align',
            'parameters': '--algorithm=clustalo --iterations=3',
            'description': 'Multiple sequence alignment with Clustal Omega'
        },
        'Align with MUSCLE': {
            'command': 'align',
            'parameters': '--algorithm=muscle --maxiters=16',
            'description': 'Multiple sequence alignment with MUSCLE'
        },
        'Align with Kalign': {
            'command': 'align',
            'parameters': '--algorithm=kalign',
            'description': 'Multiple sequence alignment with Kalign'
        },
        'Align with MAFFT': {
            'command': 'align',
            'parameters': '--algorithm=mafft --strategy=auto',
            'description': 'Multiple sequence alignment with MAFFT'
        },
        'Align with T-Coffee': {
            'command': 'align',
            'parameters': '--algorithm=tcoffee',
            'description': 'Multiple sequence alignment with T-Coffee'
        },

        # =====================================
        # PHYLOGENETIC ANALYSIS
        # =====================================
        'Build Tree with IQ-TREE': {
            'command': 'build-tree',
            'parameters': '--method=iqtree --model=AUTO --bootstrap=1000',
            'description': 'Build phylogenetic tree with IQ-TREE'
        },
        'Build Tree with PHYLIP NJ': {
            'command': 'build-tree', 
            'parameters': '--method=phylip-nj --bootstrap=100',
            'description': 'Build neighbor-joining tree with PHYLIP'
        },
        'Build Tree with MrBayes': {
            'command': 'build-tree',
            'parameters': '--method=mrbayes --ngen=10000',
            'description': 'Bayesian phylogenetic analysis with MrBayes'
        },
        'Build Tree with PhyML': {
            'command': 'build-tree',
            'parameters': '--method=phyml --model=GTR --bootstrap=100',
            'description': 'Maximum likelihood tree with PhyML'
        },

        # =====================================
        # BASIC ANALYSIS
        # =====================================
        'Statistics': {
            'command': 'sequence-statistics',
            'parameters': '--metrics=length,gc-content,composition',
            'description': 'Calculate sequence statistics'
        },
        'Summarize': {
            'command': 'summarize-data',
            'parameters': '--format=table',
            'description': 'Generate data summary'
        },

        # =====================================
        # DATA CONVERTERS
        # =====================================
        'Format Converter': {
            'command': 'convert-format',
            'parameters': '--input-format=auto --output-format=fasta',
            'description': 'Convert between file formats'
        },
        'JSON Parser': {
            'command': 'parse-json',
            'parameters': '--extract=sequences',
            'description': 'Parse JSON formatted data'
        },

        # =====================================
        # DNA ASSEMBLY
        # =====================================
        'Assembler 1': {
            'command': 'assemble-reads',
            'parameters': '--assembler=spades --k-mer=21,33,55',
            'description': 'Assemble reads using SPAdes'
        },
        'Assembler 2': {
            'command': 'assemble-reads',
            'parameters': '--assembler=velvet --k-mer=31',
            'description': 'Assemble reads using Velvet'
        },

        # =====================================
        # RNA-SEQ ANALYSIS TOOLS
        # =====================================
        'DESeq2': {
            'command': 'differential-expression',
            'parameters': '--method=deseq2 --p-value=0.05 --fold-change=2',
            'description': 'Differential expression analysis with DESeq2'
        },
        'Kallisto': {
            'command': 'quantify-expression',
            'parameters': '--method=kallisto --bootstrap=100',
            'description': 'RNA-seq quantification with Kallisto'
        },

        # =====================================
        # FILE I/O TOOLS
        # =====================================
        'CSV Reader': {
            'command': 'read-csv',
            'parameters': '--delimiter=comma --header=true',
            'input_formats': ['.csv'],
            'description': 'Read CSV formatted data'
        },
        'Excel Reader': {
            'command': 'read-excel',
            'input_formats': ['.xlsx', '.xls'],
            'description': 'Read Excel spreadsheet data'
        },
        'CSV Writer': {
            'command': 'write-csv',
            'parameters': '--delimiter=comma --header=true',
            'output_formats': ['.csv'],
            'description': 'Write CSV formatted output'
        },
        'Excel Writer': {
            'command': 'write-excel',
            'output_formats': ['.xlsx'],
            'description': 'Write Excel spreadsheet output'
        },

        # =====================================
        # NGS BASIC FUNCTIONS
        # =====================================
        'Splitter': {
            'command': 'split-sequences',
            'parameters': '--method=count --chunks=4',
            'description': 'Split sequence files into chunks'
        },
        'Merger': {
            'command': 'merge-sequences',
            'parameters': '--method=concatenate',
            'description': 'Merge multiple sequence files'
        },

        # =====================================
        # BLAST SEARCH
        # =====================================
        'NCBI GenBank BLAST': {
            'command': 'blast-search',
            'parameters': '--database=ncbi-genbank --program=blastn --evalue=1e-5',
            'description': 'BLAST search against NCBI GenBank'
        },
        'Search Cloud Database': {
            'command': 'blast-search', 
            'parameters': '--database=cloud --program=blastp --evalue=1e-3',
            'description': 'BLAST search against cloud databases'
        },
    }

    def __init__(self):
        pass
    
    def get_supported_elements(self) -> List[str]:
        """Get list of all supported workflow elements"""
        return list(self.COMMAND_MAPPINGS.keys())
    
    def is_element_supported(self, element_name: str) -> bool:
        """Check if an element is supported"""
        return element_name in self.COMMAND_MAPPINGS
    
    def get_element_info(self, element_name: str) -> Optional[Dict]:
        """Get detailed information about an element"""
        return self.COMMAND_MAPPINGS.get(element_name)
    
    def build_commands(self, workflow_definition: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert workflow definition to UGENE commands with full metadata"""
        commands = []
        nodes = workflow_definition.get('nodes', [])
        connections = workflow_definition.get('connections', [])
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(nodes, connections)
        
        # Process nodes in topological order
        execution_order = self._topological_sort(dependency_graph)
        
        for node_id in execution_order:
            node = next((n for n in nodes if n['id'] == node_id), None)
            if node:
                command_info = self._build_node_command(node, connections)
                if command_info:
                    commands.append(command_info)
        
        return commands
    
    def _build_node_command(self, node: Dict[str, Any], connections: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Build command for a single node with full metadata"""
        node_name = node.get('name', '')
        node_type = node.get('type', '')
        node_id = node.get('id')
        
        # Get command mapping
        element_info = self.COMMAND_MAPPINGS.get(node_name)
        if not element_info:
            # Fallback for unmapped elements
            element_info = {
                'command': f"process-{node_type}",
                'description': f'Generic {node_type} processing'
            }
        
        # Build base command
        base_command = element_info['command']
        parameters = element_info.get('parameters', '')
        
        # Add input files
        input_connections = [c for c in connections if c['to'] == node_id]
        input_files = []
        if input_connections:
            input_files = [f"output_{c['from']}.out" for c in input_connections]
        
        # Generate output file
        output_file = f"output_{node_id}.out"
        
        # Build full command
        full_command = f"ugene {base_command}"
        if input_files:
            full_command += f" --in={':'.join(input_files)}"
        full_command += f" --out={output_file}"
        if parameters:
            full_command += f" {parameters}"
        
        # Add node-specific parameters from UI
        if 'parameters' in node:
            for key, value in node['parameters'].items():
                full_command += f" --{key}={value}"
        
        return {
            'command': full_command,
            'node_id': node_id,
            'node_name': node_name,
            'node_type': node_type,
            'input_files': input_files,
            'output_file': output_file,
            'description': element_info.get('description', ''),
            'expected_formats': element_info.get('output_formats', []),
            'metadata': element_info
        }
    
    def _build_dependency_graph(self, nodes: List[Dict[str, Any]], connections: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build dependency graph from nodes and connections"""
        graph = {node['id']: [] for node in nodes}
        
        for connection in connections:
            from_node = connection['from']
            to_node = connection['to']
            if to_node in graph:
                graph[to_node].append(from_node)
        
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort to determine execution order"""
        # Kahn's algorithm
        in_degree = {node: 0 for node in graph}
        
        # Calculate in-degrees
        for node in graph:
            for dependency in graph[node]:
                if dependency in in_degree:
                    in_degree[dependency] += 1
        
        # Find nodes with no incoming edges
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # Remove this node from all adjacency lists
            for neighbor in list(graph.keys()):
                if node in graph[neighbor]:
                    graph[neighbor].remove(node)
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        return result

    def validate_workflow(self, workflow_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow against supported elements"""
        errors = []
        warnings = []
        unsupported_elements = []
        
        nodes = workflow_definition.get('nodes', [])
        
        for node in nodes:
            node_name = node.get('name', '')
            if not self.is_element_supported(node_name):
                unsupported_elements.append(node_name)
                warnings.append(f"Element '{node_name}' is not fully supported yet")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'unsupported_elements': unsupported_elements,
            'supported_count': len(nodes) - len(unsupported_elements),
            'total_count': len(nodes)
        }





