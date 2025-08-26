// frontend/src/components/ResultsViewer.js
import React, { useState, useEffect, useMemo } from 'react';
import { Card, Row, Col, Nav, Tab, Button, Form, Alert, Table, Badge, Modal } from 'react-bootstrap';
import { BsDownload, BsEye, BsShare, BsFilter, BsSearch, BsBarChart, BsTable, BsTree } from 'react-icons/bs';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar, PieChart, Pie, Cell, ScatterPlot, Scatter,ScatterChart,ResponsiveContainer } from 'recharts';
import enhancedApiService from '../services/enhancedApiService'; 

const ResultsViewer = ({ analyses, sequences, onAnalysisSelect }) => {
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [viewMode, setViewMode] = useState('summary');
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [showExportModal, setShowExportModal] = useState(false);
  const [sortField, setSortField] = useState('started_at');
  const [sortOrder, setSortOrder] = useState('desc');

  // Filter and sort analyses
  const filteredAnalyses = useMemo(() => {
    let filtered = analyses;

    // Filter by status
    if (filterStatus !== 'all') {
      filtered = filtered.filter(analysis => analysis.status === filterStatus);
    }

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(analysis =>
        analysis.type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (analysis.id && analysis.id.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    // Sort
    filtered.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }

      if (sortOrder === 'asc') {
        return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      } else {
        return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
      }
    });

    return filtered;
  }, [analyses, filterStatus, searchTerm, sortField, sortOrder]);

  const handleAnalysisClick = (analysis) => {
    setSelectedAnalysis(analysis);
    onAnalysisSelect?.(analysis);
  };

  const getStatusBadgeVariant = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'primary';
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
    <div className="results-viewer">
      <Row>
        {/* Analysis List */}
        <Col md={4}>
          <Card>
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">Analysis Results</h5>
                <Badge bg="info">{filteredAnalyses.length}</Badge>
              </div>
            </Card.Header>
            <Card.Body className="p-0">
              {/* Filters and Search */}
              <div className="p-3 border-bottom">
                <Form.Group className="mb-2">
                  <Form.Control
                    type="text"
                    placeholder="Search analyses..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    size="sm"
                  />
                </Form.Group>
                <Row>
                  <Col>
                    <Form.Select
                      size="sm"
                      value={filterStatus}
                      onChange={(e) => setFilterStatus(e.target.value)}
                    >
                      <option value="all">All Status</option>
                      <option value="completed">Completed</option>
                      <option value="running">Running</option>
                      <option value="failed">Failed</option>
                      <option value="pending">Pending</option>
                    </Form.Select>
                  </Col>
                  <Col>
                    <Form.Select
                      size="sm"
                      value={`${sortField}-${sortOrder}`}
                      onChange={(e) => {
                        const [field, order] = e.target.value.split('-');
                        setSortField(field);
                        setSortOrder(order);
                      }}
                    >
                      <option value="started_at-desc">Newest First</option>
                      <option value="started_at-asc">Oldest First</option>
                      <option value="type-asc">Type A-Z</option>
                      <option value="status-asc">Status A-Z</option>
                    </Form.Select>
                  </Col>
                </Row>
              </div>

              {/* Analysis List */}
              <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
                {filteredAnalyses.length === 0 ? (
                  <div className="text-center p-4 text-muted">
                    No analyses found
                  </div>
                ) : (
                  filteredAnalyses.map((analysis) => (
                    <div
                      key={analysis.id}
                      className={`p-3 border-bottom analysis-item ${
                        selectedAnalysis?.id === analysis.id ? 'bg-light' : ''
                      }`}
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleAnalysisClick(analysis)}
                    >
                      <div className="d-flex justify-content-between align-items-center mb-1">
                        <strong className="analysis-type">
                          {analysis.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </strong>
                        <Badge bg={getStatusBadgeVariant(analysis.status)}>
                          {analysis.status}
                        </Badge>
                      </div>
                      
                      <div className="small text-muted mb-1">
                        ID: {analysis.id}
                      </div>
                      
                      <div className="small text-muted">
                        Started: {formatDuration(analysis.started_at)} ago
                        {analysis.sequences && ` • ${analysis.sequences.length} sequences`}
                      </div>
                      
                      {analysis.progress !== undefined && analysis.status === 'running' && (
                        <div className="progress mt-2" style={{ height: '4px' }}>
                          <div
                            className="progress-bar"
                            role="progressbar"
                            style={{ width: `${analysis.progress}%` }}
                          />
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>

        {/* Analysis Details */}
        <Col md={8}>
          {selectedAnalysis ? (
            <AnalysisDetailsPanel
              analysis={selectedAnalysis}
              sequences={sequences}
              onExportClick={() => setShowExportModal(true)}
            />
          ) : (
            <Card>
              <Card.Body className="text-center py-5">
                <h5 className="text-muted">No Analysis Selected</h5>
                <p className="text-muted">
                  Select an analysis from the list to view detailed results and visualizations.
                </p>
              </Card.Body>
            </Card>
          )}
        </Col>
      </Row>

      {/* Export Modal */}
      <ExportModal
        show={showExportModal}
        onHide={() => setShowExportModal(false)}
        analysis={selectedAnalysis}
      />
    </div>
  );
};

// Analysis Details Panel
const AnalysisDetailsPanel = ({ analysis, sequences, onExportClick }) => {
  const [activeTab, setActiveTab] = useState('summary');

  return (
    <Card>
      <Card.Header>
        <div className="d-flex justify-content-between align-items-center">
          <div>
            <h5 className="mb-0">
              {analysis.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              <Badge bg={getStatusBadgeVariant(analysis.status)} className="ms-2">
                {analysis.status}
              </Badge>
            </h5>
            <small className="text-muted">ID: {analysis.id}</small>
          </div>
          <div>
            <Button variant="outline-secondary" size="sm" className="me-2">
              <BsShare className="me-1" />
              Share
            </Button>
            <Button variant="primary" size="sm" onClick={onExportClick}>
              <BsDownload className="me-1" />
              Export
            </Button>
          </div>
        </div>
      </Card.Header>
      
      <Tab.Container activeKey={activeTab} onSelect={setActiveTab}>
        <Nav variant="tabs" className="px-3">
          <Nav.Item>
            <Nav.Link eventKey="summary">
              <BsEye className="me-1" />
              Summary
            </Nav.Link>
          </Nav.Item>
          {analysis.status === 'completed' && analysis.results && (
            <>
              <Nav.Item>
                <Nav.Link eventKey="results">
                  <BsTable className="me-1" />
                  Results
                </Nav.Link>
              </Nav.Item>
              <Nav.Item>
                <Nav.Link eventKey="visualizations">
                  <BsBarChart className="me-1" />
                  Charts
                </Nav.Link>
              </Nav.Item>
            </>
          )}
          <Nav.Item>
            <Nav.Link eventKey="parameters">
              <BsFilter className="me-1" />
              Parameters
            </Nav.Link>
          </Nav.Item>
        </Nav>

        <Tab.Content>
          <Tab.Pane eventKey="summary">
            <Card.Body>
              <AnalysisSummary analysis={analysis} sequences={sequences} />
            </Card.Body>
          </Tab.Pane>
          
          {analysis.status === 'completed' && analysis.results && (
            <>
              <Tab.Pane eventKey="results">
                <Card.Body>
                  <AnalysisResults analysis={analysis} />
                </Card.Body>
              </Tab.Pane>
              
              <Tab.Pane eventKey="visualizations">
                <Card.Body>
                  <AnalysisVisualizations analysis={analysis} />
                </Card.Body>
              </Tab.Pane>
            </>
          )}
          
          <Tab.Pane eventKey="parameters">
            <Card.Body>
              <AnalysisParameters analysis={analysis} />
            </Card.Body>
          </Tab.Pane>
        </Tab.Content>
      </Tab.Container>
    </Card>
  );
};

// Analysis Summary Component
const AnalysisSummary = ({ analysis, sequences }) => {
  const analysisSequences = analysis.sequences
    ? analysis.sequences.map(id => sequences.find(s => s.id === id)).filter(Boolean)
    : [];

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div>
      <Row>
        <Col md={6}>
          <h6>Analysis Information</h6>
          <Table size="sm" className="mb-4">
            <tbody>
              <tr>
                <td className="fw-bold">Type:</td>
                <td>{analysis.type.replace(/_/g, ' ')}</td>
              </tr>
              <tr>
                <td className="fw-bold">Status:</td>
                <td>
                  <Badge bg={getStatusBadgeVariant(analysis.status)}>
                    {analysis.status}
                  </Badge>
                </td>
              </tr>
              <tr>
                <td className="fw-bold">Started:</td>
                <td>{analysis.started_at ? formatDate(analysis.started_at) : 'Unknown'}</td>
              </tr>
              {analysis.completed_at && (
                <tr>
                  <td className="fw-bold">Completed:</td>
                  <td>{formatDate(analysis.completed_at)}</td>
                </tr>
              )}
              <tr>
                <td className="fw-bold">Duration:</td>
                <td>{formatDuration(analysis.started_at, analysis.completed_at)}</td>
              </tr>
            </tbody>
          </Table>
        </Col>
        
        <Col md={6}>
          <h6>Input Sequences</h6>
          {analysisSequences.length > 0 ? (
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {analysisSequences.map((seq, index) => (
                <div key={seq.id || index} className="border rounded p-2 mb-2">
                  <div className="fw-bold">{seq.name}</div>
                  <div className="small text-muted">
                    {seq.sequence_type} • {seq.length} bp
                    {seq.gc_content && ` • GC: ${seq.gc_content.toFixed(1)}%`}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-muted">No sequence information available</div>
          )}
        </Col>
      </Row>

      {analysis.error && (
        <Alert variant="danger">
          <strong>Error:</strong> {analysis.error}
        </Alert>
      )}

      {analysis.status === 'running' && (
        <Alert variant="info">
          <strong>Status:</strong> Analysis is currently running...
          {analysis.progress !== undefined && (
            <div className="progress mt-2">
              <div
                className="progress-bar"
                role="progressbar"
                style={{ width: `${analysis.progress}%` }}
              >
                {analysis.progress}%
              </div>
            </div>
          )}
        </Alert>
      )}

      {analysis.status === 'completed' && analysis.results && (
        <Alert variant="success">
          <strong>Analysis completed successfully!</strong>
          {analysis.results.summary && (
            <div className="mt-2">
              {typeof analysis.results.summary === 'object'
                ? Object.entries(analysis.results.summary).map(([key, value]) => (
                    <div key={key}>
                      <strong>{key.replace(/_/g, ' ')}:</strong> {value}
                    </div>
                  ))
                : analysis.results.summary}
            </div>
          )}
        </Alert>
      )}
    </div>
  );
};

// Analysis Results Component
const AnalysisResults = ({ analysis }) => {
  if (!analysis.results) {
    return <Alert variant="info">No results data available.</Alert>;
  }

  const renderBlastResults = (results) => {
    if (!results.results || results.results.length === 0) {
      return <Alert variant="warning">No BLAST hits found.</Alert>;
    }

    return (
      <div>
        {results.results.map((queryResult, qIndex) => (
          <div key={qIndex} className="mb-4">
            <h6>Query {qIndex + 1} Results</h6>
            {queryResult.hits && queryResult.hits.length > 0 ? (
              <Table striped hover size="sm">
                <thead>
                  <tr>
                    <th>Accession</th>
                    <th>Description</th>
                    <th>Score</th>
                    <th>E-value</th>
                    <th>Identity</th>
                    <th>Length</th>
                  </tr>
                </thead>
                <tbody>
                  {queryResult.hits.slice(0, 10).map((hit, hIndex) => (
                    <tr key={hIndex}>
                      <td>
                        <code>{hit.accession}</code>
                      </td>
                      <td className="small">{hit.description}</td>
                      <td>{hit.score?.toFixed(1)}</td>
                      <td>{hit.evalue?.toExponential(2)}</td>
                      <td>{(hit.identity * 100)?.toFixed(1)}%</td>
                      <td>{hit.length}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            ) : (
              <Alert variant="warning">No hits found for this query.</Alert>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderAlignmentResults = (results) => (
    <div>
      <Alert variant="info">
        <Row>
          <Col>
            <strong>Alignment Length:</strong> {results.alignment_statistics?.alignment_length || 'N/A'}
          </Col>
          <Col>
            <strong>Conservation:</strong> {results.alignment_statistics?.conservation_percentage?.toFixed(1) || 'N/A'}%
          </Col>
          <Col>
            <strong>Gaps:</strong> {results.alignment_statistics?.gap_percentage?.toFixed(1) || 'N/A'}%
          </Col>
        </Row>
      </Alert>
      
      {results.aligned_sequences && (
        <div className="alignment-display">
          <h6>Aligned Sequences</h6>
          <div className="bg-light p-3 rounded" style={{ fontFamily: 'monospace', fontSize: '12px', overflowX: 'auto' }}>
            {results.aligned_sequences.slice(0, 20).map((seq, index) => (
              <div key={index} className="mb-1">
                <strong>{seq.id || `Seq_${index + 1}`}</strong><br />
                {seq.sequence.slice(0, 100)}{seq.sequence.length > 100 ? '...' : ''}
              </div>
            ))}
            {results.aligned_sequences.length > 20 && (
              <div className="text-muted">... and {results.aligned_sequences.length - 20} more sequences</div>
            )}
          </div>
        </div>
      )}
    </div>
  );

  const renderPhylogenyResults = (results) => (
    <div>
      <Alert variant="info">
        <Row>
          <Col>
            <strong>Method:</strong> {results.method}
          </Col>
          <Col>
            <strong>Model:</strong> {results.parameters?.model || 'N/A'}
          </Col>
          <Col>
            <strong>Bootstrap:</strong> {results.parameters?.bootstrap || 'N/A'}
          </Col>
        </Row>
      </Alert>
      
      {results.newick_tree && (
        <div>
          <h6>Newick Tree Format</h6>
          <div className="bg-light p-3 rounded">
            <pre style={{ fontSize: '11px', whiteSpace: 'pre-wrap' }}>
              {results.newick_tree}
            </pre>
          </div>
        </div>
      )}
    </div>
  );

  const renderGenePredictionResults = (results) => (
    <div>
      <Alert variant="info">
        <Row>
          <Col>
            <strong>Genes Found:</strong> {results.statistics?.total_genes || 0}
          </Col>
          <Col>
            <strong>Proteins:</strong> {results.statistics?.total_proteins || 0}
          </Col>
          <Col>
            <strong>Avg Gene Length:</strong> {results.statistics?.average_gene_length?.toFixed(0) || 'N/A'} bp
          </Col>
        </Row>
      </Alert>
      
      {results.predicted_genes && results.predicted_genes.length > 0 && (
        <div>
          <h6>Predicted Genes</h6>
          <Table striped hover size="sm">
            <thead>
              <tr>
                <th>Gene ID</th>
                <th>Start</th>
                <th>End</th>
                <th>Strand</th>
                <th>Length</th>
                <th>Product</th>
              </tr>
            </thead>
            <tbody>
              {results.predicted_genes.slice(0, 20).map((gene, index) => (
                <tr key={index}>
                  <td>{gene.attributes?.ID || `gene_${index + 1}`}</td>
                  <td>{gene.start}</td>
                  <td>{gene.end}</td>
                  <td>{gene.strand}</td>
                  <td>{gene.end - gene.start + 1} bp</td>
                  <td className="small">{gene.attributes?.product || 'Hypothetical protein'}</td>
                </tr>
              ))}
            </tbody>
          </Table>
          {results.predicted_genes.length > 20 && (
            <div className="text-muted small">
              ... and {results.predicted_genes.length - 20} more genes
            </div>
          )}
        </div>
      )}
    </div>
  );

  // Render based on analysis type
  switch (analysis.type) {
    case 'blast':
    case 'blast_search':
      return renderBlastResults(analysis.results);
    case 'alignment':
    case 'multiple_alignment':
      return renderAlignmentResults(analysis.results);
    case 'phylogeny':
    case 'phylogenetic_analysis':
      return renderPhylogenyResults(analysis.results);
    case 'gene_prediction':
      return renderGenePredictionResults(analysis.results);
    default:
      return (
        <div>
          <h6>Raw Results</h6>
          <pre className="bg-light p-3 rounded" style={{ fontSize: '11px', maxHeight: '400px', overflow: 'auto' }}>
            {JSON.stringify(analysis.results, null, 2)}
          </pre>
        </div>
      );
  }
};

// Analysis Visualizations Component
const AnalysisVisualizations = ({ analysis }) => {
  if (!analysis.results) {
    return <Alert variant="info">No visualization data available.</Alert>;
  }

  const renderBlastVisualizations = (results) => {
    if (!results.results || results.results.length === 0) return null;

    // Prepare data for charts
    const hitCounts = results.results.map((queryResult, index) => ({
      query: `Query ${index + 1}`,
      hits: queryResult.hits?.length || 0
    }));

    const scoreDistribution = [];
    results.results.forEach((queryResult, qIndex) => {
      if (queryResult.hits) {
        queryResult.hits.forEach((hit, hIndex) => {
          scoreDistribution.push({
            name: `Q${qIndex + 1}H${hIndex + 1}`,
            score: hit.score,
            evalue: -Math.log10(hit.evalue),
            identity: hit.identity * 100
          });
        });
      }
    });

    return (
      <div>
        <Row>
          <Col md={6}>
            <Card className="mb-3">
              <Card.Header>
                <h6 className="mb-0">Hit Counts by Query</h6>
              </Card.Header>
              <Card.Body>
                <BarChart width={400} height={250} data={hitCounts}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="query" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="hits" fill="#007bff" />
                </BarChart>
              </Card.Body>
            </Card>
          </Col>
          
          <Col md={6}>
            <Card className="mb-3">
              <Card.Header>
                <h6 className="mb-0">Score vs E-value</h6>
              </Card.Header>
              <Card.Body>
                <div style={{ width: '100%', height: 250 }}>
                  <ResponsiveContainer>
                    <ScatterChart data={scoreDistribution.slice(0, 50)}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="score" name="Score" />
                      <YAxis dataKey="evalue" name="-log10(E-value)" />
                      <Tooltip />
                      <Scatter dataKey="identity" fill="#28a745" />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </div>
    );
  };

  const renderAlignmentVisualizations = (results) => {
    if (!results.alignment_statistics) return null;

    const stats = results.alignment_statistics;
    const pieData = [
      { name: 'Conserved', value: stats.conserved_positions || 0, fill: '#28a745' },
      { name: 'Variable', value: (stats.alignment_length || 0) - (stats.conserved_positions || 0), fill: '#ffc107' },
      { name: 'Gaps', value: Math.round((stats.gap_percentage || 0) * (stats.alignment_length || 0) / 100), fill: '#dc3545' }
    ];

    return (
      <div>
        <Row>
          <Col md={6}>
            <Card>
              <Card.Header>
                <h6 className="mb-0">Alignment Composition</h6>
              </Card.Header>
              <Card.Body>
                <PieChart width={400} height={250}>
                  <Pie
                    data={pieData}
                    cx={200}
                    cy={125}
                    outerRadius={80}
                    dataKey="value"
                    label
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </Card.Body>
            </Card>
          </Col>
          
          <Col md={6}>
            <Card>
              <Card.Header>
                <h6 className="mb-0">Alignment Statistics</h6>
              </Card.Header>
              <Card.Body>
                <Table size="sm">
                  <tbody>
                    <tr>
                      <td>Alignment Length:</td>
                      <td>{stats.alignment_length}</td>
                    </tr>
                    <tr>
                      <td>Sequences:</td>
                      <td>{stats.num_sequences}</td>
                    </tr>
                    <tr>
                      <td>Conservation:</td>
                      <td>{stats.conservation_percentage?.toFixed(2)}%</td>
                    </tr>
                    <tr>
                      <td>Gap Content:</td>
                      <td>{stats.gap_percentage?.toFixed(2)}%</td>
                    </tr>
                    <tr>
                      <td>Average Identity:</td>
                      <td>{stats.average_identity?.toFixed(2)}%</td>
                    </tr>
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </div>
    );
  };

  const renderGenePredictionVisualizations = (results) => {
    if (!results.predicted_genes) return null;

    const genes = results.predicted_genes;
    const strandData = [
      { name: 'Forward (+)', value: genes.filter(g => g.strand === '+').length, fill: '#007bff' },
      { name: 'Reverse (-)', value: genes.filter(g => g.strand === '-').length, fill: '#dc3545' }
    ];

    const lengthDistribution = genes.map((gene, index) => ({
      gene: `Gene ${index + 1}`,
      length: gene.end - gene.start + 1
    })).slice(0, 50);

    return (
      <div>
        <Row>
          <Col md={6}>
            <Card className="mb-3">
              <Card.Header>
                <h6 className="mb-0">Gene Strand Distribution</h6>
              </Card.Header>
              <Card.Body>
                <PieChart width={400} height={250}>
                  <Pie
                    data={strandData}
                    cx={200}
                    cy={125}
                    outerRadius={80}
                    dataKey="value"
                    label
                  >
                    {strandData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </Card.Body>
            </Card>
          </Col>
          
          <Col md={6}>
            <Card className="mb-3">
              <Card.Header>
                <h6 className="mb-0">Gene Length Distribution</h6>
              </Card.Header>
              <Card.Body>
                <BarChart width={400} height={250} data={lengthDistribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="gene" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="length" fill="#28a745" />
                </BarChart>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </div>
    );
  };

  // Render based on analysis type
  switch (analysis.type) {
    case 'blast':
    case 'blast_search':
      return renderBlastVisualizations(analysis.results);
    case 'alignment':
    case 'multiple_alignment':
      return renderAlignmentVisualizations(analysis.results);
    case 'gene_prediction':
      return renderGenePredictionVisualizations(analysis.results);
    default:
      return (
        <Alert variant="info">
          No visualizations available for this analysis type.
        </Alert>
      );
  }
};

// Analysis Parameters Component
const AnalysisParameters = ({ analysis }) => {
  if (!analysis.parameters || Object.keys(analysis.parameters).length === 0) {
    return <Alert variant="info">No parameters available.</Alert>;
  }

  return (
    <div>
      <h6>Analysis Parameters</h6>
      <Table size="sm">
        <tbody>
          {Object.entries(analysis.parameters).map(([key, value]) => (
            <tr key={key}>
              <td className="fw-bold text-capitalize">
                {key.replace(/_/g, ' ')}:
              </td>
              <td>
                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
};

// Export Modal Component
const ExportModal = ({ show, onHide, analysis }) => {
  const [exportFormat, setExportFormat] = useState('json');
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    if (!analysis) return;

    setIsExporting(true);
    try {
      // This would call the export API
      const response = await enhancedApiService.exportResults(analysis.id, exportFormat);
      
      // Create and download file
      let content = '';
      let mimeType = '';
      let fileName = `analysis_${analysis.id}`;

      switch (exportFormat) {
        case 'json':
          content = JSON.stringify(analysis.results, null, 2);
          mimeType = 'application/json';
          fileName += '.json';
          break;
        case 'csv':
          content = convertToCSV(analysis.results);
          mimeType = 'text/csv';
          fileName += '.csv';
          break;
        case 'txt':
          content = convertToText(analysis.results);
          mimeType = 'text/plain';
          fileName += '.txt';
          break;
      }

      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      onHide();
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

  const convertToCSV = (results) => {
    // Simple CSV conversion - would need more sophisticated logic for different result types
    if (results.results && Array.isArray(results.results)) {
      const headers = ['Query', 'Hit ID', 'Description', 'Score', 'E-value', 'Identity'];
      const rows = [headers.join(',')];
      
      results.results.forEach((queryResult, qIndex) => {
        if (queryResult.hits) {
          queryResult.hits.forEach(hit => {
            rows.push([
              `Query ${qIndex + 1}`,
              hit.accession || '',
              `"${hit.description || ''}"`,
              hit.score || '',
              hit.evalue || '',
              hit.identity || ''
            ].join(','));
          });
        }
      });
      
      return rows.join('\n');
    }
    return JSON.stringify(results);
  };

  const convertToText = (results) => {
    // Simple text conversion
    return JSON.stringify(results, null, 2);
  };

  return (
    <Modal show={show} onHide={onHide}>
      <Modal.Header closeButton>
        <Modal.Title>Export Analysis Results</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form.Group className="mb-3">
          <Form.Label>Export Format</Form.Label>
          <Form.Select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value)}
          >
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
            <option value="txt">Text</option>
          </Form.Select>
        </Form.Group>
        
        <Alert variant="info">
          <small>
            The results will be downloaded as a {exportFormat.toUpperCase()} file containing 
            all analysis data and parameters.
          </small>
        </Alert>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Cancel
        </Button>
        <Button 
          variant="primary" 
          onClick={handleExport}
          disabled={isExporting}
        >
          {isExporting ? 'Exporting...' : 'Export'}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

// Helper function for status badge variant
const getStatusBadgeVariant = (status) => {
  switch (status) {
    case 'completed': return 'success';
    case 'running': return 'primary';
    case 'failed': return 'danger';
    case 'pending': return 'warning';
    default: return 'secondary';
  }
};

// Helper function for duration formatting
const formatDuration = (startTime, endTime) => {
  if (!startTime) return 'Unknown';
  const start = new Date(startTime);
  const end = endTime ? new Date(endTime) : new Date();
  const duration = Math.round((end - start) / 1000);
  
  if (duration < 60) return `${duration}s`;
  if (duration < 3600) return `${Math.round(duration / 60)}m`;
  return `${Math.round(duration / 3600)}h`;
};

export default ResultsViewer;