import React, { useState, useEffect } from 'react';
import { useAppContext } from '../context/AppContext';
import { BsDownload, BsSearch } from 'react-icons/bs';

const LogViewer = () => {
  const { state, actions } = useAppContext();
  const { currentTask, tasks = [], isLoading } = state;
  const [selectedTaskId, setSelectedTaskId] = useState('');
  const [filterLevel, setFilterLevel] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    // Auto-select the first task if none selected
    if (!selectedTaskId && Array.isArray(tasks) && tasks.length > 0) {
      setSelectedTaskId(tasks[0].task_id);
    }
  }, [tasks, selectedTaskId]);

  useEffect(() => {
    // Load task details when selected task changes
    if (selectedTaskId && actions.loadTaskDetails) {
      actions.loadTaskDetails(selectedTaskId);
    }
  }, [selectedTaskId]);

  const handleTaskSelect = (taskId) => {
    setSelectedTaskId(taskId);
  };

  const parseLogs = (logs) => {
    if (!logs || typeof logs !== 'string') return [];
    
    try {
      const lines = logs.split('\n').filter(line => line.trim());
      return lines.map((line, index) => {
        // Simple log level detection
        let level = 'info';
        const lowerLine = line.toLowerCase();
        if (lowerLine.includes('error') || lowerLine.includes('failed')) {
          level = 'error';
        } else if (lowerLine.includes('warning') || lowerLine.includes('warn')) {
          level = 'warning';
        } else if (lowerLine.includes('debug')) {
          level = 'debug';
        }
        
        return {
          id: index,
          timestamp: new Date().toLocaleTimeString(),
          level,
          message: String(line), // Ensure it's a string
        };
      });
    } catch (error) {
      console.error('Error parsing logs:', error);
      return [];
    }
  };

  const filteredLogs = () => {
    if (!currentTask?.logs) return [];
    
    try {
      let logs = parseLogs(currentTask.logs);
      
      // Filter by level
      if (filterLevel !== 'all') {
        logs = logs.filter(log => log.level === filterLevel);
      }
      
      // Filter by search query
      if (searchQuery) {
        logs = logs.filter(log => 
          String(log.message).toLowerCase().includes(searchQuery.toLowerCase())
        );
      }
      
      return logs;
    } catch (error) {
      console.error('Error filtering logs:', error);
      return [];
    }
  };

  const getLevelBadgeClass = (level) => {
    switch (level) {
      case 'error': return 'bg-danger';
      case 'warning': return 'bg-warning text-dark';
      case 'debug': return 'bg-secondary';
      default: return 'bg-primary';
    }
  };

  const downloadLogs = () => {
    if (!currentTask?.logs) return;
    
    try {
      const blob = new Blob([String(currentTask.logs)], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `task_${currentTask.task_id}_logs.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading logs:', error);
    }
  };

  return (
    <div className="log-viewer-container h-100 d-flex flex-column">
      {/* Controls */}
      <div className="mb-3">
        <div className="row g-2 align-items-center">
          <div className="col">
            <select
              className="form-select form-select-sm"
              value={selectedTaskId}
              onChange={(e) => handleTaskSelect(e.target.value)}
            >
              <option value="">Select Task</option>
              {Array.isArray(tasks) && tasks.map(task => (
                <option key={task.task_id} value={task.task_id}>
                  {task.task_id ? `${task.task_id.substring(0, 8)}... (${task.status})` : 'Unknown Task'}
                </option>
              ))}
            </select>
          </div>
          <div className="col-auto">
            <button
              className="btn btn-outline-secondary btn-sm"
              onClick={downloadLogs}
              disabled={!currentTask?.logs}
              title="Download Logs"
            >
              <BsDownload />
            </button>
          </div>
        </div>
        
        <div className="row g-2 mt-2">
          <div className="col">
            <div className="input-group input-group-sm">
              <span className="input-group-text">
                <BsSearch />
              </span>
              <input
                type="text"
                className="form-control"
                placeholder="Search logs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
          <div className="col-auto">
            <select
              className="form-select form-select-sm"
              value={filterLevel}
              onChange={(e) => setFilterLevel(e.target.value)}
            >
              <option value="all">All Levels</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
              <option value="debug">Debug</option>
            </select>
          </div>
        </div>
      </div>

      {/* Logs Display */}
      <div className="flex-grow-1 overflow-auto">
        {isLoading ? (
          <div className="d-flex justify-content-center align-items-center h-100">
            <div className="spinner-border spinner-border-sm text-primary" role="status">
              <span className="visually-hidden">Loading logs...</span>
            </div>
          </div>
        ) : !currentTask ? (
          <div className="text-center text-muted py-4">
            <i className="bi bi-file-text display-6 mb-2"></i>
            <p className="small mb-0">Select a task to view logs</p>
          </div>
        ) : !currentTask.logs ? (
          <div className="text-center text-muted py-4">
            <i className="bi bi-hourglass-split display-6 mb-2"></i>
            <p className="small mb-0">No logs available yet</p>
          </div>
        ) : filteredLogs().length === 0 ? (
          <div className="text-center text-muted py-4">
            <i className="bi bi-search display-6 mb-2"></i>
            <p className="small mb-0">No logs match your filters</p>
          </div>
        ) : (
          <div className="log-entries">
            {filteredLogs().map((log) => (
              <div key={log.id} className="log-entry border-bottom py-2">
                <div className="d-flex align-items-start">
                  <span className={`badge ${getLevelBadgeClass(log.level)} me-2`}>
                    {String(log.level).toUpperCase()}
                  </span>
                  <div className="flex-grow-1">
                    <div className="d-flex justify-content-between align-items-start">
                      <span className="font-monospace small text-break">
                        {String(log.message)}
                      </span>
                      <small className="text-muted ms-2 flex-shrink-0">
                        {String(log.timestamp)}
                      </small>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Error Logs Section */}
      {currentTask?.error_logs && (
        <div className="mt-3 border-top pt-3">
          <h6 className="text-danger mb-2">
            <i className="bi bi-exclamation-triangle me-1"></i>
            Error Logs
          </h6>
          <div className="bg-danger-subtle p-2 rounded">
            <pre className="mb-0 small text-danger">
              {String(currentTask.error_logs)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default LogViewer;