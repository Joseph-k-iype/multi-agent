// src/stores/chatStore.js
import { create } from 'zustand';
import { fileApi } from '../api/fileApi';
import { chatApi } from '../api/chatApi';

export const useChatStore = create((set, get) => ({
  messages: [],
  isLoading: false,
  chatHistory: [],
  uploadedFiles: [],
  error: null,
  
  // Add a message to the chat
  addMessage: (sender, content) => {
    const newMessage = {
      id: Date.now(),
      sender,
      content,
      timestamp: new Date().toISOString(),
    };
    
    set((state) => ({
      messages: [...state.messages, newMessage],
      // If it's a user or agent message, add to chat history
      ...(sender === 'user' || sender === 'agent' ? {
        chatHistory: [
          ...state.chatHistory, 
          { role: sender === 'user' ? 'user' : 'assistant', content }
        ]
      } : {})
    }));
    
    return newMessage;
  },
  
  // Add a system message (info, error, etc.)
  addSystemMessage: (type, content) => {
    set((state) => {
      // Remove any existing message of the same type
      const filteredMessages = state.messages.filter(msg => 
        !(msg.sender === 'system' && msg.type === type)
      );
      
      const newMessage = {
        id: Date.now(),
        sender: 'system',
        type, // 'info', 'error', 'typing', etc.
        content,
        timestamp: new Date().toISOString(),
      };
      
      return { messages: [...filteredMessages, newMessage] };
    });
  },
  
  // Send a message to the chat API
  sendMessage: async (content, collection = 'default') => {
    try {
      set({ isLoading: true, error: null });
      
      const { addMessage, addSystemMessage } = get();
      addMessage('user', content);
      
      // Generate a typing indicator
      addSystemMessage('typing', null);
      
      try {
        // Call the API (async)
        const response = await chatApi.sendMessage(content, get().chatHistory);
        
        // Remove typing indicator and add the response
        set((state) => ({
          messages: state.messages.filter(msg => !(msg.sender === 'system' && msg.type === 'typing')),
          isLoading: false
        }));
        
        // Add the agent's response
        addMessage('agent', response.content);
        
        return { success: true, response };
      } catch (apiError) {
        throw apiError;
      }
    } catch (error) {
      set({ 
        isLoading: false,
        error: error.message || 'Failed to send message'
      });
      
      get().addSystemMessage('error', error.message || 'Failed to send message');
      return { success: false, error };
    }
  },
  
  // Upload a file to use with agents
  uploadFile: async (files, collection = 'default') => {
    try {
      set({ isLoading: true, error: null });
      
      // Track uploaded files locally
      const newFiles = Array.from(files).map(file => ({
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified
      }));
      
      // API call to upload files
      const formData = new FormData();
      Array.from(files).forEach((file, index) => {
        formData.append(`files`, file);
      });
      formData.append('collection', collection);
      
      // Upload to backend
      const uploadResponse = await fileApi.uploadFiles(formData);
      
      // Process response
      const fileIds = uploadResponse.map(file => file.file_id);
      
      // Update state with uploaded files
      set((state) => ({
        uploadedFiles: [...state.uploadedFiles, ...newFiles.map((file, index) => ({
          ...file,
          id: fileIds[index]
        }))],
        isLoading: false
      }));
      
      return fileIds; 
    } catch (error) {
      set({ 
        isLoading: false,
        error: error.message || 'Failed to upload file'
      });
      throw error; // Re-throw so caller can handle
    }
  },
  
  // Index a file for RAG
  indexFile: async (fileId, collection = 'default') => {
    try {
      set({ isLoading: true, error: null });
      
      const indexResponse = await fileApi.indexFile(fileId, collection);
      
      set({ isLoading: false });
      
      return indexResponse;
    } catch (error) {
      set({ 
        isLoading: false,
        error: error.message || 'Failed to index file'
      });
      throw error;
    }
  },
  
  // List all collections
  listCollections: async () => {
    try {
      const response = await fileApi.listCollections();
      return response.collections;
    } catch (error) {
      set({ error: error.message || 'Failed to list collections' });
      throw error;
    }
  },
  
  // Clear the chat history
  clearChat: () => {
    if (window.confirm('Are you sure you want to clear the chat history?')) {
      set({ 
        messages: [],
        chatHistory: []
      });
      
      get().addSystemMessage('info', 'Chat history cleared');
    }
  },
  
  // Clear uploaded files
  clearFiles: () => {
    set({ uploadedFiles: [] });
  }
}));