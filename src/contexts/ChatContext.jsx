import React, { createContext, useContext, useState } from 'react';
import { fileApi } from '../api/fileApi';
import { chatApi } from '../api/chatApi';

// Create the context
export const ChatContext = createContext(null);

export const ChatProvider = ({ children }) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [error, setError] = useState(null);

  // Add a message to the chat
  const addMessage = (sender, content) => {
    const newMessage = {
      id: Date.now(),
      sender,
      content,
      timestamp: new Date().toISOString(),
    };
    
    // Update messages state
    setMessages(prev => [...prev, newMessage]);
    
    // If it's a user message, add to chat history
    if (sender === 'user') {
      setChatHistory(prev => [...prev, { role: 'user', content }]);
    } else if (sender === 'agent') {
      setChatHistory(prev => [...prev, { role: 'assistant', content }]);
    }

    return newMessage;
  };

  // Add a system message (info, error, etc.)
  const addSystemMessage = (type, content) => {
    // Remove any existing message of the same type
    const filteredMessages = messages.filter(msg => 
      !(msg.sender === 'system' && msg.type === type)
    );
    
    const newMessage = {
      id: Date.now(),
      sender: 'system',
      type, // 'info', 'error', 'typing', etc.
      content,
      timestamp: new Date().toISOString(),
    };
    
    setMessages([...filteredMessages, newMessage]);
    return newMessage;
  };

  // Send a message to the chat API
  const sendMessage = async (content) => {
    try {
      setIsLoading(true);
      addMessage('user', content);
      
      // Generate a typing indicator
      addSystemMessage('typing', null);

      try {
        // Mock response for now
        setTimeout(() => {
          // Remove typing indicator
          setMessages(prev => prev.filter(msg => !(msg.sender === 'system' && msg.type === 'typing')));
          
          // Add the response from the agent
          addMessage('agent', `This is a mock response to: "${content}"`);
          setIsLoading(false);
        }, 1500);
        
        return { success: true, response: { content: "Mock response" } };
      } catch (apiError) {
        throw apiError;
      }
    } catch (error) {
      setIsLoading(false);
      setError(error.message || 'Failed to send message');
      addSystemMessage('error', error.message || 'Failed to send message');
      return { success: false, error };
    }
  };

  // Upload a file to use with agents
  const uploadFile = async (files) => {
    try {
      setIsLoading(true);
      
      // Track uploaded files
      const newFiles = Array.from(files).map(file => ({
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified
      }));
      
      // Mock upload for now
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setUploadedFiles(prev => [...prev, ...newFiles]);
      setIsLoading(false);
      
      return newFiles.map((_, i) => `file-${Date.now()}-${i}`); // Return mock file IDs
    } catch (error) {
      setIsLoading(false);
      setError(error.message || 'Failed to upload file');
      throw error; // Re-throw so caller can handle
    }
  };

  // Clear the chat history
  const clearChat = () => {
    if (window.confirm('Are you sure you want to clear the chat history?')) {
      setMessages([]);
      setChatHistory([]);
      addSystemMessage('info', 'Chat history cleared');
    }
  };

  // Value to be provided by the context
  const value = {
    messages,
    setMessages,
    isLoading,
    error,
    chatHistory,
    uploadedFiles,
    addMessage,
    addSystemMessage,
    sendMessage,
    uploadFile,
    clearChat
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};

export default ChatContext;