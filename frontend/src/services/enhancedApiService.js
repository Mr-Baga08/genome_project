// frontend/src/services/enhancedApiService.js
import axios from 'axios';

class EnhancedApiService {
  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    this.timeout = 30000; // 30 seconds
    
    // Create axios instance
    this.api = axios.create({
      baseURL: this.baseURL,
      timeout: this.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('authToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        
        // Add user ID
        const userId = localStorage.getItem('userId');
        if (userId) {
          config.headers['X-User-ID'] = userId;
        }

        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('Request interceptor error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        console.error('API Error:', error.response?.status, error.response?.data || error.message);
        
        // Handle specific error cases
        if (error.response?.status === 401) {
          // Unauthorized - clear auth token
          localStorage.removeItem('authToken');
          // Could redirect to login
        }
        
        if (error.response?.status >= 500) {
          // Server error - show user-friendly message
          this.showErrorNotification('Server error occurred. Please try again.');
        }

        return Promise.reject(error);
      }
    );
  }

  // Generic HTTP methods
  async get(url, params = {}) {
    try {
      const response = await this.api.get(url, { params });
      return response;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async post(url, data = {}, config = {}) {
    try {
      const response = await this.api.post(url, data, config);
      return response;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async put(url, data = {}) {
    try {
      const response = await this.api.put(url, data);
      return response;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async delete(url) {
    try {
      const response = await this.api.delete(url);
      return response;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Sequence Management API
  async createSequence(sequenceData, annotationsFile = null) {
    const formData = new FormData();
    formData.append('name', sequenceData.name);
    formData.append('sequence', sequenceData.sequence);
    
    if (sequenceData.sequence_type) {
      formData.append('sequence_type', sequenceData.sequence_type);
    }
    if (sequenceData.description) {
      formData.append('description', sequenceData.description);
    }
    if (sequenceData.organism_id) {
      formData.append('organism_id', sequenceData.organism_id);
    }
    if (annotationsFile) {
      formData.append('annotations_file', annotationsFile);
    }

    return this.post('/api/v1/sequences/create', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  async createSequencesBatch(fastaFile, organismId = null, isPublic = false) {
    const formData = new FormData();
    formData.append('fasta_file', fastaFile);
    if (organismId) {
      formData.append('organism_id', organismId);
    }
    formData.append('is_public', isPublic);

    return this.post('/api/v1/sequences/batch-create', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  async getSequences(page = 1, limit = 20, sequenceType = null, userId = null) {
    const params = { skip: (page - 1) * limit, limit };
    if (sequenceType) params.sequence_type = sequenceType;
    if (userId) params.user_id = userId;
    
    return this.get('/api/v1/sequences', params);
  }

  // Analysis API
  async runBlastSearch(sequences, database = 'nr', evalue = 1e-5, maxHits = 10, wordSize = null) {
    return this.post('/api/v1/analysis/blast-search', {
      sequences,
      database,
      evalue,
      max_hits: maxHits,
      word_size: wordSize
    });
  }

  async runMultipleAlignment(sequences, method = 'muscle', parameters = {}) {
    return this.post('/api/v1/analysis/multiple-alignment', {
      sequences,
      method,
      parameters
    });
  }

  async runPhylogeneticAnalysis(alignmentData, method = 'iqtree', model = 'AUTO', bootstrap = 1000) {
    const formData = new FormData();
    formData.append('alignment_data', alignmentData);
    formData.append('method', method);
    formData.append('model', model);
    formData.append('bootstrap', bootstrap);

    return this.post('/api/v1/analysis/phylogeny', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  async runGenePrediction(sequence, organismType = 'bacteria', mode = 'single') {
    const formData = new FormData();
    formData.append('sequence', sequence);
    formData.append('organism_type', organismType);
    formData.append('mode', mode);

    return this.post('/api/v1/analysis/gene-prediction', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  async runDomainSearch(proteinSequences, database = 'pfam', evalue = 1e-3) {
    return this.post('/api/v1/analysis/domain-search', {
      protein_sequences: proteinSequences,
      database,
      evalue
    });
  }

  // Pipeline API
  async createPipeline(pipelineName, description, steps) {
    const formData = new FormData();
    formData.append('pipeline_name', pipelineName);
    formData.append('description', description);
    formData.append('steps', JSON.stringify(steps));

    return this.post('/api/v1/pipelines/create', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  async executePipeline(pipelineId, sequenceIds) {
    return this.post(`/api/v1/pipelines/${pipelineId}/execute`, {
      sequence_ids: sequenceIds
    });
  }

  async getPipelines() {
    return this.get('/api/v1/pipelines');
  }

  // File Management API
  async uploadFastaFile(file, organismId = null) {
    const formData = new FormData();
    formData.append('file', file);
    if (organismId) {
      formData.append('organism_id', organismId);
    }

    return this.post('/api/v1/files/upload-fasta', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  async exportResults(executionId, format = 'json') {
    return this.post(`/api/v1/files/export-results/${executionId}`, { format });
  }

  // Cache Management API
  async getCacheStats() {
    return this.get('/api/v1/cache/stats');
  }

  async invalidateCache(pattern) {
    return this.delete(`/api/v1/cache/invalidate?pattern=${encodeURIComponent(pattern)}`);
  }

  async warmCache(sequenceIds, analysisTypes) {
    return this.post('/api/v1/cache/warm', {
      sequence_ids: sequenceIds,
      analysis_types: analysisTypes
    });
  }

  // System API
  async getSystemHealth() {
    return this.get('/api/v1/system/health');
  }

  async getAvailableTools() {
    return this.get('/api/v1/system/tools');
  }

  // File download helper
  async downloadFile(url, filename) {
    try {
      const response = await this.api.get(url, {
        responseType: 'blob',
      });

      // Create blob link to download
      const blob = new Blob([response.data]);
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = filename;
      
      // Trigger download
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up
      window.URL.revokeObjectURL(link.href);
      
      return true;
    } catch (error) {
      console.error('Download failed:', error);
      throw error;
    }
  }

  // Error handling
  handleError(error) {
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.detail || error.response.data?.message || error.message;
      return new Error(`${error.response.status}: ${message}`);
    } else if (error.request) {
      // Request made but no response received
      return new Error('Network error: No response from server');
    } else {
      // Something else happened
      return new Error(`Request error: ${error.message}`);
    }
  }

  // Notification helper (can be replaced with actual notification system)
  showErrorNotification(message) {
    console.error('API Error Notification:', message);
    // Integrate with your notification system here
  }

  // Utility methods
  buildQueryString(params) {
    return new URLSearchParams(params).toString();
  }

  // Upload progress tracking
  async uploadWithProgress(url, formData, onProgress) {
    return this.api.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        if (onProgress) {
          onProgress(percentCompleted);
        }
      },
    });
  }

  // Batch request helper
  async batchRequests(requests, maxConcurrent = 5) {
    const results = [];
    
    for (let i = 0; i < requests.length; i += maxConcurrent) {
      const batch = requests.slice(i, i + maxConcurrent);
      const batchPromises = batch.map(request => request());
      
      try {
        const batchResults = await Promise.all(batchPromises);
        results.push(...batchResults);
      } catch (error) {
        console.error('Batch request failed:', error);
        throw error;
      }
    }
    
    return results;
  }
}

// Create and export singleton instance
const enhancedApiService = new EnhancedApiService();
export default enhancedApiService;

// Also export the class for testing
export { EnhancedApiService };