// frontend/src/components/visualizations/SequenceAlignmentViewer.js
import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Card, Form, Button, Badge, ProgressBar } from 'react-bootstrap';
import { BsZoomIn, BsZoomOut, BsPalette, BsDownload } from 'react-icons/bs';

const SequenceAlignmentViewer = ({ 
  alignmentData, 
  width = 800, 
  height = 400,
  showConsensus = true,
  colorScheme = 'nucleotide'
}) => {
  const canvasRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [scrollPosition, setScrollPosition] = useState({ x: 0, y: 0 });
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [hoveredPosition, setHoveredPosition] = useState(null);

  // Color schemes for different sequence types
  const colorSchemes = {
    nucleotide: {
      A: '#ff6b6b', T: '#4ecdc4', U: '#4ecdc4', 
      C: '#45b7d1', G: '#96ceb4', N: '#ddd', '-': '#f8f9fa'
    },
    protein: {
      A: '#c8c8c8', R: '#145aff', N: '#00dcdc', D: '#e60a0a',
      C: '#e6e600', Q: '#00dcdc', E: '#e60a0a', G: '#ebebeb',
      H: '#8282d2', I: '#0f820f', L: '#0f820f', K: '#145aff',
      M: '#e6e600', F: '#3232aa', P: '#dc9682', S: '#fa9600',
      T: '#fa9600', W: '#b45ab4', Y: '#3232aa', V: '#0f820f',
      '-': '#f8f9fa'
    },
    conservation: (conservation) => {
      const intensity = Math.floor(conservation * 255);
      return `rgb(${255-intensity}, ${255-intensity}, ${intensity})`;
    }
  };

  // Calculate conservation scores
  const conservationScores = useMemo(() => {
    if (!alignmentData?.aligned_sequences) return [];
    
    const sequences = alignmentData.aligned_sequences;
    const alignmentLength = sequences[0]?.sequence?.length || 0;
    const scores = [];
    
    for (let pos = 0; pos < alignmentLength; pos++) {
      const column = sequences.map(seq => seq.sequence[pos]).filter(char => char !== '-');
      const unique = new Set(column);
      const conservation = unique.size === 1 ? 1 : 1 - (unique.size - 1) / column.length;
      scores.push(conservation);
    }
    
    return scores;
  }, [alignmentData]);

  // Render alignment on canvas
  useEffect(() => {
    if (!alignmentData?.aligned_sequences || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const sequences = alignmentData.aligned_sequences;
    
    // Set canvas size
    canvas.width = width;
    canvas.height = height;
    
    // Clear canvas
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, width, height);
    
    // Calculate dimensions
    const charWidth = 12 * zoom;
    const charHeight = 16 * zoom;
    const maxSeqsVisible = Math.floor((height - 40) / charHeight);
    const maxCharsVisible = Math.floor((width - 100) / charWidth);
    
    // Calculate visible region
    const startSeq = Math.floor(scrollPosition.y / charHeight);
    const endSeq = Math.min(sequences.length, startSeq + maxSeqsVisible);
    const startPos = Math.floor(scrollPosition.x / charWidth);
    const endPos = Math.min(sequences[0].sequence.length, startPos + maxCharsVisible);
    
    // Draw sequence names
    ctx.fillStyle = '#333';
    ctx.font = `${10 * zoom}px monospace`;
    for (let i = startSeq; i < endSeq; i++) {
      const y = (i - startSeq) * charHeight + charHeight - 2;
      const name = sequences[i].id.substring(0, 12);
      ctx.fillText(name, 5, y);
    }
    
    // Draw sequences
    ctx.font = `${12 * zoom}px monospace`;
    for (let seqIdx = startSeq; seqIdx < endSeq; seqIdx++) {
      const sequence = sequences[seqIdx].sequence;
      const y = (seqIdx - startSeq) * charHeight + charHeight - 2;
      
      for (let pos = startPos; pos < endPos; pos++) {
        const char = sequence[pos] || '';
        const x = 100 + (pos - startPos) * charWidth;
        
        // Background color based on color scheme
        if (colorScheme === 'conservation') {
          ctx.fillStyle = colorSchemes.conservation(conservationScores[pos] || 0);
        } else {
          ctx.fillStyle = colorSchemes[colorScheme][char.toUpperCase()] || '#fff';
        }
        
        ctx.fillRect(x, y - charHeight + 2, charWidth, charHeight);
        
        // Highlight selected/hovered position
        if (selectedPosition === pos || hoveredPosition === pos) {
          ctx.strokeStyle = selectedPosition === pos ? '#ff6b6b' : '#ffa726';
          ctx.lineWidth = 2;
          ctx.strokeRect(x, y - charHeight + 2, charWidth, charHeight);
        }
        
        // Draw character
        ctx.fillStyle = '#333';
        ctx.fillText(char, x + 2, y);
      }
    }
    
    // Draw position numbers
    ctx.fillStyle = '#666';
    ctx.font = `${8 * zoom}px monospace`;
    for (let pos = startPos; pos < endPos; pos += 10) {
      const x = 100 + (pos - startPos) * charWidth;
      ctx.fillText(pos + 1, x, 12);
    }
    
    // Draw consensus sequence if enabled
    if (showConsensus && sequences.length > 0) {
      const consensusY = height - 20;
      ctx.fillStyle = '#333';
      ctx.font = `${10 * zoom}px monospace`;
      
      for (let pos = startPos; pos < endPos; pos++) {
        const column = sequences.map(seq => seq.sequence[pos]);
        const counts = {};
        column.forEach(char => {
          if (char !== '-') {
            counts[char] = (counts[char] || 0) + 1;
          }
        });
        
        const consensus = Object.entries(counts)
          .sort((a, b) => b[1] - a[1])[0]?.[0] || '-';
        
        const x = 100 + (pos - startPos) * charWidth;
        ctx.fillText(consensus, x + 2, consensusY);
      }
    }
    
  }, [alignmentData, width, height, zoom, scrollPosition, selectedPosition, hoveredPosition, colorScheme, showConsensus, conservationScores]);

  const handleCanvasClick = (event) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    const charWidth = 12 * zoom;
    const pos = Math.floor((x - 100 + scrollPosition.x) / charWidth);
    
    if (pos >= 0 && pos < alignmentData?.aligned_sequences[0]?.sequence.length) {
      setSelectedPosition(pos);
    }
  };

  const handleCanvasMouseMove = (event) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left;
    
    const charWidth = 12 * zoom;
    const pos = Math.floor((x - 100 + scrollPosition.x) / charWidth);
    
    if (pos >= 0 && pos < alignmentData?.aligned_sequences[0]?.sequence.length) {
      setHoveredPosition(pos);
    } else {
      setHoveredPosition(null);
    }
  };

  const exportAlignment = () => {
    if (!alignmentData?.aligned_sequences) return;
    
    let fastaContent = '';
    alignmentData.aligned_sequences.forEach(seq => {
      fastaContent += `>${seq.id}\n${seq.sequence}\n`;
    });
    
    const blob = new Blob([fastaContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'alignment.fasta';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!alignmentData?.aligned_sequences) {
    return (
      <Card>
        <Card.Body className="text-center">
          <p className="text-muted">No alignment data available</p>
        </Card.Body>
      </Card>
    );
  }

  const alignmentStats = alignmentData.alignment_stats || {};

  return (
    <Card>
      <Card.Header>
        <div className="d-flex justify-content-between align-items-center">
          <div>
            <h6 className="mb-0">Multiple Sequence Alignment</h6>
            <div className="mt-1">
              <Badge variant="info" className="me-2">
                {alignmentData.aligned_sequences.length} sequences
              </Badge>
              <Badge variant="secondary" className="me-2">
                {alignmentData.aligned_sequences[0]?.sequence.length} positions
              </Badge>
              {alignmentStats.average_conservation && (
                <Badge variant="success">
                  {(alignmentStats.average_conservation * 100).toFixed(1)}% conserved
                </Badge>
              )}
            </div>
          </div>
          
          <div className="d-flex gap-2">
            <Form.Select 
              size="sm" 
              value={colorScheme}
              onChange={(e) => setColorScheme(e.target.value)}
            >
              <option value="nucleotide">Nucleotide</option>
              <option value="protein">Protein</option>
              <option value="conservation">Conservation</option>
            </Form.Select>
            
            <Button 
              variant="outline-secondary" 
              size="sm"
              onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}
            >
              <BsZoomOut />
            </Button>
            <Button 
              variant="outline-secondary" 
              size="sm"
              onClick={() => setZoom(Math.min(3, zoom + 0.25))}
            >
              <BsZoomIn />
            </Button>
            <Button variant="outline-primary" size="sm" onClick={exportAlignment}>
              <BsDownload />
            </Button>
          </div>
        </div>
      </Card.Header>
      
      <Card.Body className="p-0">
        <div style={{ position: 'relative', overflow: 'hidden' }}>
          <canvas
            ref={canvasRef}
            width={width}
            height={height}
            onClick={handleCanvasClick}
            onMouseMove={handleCanvasMouseMove}
            onMouseLeave={() => setHoveredPosition(null)}
            style={{ cursor: 'crosshair', border: '1px solid #dee2e6' }}
          />
        </div>
        
        {selectedPosition !== null && (
          <div className="p-3 border-top">
            <h6>Position {selectedPosition + 1}</h6>
            <div className="row">
              <div className="col-md-6">
                <strong>Conservation:</strong> {(conservationScores[selectedPosition] * 100).toFixed(1)}%
              </div>
              <div className="col-md-6">
                <strong>Column:</strong> 
                {alignmentData.aligned_sequences.map((seq, idx) => (
                  <Badge 
                    key={idx} 
                    variant="outline-secondary" 
                    className="ms-1"
                  >
                    {seq.sequence[selectedPosition]}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        )}
        
        {alignmentStats.gap_percentage && (
          <div className="p-3 border-top">
            <div className="row">
              <div className="col-md-4">
                <small className="text-muted">Gap Percentage</small>
                <ProgressBar 
                  now={alignmentStats.gap_percentage} 
                  label={`${alignmentStats.gap_percentage.toFixed(1)}%`}
                  variant="warning"
                />
              </div>
              <div className="col-md-4">
                <small className="text-muted">Average Conservation</small>
                <ProgressBar 
                  now={alignmentStats.average_conservation * 100} 
                  label={`${(alignmentStats.average_conservation * 100).toFixed(1)}%`}
                  variant="success"
                />
              </div>
              <div className="col-md-4">
                <small className="text-muted">Alignment Quality</small>
                <ProgressBar 
                  now={(1 - alignmentStats.gap_percentage / 100) * alignmentStats.average_conservation * 100} 
                  label="Good"
                  variant="info"
                />
              </div>
            </div>
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default SequenceAlignmentViewer;
