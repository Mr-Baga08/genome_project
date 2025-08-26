// frontend/src/components/BioinformaticsWorkspace.js
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Container, Row, Col, Card, Nav, Tab, Alert, Spinner, Modal, Button, Form } from 'react-bootstrap';
import { BsUpload, BsPlay, BsPause, BsStop, BsDownload, BsGear, BsEye, BsSearch } from 'react-icons/bs';

// Import our enhanced components
import AdvancedSequenceViewer from './AdvancedSequenceViewer';
// import SequenceManager from './SequenceManager';
import AnalysisRunner from './AnalysisRunner';
import PipelineDesigner from './PipelineDesigner';
import ResultsViewer from './ResultsViewer';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAppContext } from '../context/AppContext';
import apiService from '../services/apiService';

const BioinformaticsWorkspace = () => {
  const { state, actions } = useAppContext();
  const [activeTab, setActiveTab] = useState('sequences');
  const [sequences, setSequences] = useState([]);
  const [selectedSequences, setSelectedSequences] = useState([]);
  const [currentSequence, setCurrentSequence] = useState(null);
  const [analyses, setAnalyses] = useState([]);
  const [pipelines, setPipelines] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // WebSocket connection for real-time updates
  const { 
    isConnected, 
    lastMessage, 
    sendMessage, 
    joinRoom, 
    leaveRoom 
  } = useWebSocket('ws://localhost:8000/ws');

  // File upload ref
  const fileInputRef = useRef(null);

  // Initialize workspace
  useEffect(() => {
    initializeWorkspace();
    
    // Join analysis updates room
    if (isConnected) {
      joinRoom('analysis_updates');
      joinRoom('pipeline_updates');
    }

    return () => {
      if (isConnected) {
        leaveRoom('analysis_updates');
        leaveRoom('pipeline_updates');
      }
    };
  }, [isConnected]);

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      handleWebSocketMessage(lastMessage);
    }
  }, [lastMessage]);

  const initializeWorkspace = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Load sequences with proper error handling
      try {
        const sequencesResponse = await apiService.get('/api/v1/sequences');
        setSequences(sequencesResponse || []);
      } catch (seqError) {
        console.error('Failed to load sequences:', seqError);
        setSequences([]);
      }
      
      // Load pipelines with proper error handling
      try {
        const pipelinesResponse = await apiService.get('/api/v1/pipelines');
        setPipelines(pipelinesResponse || []);
      } catch (pipeError) {
        console.error('Failed to load pipelines:', pipeError);
        setPipelines([]);
      }
      
      // Load recent analyses with proper error handling
      try {
        const analysesResponse = await apiService.get('/api/v1/analysis/recent');
        setAnalyses(analysesResponse || []);
      } catch (analysisError) {
        console.error('Failed to load analyses:', analysisError);
        setAnalyses([]);
      }
      
    } catch (err) {
      console.error('Workspace initialization error:', err);
      setError(`Failed to initialize workspace: ${err.message || 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWebSocketMessage = (message) => {
    const data = JSON.parse(message.data);
    
    switch (data.type) {
      case 'analysis_progress':
        updateAnalysisProgress(data.analysis_id, data.progress, data.status);
        break;
      case 'analysis_completed':
        handleAnalysisCompleted(data.analysis_id, data.results);
        break;
      case 'analysis_failed':
        handleAnalysisFailed(data.analysis_id, data.error);
        break;
      case 'pipeline_progress':
        updatePipelineProgress(data.execution_id, data.progress, data.current_step);
        break;
      default:
        console.log('Unhandled message type:', data.type);
    }
  };

  const updateAnalysisProgress = (analysisId, progress, status) => {
    setAnalyses(prev => prev.map(analysis => 
      analysis.id === analysisId 
        ? { ...analysis, progress, status }
        : analysis
    ));
    
    actions.addNotification({
      type: 'info',
      title: 'Analysis Progress',
      message: `Analysis ${analysisId} is ${progress}% complete`
    });
  };

  const updatePipelineProgress = (executionId, progress, currentStep) => {
    // Find the pipeline run in the analyses list and update its progress
    setAnalyses(prev => prev.map(item => 
      item.id === executionId 
        ? { ...item, progress, status: `Running: ${currentStep}` } 
        : item
    ));
    
    // Optionally, send a notification
    actions.addNotification({
      type: 'info',
      title: 'Pipeline Progress',
      message: `Pipeline ${executionId} is at step: ${currentStep}`
    });
  };

  const handleAnalysisCompleted = (analysisId, results) => {
    setAnalyses(prev => prev.map(analysis => 
      analysis.id === analysisId 
        ? { ...analysis, status: 'completed', results, progress: 100 }
        : analysis
    ));
    
    actions.addNotification({
      type: 'success',
      title: 'Analysis Complete',
      message: `Analysis ${analysisId} completed successfully`
    });
  };

  const handleAnalysisFailed = (analysisId, error) => {
    setAnalyses(prev => prev.map(analysis => 
      analysis.id === analysisId 
        ? { ...analysis, status: 'failed', error }
        : analysis
    ));
    
    actions.addNotification({
      type: 'error',
      title: 'Analysis Failed',
      message: `Analysis ${analysisId} failed: ${error}`
    });
  };

  // File upload handling
  const handleFileUpload = async (files) => {
    setIsLoading(true);
    try {
      for (const file of files) {
        // Use the correct method for FASTA uploads
        const response = await apiService.uploadFasta(file);
        
        if (response.sequences) {
          // Create sequences in database
          for (const seqData of response.sequences) {
            const createResponse = await apiService.post('/api/v1/sequences/create', seqData);
            if (createResponse) {
              setSequences(prev => [...prev, createResponse]);
            }
          }
        }
      }
      
      actions.addNotification({
        type: 'success',
        title: 'Upload Complete',
        message: `Successfully uploaded ${files.length} file(s)`
      });
      
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
    } finally {
      setIsLoading(false);
      setShowUploadModal(false);
    }
  };

  // Sequence selection handling
  const handleSequenceSelect = (sequenceIds) => {
    setSelectedSequences(sequenceIds);
    if (sequenceIds.length === 1) {
      const selected = sequences.find(seq => seq.id === sequenceIds[0]);
      setCurrentSequence(selected);
    }
  };

  // Analysis execution
  const runAnalysis = async (analysisType, parameters) => {
    if (selectedSequences.length === 0) {
      actions.addNotification({
        type: 'warning',
        title: 'No Sequences Selected',
        message: 'Please select sequences before running analysis'
      });
      return;
    }

    try {
      setIsLoading(true);
      let response;

      switch (analysisType) {
        case 'blast':
          response = await apiService.post('/api/v1/analysis/blast-search', {
            sequences: selectedSequences.map(id => sequences.find(s => s.id === id)?.sequence),
            database: parameters.database || 'nr',
            evalue: parameters.evalue || 1e-5,
            max_hits: parameters.max_hits || 10
          });
          break;

        case 'alignment':
          const seqsForAlignment = selectedSequences.map(id => sequences.find(s => s.id === id));
          response = await apiService.post('/api/v1/analysis/multiple-alignment', {
            sequences: seqsForAlignment,
            method: parameters.method || 'muscle'
          });
          break;

        case 'phylogeny':
          if (!parameters.alignment_data) {
            throw new Error('Alignment data required for phylogenetic analysis');
          }
          response = await apiService.post('/api/v1/analysis/phylogeny', {
            alignment_data: parameters.alignment_data,
            method: parameters.method || 'iqtree',
            model: parameters.model || 'AUTO'
          });
          break;

        case 'gene_prediction':
          if (selectedSequences.length !== 1) {
            throw new Error('Gene prediction requires exactly one sequence');
          }
          const seq = sequences.find(s => s.id === selectedSequences[0]);
          response = await apiService.post('/api/v1/analysis/gene-prediction', {
            sequence: seq.sequence,
            organism_type: parameters.organism_type || 'bacteria'
          });
          break;

        default:
          throw new Error(`Unsupported analysis type: ${analysisType}`);
      }

      // Add to analyses list
      const newAnalysis = {
        id: response.analysis_id || `analysis_${Date.now()}`,
        type: analysisType,
        status: 'running',
        progress: 0,
        sequences: selectedSequences,
        parameters,
        started_at: new Date().toISOString()
      };

      setAnalyses(prev => [newAnalysis, ...prev]);

    } catch (err) {
      setError(`Analysis failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const runPipeline = async (pipelineId, sequenceIds) => {
    try {
      setIsLoading(true);
      const response = await apiService.post(`/api/v1/pipelines/${pipelineId}/execute`, {
        sequence_ids: sequenceIds
      });

      const { execution_id, pipeline: pipelineName } = response;
      
      // Add a placeholder to the local state for the new pipeline run
      const newPipelineRun = {
        id: execution_id,
        type: `Pipeline: ${pipelineName}`,
        status: 'started',
        progress: 0,
        sequences: sequenceIds,
        started_at: new Date().toISOString()
      };
      setAnalyses(prev => [newPipelineRun, ...prev]);

      actions.addNotification({
        type: 'info',
        title: 'Pipeline Started',
        message: `Pipeline execution started with ID: ${execution_id}`
      });

    } catch (err) {
      setError(`Pipeline execution failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <Container className="d-flex justify-content-center align-items-center" style={{ height: '50vh' }}>
        <Spinner animation="border" variant="primary" />
        <span className="ms-2">Loading workspace...</span>
      </Container>
    );
  }

  return (
    <Container fluid className="bioinformatics-workspace">
      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Connection Status */}
      <Alert variant={isConnected ? 'success' : 'warning'} className="mb-3">
        <div className="d-flex justify-content-between align-items-center">
          <span>
            {isConnected ? '🟢 Connected to real-time updates' : '🟡 Connecting...'}
          </span>
          <div>
            <small>
              Sequences: {sequences.length} | 
              Active Analyses: {analyses.filter(a => a.status === 'running').length} |
              Selected: {selectedSequences.length}
            </small>
          </div>
        </div>
      </Alert>

      {/* Main Navigation */}
      <Tab.Container activeKey={activeTab} onSelect={setActiveTab}>
        <Nav variant="tabs" className="mb-3">
          <Nav.Item>
            <Nav.Link eventKey="sequences">Sequence Management</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="viewer">Sequence Viewer</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="analysis">Analysis Tools</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="pipelines">Pipeline Designer</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="results">Results & Visualizations</Nav.Link>
          </Nav.Item>
        </Nav>

        <Tab.Content>
          {/* Sequence Management Tab */}
          <Tab.Pane eventKey="sequences">
            <SequenceManager
              sequences={sequences}
              selectedSequences={selectedSequences}
              onSequenceSelect={handleSequenceSelect}
              onSequencesUpdated={setSequences}
              onUploadClick={() => setShowUploadModal(true)}
            />
          </Tab.Pane>

          {/* Sequence Viewer Tab */}
          <Tab.Pane eventKey="viewer">
            {currentSequence ? (
              <AdvancedSequenceViewer
                sequence={currentSequence}
                annotations={currentSequence.annotations || []}
                onRegionSelect={(region) => console.log('Region selected:', region)}
                height={600}
                width={1200}
              />
            ) : (
              <Card>
                <Card.Body className="text-center">
                  <h5>No Sequence Selected</h5>
                  <p>Please select a sequence from the Sequence Management tab to view it here.</p>
                  <Button 
                    variant="primary" 
                    onClick={() => setActiveTab('sequences')}
                  >
                    Go to Sequence Management
                  </Button>
                </Card.Body>
              </Card>
            )}
          </Tab.Pane>

          {/* Analysis Tools Tab */}
          <Tab.Pane eventKey="analysis">
            <AnalysisRunner
              selectedSequences={selectedSequences}
              sequences={sequences}
              analyses={analyses}
              onRunAnalysis={runAnalysis}
              isConnected={isConnected}
            />
          </Tab.Pane>

          {/* Pipeline Designer Tab */}
          <Tab.Pane eventKey="pipelines">
            <PipelineDesigner
              pipelines={pipelines}
              selectedSequences={selectedSequences}
              onRunPipeline={runPipeline}
              onPipelinesUpdated={setPipelines}
            />
          </Tab.Pane>

          {/* Results Tab */}
          <Tab.Pane eventKey="results">
            <ResultsViewer
              analyses={analyses}
              sequences={sequences}
              onAnalysisSelect={(analysis) => console.log('Analysis selected:', analysis)}
            />
          </Tab.Pane>
        </Tab.Content>
      </Tab.Container>

      {/* Upload Modal */}
      <Modal show={showUploadModal} onHide={() => setShowUploadModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Upload Sequence Files</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <FileUploadComponent onFilesSelected={handleFileUpload} />
        </Modal.Body>
      </Modal>
    </Container>
  );
};

// Sequence Manager Component
const SequenceManager = ({ 
  sequences, 
  selectedSequences, 
  onSequenceSelect, 
  onSequencesUpdated,
  onUploadClick 
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');

  const filteredSequences = sequences.filter(seq => {
    const matchesSearch = seq.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         seq.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'all' || seq.sequence_type === filterType;
    return matchesSearch && matchesType;
  });

  const handleSequenceClick = (sequenceId, isSelected) => {
    let newSelection;
    if (isSelected) {
      newSelection = selectedSequences.filter(id => id !== sequenceId);
    } else {
      newSelection = [...selectedSequences, sequenceId];
    }
    onSequenceSelect(newSelection);
  };

  return (
    <Card>
      <Card.Header>
        <Row className="align-items-center">
          <Col>
            <h5 className="mb-0">Sequence Library</h5>
          </Col>
          <Col xs="auto">
            <Button variant="primary" onClick={onUploadClick}>
              <BsUpload className="me-1" />
              Upload Sequences
            </Button>
          </Col>
        </Row>
      </Card.Header>
      <Card.Body>
        {/* Search and Filter Controls */}
        <Row className="mb-3">
          <Col md={8}>
            <Form.Control
              type="text"
              placeholder="Search sequences..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </Col>
          <Col md={4}>
            <Form.Select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="all">All Types</option>
              <option value="DNA">DNA</option>
              <option value="RNA">RNA</option>
              <option value="PROTEIN">Protein</option>
            </Form.Select>
          </Col>
        </Row>

        {/* Sequence List */}
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          {filteredSequences.map((sequence) => (
            <Card 
              key={sequence.id} 
              className={`mb-2 ${selectedSequences.includes(sequence.id) ? 'border-primary' : ''}`}
              style={{ cursor: 'pointer' }}
              onClick={() => handleSequenceClick(sequence.id, selectedSequences.includes(sequence.id))}
            >
              <Card.Body className="py-2">
                <Row className="align-items-center">
                  <Col>
                    <div className="d-flex align-items-center">
                      <Form.Check
                        type="checkbox"
                        checked={selectedSequences.includes(sequence.id)}
                        readOnly
                        className="me-2"
                      />
                      <div>
                        <strong>{sequence.name}</strong>
                        <br />
                        <small className="text-muted">
                          {sequence.sequence_type} | {sequence.length} bp
                          {sequence.gc_content && ` | GC: ${sequence.gc_content.toFixed(1)}%`}
                        </small>
                      </div>
                    </div>
                  </Col>
                  <Col xs="auto">
                    <Button
                      variant="outline-secondary"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        // View sequence details
                      }}
                    >
                      <BsEye />
                    </Button>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          ))}
        </div>

        {filteredSequences.length === 0 && (
          <div className="text-center py-4 text-muted">
            No sequences found matching your criteria.
          </div>
        )}
      </Card.Body>
      <Card.Footer>
        <small className="text-muted">
          Showing {filteredSequences.length} of {sequences.length} sequences
          {selectedSequences.length > 0 && ` | ${selectedSequences.length} selected`}
        </small>
      </Card.Footer>
    </Card>
  );
};

// File Upload Component
const FileUploadComponent = ({ onFilesSelected }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = Array.from(e.dataTransfer.files);
    setSelectedFiles(files);
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    setSelectedFiles(files);
  };

  const handleUpload = () => {
    if (selectedFiles.length > 0) {
      onFilesSelected(selectedFiles);
    }
  };

  return (
    <div>
      {/* Drag and Drop Area */}
      <div
        className={`border-2 border-dashed rounded p-4 text-center ${
          dragActive ? 'border-primary bg-light' : 'border-secondary'
        }`}
        style={{ minHeight: '200px' }}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <BsUpload size={48} className="text-muted mb-3" />
        <h5>Drop files here or click to browse</h5>
        <p className="text-muted">
          Supported formats: FASTA, FASTQ, GenBank, EMBL
        </p>
        
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".fasta,.fa,.fas,.fastq,.fq,.gb,.gbk,.embl"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      </div>

      {/* Selected Files */}
      {selectedFiles.length > 0 && (
        <div className="mt-3">
          <h6>Selected Files:</h6>
          <ul className="list-group">
            {selectedFiles.map((file, index) => (
              <li key={index} className="list-group-item d-flex justify-content-between">
                <span>{file.name}</span>
                <small className="text-muted">
                  {(file.size / 1024).toFixed(1)} KB
                </small>
              </li>
            ))}
          </ul>
          
          <div className="mt-3">
            <Button variant="primary" onClick={handleUpload}>
              Upload {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''}
            </Button>
            <Button 
              variant="secondary" 
              className="ms-2"
              onClick={() => setSelectedFiles([])}
            >
              Clear
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default BioinformaticsWorkspace;