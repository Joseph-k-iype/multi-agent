import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { FaFileUpload, FaFile, FaFilePdf, FaFileWord, FaFileCsv, FaFileExcel, FaFileCode } from 'react-icons/fa';
import { useFileStore } from '../../stores/fileStore';

const FileUpload = ({ onFileUpload }) => {
  const [isLocalUploading, setIsLocalUploading] = useState(false);
  const [error, setError] = useState(null);
  
  // Use the fileStore
  const { 
    files, 
    isUploading, 
    uploadProgress,
    uploadFiles,
    clearFiles 
  } = useFileStore();

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
      setError(null);
      setIsLocalUploading(true);
      
      // Use the parent callback if provided (for custom handling)
      if (onFileUpload) {
        await onFileUpload(acceptedFiles);
      } else {
        // Otherwise use the uploadFiles from store
        await uploadFiles(acceptedFiles);
      }
      
      setIsLocalUploading(false);
    } catch (err) {
      setError(err.message || 'Error uploading files');
      setIsLocalUploading(false);
    }
  }, [onFileUpload, uploadFiles]);

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

  return (
    <div className="file-upload-container">
      <div 
        {...getRootProps()} 
        className={`dropzone ${isDragActive ? 'active' : ''} ${isUploading || isLocalUploading ? 'uploading' : ''}`}
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

      {(isUploading || isLocalUploading) && (
        <div className="upload-progress">
          <p>Uploading files...</p>
          <div className="progress-bar">
            <div 
              className="progress-indicator" 
              style={{ width: `${uploadProgress || 0}%` }}
            />
          </div>
        </div>
      )}

      {files.length > 0 && (
        <div className="uploaded-files-list">
          <div className="files-header">
            <h4>Uploaded Files ({files.length})</h4>
            <button 
              className="clear-files-btn" 
              onClick={clearFiles}
              disabled={isUploading || isLocalUploading}
            >
              Clear All
            </button>
          </div>
          
          <ul>
            {files.slice(0, 5).map((file, index) => (
              <li key={file.id || index} className="file-item">
                {getFileIcon(file.original_name || file.name)}
                <span className="file-name">{file.original_name || file.name}</span>
                <span className="file-size">({((file.size || 0) / 1024).toFixed(2)} KB)</span>
              </li>
            ))}
            {files.length > 5 && (
              <li className="file-item view-more">
                <span>And {files.length - 5} more files...</span>
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};

export default FileUpload;