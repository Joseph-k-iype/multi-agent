// src/stores/fileStore.js
import { create } from 'zustand';
import { fileApi } from '../api/fileApi';

export const useFileStore = create((set, get) => ({
  files: [],
  isUploading: false,
  uploadProgress: 0,
  collections: ['default'],
  currentCollection: 'default',
  error: null,
  
  // Fetch all files
  fetchFiles: async () => {
    try {
      set({ error: null });
      const response = await fileApi.listFiles();
      set({ files: response.files });
      return response.files;
    } catch (error) {
      set({ error: error.message || 'Failed to fetch files' });
      throw error;
    }
  },
  
  // Upload files
  uploadFiles: async (files, collection = 'default') => {
    try {
      set({ isUploading: true, uploadProgress: 0, error: null });
      
      const formData = new FormData();
      Array.from(files).forEach((file) => {
        formData.append('files', file);
      });
      formData.append('collection', collection);
      
      // Configure upload with progress tracking
      const config = {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          set({ uploadProgress: percentCompleted });
        }
      };
      
      // Call API to upload
      const response = await fileApi.uploadFiles(formData, config);
      
      // Update file list
      await get().fetchFiles();
      
      set({ isUploading: false, uploadProgress: 100 });
      
      return response;
    } catch (error) {
      set({ error: error.message || 'Failed to upload files', isUploading: false });
      throw error;
    }
  },
  
  // Index a file for RAG
  indexFile: async (fileId, collection = 'default') => {
    try {
      set({ error: null });
      
      const response = await fileApi.indexFile({
        file_id: fileId,
        collection
      });
      
      // Update file list to reflect the change
      await get().fetchFiles();
      
      return response;
    } catch (error) {
      set({ error: error.message || 'Failed to index file' });
      throw error;
    }
  },
  
  // Delete a file
  deleteFile: async (fileId) => {
    try {
      set({ error: null });
      
      await fileApi.deleteFile(fileId);
      
      // Update file list
      set((state) => ({
        files: state.files.filter(file => file.id !== fileId)
      }));
      
      return { success: true };
    } catch (error) {
      set({ error: error.message || 'Failed to delete file' });
      throw error;
    }
  },
  
  // Fetch collections
  fetchCollections: async () => {
    try {
      set({ error: null });
      
      const response = await fileApi.listCollections();
      
      set({ 
        collections: response.collections,
        currentCollection: response.default_collection
      });
      
      return response.collections;
    } catch (error) {
      set({ error: error.message || 'Failed to fetch collections' });
      throw error;
    }
  },
  
  // Set current collection
  setCurrentCollection: (collection) => {
    set({ currentCollection: collection });
  },
  
  // Reset the store
  reset: () => {
    set({
      files: [],
      isUploading: false,
      uploadProgress: 0,
      error: null
    });
  }
}));