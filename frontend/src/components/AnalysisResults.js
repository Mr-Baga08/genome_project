// frontend/src/components/AnalysisResults.js
import React, { useState, useEffect } from 'react';
import { Card, Table, Badge, Button, Modal, Alert, Tabs, Tab } from 'react-bootstrap';
import { BsEye, BsDownload, BsGraphUp } from 'react-icons/bs';
import Plot from 'react-plotly.js';

const AnalysisResults = ({ taskId }) => {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedResult, setSelectedResult] = useState(null);

  useEffect(() => {
    if (taskId) {
      fetchResults();
    }
  }, [taskId]);

  const fetchResults = async () => {
    try {
      setLoading(true);
      const response = await apiService.get(`/api/v1/tasks/${taskId}/results`);
      setResults(response.data);
    } catch (error) {
      console.error('Failed to fetch results:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderBlastResults = (blastData) => {
    return (
      <div>
        <h6>BLAST Search Results</h6>
        <Table striped bordered hover responsive>
          <thead>
            <tr>
              <th>Query</th>
              <th>Hit ID</th>
              <th>Description</th>
              <th>Score</th>
              <th>E-value</th>
              <th>Identity</th>
            </tr>
          </thead>
          <tbody>
            {blastData.results?.map((result, i) =>
              result.hits?.map((hit, j) => (
                <tr key={`${i}-${j}`}>
                  <td>{result.query_id}</td>
                  <td>{hit.accession}</td>
                  <td>{hit.description}</td>
                  <td>{hit.score?.toFixed(1)}</td>
                  <td>{hit.evalue?.toExponential(2)}</td>
                  <td>{(hit.identity * 100)?.toFixed(1)}%</td>
                </tr>
              ))
            )}
          </tbody>
        </Table>
      </div>
    );
  };

  const renderAlignmentResults = (alignmentData) => {
    const conservationData = alignmentData.alignment_stats?.conservation_scores || [];
    
    return (
      <div>
        <h6>Multiple Sequence Alignment Results</h6>
        
        <div className="mb-3">
          <Badge variant="info" className="me-2">
            Sequences: {alignmentData.aligned_sequences?.length || 0}
          </Badge>
          <Badge variant="secondary" className="me-2">
            Length: {alignmentData.alignment_stats?.alignment_length || 0}
          </Badge>
          <Badge variant="success">
            Avg Conservation: {(alignmentData.alignment_stats?.average_conservation * 100)?.toFixed(1)}%
          </Badge>
        </div>

        {/* Conservation plot */}
        {conservationData.length > 0 && (
          <div className="mb-4">
            <Plot
              data={[{
                x: conservationData.map((_, i) => i + 1),
                y: conservationData,
                type: 'scatter',
                mode: 'lines',
                name: 'Conservation',
                line: { color: '#007bff' }
              }]}
              layout={{
                title: 'Conservation Score by Position',
                xaxis: { title: 'Position' },
                yaxis: { title: 'Conservation Score', range: [0, 1] },
                height: 300
              }}
              config={{ responsive: true }}
            />
          </div>
        )}

        {/* Aligned sequences preview */}
        <div className="sequence-alignment-preview">
          {alignmentData.aligned_sequences?.slice(0, 5).map((seq, index) => (
            <div key={index} className="mb-2">
              <code style={{ fontSize: '0.8em' }}>
                <strong>{seq.id}:</strong> {seq.sequence.substring(0, 80)}
                {seq.sequence.length > 80 && '...'}
              </code>
            </div>
          ))}
          {alignmentData.aligned_sequences?.length > 5 && (
            <Badge variant="light">
              ...and {alignmentData.aligned_sequences.length - 5} more sequences
            </Badge>
          )}
        </div>
      </div>
    );
  };

  const renderStatisticsResults = (statsData) => {
    const chartData = [
      {
        x: ['Total Length', 'Average Length', 'Min Length', 'Max Length'],
        y: [
          statsData.total_length || 0,
          statsData.average_length || 0,
          statsData.min_length || 0,
          statsData.max_length || 0
        ],
        type: 'bar',
        marker: { color: '#007bff' }
      }
    ];

    return (
      <div>
        <h6>Sequence Statistics</h6>
        
        <div className="mb-4">
          <div className="row">
            <div className="col-md-3">
              <Card className="text-center">
                <Card.Body>
                  <h5>{statsData.sequence_count || 0}</h5>
                  <small className="text-muted">Sequences</small>
                </Card.Body>
              </Card>
            </div>
            <div className="col-md-3">
              <Card className="text-center">
                <Card.Body>
                  <h5>{statsData.total_length?.toLocaleString() || 0}</h5>
                  <small className="text-muted">Total Length</small>
                </Card.Body>
              </Card>
            </div>
            <div className="col-md-3">
              <Card className="text-center">
                <Card.Body>
                  <h5>{statsData.average_length?.toFixed(0) || 0}</h5>
                  <small className="text-muted">Avg Length</small>
                </Card.Body>
              </Card>
            </div>
            <div className="col-md-3">
              <Card className="text-center">
                <Card.Body>
                  <h5>{statsData.max_length?.toLocaleString() || 0}</h5>
                  <small className="text-muted">Max Length</small>
                </Card.Body>
              </Card>
            </div>
          </div>
        </div>

        <Plot
          data={chartData}
          layout={{
            title: 'Length Statistics',
            xaxis: { title: 'Metric' },
            yaxis: { title: 'Base Pairs' },
            height: 300
          }}
          config={{ responsive: true }}
        />
      </div>
    );
  };

  const renderResultsByType = (resultData, type) => {
    switch (type) {
      case 'blast_search':
        return renderBlastResults(resultData);
      case 'multiple_alignment':
        return renderAlignmentResults(resultData);
      case 'statistics':
        return renderStatisticsResults(resultData);
      default:
        return (
          <div>
            <h6>Raw Results</h6>
            <pre style={{ maxHeight: '300px', overflow: 'auto' }}>
              {JSON.stringify(resultData, null, 2)}
            </pre>
          </div>
        );
    }
  };

  const downloadResults = (resultData, filename) => {
    const dataStr = JSON.stringify(resultData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <Card>
        <Card.Body className="text-center">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2">Loading results...</p>
        </Card.Body>
      </Card>
    );
  }

  if (!results) {
    return (
      <Alert variant="info">
        No results available yet. Results will appear here once the workflow completes.
      </Alert>
    );
  }

  return (
    <div className="analysis-results">
      <Card>
        <Card.Header>
          <div className="d-flex justify-content-between align-items-center">
            <h5 className="mb-0">Analysis Results</h5>
            <Badge variant="success">
              {results.length} step{results.length !== 1 ? 's' : ''} completed
            </Badge>
          </div>
        </Card.Header>
        
        <Card.Body>
          <Tabs defaultActiveKey="0">
            {results.map((result, index) => (
              <Tab 
                eventKey={index.toString()} 
                title={`Step ${result.step}: ${result.type}`}
                key={index}
              >
                <div className="mt-3">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <div>
                      <Badge variant="primary" className="me-2">
                        {result.type}
                      </Badge>
                      <small className="text-muted">
                        Completed: {new Date(result.timestamp).toLocaleString()}
                      </small>
                    </div>
                    <div className="d-flex gap-2">
                      <Button 
                        variant="outline-primary" 
                        size="sm"
                        onClick={() => {
                          setSelectedResult(result);
                          setShowDetailModal(true);
                        }}
                      >
                        <BsEye /> View Details
                      </Button>
                      <Button 
                        variant="outline-secondary" 
                        size="sm"
                        onClick={() => downloadResults(result.result, `${result.type}_step_${result.step}.json`)}
                      >
                        <BsDownload /> Download
                      </Button>
                    </div>
                  </div>
                  
                  {renderResultsByType(result.result, result.type)}
                </div>
              </Tab>
            ))}
          </Tabs>
        </Card.Body>
      </Card>

      {/* Detail Modal */}
      <Modal 
        show={showDetailModal} 
        onHide={() => setShowDetailModal(false)}
        size="lg"
      >
        <Modal.Header closeButton>
          <Modal.Title>
            {selectedResult?.type} - Step {selectedResult?.step}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedResult && renderResultsByType(selectedResult.result, selectedResult.type)}
        </Modal.Body>
        <Modal.Footer>
          <Button 
            variant="primary"
            onClick={() => downloadResults(selectedResult?.result, `${selectedResult?.type}_detailed.json`)}
          >
            <BsDownload /> Download Full Results
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default AnalysisResults;