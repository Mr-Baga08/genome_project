// frontend/src/components/Genomics.js
import React, { useState, useRef, useEffect } from 'react';
import { BsSearch, BsPlay, BsTrash, BsDownload } from 'react-icons/bs';

import { useAppContext } from '../context/AppContext';
import ToolBar from './ToolBar';
// import HeaderContent from './HeaderContent';
// import FooterContent from './FooterContent';
import RunningProcesses from './RunningProcesses';
import LogViewer from './LogViewer';
import UmapGenomeVisualization from './UmapGenomeVisualization';
import IGVViewer from './IGVViewer';
import JBrowseViewer from './JBrowseViewer';
import NotificationToast from './NotificationToast';
import menuItems from '../data/menuItems';
import elements from '../data/elements';
import samples from '../data/samples';

// Custom Menu Component (Bootstrap 5 styled)
const UgeneMenu = ({ items, closeMenu }) => {
  const UgeneMenuItem = ({ item, closeMenu }) => {
    const liRef = useRef(null);
    const [opensLeft, setOpensLeft] = useState(false);

    const handleMouseEnter = () => {
      if (item.submenu && liRef.current) {
        const rect = liRef.current.getBoundingClientRect();
        const submenuWidth = 200;
        if (rect.right + submenuWidth > window.innerWidth) {
          setOpensLeft(true);
        } else {
          setOpensLeft(false);
        }
      }
    };

    if (item.submenu) {
      return (
        <li className="dropdown-submenu position-relative" ref={liRef} onMouseEnter={handleMouseEnter}>
          <a className="dropdown-item dropdown-toggle d-flex justify-content-between align-items-center" href="#">
            {item.name}
            <i className="bi bi-chevron-right"></i>
          </a>
          <ul className={`dropdown-menu ${opensLeft ? 'dropdown-menu-start' : 'dropdown-menu-end'} border shadow-sm`}>
            {item.submenu.map((subItem, index) => (
              <UgeneMenuItem key={index} item={subItem} closeMenu={closeMenu} />
            ))}
          </ul>
        </li>
      );
    }
    return (
      <li>
        <button
          className="dropdown-item btn btn-link text-start p-2 border-0"
          type="button"
          onClick={() => {
            if (item.action) item.action();
            closeMenu();
          }}
        >
          {item.name}
        </button>
      </li>
    );
  };

  return (
    <ul className="dropdown-menu show shadow border-0 rounded-3" style={{ minWidth: '200px' }}>
      {items.map((item, index) => (
        <UgeneMenuItem key={index} item={item} closeMenu={closeMenu} />
      ))}
    </ul>
  );
};

// Draggable Element Component with Bootstrap 5 styling
const DraggableElement = ({ 
  element, 
  onPositionChange, 
  containerRef, 
  onClick, 
  isSelected, 
  onStartConnection, 
  onEndConnection 
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef(null);
  const offsetRef = useRef({ x: 0, y: 0 });
  const hasDragged = useRef(false);

  const onMouseDown = (e) => {
    if (e.button !== 0) return;
    if (e.target.classList.contains('connection-point')) {
      return;
    }
    if (dragRef.current) {
      setIsDragging(true);
      hasDragged.current = false;
      const rect = dragRef.current.getBoundingClientRect();
      offsetRef.current = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };
    }
    e.stopPropagation();
    e.preventDefault();
  };
  
  const handleMouseUp = () => {
    if (!hasDragged.current) {
      onClick(element);
    }
    setIsDragging(false);
    hasDragged.current = false;
  };

  useEffect(() => {
    const onMouseMove = (e) => {
      if (!isDragging || !dragRef.current || !containerRef.current) return;
      
      hasDragged.current = true;

      const containerRect = containerRef.current.getBoundingClientRect();
      
      let x = e.clientX - containerRect.left - offsetRef.current.x;
      let y = e.clientY - containerRect.top - offsetRef.current.y;

      const elementRect = dragRef.current.getBoundingClientRect();
      x = Math.max(0, Math.min(x, containerRect.width - elementRect.width));
      y = Math.max(0, y);

      onPositionChange(element.id, { x, y });
    };

    const onMouseUpGlobal = () => {
      if(isDragging) {
        setIsDragging(false);
        hasDragged.current = false;
      }
    };

    if (isDragging) {
      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUpGlobal);
    }

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUpGlobal);
    };
  }, [isDragging, element.id, onPositionChange, containerRef]);

  return (
    <div
      ref={dragRef}
      className={`position-absolute user-select-none border rounded-2 bg-white shadow-sm 
                  ${isSelected ? 'border-primary border-2 shadow' : 'border-light'} 
                  ${isDragging ? 'shadow-lg' : ''}`}
      style={{
        left: `${element.x}px`,
        top: `${element.y}px`,
        cursor: isDragging ? 'grabbing' : 'grab',
        width: '180px',
        padding: '0.75rem 1rem',
        transition: isDragging ? 'none' : 'all 0.2s ease',
      }}
      onMouseDown={onMouseDown}
      onMouseUp={handleMouseUp}
    >
      <div 
        className="connection-point position-absolute bg-white border border-2 border-secondary rounded-circle"
        style={{
          width: '12px',
          height: '12px',
          left: '-6px',
          top: '50%',
          transform: 'translateY(-50%)',
          cursor: 'pointer'
        }}
        onMouseUp={() => onEndConnection(element.id, 'input')}
      ></div>
      
      <div className="d-flex justify-content-between align-items-center">
        <div className="text-truncate">
          <span className="fw-medium text-dark small">{element.name}</span>
          {element.properties && (
            <p className="text-muted small mb-0 mt-1">{element.properties}</p>
          )}
        </div>
      </div>
      
      <div 
        className="connection-point position-absolute bg-white border border-2 border-secondary rounded-circle"
        style={{
          width: '12px',
          height: '12px',
          right: '-6px',
          top: '50%',
          transform: 'translateY(-50%)',
          cursor: 'pointer'
        }}
        onMouseDown={(e) => {
          e.stopPropagation();
          onStartConnection(element.id, 'output');
        }}
      ></div>
    </div>
  );
};

const Genomics = () => {
  const { state, actions } = useAppContext();
  const [filter, setFilter] = useState('');
  const [showElements, setShowElements] = useState(true);
  const [expandedElement, setExpandedElement] = useState(null);
  const [activeMenu, setActiveMenu] = useState(null);
  const [isConnecting, setIsConnecting] = useState(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [showJsonModal, setShowJsonModal] = useState(false);
  const [workflowJson, setWorkflowJson] = useState('');
  const [showUmapOverlay, setShowUmapOverlay] = useState(false);
  const [showIgvOverlay, setShowIgvOverlay] = useState(false);
  const [showJbrowseOverlay, setShowJbrowseOverlay] = useState(false);

  const menuRef = useRef(null);
  const canvasRef = useRef(null);

  const { 
    workflowElements, 
    connections, 
    selectedElement, 
    tasks, 
    currentTask, 
    isLoading, 
    notifications 
  } = state;

  const handleRemoveElement = () => {
    if (selectedElement) {
      actions.removeWorkflowElement(selectedElement.id);
      actions.addNotification({
        type: 'info',
        title: 'Element Removed',
        message: `Removed ${selectedElement.name} from workflow`
      });
    } else {
      actions.addNotification({
        type: 'warning',
        title: 'No Selection',
        message: 'Please select an element to remove'
      });
    }
  };

  const handleRunWorkflow = async () => {
    if (workflowElements.length === 0) {
      actions.addNotification({
        type: 'warning',
        title: 'Empty Workflow',
        message: 'Please add elements to your workflow before running'
      });
      return;
    }

    try {
      const taskId = await actions.submitWorkflow('medium');
      actions.addNotification({
        type: 'success',
        title: 'Workflow Submitted',
        message: `Task ${taskId} submitted successfully`
      });
    } catch (error) {
      actions.addNotification({
        type: 'error',
        title: 'Submission Failed',
        message: error.message
      });
    }
  };

  const resetCanvas = () => {
    actions.clearWorkflow();
    actions.addNotification({
      type: 'info',
      title: 'Workflow Cleared',
      message: 'All elements and connections removed'
    });
  };

  const toggleMenu = (menuName) => {
    setActiveMenu(activeMenu === menuName ? null : menuName);
  };
  
  const handleElementClick = (element) => {
    actions.setSelectedElement(element);
    if (element.visualization === 'umap') {
      setShowUmapOverlay(true);
    } else if (element.visualization === 'igv') {
      setShowIgvOverlay(true);
    } else if (element.visualization === 'jbrowse') {
      setShowJbrowseOverlay(true);
    }
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setActiveMenu(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleDragStart = (element) => (e) => {
    e.dataTransfer.setData('application/json', JSON.stringify(element));
  };

  const handleDrop = (event) => {
    event.preventDefault();
    const elementData = JSON.parse(event.dataTransfer.getData('application/json'));
    const canvasRect = canvasRef.current.getBoundingClientRect();

    const x = event.clientX - canvasRect.left;
    const y = event.clientY - canvasRect.top;

    const newElement = {
      ...elementData,
      id: Date.now(),
      x: Math.max(0, x),
      y: Math.max(0, y),
    };

    actions.addWorkflowElement(newElement);
  };
  
  const updateElementPosition = (id, newPosition) => {
    actions.updateWorkflowElement({ id, ...newPosition });
  };
  
  const handleStartConnection = (fromId, fromPoint) => {
    setIsConnecting({ fromId, fromPoint });
  };

  const handleEndConnection = (toId, toPoint) => {
    if (isConnecting && isConnecting.fromId !== toId) {
      const newConnection = { from: isConnecting.fromId, to: toId };
      actions.addConnection(newConnection);
    }
    setIsConnecting(null);
  };
  
  const handleCanvasMouseMove = (e) => {
    if (isConnecting) {
      const canvasRect = canvasRef.current.getBoundingClientRect();
      setMousePosition({
        x: e.clientX - canvasRect.left,
        y: e.clientY - canvasRect.top,
      });
    }
  };
  
  const handleCanvasMouseUp = () => {
    setIsConnecting(null);
  };
  
  const handleGenerateJson = () => {
    const workflow = {
      nodes: workflowElements.map(el => ({
        id: el.id,
        name: el.name,
        type: el.type,
        position: { x: el.x, y: el.y }
      })),
      connections: connections,
    };
    setWorkflowJson(JSON.stringify(workflow, null, 2));
    setShowJsonModal(true);
  };

  const toggleExpand = (elementName) => {
    setExpandedElement((prev) => (prev === elementName ? null : elementName));
  };

  const renderSubElements = (subElements) =>
    subElements.map((subEl) => (
      <div
        key={subEl.name}
        className="list-group-item list-group-item-action py-2 px-3 border-0 bg-light"
        style={{ cursor: 'grab' }}
        draggable
        onDragStart={handleDragStart(subEl)}
      >
        <small className="text-muted">{subEl.name}</small>
      </div>
    ));

  const renderElements = (items) =>
    items
      .filter((el) => el.name.toLowerCase().includes(filter.toLowerCase()))
      .map((el) => (
        <div key={el.name} className="mb-2">
          <div
            className="list-group-item list-group-item-action rounded-2 border"
            onClick={() => toggleExpand(el.name)}
            style={{ cursor: 'pointer' }}
          >
            <div className="d-flex w-100 justify-content-between align-items-center">
              <h6 className="mb-0 fw-medium text-dark">{el.name}</h6>
              <i className={`bi ${expandedElement === el.name ? 'bi-chevron-down' : 'bi-chevron-right'}`}></i>
            </div>
          </div>
          {expandedElement === el.name && (
            <div className="list-group mt-1">
              {renderSubElements(el.subElements)}
            </div>
          )}
        </div>
      ));

  return (
    <div className="d-flex flex-column vh-100 bg-light">
      {/* <header className="bg-white shadow-sm">
        <HeaderContent />
      </header> */}
      
      <main className="flex-grow-1 overflow-hidden">
        <div className="container-fluid h-100 py-3">
          <div className="row h-100 g-3">
            {/* Left Panel */}
            <div className="col-lg-2 col-md-3">
              <div className="card h-100 border-0 shadow-sm">
                <div className="card-body d-flex flex-column">
                  <ToolBar 
                    onRemoveElement={handleRemoveElement} 
                    onGenerateJson={handleGenerateJson}
                    onRunWorkflow={handleRunWorkflow}
                  />
                  
                  <div className="btn-group d-grid gap-1 mt-3" role="group">
                    <button
                      type="button"
                      className={`btn ${showElements ? 'btn-primary' : 'btn-outline-primary'}`}
                      onClick={() => {
                        setShowElements(true);
                        resetCanvas();
                      }}
                    >
                      Elements
                    </button>
                    <button
                      type="button"
                      className={`btn ${!showElements ? 'btn-primary' : 'btn-outline-primary'}`}
                      onClick={() => {
                        setShowElements(false);
                        resetCanvas();
                      }}
                    >
                      Samples
                    </button>
                  </div>
                  
                  <div className="input-group input-group-sm mt-3">
                    <span className="input-group-text bg-white">
                      <BsSearch className="text-muted" />
                    </span>
                    <input
                      type="text"
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                      className="form-control border-start-0"
                      placeholder="Search..."
                    />
                  </div>
                  
                  <div className="flex-grow-1 mt-3 overflow-auto">
                    {showElements ? renderElements(elements) : renderElements(samples)}
                  </div>
                </div>
              </div>
            </div>

            {/* Center Canvas */}
            <div className="col-lg-7 col-md-6">
              <div className="card h-100 border-0 shadow-sm">
                <div
                  className="card-body position-relative overflow-auto"
                  style={{
                    backgroundImage: `radial-gradient(circle, #e9ecef 1px, transparent 1px)`,
                    backgroundSize: '20px 20px',
                    minHeight: '500px'
                  }}
                  ref={canvasRef}
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  onClick={(e) => {
                    if (e.target === canvasRef.current) {
                      actions.setSelectedElement(null);
                    }
                  }}
                  onMouseMove={handleCanvasMouseMove}
                  onMouseUp={handleCanvasMouseUp}
                >
                  {/* SVG for connections */}
                  <svg className="position-absolute w-100 h-100" style={{ pointerEvents: 'none' }}>
                    <defs>
                      <marker id="arrowhead" markerWidth="6" markerHeight="4" refX="6" refY="2" orient="auto">
                        <polygon points="0 0, 6 2, 0 4" fill="#6c757d" />
                      </marker>
                    </defs>
                    {connections.map((conn, index) => {
                      const fromEl = workflowElements.find(el => el.id === conn.from);
                      const toEl = workflowElements.find(el => el.id === conn.to);
                      if (!fromEl || !toEl) return null;
                      
                      const x1 = fromEl.x + 180;
                      const y1 = fromEl.y + 20;
                      const x2 = toEl.x;
                      const y2 = toEl.y + 20;

                      const pathData = `M ${x1} ${y1} C ${x1 + 50} ${y1}, ${x2 - 50} ${y2}, ${x2} ${y2}`;
                      return (
                        <path 
                          key={index} 
                          d={pathData} 
                          stroke="#6c757d" 
                          strokeWidth="2" 
                          fill="none"
                          markerEnd="url(#arrowhead)" 
                        />
                      );
                    })}
                    {isConnecting && workflowElements.find(el => el.id === isConnecting.fromId) && (
                      <path
                        d={`M ${workflowElements.find(el => el.id === isConnecting.fromId).x + 180} ${workflowElements.find(el => el.id === isConnecting.fromId).y + 20} C ${workflowElements.find(el => el.id === isConnecting.fromId).x + 180 + 50} ${workflowElements.find(el => el.id === isConnecting.fromId).y + 20}, ${mousePosition.x - 50} ${mousePosition.y}, ${mousePosition.x} ${mousePosition.y}`}
                        stroke="#0d6efd"
                        strokeWidth="2"
                        strokeDasharray="4,4"
                        fill="none"
                      />
                    )}
                  </svg>

                  {workflowElements.length === 0 ? (
                    <div className="d-flex align-items-center justify-content-center h-100">
                      <div className="text-center text-muted">
                        <i className="bi bi-diagram-3 display-4 mb-3"></i>
                        <p className="lead">
                          {showElements ? 'Drag elements here to build your workflow' : 'Select a sample to start'}
                        </p>
                      </div>
                    </div>
                  ) : (
                    workflowElements.map((el) => (
                      <DraggableElement 
                        key={el.id} 
                        element={el}
                        onPositionChange={updateElementPosition}
                        containerRef={canvasRef}
                        onClick={handleElementClick}
                        isSelected={selectedElement?.id === el.id}
                        onStartConnection={handleStartConnection}
                        onEndConnection={handleEndConnection}
                      />
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Right Panel */}
            <div className="col-lg-3 col-md-3">
              <div className="card h-100 border-0 shadow-sm">
                <div className="card-body d-flex flex-column">
                  {/* Menu Toolbar */}
                  <div className="d-flex flex-wrap gap-1 mb-3" ref={menuRef}>
                    {['File', 'Actions', 'Settings', 'Tools', 'Window', 'Help'].map((label) => (
                      <div className="position-relative" key={label}>
                        <button
                          className="btn btn-outline-secondary btn-sm"
                          type="button"
                          onClick={() => toggleMenu(label.toLowerCase())}
                        >
                          {label}
                        </button>
                        {activeMenu === label.toLowerCase() && (
                          <div className="position-absolute top-100 start-0" style={{ zIndex: 1050 }}>
                            <UgeneMenu 
                              items={menuItems[label.toLowerCase()] || []} 
                              closeMenu={() => setActiveMenu(null)}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Running Processes */}
                  <div className="mb-3">
                    <h6 className="card-subtitle text-muted mb-2">
                      <BsPlay className="me-1" />
                      Running Processes
                    </h6>
                    <div className="border rounded p-3 bg-light" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                      <RunningProcesses />
                    </div>
                  </div>

                  {/* Logs */}
                  <div className="flex-grow-1 d-flex flex-column">
                    <h6 className="card-subtitle text-muted mb-2">
                      <i className="bi bi-file-text me-1"></i>
                      Logs
                    </h6>
                    <div className="border rounded p-3 bg-light flex-grow-1 overflow-auto">
                      <LogViewer />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      
      {/* <footer className="bg-white border-top">
        <FooterContent />
      </footer> */}
 
      {/* Notifications */}
      <div className="position-fixed bottom-0 end-0 p-3" style={{ zIndex: 1055 }}>
        {notifications.map(notification => (
          <NotificationToast
            key={notification.id}
            notification={notification}
            onClose={() => actions.removeNotification(notification.id)}
          />
        ))}
      </div>

      {/* JSON Output Modal */}
      {showJsonModal && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Workflow JSON</h5>
                <button 
                  type="button" 
                  className="btn-close" 
                  onClick={() => setShowJsonModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                <pre className="bg-light p-3 rounded small overflow-auto" style={{ maxHeight: '400px' }}>
                  {workflowJson}
                </pre>
              </div>
              <div className="modal-footer">
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={() => setShowJsonModal(false)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Visualization Overlays */}
      {showUmapOverlay && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-xl">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">UMAP Visualization</h5>
                <button type="button" className="btn-close" onClick={() => setShowUmapOverlay(false)}></button>
              </div>
              <div className="modal-body">
                <UmapGenomeVisualization jsonUrl="http://localhost:8000/data/umap" />
              </div>
            </div>
          </div>
        </div>
      )}

      {showIgvOverlay && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-xl">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">IGV Viewer</h5>
                <button type="button" className="btn-close" onClick={() => setShowIgvOverlay(false)}></button>
              </div>
              <div className="modal-body">
                <IGVViewer />
              </div>
            </div>
          </div>
        </div>
      )}

      {showJbrowseOverlay && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-xl">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">JBrowse Viewer</h5>
                <button type="button" className="btn-close" onClick={() => setShowJbrowseOverlay(false)}></button>
              </div>
              <div className="modal-body">
                <JBrowseViewer />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Genomics;