import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/main.css';
import './styles/canvas.css';

// Optional: Add glassmorphic theme if desired
// import './styles/glassmorphic-theme.css'; 

// Create configuration object for environment settings
window.appConfig = {
  apiUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  isDevelopment: import.meta.env.DEV === true,
  version: '1.0.0'
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);