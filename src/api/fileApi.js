// src/api/fileApi.js
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const fileApi = {
  // Upload files for RAG
  uploadFiles: async (formData, config = {}) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/upload-files`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        ...config
      });
      return response.data;
    } catch (error) {
      console.error('File upload failed:', error);
      throw error.response?.data || error;
    }
  },

  // Index a file for RAG
  indexFile: async (fileId, collection = 'default') => {
    try {
      const response = await axios.post(`${API_BASE_URL}/index-file`, {
        file_id: fileId,
        collection
      });
      return response.data;
    } catch (error) {
      console.error('Error indexing file:', error);
      throw error.response?.data || error;
    }
  },

  // List files in the RAG database
  listFiles: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/list-files`);
      return response.data;
    } catch (error) {
      console.error('Error listing files:', error);
      throw error.response?.data || error;
    }
  },

  // List all collections
  listCollections: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/list-collections`);
      return response.data;
    } catch (error) {
      console.error('Error listing collections:', error);
      throw error.response?.data || error;
    }
  },

  // Get collection info
  getCollectionInfo: async (collectionName) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/collection-info/${collectionName}`);
      return response.data;
    } catch (error) {
      console.error(`Error getting collection info for ${collectionName}:`, error);
      throw error.response?.data || error;
    }
  },

  // Delete a file from the RAG database
  deleteFile: async (fileId) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/delete-file/${fileId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting file:', error);
      throw error.response?.data || error;
    }
  }
};