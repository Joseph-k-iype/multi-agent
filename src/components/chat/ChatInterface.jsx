import React, { useState, useEffect, useRef } from 'react';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useChatStore } from '../../stores/chatStore';
import { useFileStore } from '../../stores/fileStore';
import ChatMessage from './ChatMessage';
import FileUpload from '../common/FileUpload';

const ChatInterface = () => {
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef(null);
  
  // Use Zustand stores
  const { runWorkflow, isRunning, workflowResult } = useWorkflowStore();
  const { 
    messages, 
    addMessage, 
    addSystemMessage,
    isLoading,
    uploadFile,
    sendMessage
  } = useChatStore();
  
  const { 
    files: uploadedFiles,
    fetchFiles,
    uploadFiles
  } = useFileStore();
  
  // Load files on component mount
  useEffect(() => {
    fetchFiles().catch(err => {
      console.error('Error fetching files:', err);
    });
  }, [fetchFiles]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Run the workflow when user sends a message
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading || isRunning) return;

    // Add user message to chat
    addMessage('user', inputMessage);
    setInputMessage('');

    // Add typing indicator
    addSystemMessage('typing', null);

    try {
      // First attempt direct chat with the LLM
      if (uploadedFiles.length > 0) {
        // If files are uploaded, use RAG approach
        const response = await sendMessage(inputMessage);
        if (response.success) {
          return; // Message handled by chat service
        }
      }
      
      // If no direct chat or it failed, run the workflow
      const result = await runWorkflow(inputMessage);

      // Remove typing indicator and add system message
      addSystemMessage('system', 'Workflow completed!');

      if (result.success) {
        // Extract the final content from the workflow result
        const finalContent = result.result?.final_state?.final_content;
        
        if (finalContent) {
          // Add agent response to chat
          addMessage('agent', finalContent);
        } else {
          // Add system message if no final content
          addSystemMessage('error', 'Workflow did not produce any final content.');
        }
      } else {
        // Handle error
        addSystemMessage('error', result.error || 'An error occurred while running the workflow.');
      }
    } catch (error) {
      // Handle error
      addSystemMessage('error', error.message || 'An error occurred while processing your request.');
    }
  };

  // Handle file upload completion
  const handleFileUpload = async (files) => {
    try {
      addSystemMessage('system', 'Uploading file(s)...');
      
      // Upload files
      const response = await uploadFiles(files);
      
      // Update file list
      await fetchFiles();
      
      addSystemMessage('system', `File(s) uploaded successfully! Added to RAG database.`);
      
    } catch (error) {
      addSystemMessage('error', `File upload failed: ${error.message}`);
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h2>Chat with Your Agents</h2>
        {workflowResult && (
          <span className="workflow-status">
            Last Run: {workflowResult ? 'Success' : 'Failed'}
          </span>
        )}
      </div>

      <div className="file-upload-area">
        <FileUpload onFileUpload={handleFileUpload} />
        
        {uploadedFiles.length > 0 && (
          <div className="uploaded-files">
            <h4>Uploaded Files ({uploadedFiles.length})</h4>
            <ul>
              {uploadedFiles.slice(0, 5).map((file, index) => (
                <li key={file.id || index}>
                  {file.original_name || file.name} ({((file.size || 0) / 1024).toFixed(2)} KB)
                </li>
              ))}
              {uploadedFiles.length > 5 && (
                <li className="more-files">
                  +{uploadedFiles.length - 5} more files
                </li>
              )}
            </ul>
          </div>
        )}
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <p>No messages yet. Start by asking your agents a question!</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Ask your agents a question..."
          disabled={isLoading || isRunning}
        />
        <button 
          type="submit" 
          disabled={isLoading || isRunning || !inputMessage.trim()}
        >
          {isLoading || isRunning ? 'Processing...' : 'Send'}
        </button>
      </form>
    </div>
  );
};

export default ChatInterface;