// frontend/src/components/SequenceViewer.js
import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { Card, Button, Row, Col, Form, Badge, Tooltip, OverlayTrigger } from 'react-bootstrap';
import { BsZoomIn, BsZoomOut, BsSearch, BsDownload } from 'react-icons/bs';

const SequenceViewer = ({ 
  sequence, 
  annotations = [], 
  selectedRegion, 
  onRegionSelect,
  height = 400 
}) => {
  const [viewportStart, setViewportStart] = useState(0);
  const [viewportEnd, setViewportEnd] = useState(Math.min(100, sequence?.sequence?.length || 100));
  const [zoomLevel, setZoomLevel] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  const sequenceData = sequence?.sequence || '';
  const sequenceLength = sequenceData.length;

  // Virtualized sequence display
  const visibleSequence = useMemo(() => {
    return sequenceData.slice(viewportStart, viewportEnd);
  }, [sequenceData, viewportStart, viewportEnd]);

  // Handle sequence search
  const handleSearch = useCallback(() => {
    if (!searchQuery || !sequenceData) return;
    
    const results = [];
    const query = searchQuery.toUpperCase();
    let index = sequenceData.indexOf(query);
    
    while (index !== -1) {
      results.push({
        start: index,
        end: index + query.length,
        match: query
      });
      index = sequenceData.indexOf(query, index + 1);
    }
    
    setSearchResults(results);
  }, [searchQuery, sequenceData]);

  // Handle zoom
  const handleZoom = (direction) => {
    if (direction === 'in') {
      setZoomLevel(Math.min(zoomLevel * 1.5, 5));
    } else {
      setZoomLevel(Math.max(zoomLevel / 1.5, 0.1));
    }
  };

  // Handle viewport navigation
  const handleScroll = (event) => {
    const target = event.target;
    const scrollRatio = target.scrollLeft / (target.scrollWidth - target.clientWidth);
    const windowSize = viewportEnd - viewportStart;
    const newStart = Math.floor(scrollRatio * (sequenceLength - windowSize));
    
    setViewportStart(Math.max(0, newStart));
    setViewportEnd(Math.min(sequenceLength, newStart + windowSize));
  };

  // Render sequence with color coding
  const renderSequenceWithColors = () => {
    return visibleSequence.split('').map((base, index) => {
      const absolutePosition = viewportStart + index;
      const isSelected = selectedRegion && 
        absolutePosition >= selectedRegion.start && 
        absolutePosition <= selectedRegion.end;
      
      // Check if this position has annotations
      const annotation = annotations.find(ann => 
        absolutePosition >= ann.start_position && 
        absolutePosition <= ann.end_position
      );
      
      // Check if this position is in search results
      const isSearchMatch = searchResults.some(result =>
        absolutePosition >= result.start && absolutePosition < result.end
      );

      const baseClass = `sequence-base base-${base.toLowerCase()} ${
        isSelected ? 'selected' : ''
      } ${annotation ? 'annotated' : ''} ${isSearchMatch ? 'search-match' : ''}`;

      return (
        <OverlayTrigger
          key={index}
          placement="top"
          overlay={
            <Tooltip>
              Position: {absolutePosition + 1}
              {annotation && <><br/>Feature: {annotation.feature_type}</>}
            </Tooltip>
          }
        >
          <span
            className={baseClass}
            onClick={() => onRegionSelect?.({ start: absolutePosition, end: absolutePosition })}
            style={{ fontSize: `${zoomLevel}em` }}
          >
            {base}
          </span>
        </OverlayTrigger>
      );
    });
  };

  // Export sequence data
  const handleExport = () => {
    const fastaContent = `>${sequence.name || 'sequence'}\n${sequenceData}`;
    const blob = new Blob([fastaContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sequence.name || 'sequence'}.fasta`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card className="sequence-viewer-card">
      <Card.Header>
        <Row className="align-items-center">
          <Col md={6}>
            <h5 className="mb-0">{sequence?.name || 'Sequence'}</h5>
            <small className="text-muted">
              Length: {sequenceLength} bp | 
              GC Content: {sequence?.gc_content?.toFixed(1)}%
            </small>
          </Col>
          <Col md={6}>
            <div className="d-flex gap-2 justify-content-end">
              <Form.Control
                type="text"
                placeholder="Search sequence..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                style={{ width: '200px' }}
              />
              <Button variant="outline-primary" size="sm" onClick={handleSearch}>
                <BsSearch />
              </Button>
              <Button variant="outline-secondary" size="sm" onClick={() => handleZoom('in')}>
                <BsZoomIn />
              </Button>
              <Button variant="outline-secondary" size="sm" onClick={() => handleZoom('out')}>
                <BsZoomOut />
              </Button>
              <Button variant="outline-success" size="sm" onClick={handleExport}>
                <BsDownload />
              </Button>
            </div>
          </Col>
        </Row>
      </Card.Header>
      
      <Card.Body>
        <div className="sequence-controls mb-3">
          <Badge variant="info">
            Position: {viewportStart + 1} - {viewportEnd} / {sequenceLength}
          </Badge>
          <Badge variant="secondary" className="ms-2">
            Zoom: {Math.round(zoomLevel * 100)}%
          </Badge>
          {searchResults.length > 0 && (
            <Badge variant="warning" className="ms-2">
              Found: {searchResults.length} matches
            </Badge>
          )}
        </div>
        
        <div 
          ref={containerRef}
          className="sequence-display"
          onScroll={handleScroll}
          style={{ 
            height: height,
            overflowX: 'auto',
            overflowY: 'auto',
            fontFamily: 'monospace',
            border: '1px solid #dee2e6',
            padding: '10px',
            backgroundColor: '#f8f9fa'
          }}
        >
          <div className="sequence-content">
            {renderSequenceWithColors()}
          </div>
        </div>
        
        {annotations.length > 0 && (
          <div className="mt-3">
            <h6>Annotations</h6>
            <div className="d-flex flex-wrap gap-2">
              {annotations.map((ann, index) => (
                <Badge 
                  key={index}
                  variant="outline-primary"
                  className="cursor-pointer"
                  onClick={() => onRegionSelect?.({
                    start: ann.start_position,
                    end: ann.end_position
                  })}
                >
                  {ann.feature_type} ({ann.start_position}-{ann.end_position})
                </Badge>
              ))}
            </div>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

// Add CSS styles
const sequenceViewerStyles = `
.sequence-base {
  cursor: pointer;
  padding: 2px;
  border-radius: 2px;
  transition: all 0.2s ease;
}

.sequence-base:hover {
  background-color: #e9ecef;
}

.sequence-base.selected {
  background-color: #007bff;
  color: white;
}

.sequence-base.annotated {
  background-color: #ffc107;
  color: #212529;
}

.sequence-base.search-match {
  background-color: #dc3545;
  color: white;
}

.base-a { color: #ff6b6b; }
.base-t { color: #4ecdc4; }
.base-c { color: #45b7d1; }
.base-g { color: #96ceb4; }

.sequence-viewer-card {
  margin-bottom: 20px;
}

.cursor-pointer {
  cursor: pointer;
}
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style');
  styleElement.textContent = sequenceViewerStyles;
  document.head.appendChild(styleElement);
}

export default SequenceViewer;