// frontend/src/services/apiService.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  // Generic request method with error handling
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // Workflow Management
  async submitWorkflow(workflowData, priority = 'medium') {
    return await this.request('/workflows/', {
      method: 'POST',
      body: JSON.stringify({
        nodes: workflowData.nodes,
        connections: workflowData.connections,
        priority: priority,
      }),
    });
  }

  // Task Management
  async getAllTasks(page = 1, size = 10) {
    return await this.request(`/tasks/?page=${page}&size=${size}`);
  }

  async getTaskDetails(taskId) {
    return await this.request(`/tasks/${taskId}`);
  }

  async getTaskResults(taskId) {
    return await this.request(`/tasks/${taskId}/results`);
  }

  async downloadFile(taskId, filename) {
    const url = `${this.baseURL}/download/${taskId}/${filename}`;
    return fetch(url);
  }

  // File Management
  async uploadFiles(files) {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    return await fetch(`${this.baseURL}/upload`, {
      method: 'POST',
      body: formData,
    }).then(response => {
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }
      return response.json();
    });
  }

  // UMAP Analysis
  async processUmapData(file) {
    const formData = new FormData();
    formData.append('file', file);

    return await fetch(`${this.baseURL}/data/umap`, {
      method: 'POST',
      body: formData,
    }).then(response => {
      if (!response.ok) {
        throw new Error(`UMAP processing failed: ${response.statusText}`);
      }
      return response.json();
    });
  }

  // Health Check
  async checkHealth() {
    return await this.request('/health');
  }

  // WebSocket connection for real-time task updates
  createTaskStatusWebSocket(taskId, onMessage, onError, onClose) {
    const wsURL = `${this.baseURL.replace('http', 'ws')}/ws/tasks/${taskId}`;
    const socket = new WebSocket(wsURL);

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('WebSocket message parsing error:', error);
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (onError) onError(error);
    };

    socket.onclose = (event) => {
      console.log('WebSocket connection closed:', event);
      if (onClose) onClose(event);
    };

    return socket;
  }
}

// Create and export singleton instance
const apiService = new ApiService();
export default apiService;

// Named exports for specific functions
export const {
  submitWorkflow,
  getAllTasks,
  getTaskDetails,
  getTaskResults,
  uploadFiles,
  processUmapData,
  checkHealth,
  downloadFile,
  createTaskStatusWebSocket,
} = apiService;
