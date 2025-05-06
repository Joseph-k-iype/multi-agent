// src/api/workflowApi.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Replace with your API URL

export const workflowApi = {
  // Run workflow with dynamic configuration
  runWorkflow: async (workflowData) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/run-workflow`, workflowData);
      return response.data;
    } catch (error) {
      console.error('Error running workflow:', error);
      throw error.response?.data || error;
    }
  },

  // Check health of the backend service
  checkHealth: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      throw error.response?.data || error;
    }
  }
};