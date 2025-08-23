// frontend/src/components/JBrowseViewer.js
import React, { useEffect, useRef, useState } from 'react';
import { useAppContext } from '../context/AppContext';
import apiService from '../services/apiService';

const JBrowseViewer = ({ taskId }) => {
  const { actions } = useAppContext();
  const containerRef = useRef(null);
  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [jbrowseInstance, setJbrowseInstance] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState({
    reference: null,
    tracks: []
  });

  useEffect(() => {
    if (taskId) {
      loadTaskResults();
    }
  }, [taskId]);

  const loadTaskResults = async () => {
    try {
      setIsLoading(true);
      const results = await apiService.getTaskResults(taskId);
      
      if (results.output_files) {
        setFiles(results.output_files);
        
        // Auto-select reference genome
        const referenceFile = results.output_files.find(f => 
          f.filename.toLowerCase().endsWith('.fasta') || 
          f.filename.toLowerCase().endsWith('.fa')
        );
        
        if (referenceFile) {
          setSelectedFiles(prev => ({
            ...prev,
            reference: referenceFile
          }));
        }
      }
    } catch (error) {
      actions.addNotification({
        type: 'error',
        title: 'Failed to Load Results',
        message: error.message
      });
    } finally {
      setIsLoading(false);
    }
  };

  const initializeJBrowse = async () => {
    if (!selectedFiles.reference || !containerRef.current) return;

    try {
      setIsLoading(true);
      
      // JBrowse Linear Genome View implementation
      // Note: This is a simplified implementation
      // Real JBrowse 2 integration would require proper plugin setup
      
      const config = {
        assembly: {
          name: 'custom',
          sequence: {
            type: 'ReferenceSequenceTrack',
            trackId: 'refseq',
            adapter: {
              type: 'IndexedFastaAdapter',
              fastaLocation: {
                uri: selectedFiles.reference.download_url
              }
            }
          }
        },
        tracks: selectedFiles.tracks.map(file => ({
          type: file.filename.endsWith('.gff') ? 'FeatureTrack' : 'AlignmentsTrack',
          trackId: file.filename,
          name: file.filename,
          assemblyNames: ['custom'],
          adapter: {
            type: file.filename.endsWith('.gff') ? 'Gff3Adapter' : 'BamAdapter',
            [file.filename.endsWith('.gff') ? 'gffLocation' : 'bamLocation']: {
              uri: file.download_url
            }
          }
        })),
        defaultSession: {
          name: 'Custom Session',
          view: {
            id: 'linearGenomeView',
            type: 'LinearGenomeView',
            tracks: selectedFiles.tracks.map(file => file.filename)
          }
        }
      };

      // Simulate JBrowse loading
      containerRef.current.innerHTML = `
        <div class="jbrowse-placeholder d-flex align-items-center justify-content-center border rounded bg-light" style="height: 600px;">
          <div class="text-center">
            <i class="bi bi-diagram-3 display-1 text-muted mb-3"></i>
            <h5 class="text-muted">JBrowse 2 Genome Browser</h5>
            <p class="text-muted">Reference: ${selectedFiles.reference.filename}</p>
            <p class="text-muted">${selectedFiles.tracks.length} track(s) loaded</p>
            <div class="alert alert-info mt-3">
              <i class="bi bi-info-circle me-2"></i>
              JBrowse 2 integration requires additional setup.<br>
              This is a placeholder for the actual genome browser.
            </div>
          </div>
        </div>
      `;

      actions.addNotification({
        type: 'info',
        title: 'JBrowse Placeholder',
        message: 'JBrowse integration is ready for implementation'
      });

    } catch (error) {
      actions.addNotification({
        type: 'error',
        title: 'JBrowse Error',
        message: error.message
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTrackToggle = (file) => {
    setSelectedFiles(prev => ({
      ...prev,
      tracks: prev.tracks.some(t => t.filename === file.filename)
        ? prev.tracks.filter(t => t.filename !== file.filename)
        : [...prev.tracks, file]
    }));
  };

  const getSupportedTrackFiles = () => {
    return files.filter(f => 
      f.filename.toLowerCase().endsWith('.bam') ||
      f.filename.toLowerCase().endsWith('.gff') ||
      f.filename.toLowerCase().endsWith('.gff3') ||
      f.filename.toLowerCase().endsWith('.bed') ||
      f.filename.toLowerCase().endsWith('.vcf') ||
      f.filename.toLowerCase().endsWith('.bigwig') ||
      f.filename.toLowerCase().endsWith('.bw')
    );
  };

  if (isLoading && !files.length) {
    return (
      <div className="d-flex justify-content-center align-items-center py-5">
        <div className="text-center">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2 text-muted">Loading task results...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container-fluid">
      <div className="row">
        <div className="col-12">
          <div className="card border-0 shadow-sm">
            <div className="card-header bg-info text-white">
              <h5 className="card-title mb-0">
                <i class="bi bi-grid-3x3-gap me-2"></i>
                JBrowse 2 Genome Browser
              </h5>
            </div>
            <div className="card-body">
              
              {!jbrowseInstance && (
                <div className="setup-panel">
                  <div className="row g-3 mb-4">
                    <div className="col-md-6">
                      <label className="form-label fw-medium">Reference Genome</label>
                      <select
                        className="form-select"
                        value={selectedFiles.reference?.filename || ''}
                        onChange={(e) => {
                          const file = files.find(f => f.filename === e.target.value);
                          setSelectedFiles(prev => ({ ...prev, reference: file }));
                        }}
                      >
                        <option value="">Select reference...</option>
                        {files.filter(f => 
                          f.filename.toLowerCase().endsWith('.fasta') || 
                          f.filename.toLowerCase().endsWith('.fa')
                        ).map(file => (
                          <option key={file.filename} value={file.filename}>
                            {file.filename}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="col-md-6">
                      <label className="form-label fw-medium">Available Tracks</label>
                      <div className="border rounded p-3" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                        {getSupportedTrackFiles().length === 0 ? (
                          <p className="text-muted mb-0">No supported track files found</p>
                        ) : (
                          getSupportedTrackFiles().map(file => (
                            <div key={file.filename} className="form-check">
                              <input
                                className="form-check-input"
                                type="checkbox"
                                id={`track-${file.filename}`}
                                checked={selectedFiles.tracks.some(t => t.filename === file.filename)}
                                onChange={() => handleTrackToggle(file)}
                              />
                              <label className="form-check-label small" htmlFor={`track-${file.filename}`}>
                                {file.filename}
                              </label>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="d-flex justify-content-between align-items-center">
                    <div>
                      <small className="text-muted">
                        Selected: {selectedFiles.tracks.length} track(s)
                      </small>
                    </div>
                    <button
                      className="btn btn-info"
                      onClick={() => {
                        setJbrowseInstance(true);
                        initializeJBrowse();
                      }}
                      disabled={!selectedFiles.reference || isLoading}
                    >
                      {isLoading ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                          Loading...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-play-circle me-2"></i>
                          Launch JBrowse
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {jbrowseInstance && (
                <div className="jbrowse-container">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <div>
                      <h6 className="mb-1">JBrowse 2 Browser</h6>
                      <small className="text-muted">
                        Reference: {selectedFiles.reference?.filename} | 
                        Tracks: {selectedFiles.tracks.length}
                      </small>
                    </div>
                    <button
                      className="btn btn-outline-secondary btn-sm"
                      onClick={() => {
                        setJbrowseInstance(null);
                        if (containerRef.current) {
                          containerRef.current.innerHTML = '';
                        }
                      }}
                    >
                      <i className="bi bi-arrow-left me-1"></i>
                      Back to Setup
                    </button>
                  </div>

                  <div ref={containerRef} className="jbrowse-wrapper" />
                </div>
              )}

            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JBrowseViewer;
