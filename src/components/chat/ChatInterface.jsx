import React, { useState, useEffect, useRef } from 'react';
import { useWorkflow } from '../../hooks/useAgentWorkflow';
import { useChat } from '../../contexts/ChatContext';
import ChatMessage from './ChatMessage';
import FileUpload from '../common/FileUpload';

const ChatInterface = () => {
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef(null);
  const { runWorkflow, isRunning, workflowResult } = useWorkflow();
  const { 
    messages, 
    addMessage, 
    addSystemMessage,
    isLoading,
    uploadFile,
    uploadedFiles
  } = useChat();

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Run the workflow when user sends a message
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    // Add user message to chat
    addMessage('user', inputMessage);
    setInputMessage('');

    // Add typing indicator
    addSystemMessage('typing', null);

    try {
      // Run the workflow with the user's message as the initial task
      const result = await runWorkflow(inputMessage);

      // Remove typing indicator
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.type === 'typing') {
        // Replace last message (typing indicator) with system message
        addSystemMessage('system', 'Workflow completed!');
      }

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
      addSystemMessage('error', error.message || 'An error occurred while running the workflow.');
    }
  };

  // Handle file upload completion
  const handleFileUpload = async (files) => {
    try {
      addSystemMessage('system', 'Uploading file(s)...');
      const uploadedFileIds = await uploadFile(files);
      addSystemMessage('system', `File(s) uploaded successfully! Added to RAG database.`);
      
      // Here you could trigger a refresh of the vector store or update UI
      // to show that the files are now available for RAG
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
            <h4>Uploaded Files</h4>
            <ul>
              {uploadedFiles.map((file, index) => (
                <li key={index}>
                  {file.name} ({(file.size / 1024).toFixed(2)} KB)
                </li>
              ))}
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