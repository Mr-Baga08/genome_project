// frontend/src/components/SettingsPage.js
import React, { useState, useEffect } from 'react';
import HeaderContent from './HeaderContent';
import FooterContent from './FooterContent';
import { useAppContext } from '../context/AppContext';
import apiService from '../services/apiService';

const SettingsPage = () => {
  const { actions } = useAppContext();
  const [healthStatus, setHealthStatus] = useState(null);
  const [isLoadingHealth, setIsLoadingHealth] = useState(false);

  const [settings, setSettings] = useState({
    notifications: true,
    autoRefresh: true,
    refreshInterval: 30,
    theme: 'light'
  });

  useEffect(() => {
    checkHealth();
    // Load settings from localStorage
    const savedSettings = localStorage.getItem('ugene_settings');
    if (savedSettings) {
      setSettings(JSON.parse(savedSettings));
    }
  }, []);

  const checkHealth = async () => {
    setIsLoadingHealth(true);
    try {
      const health = await apiService.checkHealth();
      setHealthStatus(health);
    } catch (error) {
      setHealthStatus({ status: 'unhealthy', error: error.message });
    } finally {
      setIsLoadingHealth(false);
    }
  };

  const handleSettingChange = (key, value) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    localStorage.setItem('ugene_settings', JSON.stringify(newSettings));
  };

  const handleExportSettings = () => {
    const dataStr = JSON.stringify(settings, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = 'ugene_settings.json';
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const handleImportSettings = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const importedSettings = JSON.parse(e.target.result);
          setSettings(importedSettings);
          localStorage.setItem('ugene_settings', JSON.stringify(importedSettings));
          actions.addNotification({
            type: 'success',
            title: 'Settings Imported',
            message: 'Settings imported successfully'
          });
        } catch (error) {
          actions.addNotification({
            type: 'error',
            title: 'Import Failed',
            message: 'Failed to import settings file'
          });
        }
      };
      reader.readAsText(file);
    }
    event.target.value = '';
  };

  return (
    <div className="d-flex flex-column vh-100">
      <header className="bg-white shadow-sm">
        <HeaderContent />
      </header>
      
      <main className="flex-grow-1 overflow-auto">
        <div className="container-fluid py-4">
          
          <div className="row">
            <div className="col-12">
              <h2 className="h4 mb-4">Settings</h2>
            </div>
          </div>

          <div className="row g-4">
            
            {/* System Health */}
            <div className="col-lg-6">
              <div className="card border-0 shadow-sm">
                <div className="card-header bg-primary text-white">
                  <h5 className="card-title mb-0">
                    <i className="bi bi-heart-pulse me-2"></i>
                    System Health
                  </h5>
                </div>
                <div className="card-body">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <span>System Status</span>
                    <button 
                      className="btn btn-outline-primary btn-sm"
                      onClick={checkHealth}
                      disabled={isLoadingHealth}
                    >
                      {isLoadingHealth ? (
                        <span className="loading-spinner me-1" />
                      ) : (
                        <i className="bi bi-arrow-clockwise me-1"></i>
                      )}
                      Refresh
                    </button>
                  </div>

                  {healthStatus ? (
                    <div>
                      <div className={`status-indicator status-${healthStatus.status === 'healthy' ? 'completed' : 'failed'}`}>
                        <i className={`bi bi-${healthStatus.status === 'healthy' ? 'check-circle' : 'x-circle'} me-2`}></i>
                        {healthStatus.status === 'healthy' ? 'Healthy' : 'Unhealthy'}
                      </div>
                      
                      {healthStatus.database && (
                        <div className="mt-2">
                          <small className="text-muted">Database: </small>
                          <span className={`badge ${healthStatus.database === 'connected' ? 'bg-success' : 'bg-danger'}`}>
                            {healthStatus.database}
                          </span>
                        </div>
                      )}
                      
                      {healthStatus.redis && (
                        <div className="mt-1">
                          <small className="text-muted">Redis: </small>
                          <span className={`badge ${healthStatus.redis === 'connected' ? 'bg-success' : 'bg-danger'}`}>
                            {healthStatus.redis}
                          </span>
                        </div>
                      )}
                      
                      {healthStatus.error && (
                        <div className="alert alert-danger mt-3 mb-0">
                          <small>{healthStatus.error}</small>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-3">
                      <span className="text-muted">Click refresh to check system health</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Application Settings */}
            <div className="col-lg-6">
              <div className="card border-0 shadow-sm">
                <div className="card-header bg-info text-white">
                  <h5 className="card-title mb-0">
                    <i className="bi bi-gear me-2"></i>
                    Application Settings
                  </h5>
                </div>
                <div className="card-body">
                  
                  <div className="mb-3">
                    <label className="form-label fw-medium">Notifications</label>
                    <div className="form-check form-switch">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="notifications"
                        checked={settings.notifications}
                        onChange={(e) => handleSettingChange('notifications', e.target.checked)}
                      />
                      <label className="form-check-label" htmlFor="notifications">
                        Enable notifications
                      </label>
                    </div>
                  </div>

                  <div className="mb-3">
                    <label className="form-label fw-medium">Auto Refresh</label>
                    <div className="form-check form-switch mb-2">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="autoRefresh"
                        checked={settings.autoRefresh}
                        onChange={(e) => handleSettingChange('autoRefresh', e.target.checked)}
                      />
                      <label className="form-check-label" htmlFor="autoRefresh">
                        Auto refresh tasks
                      </label>
                    </div>
                    {settings.autoRefresh && (
                      <div>
                        <label htmlFor="refreshInterval" className="form-label small text-muted">
                          Refresh interval (seconds)
                        </label>
                        <input
                          type="range"
                          className="form-range"
                          id="refreshInterval"
                          min="10"
                          max="120"
                          value={settings.refreshInterval}
                          onChange={(e) => handleSettingChange('refreshInterval', parseInt(e.target.value))}
                        />
                        <div className="d-flex justify-content-between">
                          <small className="text-muted">10s</small>
                          <small className="text-muted">{settings.refreshInterval}s</small>
                          <small className="text-muted">120s</small>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="mb-3">
                    <label htmlFor="theme" className="form-label fw-medium">Theme</label>
                    <select
                      className="form-select"
                      id="theme"
                      value={settings.theme}
                      onChange={(e) => handleSettingChange('theme', e.target.value)}
                    >
                      <option value="light">Light</option>
                      <option value="dark">Dark</option>
                      <option value="auto">Auto</option>
                    </select>
                  </div>

                  <div className="d-flex gap-2">
                    <button
                      className="btn btn-outline-secondary btn-sm"
                      onClick={handleExportSettings}
                    >
                      <i className="bi bi-download me-1"></i>
                      Export
                    </button>
                    <label className="btn btn-outline-secondary btn-sm">
                      <i className="bi bi-upload me-1"></i>
                      Import
                      <input
                        type="file"
                        className="d-none"
                        accept=".json"
                        onChange={handleImportSettings}
                      />
                    </label>
                  </div>

                </div>
              </div>
            </div>

            {/* About */}
            <div className="col-12">
              <div className="card border-0 shadow-sm">
                <div className="card-header bg-secondary text-white">
                  <h5 className="card-title mb-0">
                    <i className="bi bi-info-circle me-2"></i>
                    About
                  </h5>
                </div>
                <div className="card-body">
                  <div className="row">
                    <div className="col-md-6">
                      <h6>UGENE Workflow Designer</h6>
                      <p className="text-muted">
                        A modern web-based interface for building and executing bioinformatics workflows using the UGENE toolkit.
                      </p>
                      <ul className="list-unstyled">
                        <li><strong>Version:</strong> 1.0.0</li>
                        <li><strong>Built with:</strong> React 18, FastAPI, MongoDB</li>
                        <li><strong>UGENE Version:</strong> 51.0</li>
                      </ul>
                    </div>
                    <div className="col-md-6">
                      <h6>Resources</h6>
                      <ul className="list-unstyled">
                        <li>
                          <a href="https://ugene.net/" target="_blank" rel="noopener noreferrer" className="text-decoration-none">
                            <i className="bi bi-globe me-1"></i> UGENE Website
                          </a>
                        </li>
                        <li>
                          <a href="https://ugene.net/documentation" target="_blank" rel="noopener noreferrer" className="text-decoration-none">
                            <i className="bi bi-book me-1"></i> Documentation
                          </a>
                        </li>
                        <li>
                          <a href="https://github.com/ugeneunipro/ugene" target="_blank" rel="noopener noreferrer" className="text-decoration-none">
                            <i className="bi bi-github me-1"></i> GitHub Repository
                          </a>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </main>
      
      <footer className="bg-white border-top">
        <FooterContent />
      </footer>
    </div>
  );
};

export default SettingsPage;
