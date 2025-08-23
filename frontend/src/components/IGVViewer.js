
import React, { useEffect, useRef, useState } from 'react';
import { useAppContext } from '../context/AppContext';
import apiService from '../services/apiService';

const IGVViewer = ({ taskId }) => {
  const { state, actions } = useAppContext();
  const { currentTask } = state;
  const igvContainerRef = useRef(null);
  const [files, setFiles] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showViewer, setShowViewer] = useState(false);
  const [igvLoaded, setIgvLoaded] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState({
    reference: null,
    alignment: null
  });

  useEffect(() => {
    if (taskId) {
      loadTaskResults();
    }
  }, [taskId]);

  // Load IGV dynamically to avoid build issues
  useEffect(() => {
    if (showViewer && !igvLoaded) {
      loadIGV();
    }
  }, [showViewer, igvLoaded]);

  const loadIGV = async () => {
    try {
      // Load IGV dynamically using script tag to avoid build issues
      if (!window.igv) {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/igv@2.15.8/dist/igv.min.js';
        script.onload = () => {
          setIgvLoaded(true);
          initializeIGV();
        };
        script.onerror = () => {
          actions.addNotification({
            type: 'error',
            title: 'IGV Loading Failed',
            message: 'Could not load IGV library'
          });
        };
        document.head.appendChild(script);
      } else {
        setIgvLoaded(true);
        initializeIGV();
      }
    } catch (error) {
      actions.addNotification({
        type: 'error',
        title: 'IGV Error',
        message: error.message
      });
    }
  };

  const loadTaskResults = async () => {
    try {
      setIsLoading(true);
      const results = await apiService.getTaskResults(taskId);
      
      if (results.output_files) {
        setFiles(results.output_files);
        
        // Auto-select common file types
        const fastaFile = results.output_files.find(f => 
          f.filename.toLowerCase().endsWith('.fasta') || 
          f.filename.toLowerCase().endsWith('.fa')
        );
        const bamFile = results.output_files.find(f => 
          f.filename.toLowerCase().endsWith('.bam')
        );
        
        setSelectedFiles({
          reference: fastaFile,
          alignment: bamFile
        });
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

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (!selectedFiles.reference) {
      actions.addNotification({
        type: 'warning',
        title: 'Missing Reference',
        message: 'Please select a reference genome file'
      });
      return;
    }

    setShowViewer(true);
  };

  const initializeIGV = async () => {
    if (!igvContainerRef.current || !window.igv) return;

    try {
      setIsLoading(true);

      // Clear existing IGV instance
      igvContainerRef.current.innerHTML = '';

      const options = {
        genome: {
          fastaURL: selectedFiles.reference.download_url,
          id: 'custom',
          name: 'Custom Reference'
        },
        tracks: []
      };

      // Add alignment track if available
      if (selectedFiles.alignment) {
        options.tracks.push({
          type: 'alignment',
          format: 'bam',
          url: selectedFiles.alignment.download_url,
          indexURL: selectedFiles.alignment.download_url.replace('.bam', '.bam.bai'),
          name: selectedFiles.alignment.filename,
          height: 300,
          autoHeight: false,
          colorBy: 'strand'
        });
      }

      // Add any BED files as feature tracks
      const bedFiles = files.filter(f => f.filename.toLowerCase().endsWith('.bed'));
      bedFiles.forEach(bedFile => {
        options.tracks.push({
          type: 'annotation',
          format: 'bed',
          url: bedFile.download_url,
          name: bedFile.filename,
          displayMode: 'EXPANDED',
          height: 100
        });
      });

      // Add any VCF files as variant tracks
      const vcfFiles = files.filter(f => 
        f.filename.toLowerCase().endsWith('.vcf') || 
        f.filename.toLowerCase().endsWith('.vcf.gz')
      );
      vcfFiles.forEach(vcfFile => {
        options.tracks.push({
          type: 'variant',
          format: 'vcf',
          url: vcfFile.download_url,
          name: vcfFile.filename,
          displayMode: 'EXPANDED',
          height: 100
        });
      });

      // Create IGV browser
      const browser = await window.igv.createBrowser(igvContainerRef.current, options);
      
      // Set initial locus if available
      if (options.tracks.length > 0) {
        await browser.search('chr1:1-100000');
      }

      actions.addNotification({
        type: 'success',
        title: 'IGV Loaded',
        message: 'Genome browser initialized successfully'
      });

    } catch (error) {
      console.error('IGV initialization error:', error);
      
      // Fallback: Show placeholder when IGV fails
      igvContainerRef.current.innerHTML = `
        <div class="d-flex align-items-center justify-content-center border rounded bg-light" style="height: 600px;">
          <div class="text-center">
            <i class="bi bi-exclamation-triangle display-1 text-warning mb-3"></i>
            <h5 class="text-muted">IGV Browser Unavailable</h5>
            <p class="text-muted">Reference: ${selectedFiles.reference?.filename}</p>
            ${selectedFiles.alignment ? `<p class="text-muted">Alignment: ${selectedFiles.alignment.filename}</p>` : ''}
            <div class="alert alert-info mt-3">
              <i class="bi bi-info-circle me-2"></i>
              IGV browser could not be loaded. This may be due to network issues or file format compatibility.
            </div>
          </div>
        </div>
      `;
      
      actions.addNotification({
        type: 'warning',
        title: 'IGV Warning',
        message: 'IGV browser could not be loaded, showing placeholder instead'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSelect = (fileType, fileId) => {
    const file = files.find(f => f.filename === fileId);
    setSelectedFiles(prev => ({
      ...prev,
      [fileType]: file
    }));
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
            <div className="card-header bg-primary text-white">
              <h5 className="card-title mb-0">
                <i className="bi bi-eye me-2"></i>
                Genome Browser (IGV)
              </h5>
            </div>
            <div className="card-body">
              
              {!showViewer && (
                <form onSubmit={handleSubmit} className="mb-4">
                  <div className="row g-3">
                    <div className="col-md-6">
                      <label className="form-label fw-medium">Reference Genome</label>
                      <select
                        className="form-select"
                        value={selectedFiles.reference?.filename || ''}
                        onChange={(e) => handleFileSelect('reference', e.target.value)}
                        required
                      >
                        <option value="">Select reference genome...</option>
                        {files.filter(f => 
                          f.filename.toLowerCase().endsWith('.fasta') || 
                          f.filename.toLowerCase().endsWith('.fa')
                        ).map(file => (
                          <option key={file.filename} value={file.filename}>
                            {file.filename}
                          </option>
                        ))}
                      </select>
                      <div className="form-text">FASTA format reference genome</div>
                    </div>
                    
                    <div className="col-md-6">
                      <label className="form-label fw-medium">Alignment File (Optional)</label>
                      <select
                        className="form-select"
                        value={selectedFiles.alignment?.filename || ''}
                        onChange={(e) => handleFileSelect('alignment', e.target.value)}
                      >
                        <option value="">No alignment file</option>
                        {files.filter(f => 
                          f.filename.toLowerCase().endsWith('.bam') || 
                          f.filename.toLowerCase().endsWith('.sam')
                        ).map(file => (
                          <option key={file.filename} value={file.filename}>
                            {file.filename}
                          </option>
                        ))}
                      </select>
                      <div className="form-text">BAM/SAM alignment file</div>
                    </div>
                  </div>

                  <div className="row mt-3">
                    <div className="col-12">
                      <h6 className="text-muted">Available Files:</h6>
                      <div className="d-flex flex-wrap gap-2">
                        {files.map(file => (
                          <span key={file.filename} className="badge bg-light text-dark border">
                            {file.filename}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={isLoading || !selectedFiles.reference}
                    >
                      {isLoading ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                          Loading IGV...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-play-circle me-2"></i>
                          Launch Genome Browser
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}

              {showViewer && (
                <div className="igv-container">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <div>
                      <h6 className="mb-1">Genome Browser</h6>
                      <small className="text-muted">
                        Reference: {selectedFiles.reference?.filename}
                        {selectedFiles.alignment && ` | Alignment: ${selectedFiles.alignment.filename}`}
                      </small>
                    </div>
                    <button
                      className="btn btn-outline-secondary btn-sm"
                      onClick={() => setShowViewer(false)}
                    >
                      <i className="bi bi-arrow-left me-1"></i>
                      Back to Setup
                    </button>
                  </div>

                  {isLoading && (
                    <div className="d-flex justify-content-center align-items-center py-4">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Initializing IGV...</span>
                      </div>
                      <span className="ms-2">Initializing genome browser...</span>
                    </div>
                  )}

                  <div
                    ref={igvContainerRef}
                    className="border rounded"
                    style={{
                      width: '100%',
                      minHeight: '600px',
                      backgroundColor: '#f8f9fa'
                    }}
                  />
                </div>
              )}
              
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IGVViewer;