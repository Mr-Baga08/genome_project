// frontend/src/components/AdvancedSequenceViewer.js
import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { Card, Button, Row, Col, Form, Badge, Modal, Tooltip, OverlayTrigger, ButtonGroup } from 'react-bootstrap';
import { BsZoomIn, BsZoomOut, BsSearch, BsDownload, BsUpload, BsGear, BsFullscreen, BsArrowLeft, BsArrowRight } from 'react-icons/bs';

const AdvancedSequenceViewer = ({ 
  sequence, 
  annotations = [], 
  selectedRegion, 
  onRegionSelect,
  onAnnotationClick,
  height = 600,
  width = 1000 
}) => {
  const canvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const containerRef = useRef(null);
  
  // State management
  const [viewportStart, setViewportStart] = useState(0);
  const [viewportEnd, setViewportEnd] = useState(100);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedSearchIndex, setSelectedSearchIndex] = useState(0);
  const [showSettings, setShowSettings] = useState(false);
  const [renderSettings, setRenderSettings] = useState({
    showRuler: true,
    showTranslation: false,
    colorScheme: 'nucleotide',
    fontSize: 12,
    lineHeight: 20,
    showAnnotations: true,
    annotationHeight: 15
  });
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStart, setDrawStart] = useState(null);

  const sequenceData = sequence?.sequence || '';
  const sequenceLength = sequenceData.length;
  const basesPerRow = Math.floor(width / (renderSettings.fontSize * 0.6));

  // Color schemes
  const colorSchemes = {
    nucleotide: {
      'A': '#FF6B6B', 'T': '#4ECDC4', 'C': '#45B7D1', 'G': '#96CEB4',
      'U': '#FFA07A', 'N': '#D3D3D3'
    },
    protein: {
      'A': '#C8C8C8', 'R': '#145AFF', 'N': '#00DCDC', 'D': '#E60A0A',
      'C': '#E6E600', 'Q': '#00DCDC', 'E': '#E60A0A', 'G': '#EBEBEB',
      'H': '#8282D2', 'I': '#0F820F', 'L': '#0F820F', 'K': '#145AFF',
      'M': '#E6E600', 'F': '#3232AA', 'P': '#DC9682', 'S': '#FA9600',
      'T': '#FA9600', 'W': '#B45AB4', 'Y': '#3232AA', 'V': '#0F820F'
    },
    conservation: {
      high: '#2E8B57',
      medium: '#FFD700', 
      low: '#FF6347',
      none: '#D3D3D3'
    }
  };

  // Canvas rendering hook
  useEffect(() => {
    drawSequence();
  }, [sequenceData, viewportStart, viewportEnd, zoomLevel, renderSettings, annotations, selectedRegion, searchResults]);

  // Sequence search functionality
  const handleSearch = useCallback(() => {
    if (!searchQuery || !sequenceData) return;
    
    const results = [];
    const query = searchQuery.toUpperCase();
    let index = sequenceData.indexOf(query);
    
    while (index !== -1) {
      results.push({
        start: index,
        end: index + query.length - 1,
        match: query,
        position: index
      });
      index = sequenceData.indexOf(query, index + 1);
    }
    
    setSearchResults(results);
    setSelectedSearchIndex(0);
    
    // Navigate to first result
    if (results.length > 0) {
      navigateToPosition(results[0].start);
    }
  }, [searchQuery, sequenceData]);

  // Navigation functions
  const navigateToPosition = useCallback((position) => {
    const windowSize = viewportEnd - viewportStart;
    const newStart = Math.max(0, position - Math.floor(windowSize / 2));
    const newEnd = Math.min(sequenceLength, newStart + windowSize);
    
    setViewportStart(newStart);
    setViewportEnd(newEnd);
  }, [viewportStart, viewportEnd, sequenceLength]);

  const navigateToSearchResult = useCallback((index) => {
    if (index >= 0 && index < searchResults.length) {
      setSelectedSearchIndex(index);
      navigateToPosition(searchResults[index].start);
    }
  }, [searchResults, navigateToPosition]);

  // Zoom functions
  const handleZoom = useCallback((direction, mouseX = width / 2) => {
    const zoomFactor = direction === 'in' ? 1.5 : 1 / 1.5;
    const newZoomLevel = Math.max(0.1, Math.min(10, zoomLevel * zoomFactor));
    
    if (newZoomLevel !== zoomLevel) {
      // Calculate new viewport to zoom around mouse position
      const mouseRatio = mouseX / width;
      const currentWindowSize = viewportEnd - viewportStart;
      const newWindowSize = Math.max(10, currentWindowSize / zoomFactor);
      const centerPosition = viewportStart + (currentWindowSize * mouseRatio);
      
      const newStart = Math.max(0, centerPosition - (newWindowSize * mouseRatio));
      const newEnd = Math.min(sequenceLength, newStart + newWindowSize);
      
      setZoomLevel(newZoomLevel);
      setViewportStart(newStart);
      setViewportEnd(newEnd);
    }
  }, [zoomLevel, viewportStart, viewportEnd, sequenceLength, width]);

  // Mouse event handlers
  const handleMouseDown = useCallback((event) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const position = getPositionFromX(x);
    
    setIsDrawing(true);
    setDrawStart(position);
  }, []);

  const handleMouseMove = useCallback((event) => {
    if (!isDrawing || !drawStart) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const position = getPositionFromX(x);
    
    // Update selection
    const start = Math.min(drawStart, position);
    const end = Math.max(drawStart, position);
    
    if (onRegionSelect) {
      onRegionSelect({ start, end });
    }
  }, [isDrawing, drawStart, onRegionSelect]);

  const handleMouseUp = useCallback(() => {
    setIsDrawing(false);
    setDrawStart(null);
  }, []);

  // Convert x coordinate to sequence position
  const getPositionFromX = useCallback((x) => {
    const charWidth = renderSettings.fontSize * 0.6;
    const charsPerLine = Math.floor(width / charWidth);
    const lineHeight = renderSettings.lineHeight;
    
    const y = Math.floor((window.scrollY + 50) / lineHeight); // Account for ruler
    const xPos = Math.floor(x / charWidth);
    
    return viewportStart + (y * charsPerLine) + xPos;
  }, [width, renderSettings, viewportStart]);

  // Main drawing function
  const drawSequence = useCallback(() => {
    const canvas = canvasRef.current;
    const overlayCanvas = overlayCanvasRef.current;
    
    if (!canvas || !overlayCanvas || !sequenceData) return;
    
    const ctx = canvas.getContext('2d');
    const overlayCtx = overlayCanvas.getContext('2d');
    
    // Clear canvases
    ctx.clearRect(0, 0, width, height);
    overlayCtx.clearRect(0, 0, width, height);
    
    // Set font
    ctx.font = `${renderSettings.fontSize}px 'Courier New', monospace`;
    overlayCtx.font = `${renderSettings.fontSize}px 'Courier New', monospace`;
    
    const charWidth = renderSettings.fontSize * 0.6;
    const lineHeight = renderSettings.lineHeight;
    const charsPerLine = Math.floor(width / charWidth);
    
    // Draw ruler if enabled
    if (renderSettings.showRuler) {
      drawRuler(ctx, charWidth, lineHeight);
    }
    
    // Draw sequence
    const visibleSequence = sequenceData.slice(viewportStart, viewportEnd);
    let currentY = renderSettings.showRuler ? lineHeight + 10 : 10;
    
    for (let i = 0; i < visibleSequence.length; i += charsPerLine) {
      const line = visibleSequence.slice(i, i + charsPerLine);
      drawSequenceLine(ctx, line, currentY, charWidth, i + viewportStart);
      
      if (renderSettings.showTranslation && sequence?.sequence_type !== 'PROTEIN') {
        drawTranslation(ctx, line, currentY + lineHeight, charWidth, i + viewportStart);
        currentY += lineHeight;
      }
      
      currentY += lineHeight + 5;
    }
    
    // Draw annotations
    if (renderSettings.showAnnotations && annotations.length > 0) {
      drawAnnotations(overlayCtx, charWidth, lineHeight, charsPerLine);
    }
    
    // Draw selected region
    if (selectedRegion) {
      drawSelectedRegion(overlayCtx, charWidth, lineHeight, charsPerLine);
    }
    
    // Draw search results
    if (searchResults.length > 0) {
      drawSearchResults(overlayCtx, charWidth, lineHeight, charsPerLine);
    }
    
  }, [sequenceData, viewportStart, viewportEnd, renderSettings, annotations, selectedRegion, searchResults, width, height]);

  // Draw ruler
  const drawRuler = (ctx, charWidth, lineHeight) => {
    ctx.fillStyle = '#666';
    ctx.fillRect(0, 0, width, lineHeight);
    
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'center';
    
    const tickInterval = 10;
    for (let i = 0; i < width; i += charWidth * tickInterval) {
      const position = viewportStart + Math.floor(i / charWidth);
      if (position % tickInterval === 0) {
        ctx.fillText(position.toString(), i, lineHeight - 5);
      }
    }
  };

  // Draw sequence line with colors
  const drawSequenceLine = (ctx, line, y, charWidth, startPosition) => {
    ctx.textAlign = 'center';
    
    for (let i = 0; i < line.length; i++) {
      const base = line[i];
      const x = i * charWidth + charWidth / 2;
      const absolutePosition = startPosition + i;
      
      // Set color based on scheme
      const colors = colorSchemes[renderSettings.colorScheme] || colorSchemes.nucleotide;
      ctx.fillStyle = colors[base] || '#000';
      
      // Draw background if needed
      if (absolutePosition >= viewportStart && absolutePosition <= viewportEnd) {
        ctx.fillText(base, x, y);
      }
    }
  };

  // Draw translation (amino acids)
  const drawTranslation = (ctx, line, y, charWidth, startPosition) => {
    if (line.length < 3) return;
    
    const geneticCode = {
      'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
      'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
      'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
      'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
      // Add more codons as needed...
    };
    
    ctx.fillStyle = '#666';
    ctx.font = `${renderSettings.fontSize - 2}px 'Courier New', monospace`;
    
    for (let i = 0; i < line.length - 2; i += 3) {
      const codon = line.slice(i, i + 3);
      const aa = geneticCode[codon] || 'X';
      const x = (i + 1) * charWidth + charWidth / 2;
      
      ctx.fillText(aa, x, y);
    }
  };

  // Draw annotations
  const drawAnnotations = (ctx, charWidth, lineHeight, charsPerLine) => {
    const rulerOffset = renderSettings.showRuler ? lineHeight + 10 : 10;
    
    annotations.forEach((annotation, index) => {
      if (annotation.start_position < viewportEnd && annotation.end_position > viewportStart) {
        const start = Math.max(annotation.start_position, viewportStart);
        const end = Math.min(annotation.end_position, viewportEnd);
        
        const startRelative = start - viewportStart;
        const endRelative = end - viewportStart;
        
        // Calculate screen coordinates
        const startLine = Math.floor(startRelative / charsPerLine);
        const endLine = Math.floor(endRelative / charsPerLine);
        
        // Draw annotation across multiple lines if necessary
        for (let line = startLine; line <= endLine; line++) {
          const lineStart = Math.max(startRelative - line * charsPerLine, 0);
          const lineEnd = Math.min(endRelative - line * charsPerLine, charsPerLine - 1);
          
          const x1 = lineStart * charWidth;
          const x2 = (lineEnd + 1) * charWidth;
          const y = rulerOffset + line * (lineHeight + 5) - renderSettings.annotationHeight;
          
          // Draw annotation rectangle
          ctx.fillStyle = getAnnotationColor(annotation.feature_type);
          ctx.fillRect(x1, y, x2 - x1, renderSettings.annotationHeight);
          
          // Draw annotation label
          if (line === startLine) {
            ctx.fillStyle = '#000';
            ctx.font = `${renderSettings.fontSize - 4}px Arial`;
            ctx.fillText(annotation.feature_type, x1 + 2, y + renderSettings.annotationHeight - 2);
          }
        }
      }
    });
  };

  // Draw selected region
  const drawSelectedRegion = (ctx, charWidth, lineHeight, charsPerLine) => {
    if (!selectedRegion) return;
    
    const rulerOffset = renderSettings.showRuler ? lineHeight + 10 : 10;
    const start = Math.max(selectedRegion.start, viewportStart);
    const end = Math.min(selectedRegion.end, viewportEnd);
    
    if (start <= end) {
      ctx.fillStyle = 'rgba(0, 123, 255, 0.3)';
      
      const startRelative = start - viewportStart;
      const endRelative = end - viewportStart;
      
      const startLine = Math.floor(startRelative / charsPerLine);
      const endLine = Math.floor(endRelative / charsPerLine);
      
      for (let line = startLine; line <= endLine; line++) {
        const lineStart = Math.max(startRelative - line * charsPerLine, 0);
        const lineEnd = Math.min(endRelative - line * charsPerLine, charsPerLine - 1);
        
        const x1 = lineStart * charWidth;
        const x2 = (lineEnd + 1) * charWidth;
        const y = rulerOffset + line * (lineHeight + 5);
        
        ctx.fillRect(x1, y - 5, x2 - x1, lineHeight);
      }
    }
  };

  // Draw search results
  const drawSearchResults = (ctx, charWidth, lineHeight, charsPerLine) => {
    const rulerOffset = renderSettings.showRuler ? lineHeight + 10 : 10;
    
    searchResults.forEach((result, index) => {
      if (result.start < viewportEnd && result.end >= viewportStart) {
        const isSelected = index === selectedSearchIndex;
        ctx.fillStyle = isSelected ? 'rgba(255, 0, 0, 0.6)' : 'rgba(255, 255, 0, 0.4)';
        
        const start = Math.max(result.start, viewportStart);
        const end = Math.min(result.end, viewportEnd);
        
        const startRelative = start - viewportStart;
        const endRelative = end - viewportStart;
        
        const startLine = Math.floor(startRelative / charsPerLine);
        const endLine = Math.floor(endRelative / charsPerLine);
        
        for (let line = startLine; line <= endLine; line++) {
          const lineStart = Math.max(startRelative - line * charsPerLine, 0);
          const lineEnd = Math.min(endRelative - line * charsPerLine, charsPerLine - 1);
          
          const x1 = lineStart * charWidth;
          const x2 = (lineEnd + 1) * charWidth;
          const y = rulerOffset + line * (lineHeight + 5) - 2;
          
          ctx.fillRect(x1, y, x2 - x1, lineHeight);
        }
      }
    });
  };

  // Get annotation color
  const getAnnotationColor = (featureType) => {
    const annotationColors = {
      'gene': '#90EE90',
      'CDS': '#FFB6C1',
      'exon': '#87CEEB',
      'intron': '#DDA0DD',
      'promoter': '#F0E68C',
      'enhancer': '#FFA500',
      'repeat': '#D3D3D3',
      'domain': '#20B2AA'
    };
    
    return annotationColors[featureType] || '#B0C4DE';
  };

  // Export sequence
  const handleExport = () => {
    let content = '';
    
    if (selectedRegion) {
      const selectedSequence = sequenceData.slice(selectedRegion.start, selectedRegion.end + 1);
      content = `>${sequence?.name || 'sequence'}_${selectedRegion.start}-${selectedRegion.end}\n${selectedSequence}`;
    } else {
      content = `>${sequence?.name || 'sequence'}\n${sequenceData}`;
    }
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sequence?.name || 'sequence'}.fasta`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Card className="advanced-sequence-viewer">
      <Card.Header>
        <Row className="align-items-center">
          <Col md={4}>
            <h5 className="mb-0">{sequence?.name || 'Sequence'}</h5>
            <small className="text-muted">
              Length: {sequenceLength} bp
              {sequence?.gc_content && ` | GC: ${sequence.gc_content.toFixed(1)}%`}
            </small>
          </Col>
          
          <Col md={4}>
            <Form className="d-flex">
              <Form.Control
                type="text"
                placeholder="Search sequence..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button variant="outline-secondary" onClick={handleSearch}>
                <BsSearch />
              </Button>
            </Form>
          </Col>
          
          <Col md={4}>
            <ButtonGroup className="float-end">
              <Button variant="outline-secondary" onClick={() => handleZoom('out')}>
                <BsZoomOut />
              </Button>
              <Button variant="outline-secondary" onClick={() => handleZoom('in')}>
                <BsZoomIn />
              </Button>
              <Button variant="outline-secondary" onClick={() => setShowSettings(true)}>
                <BsGear />
              </Button>
              <Button variant="outline-secondary" onClick={handleExport}>
                <BsDownload />
              </Button>
            </ButtonGroup>
          </Col>
        </Row>
        
        {/* Search results navigation */}
        {searchResults.length > 0 && (
          <Row className="mt-2">
            <Col>
              <div className="d-flex align-items-center gap-2">
                <small>Found {searchResults.length} matches</small>
                <Button 
                  size="sm" 
                  variant="outline-secondary"
                  onClick={() => navigateToSearchResult(selectedSearchIndex - 1)}
                  disabled={selectedSearchIndex <= 0}
                >
                  <BsArrowLeft />
                </Button>
                <small>{selectedSearchIndex + 1} of {searchResults.length}</small>
                <Button 
                  size="sm" 
                  variant="outline-secondary"
                  onClick={() => navigateToSearchResult(selectedSearchIndex + 1)}
                  disabled={selectedSearchIndex >= searchResults.length - 1}
                >
                  <BsArrowRight />
                </Button>
              </div>
            </Col>
          </Row>
        )}
      </Card.Header>
      
      <Card.Body>
        <div 
          ref={containerRef}
          className="sequence-container"
          style={{ position: 'relative', overflow: 'auto', height: height }}
        >
          <canvas
            ref={canvasRef}
            width={width}
            height={height}
            style={{ position: 'absolute', top: 0, left: 0, cursor: 'text' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          />
          <canvas
            ref={overlayCanvasRef}
            width={width}
            height={height}
            style={{ 
              position: 'absolute', 
              top: 0, 
              left: 0, 
              pointerEvents: 'none',
              zIndex: 1
            }}
          />
        </div>
        
        {/* Status bar */}
        <div className="mt-2 p-2 bg-light rounded">
          <Row>
            <Col>
              <small>
                Viewing: {viewportStart + 1} - {viewportEnd} of {sequenceLength}
                {selectedRegion && ` | Selected: ${selectedRegion.start + 1} - ${selectedRegion.end + 1}`}
              </small>
            </Col>
            <Col xs="auto">
              <small>Zoom: {(zoomLevel * 100).toFixed(0)}%</small>
            </Col>
          </Row>
        </div>
      </Card.Body>
      
      {/* Settings Modal */}
      <Modal show={showSettings} onHide={() => setShowSettings(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Display Settings</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Check
                    type="switch"
                    label="Show Ruler"
                    checked={renderSettings.showRuler}
                    onChange={(e) => setRenderSettings({...renderSettings, showRuler: e.target.checked})}
                  />
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Check
                    type="switch"
                    label="Show Translation"
                    checked={renderSettings.showTranslation}
                    onChange={(e) => setRenderSettings({...renderSettings, showTranslation: e.target.checked})}
                  />
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Check
                    type="switch"
                    label="Show Annotations"
                    checked={renderSettings.showAnnotations}
                    onChange={(e) => setRenderSettings({...renderSettings, showAnnotations: e.target.checked})}
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Color Scheme</Form.Label>
                  <Form.Select
                    value={renderSettings.colorScheme}
                    onChange={(e) => setRenderSettings({...renderSettings, colorScheme: e.target.value})}
                  >
                    <option value="nucleotide">Nucleotide</option>
                    <option value="protein">Protein</option>
                    <option value="conservation">Conservation</option>
                  </Form.Select>
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Label>Font Size: {renderSettings.fontSize}</Form.Label>
                  <Form.Range
                    min={8}
                    max={24}
                    value={renderSettings.fontSize}
                    onChange={(e) => setRenderSettings({...renderSettings, fontSize: parseInt(e.target.value)})}
                  />
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Label>Line Height: {renderSettings.lineHeight}</Form.Label>
                  <Form.Range
                    min={15}
                    max={40}
                    value={renderSettings.lineHeight}
                    onChange={(e) => setRenderSettings({...renderSettings, lineHeight: parseInt(e.target.value)})}
                  />
                </Form.Group>
              </Col>
            </Row>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowSettings(false)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </Card>
  );
};

export default AdvancedSequenceViewer;