// frontend/src/components/visualizations/PhylogeneticTreeViewer.js
import React, { useRef, useEffect, useState } from 'react';
import { Card, Button, Form, Alert, Spinner } from 'react-bootstrap';
import * as d3 from 'd3';
import { BsDownload, BsZoomIn, BsZoomOut, BsArrowsMove } from 'react-icons/bs';

const PhylogeneticTreeViewer = ({ 
  treeData, 
  width = 800, 
  height = 600,
  onNodeSelect = () => {},
  interactive = true 
}) => {
  const svgRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [treeLayout, setTreeLayout] = useState('rectangular');
  const [showBootstrap, setShowBootstrap] = useState(true);
  const [loading, setLoading] = useState(false);

  // Parse Newick format tree
  const parseNewick = (newick) => {
    const tokens = newick.split(/\s*([();,])\s*/);
    let index = 0;

    const parseNode = () => {
      const node = { name: '', length: 0, children: [] };
      
      if (tokens[index] === '(') {
        index++; // skip '('
        node.children.push(parseNode());
        
        while (tokens[index] === ',') {
          index++; // skip ','
          node.children.push(parseNode());
        }
        
        if (tokens[index] === ')') {
          index++; // skip ')'
        }
      }
      
      // Get node name
      if (tokens[index] && tokens[index] !== ';' && tokens[index] !== ',' && tokens[index] !== ')') {
        const nameAndLength = tokens[index].split(':');
        node.name = nameAndLength[0] || '';
        node.length = parseFloat(nameAndLength[1]) || 0;
        index++;
      }
      
      return node;
    };

    return parseNode();
  };

  // Create tree layout
  const createTreeLayout = (data) => {
    const hierarchy = d3.hierarchy(data);
    
    if (treeLayout === 'rectangular') {
      const treeGenerator = d3.tree().size([height - 100, width - 200]);
      return treeGenerator(hierarchy);
    } else {
      const treeGenerator = d3.tree().size([2 * Math.PI, Math.min(width, height) / 2 - 100]);
      const tree = treeGenerator(hierarchy);
      
      // Convert to radial coordinates
      tree.descendants().forEach(d => {
        const angle = d.x;
        const radius = d.y;
        d.x = radius * Math.cos(angle - Math.PI / 2);
        d.y = radius * Math.sin(angle - Math.PI / 2);
      });
      
      return tree;
    }
  };

  // Render tree using D3
  useEffect(() => {
    if (!treeData || !svgRef.current) return;

    setLoading(true);
    
    try {
      // Parse tree data if it's in Newick format
      let parsedData = treeData;
      if (typeof treeData === 'string') {
        parsedData = parseNewick(treeData);
      }

      const svg = d3.select(svgRef.current);
      svg.selectAll('*').remove();

      const g = svg.append('g')
        .attr('transform', `translate(${width / 2}, ${height / 2})`);

      const tree = createTreeLayout(parsedData);
      const nodes = tree.descendants();
      const links = tree.links();

      // Add zoom behavior
      const zoomBehavior = d3.zoom()
        .scaleExtent([0.1, 3])
        .on('zoom', (event) => {
          g.attr('transform', event.transform);
        });

      if (interactive) {
        svg.call(zoomBehavior);
      }

      // Draw links
      const link = g.selectAll('.link')
        .data(links)
        .enter()
        .append('path')
        .attr('class', 'link')
        .attr('d', d3.linkHorizontal()
          .x(d => d.y)
          .y(d => d.x))
        .style('fill', 'none')
        .style('stroke', '#ccc')
        .style('stroke-width', 2);

      // Draw nodes
      const node = g.selectAll('.node')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', 'node')
        .attr('transform', d => `translate(${d.y},${d.x})`);

      // Add circles for nodes
      node.append('circle')
        .attr('r', d => d.children ? 6 : 4)
        .style('fill', d => {
          if (selectedNode && selectedNode.data.name === d.data.name) return '#ff6b6b';
          return d.children ? '#4ecdc4' : '#45b7d1';
        })
        .style('stroke', '#fff')
        .style('stroke-width', 2)
        .style('cursor', interactive ? 'pointer' : 'default')
        .on('click', (event, d) => {
          if (interactive) {
            setSelectedNode(d);
            onNodeSelect(d);
            
            // Update node colors
            node.selectAll('circle')
              .style('fill', n => {
                if (n.data.name === d.data.name) return '#ff6b6b';
                return n.children ? '#4ecdc4' : '#45b7d1';
              });
          }
        })
        .on('mouseover', function(event, d) {
          if (interactive) {
            d3.select(this).style('stroke', '#333').style('stroke-width', 3);
            
            // Show tooltip
            const tooltip = d3.select('body').append('div')
              .attr('class', 'tree-tooltip')
              .style('opacity', 0)
              .style('position', 'absolute')
              .style('background', 'rgba(0,0,0,0.8)')
              .style('color', 'white')
              .style('padding', '8px')
              .style('border-radius', '4px')
              .style('font-size', '12px');

            tooltip.transition()
              .duration(200)
              .style('opacity', 0.9);

            tooltip.html(`
              <strong>${d.data.name || 'Internal Node'}</strong><br/>
              ${d.data.length ? `Length: ${d.data.length.toFixed(4)}` : ''}
              ${d.data.bootstrap ? `<br/>Bootstrap: ${d.data.bootstrap}` : ''}
            `)
              .style('left', (event.pageX + 10) + 'px')
              .style('top', (event.pageY - 28) + 'px');
          }
        })
        .on('mouseout', function(event, d) {
          if (interactive) {
            d3.select(this).style('stroke', '#fff').style('stroke-width', 2);
            d3.selectAll('.tree-tooltip').remove();
          }
        });

      // Add labels
      node.append('text')
        .attr('dy', '0.31em')
        .attr('x', d => d.children ? -12 : 12)
        .style('text-anchor', d => d.children ? 'end' : 'start')
        .style('font-size', '11px')
        .style('font-family', 'Arial, sans-serif')
        .text(d => d.data.name || '')
        .style('fill', '#333');

      // Add bootstrap values if available and enabled
      if (showBootstrap) {
        node.filter(d => d.data.bootstrap)
          .append('text')
          .attr('dy', '-0.5em')
          .attr('x', 0)
          .style('text-anchor', 'middle')
          .style('font-size', '9px')
          .style('font-family', 'Arial, sans-serif')
          .style('fill', '#666')
          .text(d => d.data.bootstrap);
      }

      // Add scale bar
      if (nodes.some(d => d.data.length > 0)) {
        const maxLength = d3.max(nodes, d => d.data.length);
        const scaleLength = Math.pow(10, Math.floor(Math.log10(maxLength)));
        const scalePixels = (scaleLength / maxLength) * (width - 200);

        const scale = g.append('g')
          .attr('class', 'scale-bar')
          .attr('transform', `translate(${-width/2 + 50}, ${height/2 - 50})`);

        scale.append('line')
          .attr('x1', 0)
          .attr('x2', scalePixels)
          .attr('y1', 0)
          .attr('y2', 0)
          .style('stroke', '#333')
          .style('stroke-width', 2);

        scale.append('text')
          .attr('x', scalePixels / 2)
          .attr('y', -5)
          .style('text-anchor', 'middle')
          .style('font-size', '10px')
          .text(scaleLength);
      }

    } catch (error) {
      console.error('Error rendering tree:', error);
    } finally {
      setLoading(false);
    }
  }, [treeData, width, height, treeLayout, showBootstrap, selectedNode, interactive]);

  const exportTree = () => {
    const svg = svgRef.current;
    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svg);
    const blob = new Blob([svgString], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'phylogenetic_tree.svg';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <Card.Header>
        <div className="d-flex justify-content-between align-items-center">
          <h6 className="mb-0">Phylogenetic Tree</h6>
          <div className="d-flex gap-2">
            <Form.Select 
              size="sm" 
              value={treeLayout}
              onChange={(e) => setTreeLayout(e.target.value)}
            >
              <option value="rectangular">Rectangular</option>
              <option value="radial">Radial</option>
            </Form.Select>
            
            <Form.Check
              type="switch"
              id="bootstrap-switch"
              label="Bootstrap"
              checked={showBootstrap}
              onChange={(e) => setShowBootstrap(e.target.checked)}
              className="small"
            />
            
            <Button variant="outline-primary" size="sm" onClick={exportTree}>
              <BsDownload /> Export
            </Button>
          </div>
        </div>
      </Card.Header>
      
      <Card.Body className="p-0">
        {loading && (
          <div className="text-center p-4">
            <Spinner animation="border" />
            <div className="mt-2">Rendering tree...</div>
          </div>
        )}
        
        <div className="position-relative">
          <svg
            ref={svgRef}
            width={width}
            height={height}
            style={{ border: '1px solid #dee2e6' }}
          />
          
          {interactive && (
            <div className="position-absolute top-0 end-0 p-2">
              <small className="text-muted">
                <BsArrowsMove /> Drag to pan • Scroll to zoom • Click nodes to select
              </small>
            </div>
          )}
        </div>
        
        {selectedNode && (
          <Alert variant="info" className="m-3">
            <strong>Selected Node:</strong> {selectedNode.data.name || 'Internal Node'}
            {selectedNode.data.length && <><br/><strong>Branch Length:</strong> {selectedNode.data.length.toFixed(4)}</>}
            {selectedNode.data.bootstrap && <><br/><strong>Bootstrap Support:</strong> {selectedNode.data.bootstrap}</>}
          </Alert>
        )}
      </Card.Body>
    </Card>
  );
};

export default PhylogeneticTreeViewer;
