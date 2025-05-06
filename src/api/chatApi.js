// src/api/chatApi.js
export const chatApi = {
    // Send a message to the chat API
    sendMessage: async (content, history = []) => {
      try {
        const response = await axios.post(`${API_BASE_URL}/chat`, {
          message: content,
          history
        });
        return response.data;
      } catch (error) {
        console.error('Error sending message:', error);
        throw error.response?.data || error;
      }
    },
  
    // Start a new chat session
    startSession: async () => {
      try {
        const response = await axios.post(`${API_BASE_URL}/chat/session`);
        return response.data;
      } catch (error) {
        console.error('Error starting chat session:', error);
        throw error.response?.data || error;
      }
    }
  };