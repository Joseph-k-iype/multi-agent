// src/api/workflowApi.js
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

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

  // Save workflow to server (if your backend supports it)
  saveWorkflow: async (workflowData) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/save-workflow`, workflowData);
      return response.data;
    } catch (error) {
      console.error('Error saving workflow:', error);
      throw error.response?.data || error;
    }
  },

  // Load workflow from server (if your backend supports it)
  loadWorkflow: async (workflowId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/workflow/${workflowId}`);
      return response.data;
    } catch (error) {
      console.error('Error loading workflow:', error);
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