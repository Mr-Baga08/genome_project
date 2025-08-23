import React, { useEffect } from 'react';
import { useAppContext } from '../context/AppContext';
import { BsCircle, BsCheckCircle, BsXCircle, BsClock } from 'react-icons/bs';

const RunningProcesses = () => {
  const { state, actions } = useAppContext();
  const { tasks = [], isLoading } = state; // Ensure tasks is always an array

  useEffect(() => {
    // Load tasks when component mounts
    if (actions.loadTasks) {
      actions.loadTasks();
    }
  }, []);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'queued':
        return <BsClock className="text-warning" />;
      case 'running':
        return <BsCircle className="text-primary" />;
      case 'completed':
        return <BsCheckCircle className="text-success" />;
      case 'failed':
        return <BsXCircle className="text-danger" />;
      default:
        return <BsCircle className="text-muted" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'queued': return 'warning';
      case 'running': return 'primary';
      case 'completed': return 'success';
      case 'failed': return 'danger';
      default: return 'secondary';
    }
  };

  const getElapsedTime = (task) => {
    // Safely handle timestamp conversion
    if (!task.timestamps?.created) return 'Unknown';
    
    try {
      const created = new Date(task.timestamps.created);
      const now = new Date();
      const elapsed = Math.floor((now - created) / 1000);
      
      if (elapsed < 60) return `${elapsed}s`;
      if (elapsed < 3600) return `${Math.floor(elapsed / 60)}m`;
      return `${Math.floor(elapsed / 3600)}h`;
    } catch (error) {
      console.error('Error calculating elapsed time:', error);
      return 'Unknown';
    }
  };

  if (isLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center p-3">
        <div className="spinner-border spinner-border-sm text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <span className="ms-2 small text-muted">Loading tasks...</span>
      </div>
    );
  }

  // Filter active tasks safely
  const activeTasks = Array.isArray(tasks) ? tasks.filter(task => 
    task && (task.status === 'running' || task.status === 'queued')
  ) : [];

  if (activeTasks.length === 0) {
    return (
      <div className="text-center text-muted py-3">
        <i className="bi bi-inbox display-6 mb-2"></i>
        <p className="small mb-0">No active processes</p>
      </div>
    );
  }

  return (
    <div className="processes-container">
      {activeTasks.map((task) => {
        // Safely extract task properties
        const taskId = task.task_id || 'unknown';
        const status = task.status || 'unknown';
        const nodeCount = task.workflow_definition?.nodes?.length || 0;
        
        return (
          <div key={taskId} className="card border-0 bg-white mb-2 shadow-sm">
            <div className="card-body p-2">
              <div className="d-flex justify-content-between align-items-center mb-1">
                <div className="d-flex align-items-center">
                  {getStatusIcon(status)}
                  <span className="ms-2 small fw-medium">
                    {taskId.length > 8 ? `${taskId.substring(0, 8)}...` : taskId}
                  </span>
                </div>
                <span className="small text-muted">{getElapsedTime(task)}</span>
              </div>
              
              <div className="progress" style={{ height: '4px' }}>
                <div
                  className={`progress-bar bg-${getStatusColor(status)}`}
                  style={{ 
                    width: status === 'running' ? '75%' : 
                          status === 'completed' ? '100%' : '25%',
                    transition: 'width 0.3s ease'
                  }}
                />
              </div>
              
              <div className="d-flex justify-content-between align-items-center mt-1">
                <span className={`badge bg-${getStatusColor(status)} fs-6`}>
                  {String(status).toUpperCase()}
                </span>
                <small className="text-muted">
                  {nodeCount} nodes
                </small>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default RunningProcesses;