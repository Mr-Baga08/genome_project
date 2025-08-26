// frontend/src/services/apiService.js - Enhanced and completed with all endpoints

class ApiService {
  constructor() {
    this.baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    this.token = null; // Placeholder for JWT token
  }

  // Method to set the authentication token
  setAuthToken(token) {
    this.token = token;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add authorization header if a token is set
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const config = {
      headers,
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        // Try to parse error details from the response body
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      // Handle responses that might not have a body (e.g., 204 No Content)
      if (response.status === 204) {
        return null;
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // ============================================================================
  // EXISTING METHODS (keep these)
  // ============================================================================

  async submitWorkflow(workflowData, priority = 'medium') {
    return await this.request('/api/v1/workflows/execute', {
      method: 'POST',
      body: JSON.stringify({
        workflow_definition: {
            nodes: workflowData.nodes,
            connections: workflowData.connections,
        },
        priority: priority,
      }),
    });
  }

  async getAllTasks(page = 1, size = 10) {
    return await this.request(`/api/v1/tasks/?page=${page}&size=${size}`);
  }

  async getTaskDetails(taskId) {
    return await this.request(`/api/v1/tasks/${taskId}`);
  }

  async uploadFiles(files) {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    const headers = {};
    if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
    }

    return await fetch(`${this.baseURL}/upload`, {
      method: 'POST',
      body: formData,
      headers,
    }).then(response => {
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }
      return response.json();
    });
  }

  // ============================================================================
  // DATA WRITERS API METHODS
  // ============================================================================

  async writeFastaFile(sequences, filename = null, parameters = {}) {
    return await this.request('/api/v1/data-writers/write-fasta', {
      method: 'POST',
      body: JSON.stringify({ sequences, filename, parameters })
    });
  }

  async writeFastqFile(sequences, filename = null, parameters = {}) {
    return await this.request('/api/v1/data-writers/write-fastq', {
      method: 'POST',
      body: JSON.stringify({ sequences, filename, parameters })
    });
  }

  async writeGff3File(annotations, filename = null, parameters = {}) {
    return await this.request('/api/v1/data-writers/write-gff3', {
      method: 'POST',
      body: JSON.stringify({ annotations, filename, parameters })
    });
  }

  async writeBedFile(features, filename = null, parameters = {}) {
    return await this.request('/api/v1/data-writers/write-bed', {
      method: 'POST',
      body: JSON.stringify({ features, filename, parameters })
    });
  }

  async writeVcfFile(variants, filename = null, parameters = {}) {
    return await this.request('/api/v1/data-writers/write-vcf', {
      method: 'POST',
      body: JSON.stringify({ variants, filename, parameters })
    });
  }

  async writeMultipleFormats(data, formats, baseFilename = null, parameters = {}) {
    return await this.request('/api/v1/data-writers/write-multiple-formats', {
      method: 'POST',
      body: JSON.stringify({ data, formats, base_filename: baseFilename, parameters })
    });
  }

  async exportAnalysisResults(results, formatType, filename = null) {
    return await this.request('/api/v1/data-writers/export-analysis-results', {
      method: 'POST',
      body: JSON.stringify({ results, format_type: formatType, filename })
    });
  }

  async getSupportedWriteFormats() {
    return await this.request('/api/v1/data-writers/formats');
  }

  async downloadFile(operationId) {
    const url = `${this.baseURL}/api/v1/data-writers/download/${operationId}`;
    const headers = {};
    if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
    }
    return fetch(url, { headers });
  }

  // ============================================================================
  // DATA CONVERTERS API METHODS
  // ============================================================================

  async convertFormat(data, inputFormat, outputFormat, parameters = {}) {
    return await this.request('/api/v1/data-converters/convert-format', {
      method: 'POST',
      body: JSON.stringify({
        data,
        input_format: inputFormat,
        output_format: outputFormat,
        parameters
      })
    });
  }

  async convertSequences(sequences, conversionType, parameters = {}) {
    return await this.request('/api/v1/data-converters/convert-sequences', {
      method: 'POST',
      body: JSON.stringify({
        sequences,
        conversion_type: conversionType,
        parameters
      })
    });
  }

  async reverseComplement(sequences) {
    return await this.request('/api/v1/data-converters/reverse-complement', {
      method: 'POST',
      body: JSON.stringify({ sequences })
    });
  }

  async convertTextToSequence(textData, sequenceType = 'DNA', parameters = {}) {
    return await this.request('/api/v1/data-converters/text-to-sequence', {
      method: 'POST',
      body: JSON.stringify({
        text_data: textData,
        sequence_type: sequenceType,
        parameters
      })
    });
  }

  async convertCoordinates(coordinates, conversionType) {
    return await this.request('/api/v1/data-converters/convert-coordinates', {
      method: 'POST',
      body: JSON.stringify({
        coordinates,
        conversion_type: conversionType
      })
    });
  }

  async getSupportedConversions() {
    return await this.request('/api/v1/data-converters/supported-conversions');
  }

  async convertUploadedFile(file, inputFormat, outputFormat, parameters = {}) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('input_format', inputFormat);
    formData.append('output_format', outputFormat);
    formData.append('parameters', JSON.stringify(parameters));
    
    const headers = {};
    if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
    }

    return await fetch(`${this.baseURL}/api/v1/data-converters/convert-file`, {
      method: 'POST',
      body: formData,
      headers,
    }).then(res => res.json());
  }

  // ============================================================================
  // DATA FLOW API METHODS
  // ============================================================================

  async filterSequences(sequences, criteria) {
    return await this.request('/api/v1/data-flow/filter-sequences', {
      method: 'POST',
      body: JSON.stringify({ sequences, criteria })
    });
  }

  async groupSequences(sequences, groupBy, parameters = {}) {
    return await this.request('/api/v1/data-flow/group-sequences', {
      method: 'POST',
      body: JSON.stringify({
        sequences,
        group_by: groupBy,
        parameters
      })
    });
  }

  async sortSequences(sequences, sortBy, reverse = false) {
    return await this.request('/api/v1/data-flow/sort-sequences', {
      method: 'POST',
      body: JSON.stringify({
        sequences,
        sort_by: sortBy,
        reverse
      })
    });
  }

  async splitData(data, splitCriteria) {
    return await this.request('/api/v1/data-flow/split-data', {
      method: 'POST',
      body: JSON.stringify({
        data,
        split_criteria: splitCriteria
      })
    });
  }

  async multiplexData(dataSources, operation) {
    return await this.request('/api/v1/data-flow/multiplex-data', {
      method: 'POST',
      body: JSON.stringify({
        data_sources: dataSources,
        operation
      })
    });
  }

  async validateDataIntegrity(data, validationRules) {
    return await this.request('/api/v1/data-flow/validate-data-integrity', {
      method: 'POST',
      body: JSON.stringify({
        data,
        validation_rules: validationRules
      })
    });
  }

  async calculateSequenceStatistics(sequences) {
    return await this.request('/api/v1/data-flow/calculate-sequence-statistics', {
      method: 'POST',
      body: JSON.stringify({ sequences })
    });
  }

  // ============================================================================
  // DNA ASSEMBLY API METHODS
  // ============================================================================

  async runOLCAssembly(reads, parameters = {}) {
    return await this.request('/api/v1/dna-assembly/olc-assembly', {
      method: 'POST',
      body: JSON.stringify({ reads, parameters })
    });
  }

  async runKmerAssembly(reads, parameters = {}) {
    return await this.request('/api/v1/dna-assembly/kmer-assembly', {
      method: 'POST',
      body: JSON.stringify({ reads, parameters })
    });
  }

  async runSpadesAssembly(reads, parameters = {}) {
    return await this.request('/api/v1/dna-assembly/spades-assembly', {
      method: 'POST',
      body: JSON.stringify({ reads, parameters })
    });
  }

  async runCap3Assembly(reads, parameters = {}) {
    return await this.request('/api/v1/dna-assembly/cap3-assembly', {
      method: 'POST',
      body: JSON.stringify({ reads, parameters })
    });
  }

  async evaluateAssemblyQuality(contigs, referenceSequences = null) {
    return await this.request('/api/v1/dna-assembly/evaluate-quality', {
      method: 'POST',
      body: JSON.stringify({
        contigs,
        reference_sequences: referenceSequences
      })
    });
  }

  async compareAssemblies(assemblies) {
    return await this.request('/api/v1/dna-assembly/compare-assemblies', {
      method: 'POST',
      body: JSON.stringify({ assemblies })
    });
  }

  async runAssemblyPipeline(reads, algorithms = ['spades', 'cap3'], compareResults = true) {
    return await this.request('/api/v1/dna-assembly/run-assembly-pipeline', {
      method: 'POST',
      body: JSON.stringify({
        reads,
        algorithms,
        compare_results: compareResults
      })
    });
  }

  async getAssemblyPipelineStatus(pipelineId) {
    return await this.request(`/api/v1/dna-assembly/pipeline-status/${pipelineId}`);
  }

  async exportContigs(contigs, formatType = 'fasta', filename = null) {
    return await this.request('/api/v1/dna-assembly/export-contigs', {
      method: 'POST',
      body: JSON.stringify({
        contigs,
        format_type: formatType,
        filename
      })
    });
  }

  // ============================================================================
  // NGS MAPPING API METHODS
  // ============================================================================

  async mapReads(reads, referenceSequence, parameters = {}) {
    return await this.request('/api/v1/ngs-mapping/map-reads', {
      method: 'POST',
      body: JSON.stringify({
        reads,
        reference_sequence: referenceSequence,
        parameters
      })
    });
  }

  async mapPairedReads(pairedReads, referenceSequence, parameters = {}) {
    return await this.request('/api/v1/ngs-mapping/map-paired-reads', {
      method: 'POST',
      body: JSON.stringify({
        paired_reads: pairedReads,
        reference_sequence: referenceSequence,
        parameters
      })
    });
  }

  async mapLongReads(reads, referenceSequence, algorithm = 'minimap2', preset = 'map-ont') {
    return await this.request('/api/v1/ngs-mapping/map-long-reads', {
      method: 'POST',
      body: JSON.stringify({
        reads,
        reference_sequence: referenceSequence,
        algorithm,
        preset
      })
    });
  }

  async analyzeCoverage(mappedReads, referenceLength, windowSize = 1000) {
    return await this.request('/api/v1/ngs-mapping/analyze-coverage', {
      method: 'POST',
      body: JSON.stringify({
        mapped_reads: mappedReads,
        reference_length: referenceLength,
        window_size: windowSize
      })
    });
  }

  async calculateMappingStatistics(mappedReads, unmappedReads = []) {
    return await this.request('/api/v1/ngs-mapping/mapping-statistics', {
      method: 'POST',
      body: JSON.stringify({
        mapped_reads: mappedReads,
        unmapped_reads: unmappedReads,
        detailed_analysis: true
      })
    });
  }

  async callVariants(mappedReads, referenceSequence, parameters = {}) {
    return await this.request('/api/v1/ngs-mapping/call-variants', {
      method: 'POST',
      body: JSON.stringify({
        mapped_reads: mappedReads,
        reference_sequence: referenceSequence,
        parameters
      })
    });
  }

  async getMappingAlgorithms() {
    return await this.request('/api/v1/ngs-mapping/algorithms');
  }

  async getRecommendedMappingParameters(readType, dataType, readLength) {
    return await this.request(`/api/v1/ngs-mapping/recommended-parameters?read_type=${readType}&data_type=${dataType}&read_length=${readLength}`);
  }

  // ============================================================================
  // MONITORING API METHODS
  // ============================================================================

  async getSystemHealth() {
    return await this.request('/api/v1/monitoring/health');
  }

  async getSystemMetrics() {
    return await this.request('/api/v1/monitoring/system-metrics');
  }

  async getPerformanceHistory(hours = 24, metric = 'all') {
    return await this.request(`/api/v1/monitoring/performance-history?hours=${hours}&metric=${metric}`);
  }

  async getResourceUsage() {
    return await this.request('/api/v1/monitoring/resource-usage');
  }

  async getApiPerformance() {
    return await this.request('/api/v1/monitoring/api-performance');
  }

  async getTaskQueueStatus() {
    return await this.request('/api/v1/monitoring/task-queue-status');
  }

  async getErrorLogs(hours = 24, severity = 'all', limit = 100) {
    return await this.request(`/api/v1/monitoring/error-logs?hours=${hours}&severity=${severity}&limit=${limit}`);
  }

  async getContainerStatus() {
    return await this.request('/api/v1/monitoring/container-status');
  }

  async runSystemDiagnostics(diagnosticType = 'full') {
    return await this.request('/api/v1/monitoring/run-diagnostics', {
      method: 'POST',
      body: JSON.stringify({ diagnostic_type: diagnosticType })
    });
  }

  async getDiagnosticsStatus(diagnosticId) {
    return await this.request(`/api/v1/monitoring/diagnostics-status/${diagnosticId}`);
  }

  // ============================================================================
  // SYSTEM ADMIN API METHODS (Require admin permissions)
  // ============================================================================

  async scheduleSystemMaintenance(operationType, parameters = {}, scheduleTime = null) {
    return await this.request('/api/v1/admin/system/maintenance', {
      method: 'POST',
      body: JSON.stringify({
        operation_type: operationType,
        parameters,
        schedule_time: scheduleTime
      })
    });
  }

  async getMaintenanceStatus(maintenanceId) {
    return await this.request(`/api/v1/admin/maintenance-status/${maintenanceId}`);
  }

  async cleanupFilesystem(directories = ['temp', 'uploads', 'outputs'], maxAgeDays = 7, dryRun = false) {
    return await this.request('/api/v1/admin/filesystem/cleanup', {
      method: 'POST',
      body: JSON.stringify({
        target_directories: directories,
        max_age_days: maxAgeDays,
        dry_run: dryRun
      })
    });
  }

  async getFilesystemUsage() {
    return await this.request('/api/v1/admin/filesystem/usage');
  }

  async getDatabaseStatistics() {
    return await this.request('/api/v1/admin/database/statistics');
  }

  async listUsers(page = 1, size = 50, statusFilter = 'all', roleFilter = 'all') {
    return await this.request(`/api/v1/admin/users/list?page=${page}&size=${size}&status_filter=${statusFilter}&role_filter=${roleFilter}`);
  }

  async manageUser(action, userData) {
    return await this.request('/api/v1/admin/users/manage', {
      method: 'POST',
      body: JSON.stringify({
        action,
        user_data: userData
      })
    });
  }

  async updateSystemConfig(configSection, configValues, applyImmediately = true) {
    return await this.request('/api/v1/admin/config/update', {
      method: 'POST',
      body: JSON.stringify({
        config_section: configSection,
        config_values: configValues,
        apply_immediately: applyImmediately
      })
    });
  }

  async getCurrentConfig(section = null) {
    const url = section ? `/api/v1/admin/config/current?section=${section}` : '/api/v1/admin/config/current';
    return await this.request(url);
  }

  async listDockerContainers() {
    return await this.request('/api/v1/admin/docker/containers');
  }

  async cleanupDockerResources(removeImages = true, removeContainers = true, removeVolumes = false) {
    return await this.request('/api/v1/admin/docker/cleanup', {
      method: 'POST',
      body: JSON.stringify({
        remove_unused_images: removeImages,
        remove_stopped_containers: removeContainers,
        remove_unused_volumes: removeVolumes
      })
    });
  }

  // ============================================================================
  // SPECIALIZED ANALYSIS METHODS
  // ============================================================================

  async runBasicAnalysis(sequences, analysisType, parameters = {}) {
    return await this.request('/api/v1/analysis/basic-analysis', {
      method: 'POST',
      body: JSON.stringify({
        sequences,
        analysis_type: analysisType,
        parameters
      })
    });
  }

  async searchTFBS(sequences, motifs, parameters = {}) {
    return await this.request('/api/v1/analysis/tfbs-search', {
      method: 'POST',
      body: JSON.stringify({
        sequences,
        motifs,
        parameters
      })
    });
  }

  async executeCustomScript(scriptContent, scriptType, inputData, parameters = {}) {
    return await this.request('/api/v1/analysis/custom-script', {
      method: 'POST',
      body: JSON.stringify({
        script_content: scriptContent,
        script_type: scriptType,
        input_data: inputData,
        parameters
      })
    });
  }

  // ============================================================================
  // FILE HANDLING METHODS
  // ============================================================================

  async uploadFileForAnalysis(file, analysisType, parameters = {}) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('analysis_type', analysisType);
    formData.append('parameters', JSON.stringify(parameters));
    
    const headers = {};
    if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
    }

    return await fetch(`${this.baseURL}/api/v1/files/upload-for-analysis`, {
      method: 'POST',
      body: formData,
      headers
    }).then(response => {
      if (!response.ok) {
        throw new Error(`File upload failed: ${response.statusText}`);
      }
      return response.json();
    });
  }

  async validateFileFormat(file, expectedFormat) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('expected_format', expectedFormat);

    const headers = {};
    if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
    }

    return await fetch(`${this.baseURL}/api/v1/files/validate-format`, {
      method: 'POST',
      body: formData,
      headers
    }).then(response => response.json());
  }

  // ============================================================================
  // WEBSOCKET METHODS
  // ============================================================================

  createWebSocketConnection(endpoint, onMessage, onError, onClose) {
    const wsURL = `${this.baseURL.replace(/^http/, 'ws')}${endpoint}`;
    const socket = new WebSocket(wsURL);

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('WebSocket message parsing error:', error, event.data);
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (onError) onError(error);
    };

    socket.onclose = (event) => {
      console.log('WebSocket connection closed:', event.code, event.reason);
      if (onClose) onClose(event);
    };

    return socket;
  }

  createTaskStatusWebSocket(taskId, onMessage, onError, onClose) {
    return this.createWebSocketConnection(
      `/ws/tasks/${taskId}`,
      onMessage,
      onError,
      onClose
    );
  }

  createAssemblyProgressWebSocket(assemblyId, onMessage, onError, onClose) {
    return this.createWebSocketConnection(
      `/ws/assembly-progress/${assemblyId}`,
      onMessage,
      onError,
      onClose
    );
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  async checkHealth() {
    return await this.request('/health');
  }

  async getSystemInfo() {
    return await this.request('/info');
  }

  // Batch operations helper
  async executeBatchOperation(operation, dataList, batchSize = 10) {
    const results = [];
    
    for (let i = 0; i < dataList.length; i += batchSize) {
      const batch = dataList.slice(i, i + batchSize);
      
      try {
        const batchResult = await operation(batch);
        results.push({
          batch_index: Math.floor(i / batchSize),
          success: true,
          result: batchResult
        });
      } catch (error) {
        results.push({
          batch_index: Math.floor(i / batchSize),
          success: false,
          error: error.message
        });
      }
    }
    
    return {
      total_batches: Math.ceil(dataList.length / batchSize),
      successful_batches: results.filter(r => r.success).length,
      failed_batches: results.filter(r => !r.success).length,
      results
    };
  }

  // Error handling wrapper
  async safeRequest(endpoint, options = {}, retries = 3) {
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        return await this.request(endpoint, options);
      } catch (error) {
        if (attempt === retries) {
          throw error;
        }
        
        // Wait before retry (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 100));
      }
    }
  }
}

// Create and export singleton instance
const apiService = new ApiService();
export default apiService;

// Named exports for specific functions for easier import
export const {
  // Existing methods
  submitWorkflow,
  getAllTasks,
  getTaskDetails,
  uploadFiles,
  checkHealth,
  
  // Data Writers methods
  writeFastaFile,
  writeFastqFile,
  writeGff3File,
  writeBedFile,
  writeVcfFile,
  writeMultipleFormats,
  exportAnalysisResults,
  getSupportedWriteFormats,
  downloadFile,
  
  // Data Converters methods
  convertFormat,
  convertSequences,
  reverseComplement,
  convertTextToSequence,
  convertCoordinates,
  getSupportedConversions,
  convertUploadedFile,
  
  // Data Flow methods
  filterSequences,
  groupSequences,
  sortSequences,
  splitData,
  multiplexData,
  validateDataIntegrity,
  calculateSequenceStatistics,
  
  // DNA Assembly methods
  runOLCAssembly,
  runKmerAssembly,
  runSpadesAssembly,
  runCap3Assembly,
  evaluateAssemblyQuality,
  compareAssemblies,
  runAssemblyPipeline,
  getAssemblyPipelineStatus,
  exportContigs,
  
  // NGS Mapping methods
  mapReads,
  mapPairedReads,
  mapLongReads,
  analyzeCoverage,
  calculateMappingStatistics,
  callVariants,
  getMappingAlgorithms,
  getRecommendedMappingParameters,
  
  // Monitoring methods
  getSystemHealth,
  getSystemMetrics,
  getPerformanceHistory,
  getResourceUsage,
  getApiPerformance,
  getTaskQueueStatus,
  getErrorLogs,
  getContainerStatus,
  runSystemDiagnostics,
  getDiagnosticsStatus,
  
  // System Admin methods
  scheduleSystemMaintenance,
  getMaintenanceStatus,
  cleanupFilesystem,
  getFilesystemUsage,
  getDatabaseStatistics,
  listUsers,
  manageUser,
  updateSystemConfig,
  getCurrentConfig,
  listDockerContainers,
  cleanupDockerResources,
  
  // Specialized Analysis methods
  runBasicAnalysis,
  searchTFBS,
  executeCustomScript,
  
  // Utility methods
  createWebSocketConnection,
  createTaskStatusWebSocket,
  createAssemblyProgressWebSocket,
  executeBatchOperation,
  safeRequest
} = apiService;
