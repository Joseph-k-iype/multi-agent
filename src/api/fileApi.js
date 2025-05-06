// src/api/fileApi.js
export const fileApi = {
    // Upload files for RAG
    uploadFiles: async (files) => {
      try {
        const formData = new FormData();
        Array.from(files).forEach((file, index) => {
          formData.append(`file${index}`, file);
        });
  
        const response = await axios.post(`${API_BASE_URL}/upload-files`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        return response.data;
      } catch (error) {
        console.error('File upload failed:', error);
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