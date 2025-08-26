// frontend/src/components/PipelineDesigner.js
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Card, Button, Row, Col, Modal, Form, Alert, Badge, Dropdown, OverlayTrigger, Tooltip } from 'react-bootstrap';
import { BsPlus, BsPlay, BsSave, BsDownload, BsUpload, BsTrash, BsGear, BsArrowRight, BsArrowDown } from 'react-icons/bs';
import enhancedApiService from '../services/enhancedApiService';

const PipelineDesigner = ({ pipelines, selectedSequences, onRunPipeline, onPipelinesUpdated }) => {
  const [currentPipeline, setCurrentPipeline] = useState({
    name: 'New Pipeline',
    description: '',
    steps: [],
    connections: []
  });
  const [showStepModal, setShowStepModal] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [selectedStep, setSelectedStep] = useState(null);
  const [draggedStep, setDraggedStep] = useState(null);
  const [executionHistory, setExecutionHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const canvasRef = useRef(null);

  // Available pipeline steps
  const availableSteps = {
    'data_input': {
      name: 'Data Input',
      category: 'Input/Output',
      description: 'Input sequences or files',
      icon: '📥',
      inputs: [],
      outputs: ['sequences'],
      parameters: {
        source_type: { type: 'select', options: ['sequences', 'file_upload', 'database'], default: 'sequences' }
      }
    },
    'blast_search': {
      name: 'BLAST Search',
      category: 'Sequence Analysis',
      description: 'Perform BLAST sequence similarity search',
      icon: '🔍',
      inputs: ['sequences'],
      outputs: ['blast_results'],
      parameters: {
        database: { type: 'select', options: ['nr', 'nt', 'swissprot'], default: 'nr' },
        evalue: { type: 'number', default: 1e-5, min: 1e-20, max: 1 },
        max_hits: { type: 'number', default: 10, min: 1, max: 1000 }
      }
    },
    'multiple_alignment': {
      name: 'Multiple Alignment',
      category: 'Sequence Analysis',
      description: 'Align multiple sequences',
      icon: '📊',
      inputs: ['sequences'],
      outputs: ['alignment'],
      parameters: {
        method: { type: 'select', options: ['muscle', 'clustalw', 'mafft'], default: 'muscle' },
        gap_penalty: { type: 'number', default: -10, min: -100, max: 0 }
      }
    },
    'phylogenetic_tree': {
      name: 'Phylogenetic Tree',
      category: 'Phylogenetics',
      description: 'Build phylogenetic tree',
      icon: '🌳',
      inputs: ['alignment'],
      outputs: ['tree'],
      parameters: {
        method: { type: 'select', options: ['iqtree', 'raxml', 'fasttree'], default: 'iqtree' },
        model: { type: 'select', options: ['AUTO', 'JTT', 'WAG'], default: 'AUTO' },
        bootstrap: { type: 'number', default: 1000, min: 100, max: 10000 }
      }
    },
    'gene_prediction': {
      name: 'Gene Prediction',
      category: 'Annotation',
      description: 'Predict genes in sequences',
      icon: '🧬',
      inputs: ['sequences'],
      outputs: ['genes'],
      parameters: {
        organism_type: { type: 'select', options: ['bacteria', 'archaea', 'virus'], default: 'bacteria' },
        mode: { type: 'select', options: ['single', 'meta'], default: 'single' }
      }
    },
    'domain_search': {
      name: 'Domain Search',
      category: 'Protein Analysis',
      description: 'Search for protein domains',
      icon: '🔷',
      inputs: ['sequences'],
      outputs: ['domains'],
      parameters: {
        database: { type: 'select', options: ['pfam', 'smart', 'cdd'], default: 'pfam' },
        evalue: { type: 'number', default: 1e-3, min: 1e-20, max: 1 }
      }
    },
    'data_filter': {
      name: 'Data Filter',
      category: 'Data Processing',
      description: 'Filter data based on criteria',
      icon: '🔽',
      inputs: ['sequences', 'blast_results', 'domains'],
      outputs: ['filtered_data'],
      parameters: {
        filter_type: { type: 'select', options: ['length', 'quality', 'score'], default: 'length' },
        min_value: { type: 'number', default: 100, min: 0 },
        max_value: { type: 'number', default: 10000, min: 0 }
      }
    },
    'data_export': {
      name: 'Data Export',
      category: 'Input/Output',
      description: 'Export results to file',
      icon: '📤',
      inputs: ['sequences', 'alignment', 'tree', 'blast_results', 'genes', 'domains'],
      outputs: [],
      parameters: {
        format: { type: 'select', options: ['fasta', 'json', 'csv', 'gff'], default: 'fasta' },
        filename: { type: 'text', default: 'results' }
      }
    }
  };

  // Group steps by category
  const stepCategories = {};
  Object.keys(availableSteps).forEach(stepKey => {
    const step = availableSteps[stepKey];
    if (!stepCategories[step.category]) {
      stepCategories[step.category] = [];
    }
    stepCategories[step.category].push({ key: stepKey, ...step });
  });

  // Load pipeline execution history
  useEffect(() => {
    loadExecutionHistory();
  }, []);

  const loadExecutionHistory = async () => {
    try {
      // This would fetch execution history from API
      // For now, using mock data
      setExecutionHistory([
        {
          id: 'exec_1',
          pipeline_name: 'Gene Analysis Pipeline',
          status: 'completed',
          started_at: '2024-01-15T10:30:00Z',
          completed_at: '2024-01-15T10:45:00Z',
          sequence_count: 5
        }
      ]);
    } catch (err) {
      console.error('Failed to load execution history:', err);
    }
  };

  // Add step to pipeline
  const addStep = (stepType, position = null) => {
    const newStep = {
      id: `step_${Date.now()}`,
      type: stepType,
      name: availableSteps[stepType].name,
      position: position || { x: 100 + currentPipeline.steps.length * 200, y: 100 },
      parameters: {},
      isConfigured: false
    };

    // Set default parameters
    Object.keys(availableSteps[stepType].parameters).forEach(paramKey => {
      newStep.parameters[paramKey] = availableSteps[stepType].parameters[paramKey].default;
    });

    setCurrentPipeline(prev => ({
      ...prev,
      steps: [...prev.steps, newStep]
    }));
  };

  // Remove step from pipeline
  const removeStep = (stepId) => {
    setCurrentPipeline(prev => ({
      ...prev,
      steps: prev.steps.filter(step => step.id !== stepId),
      connections: prev.connections.filter(conn => conn.from !== stepId && conn.to !== stepId)
    }));
  };

  // Connect two steps
  const connectSteps = (fromStepId, toStepId) => {
    // Check if connection already exists
    const exists = currentPipeline.connections.find(
      conn => conn.from === fromStepId && conn.to === toStepId
    );
    
    if (exists) return;

    // Validate connection compatibility
    const fromStep = currentPipeline.steps.find(s => s.id === fromStepId);
    const toStep = currentPipeline.steps.find(s => s.id === toStepId);
    
    if (!fromStep || !toStep) return;

    const fromOutputs = availableSteps[fromStep.type].outputs;
    const toInputs = availableSteps[toStep.type].inputs;
    
    // Check if outputs match inputs
    const compatible = fromOutputs.some(output => toInputs.includes(output));
    
    if (!compatible) {
      setError('Incompatible step types - outputs do not match inputs');
      return;
    }

    const newConnection = {
      id: `conn_${Date.now()}`,
      from: fromStepId,
      to: toStepId
    };

    setCurrentPipeline(prev => ({
      ...prev,
      connections: [...prev.connections, newConnection]
    }));
  };

  // Configure step parameters
  const configureStep = (step) => {
    setSelectedStep(step);
    setShowStepModal(true);
  };

  // Update step parameters
  const updateStepParameters = (parameters) => {
    if (!selectedStep) return;

    setCurrentPipeline(prev => ({
      ...prev,
      steps: prev.steps.map(step =>
        step.id === selectedStep.id
          ? { ...step, parameters, isConfigured: true }
          : step
      )
    }));
  };

  // Validate pipeline
  const validatePipeline = () => {
    const errors = [];
    
    // Check if pipeline has steps
    if (currentPipeline.steps.length === 0) {
      errors.push('Pipeline must have at least one step');
    }

    // Check for input step
    const hasInput = currentPipeline.steps.some(step => 
      availableSteps[step.type].inputs.length === 0
    );
    
    if (!hasInput) {
      errors.push('Pipeline must have an input step');
    }

    // Check for disconnected steps
    const connectedSteps = new Set();
    currentPipeline.connections.forEach(conn => {
      connectedSteps.add(conn.from);
      connectedSteps.add(conn.to);
    });

    const disconnectedSteps = currentPipeline.steps.filter(step => 
      !connectedSteps.has(step.id) && availableSteps[step.type].inputs.length > 0
    );

    if (disconnectedSteps.length > 0) {
      errors.push(`Disconnected steps: ${disconnectedSteps.map(s => s.name).join(', ')}`);
    }

    return errors;
  };

  // Save pipeline
  const savePipeline = async (name, description) => {
    try {
      setIsLoading(true);
      
      const pipelineData = {
        name,
        description,
        steps: currentPipeline.steps.map(step => ({
          type: step.type,
          parameters: step.parameters
        }))
      };

      const response = await enhancedApiService.createPipeline(
        name,
        description,
        currentPipeline.steps
      );

      if (response.data) {
        onPipelinesUpdated([...pipelines, response.data]);
        setShowSaveModal(false);
        setError(null);
      }
    } catch (err) {
      setError(`Failed to save pipeline: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Run pipeline
  const runCurrentPipeline = async () => {
    if (selectedSequences.length === 0) {
      setError('Please select sequences to run the pipeline');
      return;
    }

    const validationErrors = validatePipeline();
    if (validationErrors.length > 0) {
      setError(`Pipeline validation failed: ${validationErrors.join(', ')}`);
      return;
    }

    try {
      setIsLoading(true);
      
      // First save the pipeline if it's not saved
      if (!currentPipeline.id) {
        const tempName = `Temp_Pipeline_${Date.now()}`;
        const saveResponse = await enhancedApiService.createPipeline(
          tempName,
          'Temporary pipeline for execution',
          currentPipeline.steps
        );
        
        if (saveResponse.data) {
          await onRunPipeline(saveResponse.data.id, selectedSequences);
        }
      } else {
        await onRunPipeline(currentPipeline.id, selectedSequences);
      }
    } catch (err) {
      setError(`Failed to run pipeline: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Load saved pipeline
  const loadPipeline = (pipeline) => {
    setCurrentPipeline({
      id: pipeline.id,
      name: pipeline.name,
      description: pipeline.description,
      steps: pipeline.steps.map((step, index) => ({
        id: `step_${index}`,
        type: step.type,
        name: availableSteps[step.type]?.name || step.type,
        position: { x: 100 + index * 200, y: 100 },
        parameters: step.parameters,
        isConfigured: true
      })),
      connections: [] // Would need to reconstruct connections based on step order
    });
  };

  return (
    <div className="pipeline-designer">
      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Row>
        {/* Pipeline Canvas */}
        <Col lg={8}>
          <Card className="h-100">
            <Card.Header>
              <Row className="align-items-center">
                <Col>
                  <h5 className="mb-0">
                    {currentPipeline.name}
                    {currentPipeline.steps.length > 0 && (
                      <Badge bg="secondary" className="ms-2">
                        {currentPipeline.steps.length} steps
                      </Badge>
                    )}
                  </h5>
                </Col>
                <Col xs="auto">
                  <Button
                    variant="success"
                    onClick={runCurrentPipeline}
                    disabled={isLoading || selectedSequences.length === 0}
                  >
                    <BsPlay className="me-1" />
                    Run Pipeline
                  </Button>
                  <Button
                    variant="primary"
                    className="ms-2"
                    onClick={() => setShowSaveModal(true)}
                    disabled={isLoading}
                  >
                    <BsSave className="me-1" />
                    Save
                  </Button>
                </Col>
              </Row>
            </Card.Header>
            <Card.Body>
              <div className="pipeline-canvas" style={{ minHeight: '500px', position: 'relative' }}>
                <PipelineCanvas
                  steps={currentPipeline.steps}
                  connections={currentPipeline.connections}
                  availableSteps={availableSteps}
                  onStepClick={configureStep}
                  onStepRemove={removeStep}
                  onConnection={connectSteps}
                />
                
                {currentPipeline.steps.length === 0 && (
                  <div className="text-center mt-5 pt-5">
                    <h6 className="text-muted">Empty Pipeline</h6>
                    <p className="text-muted">
                      Drag steps from the toolbox to build your analysis pipeline
                    </p>
                  </div>
                )}
              </div>
            </Card.Body>
            <Card.Footer>
              <small className="text-muted">
                Selected Sequences: {selectedSequences.length} | 
                Pipeline Steps: {currentPipeline.steps.length} |
                Connections: {currentPipeline.connections.length}
              </small>
            </Card.Footer>
          </Card>
        </Col>

        {/* Toolbox and Controls */}
        <Col lg={4}>
          {/* Step Toolbox */}
          <Card className="mb-3">
            <Card.Header>
              <h6 className="mb-0">Analysis Steps</h6>
            </Card.Header>
            <Card.Body style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {Object.keys(stepCategories).map(category => (
                <div key={category} className="mb-3">
                  <h6 className="text-muted small">{category}</h6>
                  {stepCategories[category].map(step => (
                    <div
                      key={step.key}
                      className="step-tool d-flex align-items-center p-2 border rounded mb-2"
                      style={{ cursor: 'grab' }}
                      draggable
                      onDragStart={() => setDraggedStep(step.key)}
                      onClick={() => addStep(step.key)}
                    >
                      <span className="me-2" style={{ fontSize: '16px' }}>
                        {step.icon}
                      </span>
                      <div>
                        <div className="fw-bold small">{step.name}</div>
                        <div className="text-muted small">{step.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </Card.Body>
          </Card>

          {/* Saved Pipelines */}
          <Card className="mb-3">
            <Card.Header>
              <h6 className="mb-0">Saved Pipelines</h6>
            </Card.Header>
            <Card.Body style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {pipelines.length === 0 ? (
                <div className="text-center text-muted py-3">
                  No saved pipelines
                </div>
              ) : (
                pipelines.map(pipeline => (
                  <div
                    key={pipeline.id}
                    className="d-flex justify-content-between align-items-center border rounded p-2 mb-2"
                  >
                    <div>
                      <div className="fw-bold small">{pipeline.name}</div>
                      <div className="text-muted small">{pipeline.description}</div>
                    </div>
                    <Button
                      variant="outline-primary"
                      size="sm"
                      onClick={() => loadPipeline(pipeline)}
                    >
                      Load
                    </Button>
                  </div>
                ))
              )}
            </Card.Body>
          </Card>

          {/* Execution History */}
          <Card>
            <Card.Header>
              <h6 className="mb-0">Recent Executions</h6>
            </Card.Header>
            <Card.Body>
              {executionHistory.length === 0 ? (
                <div className="text-center text-muted py-3">
                  No executions yet
                </div>
              ) : (
                executionHistory.map(execution => (
                  <div key={execution.id} className="border rounded p-2 mb-2">
                    <div className="d-flex justify-content-between align-items-center">
                      <div className="fw-bold small">{execution.pipeline_name}</div>
                      <Badge bg={execution.status === 'completed' ? 'success' : 'warning'}>
                        {execution.status}
                      </Badge>
                    </div>
                    <div className="text-muted small">
                      {new Date(execution.started_at).toLocaleString()}
                    </div>
                  </div>
                ))
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Step Configuration Modal */}
      <StepConfigurationModal
        show={showStepModal}
        onHide={() => setShowStepModal(false)}
        step={selectedStep}
        stepDefinition={selectedStep ? availableSteps[selectedStep.type] : null}
        onParametersUpdate={updateStepParameters}
      />

      {/* Save Pipeline Modal */}
      <Modal show={showSaveModal} onHide={() => setShowSaveModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Save Pipeline</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <SavePipelineForm onSave={savePipeline} isLoading={isLoading} />
        </Modal.Body>
      </Modal>
    </div>
  );
};

// Pipeline Canvas Component
const PipelineCanvas = ({ 
  steps, 
  connections, 
  availableSteps, 
  onStepClick, 
  onStepRemove, 
  onConnection 
}) => {
  const [selectedStep, setSelectedStep] = useState(null);
  const [connecting, setConnecting] = useState(null);

  const handleStepClick = (step, event) => {
    event.stopPropagation();
    
    if (connecting) {
      // Complete connection
      if (connecting !== step.id) {
        onConnection(connecting, step.id);
      }
      setConnecting(null);
    } else {
      setSelectedStep(step.id);
      onStepClick(step);
    }
  };

  const handleConnectionStart = (stepId, event) => {
    event.stopPropagation();
    setConnecting(stepId);
  };

  return (
    <div className="position-relative w-100 h-100">
      {/* Render connections */}
      <svg className="position-absolute w-100 h-100" style={{ zIndex: 1 }}>
        {connections.map(connection => {
          const fromStep = steps.find(s => s.id === connection.from);
          const toStep = steps.find(s => s.id === connection.to);
          
          if (!fromStep || !toStep) return null;

          const x1 = fromStep.position.x + 100; // Step width / 2
          const y1 = fromStep.position.y + 40;  // Step height / 2
          const x2 = toStep.position.x + 100;
          const y2 = toStep.position.y + 40;

          return (
            <line
              key={connection.id}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="#007bff"
              strokeWidth="2"
              markerEnd="url(#arrowhead)"
            />
          );
        })}
        
        {/* Arrow marker definition */}
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon
              points="0 0, 10 3.5, 0 7"
              fill="#007bff"
            />
          </marker>
        </defs>
      </svg>

      {/* Render steps */}
      {steps.map(step => (
        <PipelineStep
          key={step.id}
          step={step}
          stepDefinition={availableSteps[step.type]}
          selected={selectedStep === step.id}
          connecting={connecting === step.id}
          onClick={(e) => handleStepClick(step, e)}
          onConnectionStart={(e) => handleConnectionStart(step.id, e)}
          onRemove={() => onStepRemove(step.id)}
        />
      ))}
    </div>
  );
};

// Pipeline Step Component
const PipelineStep = ({ 
  step, 
  stepDefinition, 
  selected, 
  connecting, 
  onClick, 
  onConnectionStart, 
  onRemove 
}) => {
  return (
    <div
      className={`pipeline-step position-absolute ${selected ? 'selected' : ''} ${connecting ? 'connecting' : ''}`}
      style={{
        left: step.position.x,
        top: step.position.y,
        width: '200px',
        zIndex: 2
      }}
      onClick={onClick}
    >
      <Card className={`border-2 ${selected ? 'border-primary' : 'border-secondary'}`}>
        <Card.Body className="p-2">
          <div className="d-flex align-items-center justify-content-between mb-1">
            <div className="d-flex align-items-center">
              <span className="me-2">{stepDefinition.icon}</span>
              <strong className="small">{step.name}</strong>
            </div>
            <Dropdown>
              <Dropdown.Toggle variant="link" size="sm" className="p-0">
                <BsGear />
              </Dropdown.Toggle>
              <Dropdown.Menu>
                <Dropdown.Item onClick={onConnectionStart}>
                  <BsArrowRight className="me-1" />
                  Connect
                </Dropdown.Item>
                <Dropdown.Item onClick={onRemove} className="text-danger">
                  <BsTrash className="me-1" />
                  Remove
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
          </div>
          
          <div className="small text-muted mb-1">
            {stepDefinition.description}
          </div>
          
          <div className="d-flex justify-content-between">
            <Badge bg={step.isConfigured ? 'success' : 'warning'} className="small">
              {step.isConfigured ? 'Configured' : 'Needs Config'}
            </Badge>
            <div className="small text-muted">
              In: {stepDefinition.inputs.length} | Out: {stepDefinition.outputs.length}
            </div>
          </div>
        </Card.Body>
      </Card>
    </div>
  );
};

// Step Configuration Modal
const StepConfigurationModal = ({ 
  show, 
  onHide, 
  step, 
  stepDefinition, 
  onParametersUpdate 
}) => {
  const [parameters, setParameters] = useState({});

  useEffect(() => {
    if (step) {
      setParameters(step.parameters || {});
    }
  }, [step]);

  const handleParameterChange = (paramName, value) => {
    setParameters(prev => ({
      ...prev,
      [paramName]: value
    }));
  };

  const handleSave = () => {
    onParametersUpdate(parameters);
    onHide();
  };

  if (!step || !stepDefinition) return null;

  return (
    <Modal show={show} onHide={onHide} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>
          Configure {stepDefinition.name}
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Alert variant="info">
          {stepDefinition.description}
        </Alert>
        
        <Form>
          {Object.keys(stepDefinition.parameters).map(paramName => {
            const param = stepDefinition.parameters[paramName];
            
            return (
              <Form.Group key={paramName} className="mb-3">
                <Form.Label className="text-capitalize">
                  {paramName.replace(/_/g, ' ')}
                </Form.Label>
                
                {param.type === 'select' ? (
                  <Form.Select
                    value={parameters[paramName] || param.default}
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
                    value={parameters[paramName] || param.default}
                    onChange={(e) => handleParameterChange(paramName, parseFloat(e.target.value))}
                    min={param.min}
                    max={param.max}
                    step={paramName.includes('evalue') ? 'any' : 1}
                  />
                ) : (
                  <Form.Control
                    type="text"
                    value={parameters[paramName] || param.default}
                    onChange={(e) => handleParameterChange(paramName, e.target.value)}
                  />
                )}
              </Form.Group>
            );
          })}
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Cancel
        </Button>
        <Button variant="primary" onClick={handleSave}>
          Save Configuration
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

// Save Pipeline Form
const SavePipelineForm = ({ onSave, isLoading }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (name.trim()) {
      onSave(name.trim(), description.trim());
    }
  };

  return (
    <Form onSubmit={handleSubmit}>
      <Form.Group className="mb-3">
        <Form.Label>Pipeline Name *</Form.Label>
        <Form.Control
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Enter pipeline name"
          required
        />
      </Form.Group>
      
      <Form.Group className="mb-3">
        <Form.Label>Description</Form.Label>
        <Form.Control
          as="textarea"
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what this pipeline does"
        />
      </Form.Group>
      
      <div className="d-grid gap-2">
        <Button type="submit" variant="primary" disabled={!name.trim() || isLoading}>
          {isLoading ? 'Saving...' : 'Save Pipeline'}
        </Button>
      </div>
    </Form>
  );
};

export default PipelineDesigner;