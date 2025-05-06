import React from 'react';
import { FaRobot, FaUser, FaInfo, FaExclamationCircle } from 'react-icons/fa';

const ChatMessage = ({ message }) => {
  // Determine message type and styling
  const getMessageClass = () => {
    if (message.sender === 'system') {
      return `system ${message.type || 'info'}`;
    }
    return message.sender;
  };

  // Render icon based on message sender
  const renderIcon = () => {
    switch (message.sender) {
      case 'user':
        return <FaUser className="message-icon user" />;
      case 'agent':
        return <FaRobot className="message-icon agent" />;
      case 'system':
        if (message.type === 'error') {
          return <FaExclamationCircle className="message-icon error" />;
        }
        return <FaInfo className="message-icon info" />;
      default:
        return null;
    }
  };

  // Render typing indicator
  const renderTypingIndicator = () => {
    return (
      <div className="typing-indicator">
        <div className="typing-dot"></div>
        <div className="typing-dot"></div>
        <div className="typing-dot"></div>
      </div>
    );
  };

  // Format message content with markdown (for code blocks, links, etc.)
  const formatContent = (content) => {
    if (!content) return null;

    // For future enhancement: use a markdown library to render content
    // For now, we'll just return the raw content
    return (
      <div className="message-markdown">
        {content}
      </div>
    );
  };

  return (
    <div className={`chat-message ${message.sender}`}>
      {/* Don't show icon for typing indicator */}
      {message.type !== 'typing' && renderIcon()}
      
      <div className={`message-content ${getMessageClass()}`}>
        {message.type === 'typing' ? (
          renderTypingIndicator()
        ) : (
          formatContent(message.content)
        )}
      </div>
    </div>
  );
};

export default ChatMessage;