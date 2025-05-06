import { useState, useCallback } from 'react';
import { fileApi } from '../api/fileApi';

/**
 * Custom hook for managing file uploads to the RAG database
 */
export const useFileUpload = () => {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);

  /**
   * Upload files to the RAG database
   */
  const uploadFiles = useCallback(async (files) => {
    if (!files || files.length === 0) return [];
    
    try {
      setIsUploading(true);
      setError(null);
      setUploadProgress(0);
      
      // Add files to local state for UI
      const newFiles = Array.from(files).map(file => ({
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified,
        status: 'uploading'
      }));
      
      setUploadedFiles(prev => [...prev, ...newFiles]);
      
      // Create form data for API
      const formData = new FormData();
      Array.from(files).forEach((file, index) => {
        formData.append(`file${index}`, file);
      });
      
      // Configure upload with progress tracking
      const config = {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        }
      };
      
      // Call API to upload
      const response = await fileApi.uploadFiles(formData, config);
      
      // Update status of uploaded files
      setUploadedFiles(prev => 
        prev.map(file => {
          if (newFiles.some(newFile => newFile.name === file.name && newFile.lastModified === file.lastModified)) {
            return { ...file, status: 'uploaded', id: response.fileIds[file.name] };
          }
          return file;
        })
      );
      
      setIsUploading(false);
      setUploadProgress(100);
      
      return response.fileIds;
    } catch (err) {
      setError(err.message || 'Error uploading files');
      
      // Update status of failed files
      setUploadedFiles(prev => 
        prev.map(file => {
          if (newFiles.some(newFile => newFile.name === file.name && newFile.lastModified === file.lastModified)) {
            return { ...file, status: 'error' };
          }
          return file;
        })
      );
      
      setIsUploading(false);
      throw err;
    }
  }, []);

  /**
   * Remove a file from the local state
   */
  const removeFile = useCallback((fileToRemove) => {
    setUploadedFiles(prev => 
      prev.filter(file => 
        !(file.name === fileToRemove.name && file.lastModified === fileToRemove.lastModified)
      )
    );
  }, []);

  /**
   * Delete a file from the RAG database
   */
  const deleteFile = useCallback(async (fileId) => {
    try {
      await fileApi.deleteFile(fileId);
      
      // Remove from local state
      setUploadedFiles(prev => 
        prev.filter(file => file.id !== fileId)
      );
      
      return { success: true };
    } catch (err) {
      setError(err.message || 'Error deleting file');
      return { success: false, error: err };
    }
  }, []);

  /**
   * Clear all files from local state
   */
  const clearFiles = useCallback(() => {
    setUploadedFiles([]);
  }, []);

  return {
    uploadedFiles,
    isUploading,
    uploadProgress,
    error,
    uploadFiles,
    removeFile,
    deleteFile,
    clearFiles
  };
};