import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { FaFileUpload, FaFile, FaFilePdf, FaFileWord, FaFileCsv, FaFileExcel, FaFileCode } from 'react-icons/fa';

const FileUpload = ({ onFileUpload }) => {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);

  // Get appropriate icon based on file type
  const getFileIcon = (filename) => {
    const extension = filename.split('.').pop().toLowerCase();
    
    switch (extension) {
      case 'pdf':
        return <FaFilePdf className="file-icon pdf" />;
      case 'doc':
      case 'docx':
        return <FaFileWord className="file-icon doc" />;
      case 'csv':
        return <FaFileCsv className="file-icon csv" />;
      case 'xls':
      case 'xlsx':
        return <FaFileExcel className="file-icon excel" />;
      case 'js':
      case 'jsx':
      case 'py':
      case 'java':
      case 'html':
      case 'css':
        return <FaFileCode className="file-icon code" />;
      default:
        return <FaFile className="file-icon default" />;
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    try {
      setIsUploading(true);
      setError(null);
      
      // Add to local state for UI display
      setUploadedFiles(prev => [...prev, ...acceptedFiles]);
      
      // Call parent handler to actually upload the files
      if (onFileUpload) {
        await onFileUpload(acceptedFiles);
      }
      
      setIsUploading(false);
    } catch (err) {
      setError(err.message || 'Error uploading files');
      setIsUploading(false);
    }
  }, [onFileUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'text/csv': ['.csv'],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/json': ['.json']
    },
    maxSize: 10485760, // 10MB
    multiple: true
  });

  const clearFiles = () => {
    setUploadedFiles([]);
  };

  return (
    <div className="file-upload-container">
      <div 
        {...getRootProps()} 
        className={`dropzone ${isDragActive ? 'active' : ''} ${isUploading ? 'uploading' : ''}`}
      >
        <input {...getInputProps()} />
        
        <div className="upload-icon">
          <FaFileUpload size={24} />
        </div>
        
        {isDragActive ? (
          <p>Drop the files here ...</p>
        ) : (
          <p>Drag and drop files here, or click to select files</p>
        )}
        
        <p className="upload-hint">
          Supported files: TXT, CSV, PDF, DOC/DOCX, XLS/XLSX, JSON (Max: 10MB)
        </p>
      </div>

      {error && (
        <div className="upload-error">
          <p>{error}</p>
        </div>
      )}

      {isUploading && (
        <div className="upload-progress">
          <p>Uploading files...</p>
          <div className="progress-bar">
            <div className="progress-indicator" />
          </div>
        </div>
      )}

      {uploadedFiles.length > 0 && (
        <div className="uploaded-files-list">
          <div className="files-header">
            <h4>Uploaded Files</h4>
            <button 
              className="clear-files-btn" 
              onClick={clearFiles}
              disabled={isUploading}
            >
              Clear All
            </button>
          </div>
          
          <ul>
            {uploadedFiles.map((file, index) => (
              <li key={index} className="file-item">
                {getFileIcon(file.name)}
                <span className="file-name">{file.name}</span>
                <span className="file-size">({(file.size / 1024).toFixed(2)} KB)</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default FileUpload;