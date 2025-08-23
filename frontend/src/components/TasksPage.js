// frontend/src/components/TasksPage.js
import React, { useEffect, useState } from 'react';
import { useAppContext } from '../context/AppContext';
import HeaderContent from './HeaderContent';
import FooterContent from './FooterContent';
import { 
  BsPlay, 
  BsStop, 
  BsDownload, 
  BsEye, 
  BsTrash,
  BsSearch,
  BsFilter
} from 'react-icons/bs';

const TasksPage = () => {
  const { state, actions } = useAppContext();
  const { tasks, isLoading, pagination } = state;
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedTasks, setSelectedTasks] = useState(new Set());

  useEffect(() => {
    actions.loadTasks();
  }, []);

  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.task_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         (task.workflow_definition?.nodes?.some(node => 
                           node.name.toLowerCase().includes(searchQuery.toLowerCase())
                         ));
    
    const matchesStatus = statusFilter === 'all' || task.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status) => {
    const statusClasses = {
      queued: 'bg-warning text-dark',
      running: 'bg-primary',
      completed: 'bg-success',
      failed: 'bg-danger'
    };
    
    return <span className={`badge ${statusClasses[status] || 'bg-secondary'}`}>
      {status.toUpperCase()}
    </span>;
  };

  const getStatusIcon = (status) => {
    const icons = {
      queued: <BsPlay className="text-warning" />,
      running: <div className="loading-spinner text-primary" />,
      completed: <BsStop className="text-success" />,
      failed: <BsStop className="text-danger" />
    };
    
    return icons[status] || <BsStop className="text-muted" />;
  };

  const handleSelectTask = (taskId) => {
    const newSelected = new Set(selectedTasks);
    if (newSelected.has(taskId)) {
      newSelected.delete(taskId);
    } else {
      newSelected.add(taskId);
    }
    setSelectedTasks(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedTasks.size === filteredTasks.length) {
      setSelectedTasks(new Set());
    } else {
      setSelectedTasks(new Set(filteredTasks.map(task => task.task_id)));
    }
  };

  const handleDownloadResults = async (taskId) => {
    try {
      const results = await actions.getTaskResults?.(taskId);
      if (results?.output_files?.length > 0) {
        // Download first file as example
        const file = results.output_files[0];
        const response = await fetch(file.download_url);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = file.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      actions.addNotification({
        type: 'error',
        title: 'Download Failed',
        message: error.message
      });
    }
  };

  const getElapsedTime = (task) => {
    if (!task.timestamps?.created) return 'Unknown';
    
    const created = new Date(task.timestamps.created);
    const completed = task.timestamps.completed ? new Date(task.timestamps.completed) : new Date();
    const elapsed = Math.floor((completed - created) / 1000);
    
    if (elapsed < 60) return `${elapsed}s`;
    if (elapsed < 3600) return `${Math.floor(elapsed / 60)}m`;
    return `${Math.floor(elapsed / 3600)}h ${Math.floor((elapsed % 3600) / 60)}m`;
  };

  return (
    <div className="d-flex flex-column vh-100">
      <header className="bg-white shadow-sm">
        <HeaderContent />
      </header>
      
      <main className="flex-grow-1 overflow-auto">
        <div className="container-fluid py-4">
          
          {/* Header */}
          <div className="row mb-4">
            <div className="col">
              <h2 className="h4 mb-0">Workflow Tasks</h2>
              <p className="text-muted mb-0">Monitor and manage your bioinformatics workflows</p>
            </div>
          </div>

          {/* Controls */}
          <div className="row mb-4">
            <div className="col-md-6">
              <div className="input-group">
                <span className="input-group-text">
                  <BsSearch />
                </span>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Search tasks..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>
            <div className="col-md-3">
              <select
                className="form-select"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="all">All Status</option>
                <option value="queued">Queued</option>
                <option value="running">Running</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>
            <div className="col-md-3">
              <button 
                className="btn btn-primary"
                onClick={() => actions.loadTasks()}
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="loading-spinner me-2" />
                    Refreshing...
                  </>
                ) : (
                  'Refresh'
                )}
              </button>
            </div>
          </div>

          {/* Tasks Table */}
          <div className="card border-0 shadow-sm">
            <div className="card-body p-0">
              <div className="table-responsive">
                <table className="table table-hover mb-0">
                  <thead className="bg-light">
                    <tr>
                      <th width="40">
                        <input
                          type="checkbox"
                          className="form-check-input"
                          checked={selectedTasks.size === filteredTasks.length && filteredTasks.length > 0}
                          onChange={handleSelectAll}
                        />
                      </th>
                      <th width="60">Status</th>
                      <th>Task ID</th>
                      <th>Workflow</th>
                      <th width="120">Duration</th>
                      <th width="150">Created</th>
                      <th width="120">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTasks.length === 0 ? (
                      <tr>
                        <td colSpan="7" className="text-center py-5 text-muted">
                          {isLoading ? (
                            <>
                              <div className="loading-spinner mb-2" />
                              <p>Loading tasks...</p>
                            </>
                          ) : (
                            <>
                              <i className="bi bi-inbox display-6 mb-3"></i>
                              <p>No tasks found</p>
                            </>
                          )}
                        </td>
                      </tr>
                    ) : (
                      filteredTasks.map((task) => (
                        <tr key={task.task_id} className={selectedTasks.has(task.task_id) ? 'table-active' : ''}>
                          <td>
                            <input
                              type="checkbox"
                              className="form-check-input"
                              checked={selectedTasks.has(task.task_id)}
                              onChange={() => handleSelectTask(task.task_id)}
                            />
                          </td>
                          <td>
                            <div className="d-flex align-items-center">
                              {getStatusIcon(task.status)}
                              <span className="ms-2">{getStatusBadge(task.status)}</span>
                            </div>
                          </td>
                          <td>
                            <code className="text-muted small">
                              {task.task_id.substring(0, 8)}...
                            </code>
                          </td>
                          <td>
                            <div>
                              <div className="fw-medium">
                                {task.workflow_definition?.nodes?.length || 0} nodes
                              </div>
                              <small className="text-muted">
                                {task.workflow_definition?.connections?.length || 0} connections
                              </small>
                            </div>
                          </td>
                          <td>
                            <small className="text-muted">{getElapsedTime(task)}</small>
                          </td>
                          <td>
                            <small className="text-muted">
                              {task.timestamps?.created 
                                ? new Date(task.timestamps.created).toLocaleString()
                                : 'Unknown'
                              }
                            </small>
                          </td>
                          <td>
                            <div className="btn-group btn-group-sm" role="group">
                              <button
                                className="btn btn-outline-primary"
                                title="View Details"
                                onClick={() => actions.loadTaskDetails(task.task_id)}
                              >
                                <BsEye />
                              </button>
                              {task.status === 'completed' && (
                                <button
                                  className="btn btn-outline-success"
                                  title="Download Results"
                                  onClick={() => handleDownloadResults(task.task_id)}
                                >
                                  <BsDownload />
                                </button>
                              )}
                              <button
                                className="btn btn-outline-danger"
                                title="Delete Task"
                                onClick={() => {
                                  if (window.confirm('Are you sure you want to delete this task?')) {
                                    // Implement delete functionality
                                  }
                                }}
                              >
                                <BsTrash />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Pagination */}
          {pagination.totalCount > pagination.size && (
            <nav className="mt-4">
              <ul className="pagination justify-content-center">
                <li className={`page-item ${pagination.page === 1 ? 'disabled' : ''}`}>
                  <button 
                    className="page-link"
                    onClick={() => actions.loadTasks(pagination.page - 1, pagination.size)}
                  >
                    Previous
                  </button>
                </li>
                
                {Array.from(
                  { length: Math.ceil(pagination.totalCount / pagination.size) },
                  (_, i) => i + 1
                ).map(pageNum => (
                  <li key={pageNum} className={`page-item ${pageNum === pagination.page ? 'active' : ''}`}>
                    <button 
                      className="page-link"
                      onClick={() => actions.loadTasks(pageNum, pagination.size)}
                    >
                      {pageNum}
                    </button>
                  </li>
                ))}
                
                <li className={`page-item ${pagination.page >= Math.ceil(pagination.totalCount / pagination.size) ? 'disabled' : ''}`}>
                  <button 
                    className="page-link"
                    onClick={() => actions.loadTasks(pagination.page + 1, pagination.size)}
                  >
                    Next
                  </button>
                </li>
              </ul>
            </nav>
          )}

        </div>
      </main>
      
      <footer className="bg-white border-top">
        <FooterContent />
      </footer>
    </div>
  );
};

export default TasksPage;

