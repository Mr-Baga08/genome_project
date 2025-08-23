const elements = [
  {
    name: 'Data Readers',
    subElements: [
      { 
        name: 'Read Alignment', 
        type: 'reader',
        description: 'Read alignment from various formats (.aln, .clustal, .msf)',
        supportedFormats: ['.aln', '.clustal', '.msf', '.stockholm'],
        backendSupported: true
      },
      { 
        name: 'Read Annotations', 
        type: 'reader',
        description: 'Read genome annotations (.gff, .gtf, .bed)',
        supportedFormats: ['.gff', '.gtf', '.bed', '.gb'],
        backendSupported: true
      },
      {
        name: 'Read FASTQ File with SE Reads',
        type: 'reader',
        description: 'Read single-end FASTQ sequencing files',
        supportedFormats: ['.fastq', '.fq'],
        backendSupported: true
      },
      {
        name: 'Read FASTQ File with PE Reads',
        type: 'reader',
        description: 'Read paired-end FASTQ sequencing files',
        supportedFormats: ['.fastq', '.fq'],
        backendSupported: true
      },
      { 
        name: 'Read File URL(s)', 
        type: 'reader',
        description: 'Download sequences from remote URLs',
        supportedFormats: ['url'],
        backendSupported: true
      },
      {
        name: 'Read NGS Reads Assembly',
        type: 'reader',
        description: 'Read assembled NGS data',
        supportedFormats: ['.fasta', '.fa', '.contigs'],
        backendSupported: true
      },
      { 
        name: 'Read Plain Text', 
        type: 'reader',
        description: 'Read plain text files',
        supportedFormats: ['.txt'],
        backendSupported: true
      },
      { 
        name: 'Read Sequence', 
        type: 'reader',
        description: 'Read sequence data in various formats',
        supportedFormats: ['.fasta', '.fa', '.seq'],
        backendSupported: true
      },
      {
        name: 'Read Sequence from Remote Database',
        type: 'reader',
        description: 'Fetch sequences from NCBI and other databases',
        supportedFormats: ['accession'],
        backendSupported: true
      },
      { 
        name: 'Read Variants', 
        type: 'reader',
        description: 'Read variant call format files',
        supportedFormats: ['.vcf', '.bcf'],
        backendSupported: true
      },
    ],
  },
  {
    name: 'Data Writers',
    subElements: [
      { 
        name: 'Write Alignment', 
        type: 'writer',
        description: 'Write alignment in specified format',
        outputFormats: ['.aln', '.clustal'],
        backendSupported: true
      },
      { 
        name: 'Write Annotations', 
        type: 'writer',
        description: 'Write genome annotations',
        outputFormats: ['.gff', '.gff3'],
        backendSupported: true
      },
      { 
        name: 'Write FASTA', 
        type: 'writer',
        description: 'Write sequences in FASTA format',
        outputFormats: ['.fasta', '.fa'],
        backendSupported: true
      },
      {
        name: 'Write NGS Reads Assembly',
        type: 'writer',
        description: 'Write assembled NGS data',
        outputFormats: ['.fasta'],
        backendSupported: true
      },
      { 
        name: 'Write Plain Text', 
        type: 'writer',
        description: 'Write plain text output',
        outputFormats: ['.txt'],
        backendSupported: true
      },
      { 
        name: 'Write Sequence', 
        type: 'writer',
        description: 'Write sequence data',
        outputFormats: ['.fasta', '.fa', '.seq'],
        backendSupported: true
      },
      { 
        name: 'Write Variants', 
        type: 'writer',
        description: 'Write variant data',
        outputFormats: ['.vcf'],
        backendSupported: true
      },
    ],
  },
  {
    name: 'Data Flow',
    subElements: [
      { 
        name: 'Filter', 
        type: 'filter',
        description: 'Filter sequences based on criteria',
        parameters: ['criteria', 'threshold'],
        backendSupported: true
      },
      { 
        name: 'Grouper', 
        type: 'flow',
        description: 'Group sequences by similarity',
        parameters: ['method', 'similarity_threshold'],
        backendSupported: true
      },
      { 
        name: 'Multiplexer', 
        type: 'flow',
        description: 'Combine multiple data streams',
        backendSupported: true
      },
      { 
        name: 'Sequence Marker', 
        type: 'flow',
        description: 'Mark sequences with identifiers',
        parameters: ['marker_type'],
        backendSupported: true
      },
    ],
  },
  {
    name: 'Sequence Editing & Annotation',
    subElements: [
      { name: 'Create New Sequence', type: 'sequence_editor' },
      { name: 'Edit Sequence', type: 'sequence_editor' },
      { name: 'Annotate Sequence', type: 'sequence_editor' },
    ],
  },
  {
    name: 'Basic Analysis',
    subElements: [
      { 
        name: 'Statistics', 
        type: 'analyzer',
        description: 'Calculate sequence statistics (length, GC content, composition)',
        parameters: ['metrics'],
        backendSupported: true
      },
      { 
        name: 'Summarize', 
        type: 'analyzer',
        description: 'Generate data summary',
        parameters: ['format'],
        backendSupported: true
      },
    ],
  },
  {
    name: 'Data Converters',
    subElements: [
      { 
        name: 'Format Converter', 
        type: 'converter',
        description: 'Convert between file formats',
        parameters: ['input_format', 'output_format'],
        backendSupported: true
      },
      { 
        name: 'JSON Parser', 
        type: 'converter',
        description: 'Parse JSON formatted data',
        parameters: ['extract_field'],
        backendSupported: true
      },
    ],
  },
  {
    name: 'DNA Assembly',
    subElements: [
      { 
        name: 'Assembler 1', 
        type: 'assembler',
        description: 'Assemble reads using SPAdes',
        parameters: ['k-mer', 'coverage_cutoff'],
        backendSupported: true
      },
      { 
        name: 'Assembler 2', 
        type: 'assembler',
        description: 'Assemble reads using Velvet',
        parameters: ['k-mer', 'expected_coverage'],
        backendSupported: true
      },
    ],
  },
  {
    name: 'HMMER2 Tools',
    subElements: [
      { 
        name: 'DESeq2', 
        type: 'analyzer',
        description: 'Differential expression analysis with DESeq2',
        parameters: ['p_value', 'fold_change'],
        backendSupported: true
      },
      { 
        name: 'Kallisto', 
        type: 'analyzer',
        description: 'RNA-seq quantification with Kallisto',
        parameters: ['bootstrap', 'fragment_length'],
        backendSupported: true
      },
    ],
  },
  {
    name: 'HMMER3 Tools',
    subElements: [
      { 
        name: 'CSV Reader', 
        type: 'reader',
        description: 'Read CSV formatted data',
        supportedFormats: ['.csv'],
        parameters: ['delimiter', 'header'],
        backendSupported: true
      },
      { 
        name: 'Excel Reader', 
        type: 'reader',
        description: 'Read Excel spreadsheet data',
        supportedFormats: ['.xlsx', '.xls'],
        backendSupported: true
      },
    ],
  },
  {
    name: 'Multiple Sequence Alignment',
    subElements: [
      { 
        name: 'Align with ClustalW', 
        type: 'aligner',
        description: 'Multiple sequence alignment with ClustalW',
        parameters: ['gap_open', 'gap_extend'],
        backendSupported: true
      },
      { 
        name: 'Align with ClustalO', 
        type: 'aligner',
        description: 'Multiple sequence alignment with Clustal Omega',
        parameters: ['iterations'],
        backendSupported: true
      },
      { 
        name: 'Align with MUSCLE', 
        type: 'aligner',
        description: 'Multiple sequence alignment with MUSCLE',
        parameters: ['maxiters'],
        backendSupported: true
      },
      { 
        name: 'Align with Kalign', 
        type: 'aligner',
        description: 'Multiple sequence alignment with Kalign',
        backendSupported: true
      },
      { 
        name: 'Align with MAFFT', 
        type: 'aligner',
        description: 'Multiple sequence alignment with MAFFT',
        parameters: ['strategy'],
        backendSupported: true
      },
      { 
        name: 'Align with T-Coffee', 
        type: 'aligner',
        description: 'Multiple sequence alignment with T-Coffee',
        backendSupported: true
      },
      { 
        name: 'CSV Writer', 
        type: 'writer',
        description: 'Write CSV formatted output',
        outputFormats: ['.csv'],
        parameters: ['delimiter', 'header'],
        backendSupported: true
      },
      { 
        name: 'Excel Writer', 
        type: 'writer',
        description: 'Write Excel spreadsheet output',
        outputFormats: ['.xlsx'],
        backendSupported: true
      },
    ],
  },
  {
    name: 'Fast Search and Alignment',
    subElements: [
      { name: 'Align with ClustalW', type: 'alignment', backendSupported: true },
      { name: 'Align with ClustalO', type: 'alignment', backendSupported: true },
      { name: 'Align with MUSCLE', type: 'alignment', backendSupported: true },
      { name: 'Align with Kalign', type: 'alignment', backendSupported: true },
      { name: 'Align with MAFFT', type: 'alignment', backendSupported: true },
      { name: 'Align with T-Coffee', type: 'alignment', backendSupported: true },
    ],
  },
  {
    name: 'PCR and Database Search',
    subElements: [
      { name: 'In Silico PCR', type: 'search' },
      { name: 'Search NCBI', type: 'search' },
      { name: 'Search PDB', type: 'search' },
      { name: 'Search UniProtKB/Swiss-Prot', type: 'search' },
      { name: 'Search UniProtKB/TrEMBL', type: 'search' },
    ],
  },
  {
    name: 'BLAST Search',
    subElements: [
      { 
        name: 'NCBI GenBank BLAST', 
        type: 'blast',
        description: 'BLAST search against NCBI GenBank',
        parameters: ['program', 'evalue', 'max_hits'],
        backendSupported: true
      },
      { 
        name: 'Search Cloud Database', 
        type: 'blast',
        description: 'BLAST search against cloud databases',
        parameters: ['database', 'program', 'evalue'],
        backendSupported: true
      },
    ],
  },
  {
    name: 'NGS: Basic Functions',
    subElements: [
      { 
        name: 'Splitter', 
        type: 'flow',
        description: 'Split sequence files into chunks',
        parameters: ['method', 'chunks'],
        backendSupported: true
      },
      { 
        name: 'Merger', 
        type: 'flow',
        description: 'Merge multiple sequence files',
        parameters: ['method'],
        backendSupported: true
      },
    ],
  },
  {
    name: 'NGS: Map/Assemble Reads',
    subElements: [
      { 
        name: 'Statistics', 
        type: 'analyzer',
        description: 'Calculate NGS statistics',
        backendSupported: true
      },
      { 
        name: 'Summarize', 
        type: 'analyzer',
        description: 'Summarize NGS data',
        backendSupported: true
      },
    ],
  },
  {
    name: 'NGS: RNA-Seq Analysis',
    subElements: [
      { 
        name: 'DESeq2', 
        type: 'analyzer',
        description: 'Differential expression analysis',
        backendSupported: true
      },
      { 
        name: 'Kallisto', 
        type: 'analyzer',
        description: 'RNA-seq quantification',
        backendSupported: true
      },
      { 
        name: 'Format Converter', 
        type: 'converter',
        description: 'Convert RNA-seq file formats',
        backendSupported: true
      },
      { 
        name: 'JSON Parser', 
        type: 'converter',
        description: 'Parse RNA-seq JSON data',
        backendSupported: true
      },
    ],
  },
  {
    name: 'NGS: Variant Analysis',
    subElements: [
      { 
        name: 'Call Variants', 
        type: 'analyzer',
        description: 'Call genetic variants from NGS data',
        parameters: ['caller', 'quality_threshold']
      },
      { 
        name: 'Filter Variants', 
        type: 'filter',
        description: 'Filter variant calls by quality',
        parameters: ['quality', 'depth', 'frequency']
      },
      { 
        name: 'Annotate Variants', 
        type: 'analyzer',
        description: 'Annotate variants with functional information',
        parameters: ['database', 'annotation_type']
      },
    ],
  },
  {
    name: 'Phylogenetic Tree',
    subElements: [
      { 
        name: 'Build Tree with IQ-TREE', 
        type: 'tree',
        description: 'Build phylogenetic tree with IQ-TREE',
        parameters: ['model', 'bootstrap'],
        backendSupported: true
      },
      { 
        name: 'Build Tree with PHYLIP NJ', 
        type: 'tree',
        description: 'Build neighbor-joining tree with PHYLIP',
        parameters: ['bootstrap'],
        backendSupported: true
      },
      { 
        name: 'Build Tree with MrBayes', 
        type: 'tree',
        description: 'Bayesian phylogenetic analysis with MrBayes',
        parameters: ['ngen', 'burnin'],
        backendSupported: true
      },
      { 
        name: 'Build Tree with PhyML', 
        type: 'tree',
        description: 'Maximum likelihood tree with PhyML',
        parameters: ['model', 'bootstrap'],
        backendSupported: true
      },
    ],
  },
  {
    name: '3D Structure Viewer',
    subElements: [
      { name: 'View PDB/MMDB File', type: 'viewer3d' },
    ],
  },
  {
    name: 'Primer Design',
    subElements: [
      { name: 'Design PCR Primers (Primer3)', type: 'primer' },
    ],
  },
  {
    name: 'Spatial Multi-omics',
    subElements: [
      { name: 'Giotto: Process Data', type: 'spatial' },
      { name: 'Giotto: Dimension Reduction', type: 'spatial' },
      { name: 'Giotto: Clustering', type: 'spatial' },
      { name: 'Giotto: Spatial Analysis', type: 'spatial' },
      { name: 'Giotto: Visualize Results', type: 'spatial' },
    ],
  },
  {
    name: 'Transcription Factor Binding Sites',
    subElements: [
      { 
        name: 'TFBS Prediction', 
        type: 'analyzer',
        description: 'Predict transcription factor binding sites',
        parameters: ['matrix', 'threshold']
      },
      { 
        name: 'TFBS Scanning', 
        type: 'analyzer',
        description: 'Scan sequences for known binding sites',
        parameters: ['database', 'p_value']
      },
    ],
  },
  {
    name: 'Utils',
    subElements: [
      { 
        name: 'Sequence Utilities', 
        type: 'utility',
        description: 'Various sequence manipulation utilities',
        parameters: ['operation']
      },
      { 
        name: 'File Utilities', 
        type: 'utility',
        description: 'File manipulation and conversion utilities',
        parameters: ['operation', 'format']
      },
    ],
  },
  {
    name: 'Custom Elements with Script',
    subElements: [
      { 
        name: 'Custom Python Script', 
        type: 'custom',
        description: 'Execute custom Python analysis script',
        parameters: ['script_path', 'arguments']
      },
      { 
        name: 'Custom R Script', 
        type: 'custom',
        description: 'Execute custom R analysis script',
        parameters: ['script_path', 'arguments']
      },
      { 
        name: 'Custom Shell Command', 
        type: 'custom',
        description: 'Execute custom shell command',
        parameters: ['command', 'arguments']
      },
    ],
  },
  {
    name: 'Workflow Tools',
    subElements: [
      { name: 'LAG Workflow Designer', type: 'workflow' },
    ],
  },
];

// Export additional metadata about elements
export const elementCategories = elements.map(category => ({
  name: category.name,
  count: category.subElements.length,
  supportedCount: category.subElements.filter(el => el.backendSupported).length
}));

export const supportedElements = elements.flatMap(category => 
  category.subElements.filter(element => element.backendSupported)
);

export const totalElementCount = elements.reduce((total, category) => 
  total + category.subElements.length, 0
);

export const supportedElementCount = elements.reduce((total, category) => 
  total + category.subElements.filter(el => el.backendSupported).length, 0
);

export default elements;

// frontend/src/services/elementsService.js - NEW FILE
// Service to interact with backend element validation

class ElementsService {
  constructor() {
    this.apiBase = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  }

  async getSupportedElements() {
    try {
      const response = await fetch(`${this.apiBase}/api/v1/elements`);
      if (!response.ok) throw new Error('Failed to fetch supported elements');
      return await response.json();
    } catch (error) {
      console.error('Error fetching supported elements:', error);
      return null;
    }
  }

  async validateWorkflow(workflow) {
    try {
      const response = await fetch(`${this.apiBase}/api/v1/elements/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflow)
      });
      if (!response.ok) throw new Error('Failed to validate workflow');
      return await response.json();
    } catch (error) {
      console.error('Error validating workflow:', error);
      return { valid: false, errors: [error.message] };
    }
  }

  async getElementDetails(elementName) {
    try {
      const response = await fetch(`${this.apiBase}/api/v1/elements/${encodeURIComponent(elementName)}`);
      if (!response.ok) throw new Error('Element not found');
      return await response.json();
    } catch (error) {
      console.error('Error getting element details:', error);
      return null;
    }
  }

  // Helper method to check if an element is supported
  isElementSupported(elementName) {
    const supportedElementNames = supportedElements.map(el => el.name);
    return supportedElementNames.includes(elementName);
  }

  // Get element by name from local data
  getElement(elementName) {
    for (const category of elements) {
      const element = category.subElements.find(el => el.name === elementName);
      if (element) {
        return {
          ...element,
          category: category.name
        };
      }
    }
    return null;
  }

  // Get all elements with backend support info
  getAllElementsWithSupport() {
    return elements.map(category => ({
      ...category,
      subElements: category.subElements.map(element => ({
        ...element,
        supported: element.backendSupported || false
      }))
    }));
  }
}

export const elementsService = new ElementsService();