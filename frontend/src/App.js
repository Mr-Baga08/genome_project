// frontend/src/App.js - Enhanced Main Application
import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Container, Navbar, Nav, Badge, Alert } from 'react-bootstrap';
import { BsHouse, BsGear, BsActivity, BsDatabase, BsPipeline } from 'react-icons/bs';

// Import enhanced components
import BioinformaticsWorkspace from './components/BioinformaticsWorkspace';
// import SystemSettings from './components/SystemSettings';
// import SystemHealth from './components/SystemHealth';
import { AppProvider, useAppContext } from './context/AppContext';
import { useWebSocket } from './hooks/useWebSocket';
import enhancedApiService from './services/enhancedApiService';

// Import Bootstrap CSS and custom styles
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import './App.css';

function App() {
  return (
    <AppProvider>
      <Router>
        <div className="App">
          <AppContent />
        </div>
      </Router>
    </AppProvider>
  );
}

const AppContent = () => {
  const { state, actions } = useAppContext();
  const { isConnected } = useWebSocket(process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws');

  // Initialize application
  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      // Check system health
      const healthResponse = await enhancedApiService.getSystemHealth();
      if (healthResponse.data.status !== 'healthy') {
        actions.addNotification({
          type: 'warning',
          title: 'System Warning',
          message: 'Some system components may not be fully operational'
        });
      }

      // Load cache statistics
      const cacheStats = await enhancedApiService.getCacheStats();
      console.log('Cache statistics:', cacheStats.data);

    } catch (error) {
      console.error('App initialization error:', error);
      actions.addNotification({
        type: 'error',
        title: 'Initialization Error',
        message: 'Failed to initialize application components'
      });
    }
  };

  return (
    <>
      {/* Navigation Bar */}
      <Navbar bg="dark" variant="dark" expand="lg" className="mb-0">
        <Container fluid>
          <Navbar.Brand href="/" className="d-flex align-items-center">
            <BsDatabase className="me-2" />
            UGENE Web Platform
          </Navbar.Brand>
          
          <Navbar.Toggle aria-controls="basic-navbar-nav" />
          
          <Navbar.Collapse id="basic-navbar-nav">
            <Nav className="me-auto">
              <Nav.Link href="/workspace">
                <BsHouse className="me-1" />
                Workspace
              </Nav.Link>
              <Nav.Link href="/health">
                <BsActivity className="me-1" />
                System Health
              </Nav.Link>
              <Nav.Link href="/settings">
                <BsGear className="me-1" />
                Settings
              </Nav.Link>
            </Nav>
            
            <Nav className="ms-auto">
              {/* Connection Status */}
              <Nav.Item className="d-flex align-items-center me-3">
                <Badge bg={isConnected ? 'success' : 'danger'}>
                  {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
                </Badge>
              </Nav.Item>
              
              {/* Active Tasks Counter */}
              <Nav.Item className="d-flex align-items-center">
                <Badge bg="primary">
                  {state.tasks.filter(t => t.status === 'running').length} Active
                </Badge>
              </Nav.Item>
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      {/* Notification Area */}
      <NotificationArea />

      {/* Main Content */}
      <Container fluid className="p-0">
        <Routes>
          <Route path="/" element={<Navigate to="/workspace" replace />} />
          <Route path="/workspace" element={<BioinformaticsWorkspace />} />
          <Route path="/health" element={<SystemHealth />} />
          <Route path="/settings" element={<SystemSettings />} />
          <Route path="*" element={<Navigate to="/workspace" replace />} />
        </Routes>
      </Container>

      {/* Global Error Boundary */}
      <GlobalErrorHandler />
    </>
  );
};

// Notification Area Component
const NotificationArea = () => {
  const { state, actions } = useAppContext();

  return (
    <div className="notification-area">
      {state.notifications.map((notification) => (
        <Alert
          key={notification.id}
          variant={notification.type}
          dismissible
          onClose={() => actions.removeNotification(notification.id)}
          className="mb-2 mx-3"
        >
          <Alert.Heading>{notification.title}</Alert.Heading>
          {notification.message}
        </Alert>
      ))}
    </div>
  );
};

// System Health Component
const SystemHealth = () => {
  const [healthData, setHealthData] = React.useState(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    loadHealthData();
    const interval = setInterval(loadHealthData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadHealthData = async () => {
    try {
      setIsLoading(true);
      const [healthResponse, cacheResponse, toolsResponse] = await Promise.all([
        enhancedApiService.getSystemHealth(),
        enhancedApiService.getCacheStats(),
        enhancedApiService.getAvailableTools()
      ]);

      setHealthData({
        system: healthResponse.data,
        cache: cacheResponse.data,
        tools: toolsResponse.data
      });
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <Container className="py-4">
        <div className="text-center">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      </Container>
    );
  }

  if (error) {
    return (
      <Container className="py-4">
        <Alert variant="danger">
          <Alert.Heading>Health Check Failed</Alert.Heading>
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container className="py-4">
      <h2 className="mb-4">System Health Dashboard</h2>
      
      <div className="row">
        {/* System Status */}
        <div className="col-md-6 mb-4">
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">System Status</h5>
            </div>
            <div className="card-body">
              <div className="d-flex align-items-center mb-3">
                <Badge bg={healthData?.system?.status === 'healthy' ? 'success' : 'danger'} className="me-2">
                  {healthData?.system?.status || 'Unknown'}
                </Badge>
                <span>Overall System Health</span>
              </div>
              
              <div className="row">
                {healthData?.system?.services && Object.entries(healthData.system.services).map(([service, status]) => (
                  <div key={service} className="col-6 mb-2">
                    <Badge bg={status === 'healthy' ? 'success' : 'danger'} className="me-2">
                      {status}
                    </Badge>
                    <small className="text-capitalize">{service.replace('_', ' ')}</small>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Cache Statistics */}
        <div className="col-md-6 mb-4">
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">Cache Performance</h5>
            </div>
            <div className="card-body">
              {healthData?.cache && (
                <div className="row">
                  <div className="col-6 mb-2">
                    <strong>Hit Rate:</strong>
                    <div className="progress mt-1">
                      <div 
                        className="progress-bar bg-success" 
                        style={{ width: `${healthData.cache.hit_rate}%` }}
                      >
                        {healthData.cache.hit_rate}%
                      </div>
                    </div>
                  </div>
                  <div className="col-6 mb-2">
                    <strong>Memory Usage:</strong><br />
                    <small>{healthData.cache.redis_used_memory}</small>
                  </div>
                  <div className="col-6 mb-2">
                    <strong>Total Hits:</strong><br />
                    <small>{healthData.cache.total_hits}</small>
                  </div>
                  <div className="col-6 mb-2">
                    <strong>Local Cache:</strong><br />
                    <small>{healthData.cache.local_cache_size} entries</small>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Available Tools */}
        <div className="col-12 mb-4">
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">Bioinformatics Tools</h5>
            </div>
            <div className="card-body">
              <div className="row">
                {healthData?.tools?.tools && healthData.tools.tools.map((tool) => (
                  <div key={tool} className="col-md-3 col-sm-4 col-6 mb-2">
                    <Badge bg="info" className="me-2">
                      ✓
                    </Badge>
                    <small className="text-uppercase">{tool}</small>
                  </div>
                ))}
              </div>
              
              {healthData?.system?.docker_containers !== undefined && (
                <div className="mt-3">
                  <small className="text-muted">
                    Docker Containers Available: {healthData.system.docker_containers}
                  </small>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      <div className="text-center">
        <button className="btn btn-primary" onClick={loadHealthData}>
          Refresh Health Data
        </button>
      </div>
    </Container>
  );
};

// System Settings Component
const SystemSettings = () => {
  const [cacheStats, setCacheStats] = React.useState(null);
  const [isClearing, setIsClearing] = React.useState(false);
  const { actions } = useAppContext();

  React.useEffect(() => {
    loadCacheStats();
  }, []);

  const loadCacheStats = async () => {
    try {
      const response = await enhancedApiService.getCacheStats();
      setCacheStats(response.data);
    } catch (error) {
      console.error('Failed to load cache stats:', error);
    }
  };

  const handleClearCache = async () => {
    try {
      setIsClearing(true);
      await enhancedApiService.invalidateCache('*');
      
      actions.addNotification({
        type: 'success',
        title: 'Cache Cleared',
        message: 'All cache entries have been cleared successfully'
      });
      
      // Reload stats
      await loadCacheStats();
    } catch (error) {
      actions.addNotification({
        type: 'error',
        title: 'Cache Clear Failed',
        message: error.message
      });
    } finally {
      setIsClearing(false);
    }
  };

  const handleWarmCache = async () => {
    try {
      await enhancedApiService.warmCache(['popular_seq_1', 'popular_seq_2'], ['blast_search', 'alignment']);
      
      actions.addNotification({
        type: 'info',
        title: 'Cache Warming Started',
        message: 'Cache warming process has been initiated in the background'
      });
    } catch (error) {
      actions.addNotification({
        type: 'error',
        title: 'Cache Warming Failed',
        message: error.message
      });
    }
  };

  return (
    <Container className="py-4">
      <h2 className="mb-4">System Settings</h2>
      
      <div className="row">
        {/* Cache Management */}
        <div className="col-md-6 mb-4">
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">Cache Management</h5>
            </div>
            <div className="card-body">
              {cacheStats && (
                <div className="mb-3">
                  <div className="row">
                    <div className="col-6">
                      <strong>Hit Rate:</strong><br />
                      <span className="h4 text-success">{cacheStats.hit_rate}%</span>
                    </div>
                    <div className="col-6">
                      <strong>Total Requests:</strong><br />
                      <span className="h4">{cacheStats.total_hits + cacheStats.total_misses}</span>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="d-grid gap-2">
                <button 
                  className="btn btn-warning"
                  onClick={handleClearCache}
                  disabled={isClearing}
                >
                  {isClearing ? 'Clearing...' : 'Clear All Cache'}
                </button>
                
                <button 
                  className="btn btn-info"
                  onClick={handleWarmCache}
                >
                  Warm Cache
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Application Info */}
        <div className="col-md-6 mb-4">
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">Application Information</h5>
            </div>
            <div className="card-body">
              <table className="table table-sm">
                <tbody>
                  <tr>
                    <td><strong>Version:</strong></td>
                    <td>1.0.0</td>
                  </tr>
                  <tr>
                    <td><strong>Environment:</strong></td>
                    <td>{process.env.NODE_ENV || 'development'}</td>
                  </tr>
                  <tr>
                    <td><strong>API URL:</strong></td>
                    <td><code>{process.env.REACT_APP_API_URL || 'http://localhost:8000'}</code></td>
                  </tr>
                  <tr>
                    <td><strong>WebSocket URL:</strong></td>
                    <td><code>{process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws'}</code></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </Container>
  );
};

// Global Error Handler
const GlobalErrorHandler = () => {
  const { actions } = useAppContext();

  React.useEffect(() => {
    const handleError = (event) => {
      console.error('Global error:', event.error);
      actions.addNotification({
        type: 'error',
        title: 'Application Error',
        message: 'An unexpected error occurred. Please refresh the page if problems persist.'
      });
    };

    const handleUnhandledRejection = (event) => {
      console.error('Unhandled promise rejection:', event.reason);
      actions.addNotification({
        type: 'error',
        title: 'Promise Rejection',
        message: 'An async operation failed. Please try again.'
      });
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [actions]);

  return null;
};

export default App;