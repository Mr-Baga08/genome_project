// frontend/src/components/WorkflowDesigner.js
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Card, Button, Row, Col, Modal, Form, Alert, Spinner } from 'react-bootstrap';
import { BsPlay, BsTrash, BsGear, BsPlusCircle, BsSave, BsDownload } from 'react-icons/bs';
import apiService from '../services/apiService';

const WorkflowDesigner = () => {
  const [workflow, setWorkflow] = useState({
    id: '',
    name: 'New Workflow',
    description: '',
    nodes: [],
    connections: []
  });
  
  const [availableElements, setAvailableElements] = useState({});
  const [selectedElement, setSelectedElement] = useState(null);
  const [draggedElement, setDraggedElement] = useState(null);
  const [showPropertyModal, setShowPropertyModal] = useState(false);
  const [executionStatus, setExecutionStatus] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);
  
  const canvasRef = useRef(null);
  const [canvasOffset, setCanvasOffset] = useState({ x: 0, y: 0 });

  // Load available workflow elements
  useEffect(() => {
    loadWorkflowElements();
  }, []);

  const loadWorkflowElements = async () => {
    try {
      const response = await apiService.get('/api/v1/workflow/elements');
      setAvailableElements(response.data);
    } catch (error) {
      console.error('Failed to load workflow elements:', error);
    }
  };

  // Handle drag and drop
  const handleDrop = useCallback((event) => {
    event.preventDefault();
    if (!draggedElement) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const position = {
      x: event.clientX - rect.left - canvasOffset.x,
      y: event.clientY - rect.top - canvasOffset.y
    };
    
    addWorkflowNode(draggedElement, position);
    setDraggedElement(null);
  }, [draggedElement, canvasOffset]);

  const addWorkflowNode = (elementInfo, position) => {
    const newNode = {
      id: `node_${Date.now()}`,
      type: elementInfo.name,
      display_name: elementInfo.display_name,
      position,
      parameters: {},
      input_ports: elementInfo.input_ports || [],
      output_ports: elementInfo.output_ports || []
    };
    
    setWorkflow(prev => ({
      ...prev,
      nodes: [...prev.nodes, newNode]
    }));
  };

  // Handle node selection and property editing
  const handleNodeClick = (node) => {
    setSelectedElement(node);
    setShowPropertyModal(true);
  };

  const updateNodeProperties = (nodeId, properties) => {
    setWorkflow(prev => ({
      ...prev,
      nodes: prev.nodes.map(node =>
        node.id === nodeId ? { ...node, parameters: properties } : node
      )
    }));
  };

  const removeNode = (nodeId) => {
    setWorkflow(prev => ({
      ...prev,
      nodes: prev.nodes.filter(node => node.id !== nodeId),
      connections: prev.connections.filter(
        conn => conn.from !== nodeId && conn.to !== nodeId
      )
    }));
  };

  // Execute workflow
  const executeWorkflow = async () => {
    if (workflow.nodes.length === 0) {
      alert('Please add some workflow elements first');
      return;
    }

    setIsExecuting(true);
    try {
      const response = await apiService.post('/api/v1/workflows/execute', {
        workflow_definition: workflow,
        input_data: null
      });
      
      const workflowId = response.data.workflow_id;
      setExecutionStatus({ id: workflowId, status: 'running' });
      
      // Poll for status updates
      pollWorkflowStatus(workflowId);
      
    } catch (error) {
      console.error('Failed to execute workflow:', error);
      setExecutionStatus({ status: 'failed', error: error.message });
    } finally {
      setIsExecuting(false);
    }
  };

  const pollWorkflowStatus = async (workflowId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await apiService.get(`/api/v1/workflows/${workflowId}/status`);
        const status = response.data;
        
        setExecutionStatus(status);
        
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error('Failed to poll workflow status:', error);
        clearInterval(pollInterval);
      }
    }, 2000);
  };

  // Save workflow
  const saveWorkflow = () => {
    const workflowData = JSON.stringify(workflow, null, 2);
    const blob = new Blob([workflowData], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflow.name}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Render workflow canvas
  const renderWorkflowCanvas = () => {
    return (
      <div 
        ref={canvasRef}
        className="workflow-canvas"
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        style={{
          width: '100%',
          height: '500px',
          border: '2px dashed #dee2e6',
          borderRadius: '8px',
          position: 'relative',
          backgroundColor: '#f8f9fa',
          overflow: 'auto'
        }}
      >
        {/* Render connections */}
        <svg 
          className="connections-overlay"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            zIndex: 1
          }}
        >
          {workflow.connections.map((conn, index) => {
            const fromNode = workflow.nodes.find(n => n.id === conn.from);
            const toNode = workflow.nodes.find(n => n.id === conn.to);
            
            if (!fromNode || !toNode) return null;
            
            return (
              <line
                key={index}
                x1={fromNode.position.x + 120}
                y1={fromNode.position.y + 40}
                x2={toNode.position.x}
                y2={toNode.position.y + 40}
                stroke="#007bff"
                strokeWidth="2"
                markerEnd="url(#arrowhead)"
              />
            );
          })}
          
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#007bff" />
            </marker>
          </defs>
        </svg>

        {/* Render nodes */}
        {workflow.nodes.map((node) => (
          <div
            key={node.id}
            className="workflow-node"
            style={{
              position: 'absolute',
              left: node.position.x,
              top: node.position.y,
              width: '120px',
              zIndex: 2
            }}
          >
            <Card 
              className="cursor-pointer shadow-sm"
              onClick={() => handleNodeClick(node)}
              style={{ fontSize: '0.85rem' }}
            >
              <Card.Body className="p-2">
                <div className="d-flex justify-content-between align-items-start">
                  <small className="fw-bold text-truncate">
                    {node.display_name}
                  </small>
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeNode(node.id);
                    }}
                    style={{ padding: '2px 6px', fontSize: '0.7rem' }}
                  >
                    <BsTrash />
                  </Button>
                </div>
                <div className="mt-1">
                  {node.input_ports.length > 0 && (
                    <small className="text-muted d-block">
                      In: {node.input_ports.join(', ')}
                    </small>
                  )}
                  {node.output_ports.length > 0 && (
                    <small className="text-muted d-block">
                      Out: {node.output_ports.join(', ')}
                    </small>
                  )}
                </div>
              </Card.Body>
            </Card>
          </div>
        ))}
        
        {workflow.nodes.length === 0 && (
          <div className="text-center text-muted" style={{ 
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)'
          }}>
            <BsPlusCircle size={48} className="mb-3" />
            <p>Drag workflow elements here to build your analysis pipeline</p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="workflow-designer">
      <Row>
        {/* Element Palette */}
        <Col md={3}>
          <Card>
            <Card.Header>
              <h6 className="mb-0">Workflow Elements</h6>
            </Card.Header>
            <Card.Body style={{ maxHeight: '600px', overflowY: 'auto' }}>
              {Object.entries(availableElements).map(([category, elements]) => (
                <div key={category} className="mb-3">
                  <h6 className="text-muted">{category}</h6>
                  {elements.map((element, index) => (
                    <Card
                      key={index}
                      className="mb-2 cursor-pointer border-0 shadow-sm"
                      draggable
                      onDragStart={() => setDraggedElement(element)}
                      style={{ backgroundColor: '#f8f9fa' }}
                    >
                      <Card.Body className="p-2">
                        <small className="fw-bold d-block">{element.display_name}</small>
                        <small className="text-muted">{element.description}</small>
                      </Card.Body>
                    </Card>
                  ))}
                </div>
              ))}
            </Card.Body>
          </Card>
        </Col>

        {/* Main Canvas */}
        <Col md={9}>
          <Card>
            <Card.Header>
              <Row className="align-items-center">
                <Col>
                  <Form.Control
                    type="text"
                    value={workflow.name}
                    onChange={(e) => setWorkflow(prev => ({ ...prev, name: e.target.value }))}
                    style={{ fontWeight: 'bold', border: 'none', background: 'transparent' }}
                  />
                </Col>
                <Col xs="auto">
                  <div className="d-flex gap-2">
                    <Button 
                      variant="success" 
                      size="sm"
                      onClick={executeWorkflow}
                      disabled={isExecuting || workflow.nodes.length === 0}
                    >
                      {isExecuting ? <Spinner animation="border" size="sm" /> : <BsPlay />}
                      {isExecuting ? 'Executing...' : 'Execute'}
                    </Button>
                    <Button variant="outline-primary" size="sm" onClick={saveWorkflow}>
                      <BsSave /> Save
                    </Button>
                    <Button 
                      variant="outline-danger" 
                      size="sm"
                      onClick={() => setWorkflow({ ...workflow, nodes: [], connections: [] })}
                    >
                      <BsTrash /> Clear
                    </Button>
                  </div>
                </Col>
              </Row>
            </Card.Header>
            
            <Card.Body>
              {executionStatus && (
                <Alert 
                  variant={
                    executionStatus.status === 'completed' ? 'success' :
                    executionStatus.status === 'failed' ? 'danger' : 'info'
                  }
                  className="mb-3"
                >
                  <strong>Workflow Status:</strong> {executionStatus.status}
                  {executionStatus.error && (
                    <div><strong>Error:</strong> {executionStatus.error}</div>
                  )}
                </Alert>
              )}
              
              {renderWorkflowCanvas()}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Property Modal */}
      <Modal show={showPropertyModal} onHide={() => setShowPropertyModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>
            {selectedElement?.display_name} Properties
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedElement && (
            <NodePropertiesForm
              node={selectedElement}
              onUpdate={(properties) => {
                updateNodeProperties(selectedElement.id, properties);
                setShowPropertyModal(false);
              }}
            />
          )}
        </Modal.Body>
      </Modal>
    </div>
  );
};

// Node Properties Form Component
const NodePropertiesForm = ({ node, onUpdate }) => {
  const [properties, setProperties] = useState(node.parameters || {});
  
  const handleSubmit = (e) => {
    e.preventDefault();
    onUpdate(properties);
  };

  return (
    <Form onSubmit={handleSubmit}>
      <div className="mb-3">
        <strong>Node Type:</strong> {node.display_name}
      </div>
      
      {/* Render parameter inputs based on element definition */}
      {Object.entries(properties).map(([key, value]) => (
        <Form.Group key={key} className="mb-3">
          <Form.Label>{key}</Form.Label>
          <Form.Control
            type="text"
            value={value}
            onChange={(e) => setProperties(prev => ({
              ...prev,
              [key]: e.target.value
            }))}
          />
        </Form.Group>
      ))}
      
      <div className="d-flex justify-content-end gap-2">
        <Button type="submit" variant="primary">Update</Button>
      </div>
    </Form>
  );
};

export default WorkflowDesigner;
