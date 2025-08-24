// frontend/src/components/visualizations/GenomeViewer.js
import React, { useRef, useEffect, useState } from 'react';
import { Card, Form, Button, Badge, Modal, Table } from 'react-bootstrap';
import { BsZoomIn, BsZoomOut, BsSearch, BsInfo } from 'react-icons/bs';
import * as d3 from 'd3';

const GenomeViewer = ({ 
  genomeData, 
  annotations = [], 
  width = 1000, 
  height = 200,
  onFeatureSelect = () => {} 
}) => {
  const svgRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [viewStart, setViewStart] = useState(0);
  const [viewEnd, setViewEnd] = useState(10000);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [showFeatureModal, setShowFeatureModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [tracks, setTracks] = useState({
    genes: true,
    cds: true,
    exons: true,
    repeats: false
  });

  const genomeLength = genomeData?.length || 100000;
  const viewWindow = viewEnd - viewStart;

  // Feature type colors
  const featureColors = {
    gene: '#4CAF50',
    CDS: '#2196F3',
    exon: '#FF9800',
    intron: '#9C27B0',
    repeat: '#F44336',
    tRNA: '#00BCD4',
    rRNA: '#3F51B5'
  };

  const renderGenome = () => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 20, right: 50, bottom: 60, left: 50 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left}, ${margin.top})`);

    // Scale for genomic coordinates
    const xScale = d3.scaleLinear()
      .domain([viewStart, viewEnd])
      .range([0, innerWidth]);

    // Add axis
    const xAxis = d3.axisBottom(xScale)
      .tickFormat(d3.format('~s'));
    
    g.append('g')
      .attr('transform', `translate(0, ${innerHeight})`)
      .call(xAxis)
      .append('text')
      .attr('x', innerWidth / 2)
      .attr('y', 35)
      .attr('fill', '#333')
      .style('text-anchor', 'middle')
      .text('Genomic Position (bp)');

    // Draw genome backbone
    g.append('line')
      .attr('x1', 0)
      .attr('x2', innerWidth)
      .attr('y1', innerHeight / 2)
      .attr('y2', innerHeight / 2)
      .style('stroke', '#333')
      .style('stroke-width', 3);

    // Filter annotations to visible region
    const visibleAnnotations = annotations.filter(ann => 
      ann.end >= viewStart && ann.start <= viewEnd &&
      tracks[ann.type.toLowerCase()]
    );

    // Group annotations by track
    const trackGroups = d3.group(visibleAnnotations, d => d.type);
    const trackHeight = 20;
    let trackY = innerHeight / 2 - 40;

    trackGroups.forEach((features, featureType) => {
      // Draw track label
      g.append('text')
        .attr('x', -10)
        .attr('y', trackY + trackHeight / 2)
        .attr('dy', '0.35em')
        .style('text-anchor', 'end')
        .style('font-size', '12px')
        .style('fill', '#666')
        .text(featureType);

      // Draw features
      const featureSelection = g.selectAll(`.feature-${featureType}`)
        .data(features)
        .enter()
        .append('g')
        .attr('class', `feature-${featureType}`)
        .style('cursor', 'pointer');

      featureSelection.append('rect')
        .attr('x', d => xScale(Math.max(d.start, viewStart)))
        .attr('y', trackY)
        .attr('width', d => Math.max(2, xScale(Math.min(d.end, viewEnd)) - xScale(Math.max(d.start, viewStart))))
        .attr('height', trackHeight - 2)
        .attr('fill', featureColors[featureType] || '#666')
        .attr('opacity', 0.8)
        .on('click', (event, d) => {
          setSelectedFeature(d);
          setShowFeatureModal(true);
          onFeatureSelect(d);
        })
        .on('mouseover', function(event, d) {
          d3.select(this).attr('opacity', 1);
          
          // Show tooltip
          const tooltip = d3.select('body').append('div')
            .attr('class', 'genome-tooltip')
            .style('opacity', 0)
            .style('position', 'absolute')
            .style('background', 'rgba(0,0,0,0.8)')
            .style('color', 'white')
            .style('padding', '8px')
            .style('border-radius', '4px')
            .style('font-size', '12px')
            .style('pointer-events', 'none');

          tooltip.transition()
            .duration(200)
            .style('opacity', 0.9);

          tooltip.html(`
            <strong>${d.type}: ${d.attributes?.Name || d.attributes?.ID || 'Unknown'}</strong><br/>
            Position: ${d.start.toLocaleString()} - ${d.end.toLocaleString()}<br/>
            Length: ${(d.end - d.start + 1).toLocaleString()} bp<br/>
            Strand: ${d.strand}
          `)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function(event, d) {
          d3.select(this).attr('opacity', 0.8);
          d3.selectAll('.genome-tooltip').remove();
        });

      // Add strand indicators for genes
      if (featureType === 'gene') {
        featureSelection.append('polygon')
          .attr('points', d => {
            const x = xScale(d.strand === '+' ? d.end : d.start);
            const y = trackY + trackHeight / 2;
            const size = 4;
            
            if (d.strand === '+') {
              return `${x},${y} ${x-size},${y-size} ${x-size},${y+size}`;
            } else {
              return `${x},${y} ${x+size},${y-size} ${x+size},${y+size}`;
            }
          })
          .attr('fill', '#333')
          .attr('opacity', 0.7);
      }

      trackY -= 25;
    });

    // Add zoom behavior
    const zoomBehavior = d3.zoom()
      .scaleExtent([0.1, 100])
      .on('zoom', (event) => {
        const newXScale = event.transform.rescaleX(xScale);
        const [newStart, newEnd] = newXScale.domain();
        
        setViewStart(Math.max(0, newStart));
        setViewEnd(Math.min(genomeLength, newEnd));
      });

    svg.call(zoomBehavior);
  };

  useEffect(() => {
    renderGenome();
  }, [genomeData, annotations, viewStart, viewEnd, tracks, width, height]);

  const handleSearch = () => {
    if (!searchQuery) return;
    
    // Find features matching search query
    const matchingFeatures = annotations.filter(ann => 
      ann.attributes?.Name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ann.attributes?.ID?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ann.type.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (matchingFeatures.length > 0) {
      const feature = matchingFeatures[0];
      const center = (feature.start + feature.end) / 2;
      const window = Math.max(10000, feature.end - feature.start + 5000);
      
      setViewStart(Math.max(0, center - window / 2));
      setViewEnd(Math.min(genomeLength, center + window / 2));
      setSelectedFeature(feature);
    }
  };

  const zoomToFeature = (feature) => {
    const center = (feature.start + feature.end) / 2;
    const window = Math.max(1000, (feature.end - feature.start) * 5);
    
    setViewStart(Math.max(0, center - window / 2));
    setViewEnd(Math.min(genomeLength, center + window / 2));
  };

  return (
    <Card>
      <Card.Header>
        <div className="d-flex justify-content-between align-items-center">
          <div>
            <h6 className="mb-0">Genome Browser</h6>
            <small className="text-muted">
              {genomeData?.name || 'Genome'} • 
              Showing {viewStart.toLocaleString()} - {viewEnd.toLocaleString()} bp 
              ({((viewEnd - viewStart) / 1000).toFixed(1)} kb)
            </small>
          </div>
          
          <div className="d-flex gap-2 align-items-center">
            <Form.Control
              type="text"
              placeholder="Search features..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              size="sm"
              style={{ width: '200px' }}
            />
            <Button variant="outline-primary" size="sm" onClick={handleSearch}>
              <BsSearch />
            </Button>
            
            <Button 
              variant="outline-secondary" 
              size="sm"
              onClick={() => {
                const center = (viewStart + viewEnd) / 2;
                const newWindow = (viewEnd - viewStart) / 2;
                setViewStart(Math.max(0, center - newWindow / 2));
                setViewEnd(Math.min(genomeLength, center + newWindow / 2));
              }}
            >
              <BsZoomIn />
            </Button>
            <Button 
              variant="outline-secondary" 
              size="sm"
              onClick={() => {
                const center = (viewStart + viewEnd) / 2;
                const newWindow = Math.min(genomeLength, (viewEnd - viewStart) * 2);
                setViewStart(Math.max(0, center - newWindow / 2));
                setViewEnd(Math.min(genomeLength, center + newWindow / 2));
              }}
            >
              <BsZoomOut />
            </Button>
          </div>
        </div>
        
        {/* Track toggles */}
        <div className="mt-2">
          {Object.entries(tracks).map(([track, visible]) => (
            <Form.Check
              key={track}
              inline
              type="switch"
              id={`track-${track}`}
              label={track.charAt(0).toUpperCase() + track.slice(1)}
              checked={visible}
              onChange={(e) => setTracks(prev => ({ ...prev, [track]: e.target.checked }))}
            />
          ))}
        </div>
      </Card.Header>
      
      <Card.Body className="p-0">
        <svg
          ref={svgRef}
          width={width}
          height={height + 100}
          style={{ border: '1px solid #dee2e6' }}
        />
        
        {/* Navigation controls */}
        <div className="p-3 border-top">
          <div className="d-flex justify-content-between align-items-center">
            <div className="btn-group" role="group">
              <Button 
                variant="outline-secondary" 
                size="sm"
                onClick={() => {
                  const window = viewEnd - viewStart;
                  setViewStart(Math.max(0, viewStart - window));
                  setViewEnd(Math.max(window, viewEnd - window));
                }}
              >
                ← Left
              </Button>
              <Button 
                variant="outline-secondary" 
                size="sm"
                onClick={() => {
                  const window = viewEnd - viewStart;
                  setViewStart(Math.min(genomeLength - window, viewStart + window));
                  setViewEnd(Math.min(genomeLength, viewEnd + window));
                }}
              >
                Right →
              </Button>
            </div>
            
            <div className="d-flex gap-2">
              <Badge variant="primary">
                {annotations.filter(a => a.start >= viewStart && a.end <= viewEnd).length} features visible
              </Badge>
              <Badge variant="secondary">
                {(viewWindow / genomeLength * 100).toFixed(2)}% of genome
              </Badge>
            </div>
          </div>
        </div>
      </Card.Body>
      
      {/* Feature details modal */}
      <Modal show={showFeatureModal} onHide={() => setShowFeatureModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            <BsInfo className="me-2" />
            Feature Details
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedFeature && (
            <div>
              <Table bordered>
                <tbody>
                  <tr>
                    <td><strong>Type</strong></td>
                    <td><Badge variant="primary">{selectedFeature.type}</Badge></td>
                  </tr>
                  <tr>
                    <td><strong>Position</strong></td>
                    <td>{selectedFeature.start.toLocaleString()} - {selectedFeature.end.toLocaleString()}</td>
                  </tr>
                  <tr>
                    <td><strong>Length</strong></td>
                    <td>{(selectedFeature.end - selectedFeature.start + 1).toLocaleString()} bp</td>
                  </tr>
                  <tr>
                    <td><strong>Strand</strong></td>
                    <td>{selectedFeature.strand === '+' ? 'Forward (+)' : 'Reverse (-)'}</td>
                  </tr>
                  {selectedFeature.score && (
                    <tr>
                      <td><strong>Score</strong></td>
                      <td>{selectedFeature.score}</td>
                    </tr>
                  )}
                </tbody>
              </Table>
              
              {selectedFeature.attributes && Object.keys(selectedFeature.attributes).length > 0 && (
                <div>
                  <h6>Attributes</h6>
                  <Table size="sm">
                    <tbody>
                      {Object.entries(selectedFeature.attributes).map(([key, value]) => (
                        <tr key={key}>
                          <td><strong>{key}</strong></td>
                          <td>{value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              )}
              
              <div className="mt-3">
                <Button 
                  variant="primary"
                  onClick={() => {
                    zoomToFeature(selectedFeature);
                    setShowFeatureModal(false);
                  }}
                >
                  Zoom to Feature
                </Button>
              </div>
            </div>
          )}
        </Modal.Body>
      </Modal>
    </Card>
  );
};

export default GenomeViewer;