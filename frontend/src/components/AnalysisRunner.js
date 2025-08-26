// frontend/src/components/AnalysisRunner.js
import React, { useState } from 'react';
import { Card, Row, Col, Button, Form, Modal, Alert, ProgressBar, Badge } from 'react-bootstrap';
import { BsPlay, BsStop, BsGear, BsDownload, BsEye, BsTrash } from 'react-icons/bs';

const AnalysisRunner = ({ 
  selectedSequences, 
  sequences, 
  analyses, 
  onRunAnalysis, 
  isConnected 
}) => {
  const [selectedTool, setSelectedTool] = useState('blast');
  const [showParametersModal, setShowParametersModal] = useState(false);
  const [analysisParameters, setAnalysisParameters] = useState({});
  const [showResultsModal, setShowResultsModal] = useState(false);
  const [selectedResult, setSelectedResult] = useState(null);

  const analysisTools = {
    blast: {
      name: 'BLAST Search',
      description: 'Sequence similarity search against databases',
      parameters: {
        database: { type: 'select', options: ['nr', 'nt', 'swissprot', 'pdb'], default: 'nr' },
        evalue: { type: 'number', default: 1e-5, min: 1e-10, max: 1 },
        max_hits: { type: 'number', default: 10, min: 1, max: 100 },
        word_size: { type: 'number', default: null, min: 2, max: 50 }
      }
    },
    alignment: {
      name: 'Multiple Sequence Alignment',
      description: 'Align multiple sequences to identify conserved regions',
      parameters: {
        method: { type: 'select', options: ['muscle', 'clustalw', 'mafft'], default: 'muscle' },
        gap_penalty: { type: 'number', default: -10, min: -50, max: 0 },
        gap_extension: { type: 'number', default: -1, min: -10, max: 0 }
      },
      minSequences: 2
    },
    phylogeny: {
      name: 'Phylogenetic Analysis',
      description: 'Construct evolutionary trees from aligned sequences',
      parameters: {
        method: { type: 'select', options: ['iqtree', 'raxml', 'fasttree'], default: 'iqtree' },
        model: { type: 'select', options: ['AUTO', 'JTT', 'WAG', 'LG'], default: 'AUTO' },
        bootstrap: { type: 'number', default: 1000, min: 100, max: 10000 }
      },
      requiresAlignment: true
    },
    gene_prediction: {
      name: 'Gene Prediction',
      description: 'Identify genes and coding sequences',
      parameters: {
        organism_type: { type: 'select', options: ['bacteria', 'archaea', 'virus'], default: 'bacteria' },
        mode: { type: 'select', options: ['single', 'meta'], default: 'single' },
        min_gene_length: { type: 'number', default: 90, min: 60, max: 500 }
      },
      maxSequences: 1
    },
    domain_search: {
      name: 'Protein Domain Search',
      description: 'Search for conserved protein domains and motifs',
      parameters: {
        database: { type: 'select', options: ['pfam', 'smart', 'cdd'], default: 'pfam' },
        evalue: { type: 'number', default: 1e-3, min: 1e-10, max: 1 },
        coverage_threshold: { type: 'number', default: 0.5, min: 0.1, max: 1.0 }
      },
      sequenceType: 'PROTEIN'
    }
  };

  const handleRunAnalysis = () => {
    const tool = analysisTools[selectedTool];
    
    // Validation
    if (selectedSequences.length === 0) {
      alert('Please select at least one sequence');
      return;
    }

    if (tool.minSequences && selectedSequences.length < tool.minSequences) {
      alert(`This analysis requires at least ${tool.minSequences} sequences`);
      return;
    }

    if (tool.maxSequences && selectedSequences.length > tool.maxSequences) {
      alert(`This analysis requires at most ${tool.maxSequences} sequence`);
      return;
    }

    if (tool.sequenceType) {
      const selectedSeqs = selectedSequences.map(id => sequences.find(s => s.id === id));
      const wrongType = selectedSeqs.find(seq => seq.sequence_type !== tool.sequenceType);
      if (wrongType) {
        alert(`This analysis requires ${tool.sequenceType} sequences only`);
        return;
      }
    }

    // Run the analysis
    onRunAnalysis(selectedTool, analysisParameters);
    setAnalysisParameters({});
  };

  const openParametersModal = () => {
    // Initialize parameters with defaults
    const tool = analysisTools[selectedTool];
    const defaultParams = {};
    Object.keys(tool.parameters).forEach(key => {
      defaultParams[key] = tool.parameters[key].default;
    });
    setAnalysisParameters(defaultParams);
    setShowParametersModal(true);
  };

  const handleParameterChange = (paramName, value) => {
    setAnalysisParameters(prev => ({
      ...prev,
      [paramName]: value
    }));
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'primary';
      case 'completed': return 'success';
      case 'failed': return 'danger';
      case 'pending': return 'warning';
      default: return 'secondary';
    }
  };

  const formatDuration = (startTime, endTime) => {
    if (!startTime) return 'Unknown';
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const duration = Math.round((end - start) / 1000);
    
    if (duration < 60) return `${duration}s`;
    if (duration < 3600) return `${Math.round(duration / 60)}m`;
    return `${Math.round(duration / 3600)}h`;
  };

  return (
    <div>
      <Row>
        {/* Analysis Tools Panel */}
        <Col md={6}>
          <Card>
            <Card.Header>
              <h5 className="mb-0">Analysis Tools</h5>
            </Card.Header>
            <Card.Body>
              {/* Tool Selection */}
              <Form.Group className="mb-3">
                <Form.Label>Select Analysis Tool</Form.Label>
                <Form.Select 
                  value={selectedTool} 
                  onChange={(e) => setSelectedTool(e.target.value)}
                >
                  {Object.keys(analysisTools).map(key => (
                    <option key={key} value={key}>
                      {analysisTools[key].name}
                    </option>
                  ))}
                </Form.Select>
                <Form.Text className="text-muted">
                  {analysisTools[selectedTool].description}
                </Form.Text>
              </Form.Group>

              {/* Selected Sequences Info */}
              <Alert variant="info">
                <strong>Selected Sequences:</strong> {selectedSequences.length}
                <br />
                {selectedSequences.length > 0 && (
                  <small>
                    Types: {[...new Set(selectedSequences.map(id => 
                      sequences.find(s => s.id === id)?.sequence_type
                    ))].join(', ')}
                  </small>
                )}
              </Alert>

              {/* Connection Status */}
              <Alert variant={isConnected ? 'success' : 'warning'}>
                Real-time updates: {isConnected ? 'Connected' : 'Disconnected'}
              </Alert>

              {/* Action Buttons */}
              <div className="d-grid gap-2">
                <Button
                  variant="primary"
                  size="lg"
                  onClick={handleRunAnalysis}
                  disabled={selectedSequences.length === 0}
                >
                  <BsPlay className="me-1" />
                  Run {analysisTools[selectedTool].name}
                </Button>
                <Button
                  variant="outline-secondary"
                  onClick={openParametersModal}
                >
                  <BsGear className="me-1" />
                  Configure Parameters
                </Button>
              </div>
            </Card.Body>
          </Card>
        </Col>

        {/* Running Analyses Panel */}
        <Col md={6}>
          <Card>
            <Card.Header>
              <h5 className="mb-0">Analysis Queue ({analyses.length})</h5>
            </Card.Header>
            <Card.Body style={{ maxHeight: '500px', overflowY: 'auto' }}>
              {analyses.length === 0 ? (
                <div className="text-center text-muted py-4">
                  No analyses running
                </div>
              ) : (
                analyses.map((analysis) => (
                  <Card key={analysis.id} className="mb-2">
                    <Card.Body className="py-2">
                      <Row className="align-items-center">
                        <Col>
                          <div className="d-flex justify-content-between align-items-center mb-1">
                            <strong>{analysisTools[analysis.type]?.name || analysis.type}</strong>
                            <Badge bg={getStatusColor(analysis.status)}>
                              {analysis.status}
                            </Badge>
                          </div>
                          
                          {analysis.status === 'running' && (
                            <ProgressBar 
                              now={analysis.progress} 
                              label={`${analysis.progress}%`}
                              className="mb-1"
                            />
                          )}
                          
                          <small className="text-muted">
                            Started: {formatDuration(analysis.started_at)}
                            {analysis.sequences && ` | Sequences: ${analysis.sequences.length}`}
                          </small>
                        </Col>
                        
                        <Col xs="auto">
                          <div className="btn-group-vertical btn-group-sm">
                            {analysis.status === 'completed' && (
                              <Button
                                variant="outline-primary"
                                size="sm"
                                onClick={() => {
                                  setSelectedResult(analysis);
                                  setShowResultsModal(true);
                                }}
                              >
                                <BsEye />
                              </Button>
                            )}
                            {analysis.status === 'running' && (
                              <Button
                                variant="outline-danger"
                                size="sm"
                                onClick={() => {
                                  // Stop analysis functionality
                                }}
                              >
                                <BsStop />
                              </Button>
                            )}
                            <Button
                              variant="outline-secondary"
                              size="sm"
                              onClick={() => {
                                // Remove from list
                              }}
                            >
                              <BsTrash />
                            </Button>
                          </div>
                        </Col>
                      </Row>
                      
                      {analysis.error && (
                        <Alert variant="danger" className="mt-2 mb-0">
                          <small>{analysis.error}</small>
                        </Alert>
                      )}
                    </Card.Body>
                  </Card>
                ))
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Parameters Configuration Modal */}
      <Modal 
        show={showParametersModal} 
        onHide={() => setShowParametersModal(false)}
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>
            Configure {analysisTools[selectedTool].name} Parameters
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            {Object.keys(analysisTools[selectedTool].parameters).map(paramName => {
              const param = analysisTools[selectedTool].parameters[paramName];
              
              return (
                <Form.Group key={paramName} className="mb-3">
                  <Form.Label className="text-capitalize">
                    {paramName.replace(/_/g, ' ')}
                  </Form.Label>
                  
                  {param.type === 'select' ? (
                    <Form.Select
                      value={analysisParameters[paramName] || param.default}
                      onChange={(e) => handleParameterChange(paramName, e.target.value)}
                    >
                      {param.options.map(option => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </Form.Select>
                  ) : param.type === 'number' ? (
                    <Form.Control
                      type="number"
                      value={analysisParameters[paramName] || param.default}
                      onChange={(e) => handleParameterChange(paramName, parseFloat(e.target.value))}
                      min={param.min}
                      max={param.max}
                      step={paramName.includes('evalue') ? 'any' : 1}
                    />
                  ) : (
                    <Form.Control
                      type="text"
                      value={analysisParameters[paramName] || param.default}
                      onChange={(e) => handleParameterChange(paramName, e.target.value)}
                    />
                  )}
                </Form.Group>
              );
            })}
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button 
            variant="secondary" 
            onClick={() => setShowParametersModal(false)}
          >
            Cancel
          </Button>
          <Button 
            variant="primary" 
            onClick={() => {
              setShowParametersModal(false);
              handleRunAnalysis();
            }}
          >
            Run Analysis
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Results Modal */}
      <Modal 
        show={showResultsModal} 
        onHide={() => setShowResultsModal(false)}
        size="xl"
      >
        <Modal.Header closeButton>
          <Modal.Title>
            Analysis Results: {selectedResult?.type}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedResult && (
            <AnalysisResultsDisplay analysis={selectedResult} />
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button
            variant="primary"
            onClick={() => {
              // Download results
            }}
          >
            <BsDownload className="me-1" />
            Download Results
          </Button>
          <Button 
            variant="secondary" 
            onClick={() => setShowResultsModal(false)}
          >
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

// Analysis Results Display Component
const AnalysisResultsDisplay = ({ analysis }) => {
  if (!analysis.results) {
    return <Alert variant="info">No results available</Alert>;
  }

  const renderBlastResults = (results) => (
    <div>
      <h6>BLAST Hits</h6>
      {results.results?.map((queryResult, qIndex) => (
        <Card key={qIndex} className="mb-3">
          <Card.Header>Query {qIndex + 1}</Card.Header>
          <Card.Body>
            {queryResult.hits?.length > 0 ? (
              <div className="table-responsive">
                <table className="table table-sm">
                  <thead>
                    <tr>
                      <th>Hit ID</th>
                      <th>Description</th>
                      <th>Score</th>
                      <th>E-value</th>
                      <th>Identity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queryResult.hits.map((hit, hIndex) => (
                      <tr key={hIndex}>
                        <td>{hit.accession}</td>
                        <td>{hit.description}</td>
                        <td>{hit.score?.toFixed(1)}</td>
                        <td>{hit.evalue?.toExponential(2)}</td>
                        <td>{(hit.identity * 100)?.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Alert variant="warning">No significant hits found</Alert>
            )}
          </Card.Body>
        </Card>
      ))}
    </div>
  );

  const renderAlignmentResults = (results) => (
    <div>
      <h6>Multiple Sequence Alignment</h6>
      <Alert variant="info">
        <strong>Statistics:</strong><br />
        Alignment Length: {results.alignment_statistics?.alignment_length}<br />
        Conservation: {results.alignment_statistics?.conservation_percentage?.toFixed(1)}%<br />
        Gap Content: {results.alignment_statistics?.gap_percentage?.toFixed(1)}%
      </Alert>
      
      <div className="bg-light p-3 rounded" style={{ fontFamily: 'monospace', fontSize: '12px', overflowX: 'auto' }}>
        {results.aligned_sequences?.map((seq, index) => (
          <div key={index}>
            <strong>{seq.id || `Seq_${index + 1}`}</strong><br />
            {seq.sequence}<br /><br />
          </div>
        ))}
      </div>
    </div>
  );

  const renderPhylogenyResults = (results) => (
    <div>
      <h6>Phylogenetic Tree</h6>
      <Alert variant="info">
        Method: {results.method}<br />
        Model: {results.parameters?.model}
      </Alert>
      
      <div className="bg-light p-3 rounded">
        <strong>Newick Format:</strong>
        <pre style={{ fontSize: '12px' }}>{results.newick_tree}</pre>
      </div>
    </div>
  );

  const renderGenePredictionResults = (results) => (
    <div>
      <h6>Gene Prediction Results</h6>
      <Alert variant="info">
        <strong>Summary:</strong><br />
        Genes Found: {results.statistics?.total_genes}<br />
        Proteins: {results.statistics?.total_proteins}<br />
        Average Gene Length: {results.statistics?.average_gene_length?.toFixed(0)} bp
      </Alert>
      
      {results.predicted_genes?.length > 0 && (
        <div className="table-responsive">
          <h6>Predicted Genes</h6>
          <table className="table table-sm">
            <thead>
              <tr>
                <th>Gene ID</th>
                <th>Start</th>
                <th>End</th>
                <th>Strand</th>
                <th>Length</th>
              </tr>
            </thead>
            <tbody>
              {results.predicted_genes.map((gene, index) => (
                <tr key={index}>
                  <td>{gene.attributes?.ID || `gene_${index + 1}`}</td>
                  <td>{gene.start}</td>
                  <td>{gene.end}</td>
                  <td>{gene.strand}</td>
                  <td>{gene.end - gene.start + 1} bp</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );

  // Render based on analysis type
  switch (analysis.type) {
    case 'blast':
      return renderBlastResults(analysis.results);
    case 'alignment':
      return renderAlignmentResults(analysis.results);
    case 'phylogeny':
      return renderPhylogenyResults(analysis.results);
    case 'gene_prediction':
      return renderGenePredictionResults(analysis.results);
    default:
      return (
        <div>
          <h6>Raw Results</h6>
          <pre className="bg-light p-3 rounded" style={{ fontSize: '12px', maxHeight: '400px', overflow: 'auto' }}>
            {JSON.stringify(analysis.results, null, 2)}
          </pre>
        </div>
      );
  }
};

export default AnalysisRunner;