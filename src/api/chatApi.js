// src/api/chatApi.js
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const chatApi = {
  // Send a message to the chat API
  sendMessage: async (message, history = [], collection = 'default') => {
    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message,
        history,
        collection
      });
      return response.data;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error.response?.data || error;
    }
  },

  // Chat with WebSocket for real-time responses
  setupWebSocketChat: () => {
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws');
    const socket = new WebSocket(`${wsUrl}/ws/chat`);
    
    return {
      socket,
      
      connect: (onMessage, onOpen, onClose, onError) => {
        socket.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (onMessage) onMessage(data);
        };
        
        socket.onopen = () => {
          if (onOpen) onOpen();
        };
        
        socket.onclose = (event) => {
          if (onClose) onClose(event);
        };
        
        socket.onerror = (error) => {
          if (onError) onError(error);
        };
      },
      
      send: (message, history = [], collection = 'default') => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({
            message,
            history,
            collection
          }));
          return true;
        }
        return false;
      },
      
      disconnect: () => {
        socket.close();
      }
    };
  }
};