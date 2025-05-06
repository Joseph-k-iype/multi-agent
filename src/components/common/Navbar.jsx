import React, { useEffect, useState } from 'react';
import { FaRobot, FaComment, FaDatabase, FaInfo, FaGithub } from 'react-icons/fa';
import { workflowApi } from '../../api/workflowApi';

const Navbar = ({ toggleChat }) => {
  const [backendStatus, setBackendStatus] = useState('unknown');
  
  // Check backend health on load
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const result = await workflowApi.checkHealth();
        setBackendStatus(result.status === 'ok' ? 'online' : 'error');
      } catch (error) {
        console.error('Backend health check failed:', error);
        setBackendStatus('offline');
      }
    };
    
    checkBackendHealth();
    
    // Check health periodically
    const interval = setInterval(checkBackendHealth, 30000); // Every 30 seconds
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="navbar">
      <div className="navbar-brand">
        <FaRobot size={24} />
        <span>Multi-Agent RAG Builder</span>
      </div>
      
      <div className="navbar-links">
        <a href="#" className="navbar-link">Home</a>
        <a href="#" className="navbar-link">Documentation</a>
        <a href="#" className="navbar-link">Examples</a>
      </div>
      
      <div className="navbar-actions">
        {/* Backend status indicator */}
        <div className={`backend-status ${backendStatus}`}>
          <span className="status-indicator"></span>
          <span className="status-text">
            {backendStatus === 'online' ? 'Backend Connected' : 
             backendStatus === 'offline' ? 'Backend Offline' : 
             backendStatus === 'error' ? 'Backend Error' : 'Checking...'}
          </span>
        </div>
        
        {/* Toggle chat button */}
        <button 
          className="navbar-button"
          onClick={toggleChat}
        >
          <FaComment size={16} />
          <span>Toggle Chat</span>
        </button>
        
        {/* RAG DB Info button */}
        <button 
          className="navbar-button secondary"
          onClick={() => alert('RAG Database Management panel coming soon!')}
        >
          <FaDatabase size={16} />
          <span>RAG Database</span>
        </button>
        
        {/* About button */}
        <button 
          className="navbar-button transparent"
          onClick={() => alert('Multi-Agent RAG Builder v1.0.0\n\nA tool for building and managing multi-agent workflows with RAG capabilities.')}
        >
          <FaInfo size={16} />
        </button>
        
        {/* GitHub link */}
        <a 
          href="https://github.com/yourusername/multi-agent-rag-app"
          target="_blank"
          rel="noopener noreferrer"
          className="navbar-button github"
        >
          <FaGithub size={16} />
        </a>
      </div>
    </div>
  );
};

export default Navbar;