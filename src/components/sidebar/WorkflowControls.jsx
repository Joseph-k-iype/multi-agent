import React, { useState } from 'react';
import { FaPlay, FaSave, FaTrash, FaShare } from 'react-icons/fa';
import { useWorkflowStore } from '../../stores/workflowStore';

const WorkflowControls = () => {
  // Use Zustand store
  const { 
    saveWorkflow, 
    runWorkflow, 
    clearWorkflow, 
    exportWorkflow,
    isRunning, 
    workflowResult, 
    error 
  } = useWorkflowStore();
  
  const [taskInput, setTaskInput] = useState('');
  const [showTaskInput, setShowTaskInput] = useState(false);
  
  // Handle save workflow
  const handleSave = () => {
    const result = saveWorkflow();
    if (result.success) {
      alert('Workflow saved successfully!');
    } else {
      alert(`Failed to save workflow: ${result.error}`);
    }
  };
  
  // Handle run workflow
  const handleRun = async () => {
    if (!taskInput.trim()) {
      alert('Please enter a task description');
      return;
    }
    
    try {
      const result = await runWorkflow(taskInput);
      if (!result.success) {
        alert(`Error running workflow: ${result.error}`);
      }
      setShowTaskInput(false); // Hide input after running
    } catch (error) {
      console.error('Error running workflow:', error);
      alert(`Error running workflow: ${error.message}`);
    }
  };
  
  // Handle export workflow
  const handleExport = () => {
    const result = exportWorkflow();
    if (!result.success) {
      alert(`Failed to export workflow: ${result.error}`);
    }
  };
  
  // Toggle task input visibility
  const toggleTaskInput = () => {
    setShowTaskInput(!showTaskInput);
  };
  
  return (
    <div className="workflow-controls">
      <h3 className="workflow-title">Workflow Controls</h3>
      
      {/* Run workflow button */}
      <button 
        className="workflow-action-button run-button"
        onClick={toggleTaskInput}
        disabled={isRunning}
      >
        <FaPlay />
        <span>Run Workflow</span>
      </button>
      
      {/* Task input (conditionally shown) */}
      {showTaskInput && (
        <div className="task-input-container">
          <div className="form-group">
            <label htmlFor="task">Task Description</label>
            <textarea
              id="task"
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              placeholder="Describe the task for your agents..."
              rows={3}
              disabled={isRunning}
            />
          </div>
          
          <button 
            className="run-task-button"
            onClick={handleRun}
            disabled={isRunning || !taskInput.trim()}
          >
            {isRunning ? 'Processing...' : 'Start Task'}
          </button>
        </div>
      )}
      
      {/* Save workflow button */}
      <button 
        className="workflow-action-button save-workflow-button"
        onClick={handleSave}
        disabled={isRunning}
      >
        <FaSave />
        <span>Save Workflow</span>
      </button>
      
      {/* Clear workflow button */}
      <button 
        className="workflow-action-button clear-button"
        onClick={clearWorkflow}
        disabled={isRunning}
      >
        <FaTrash />
        <span>Clear Workflow</span>
      </button>
      
      {/* Export/share button */}
      <button 
        className="workflow-action-button export-button"
        onClick={handleExport}
        disabled={isRunning}
      >
        <FaShare />
        <span>Export Workflow</span>
      </button>
      
      {/* Status display */}
      {isRunning && (
        <div className="workflow-status-indicator">
          <div className="loading-spinner"></div>
          <span>Running workflow...</span>
        </div>
      )}
      
      {error && (
        <div className="workflow-error">
          <p>{error}</p>
        </div>
      )}
      
      {workflowResult && !error && !isRunning && (
        <div className="workflow-success">
          <p>Workflow completed successfully!</p>
        </div>
      )}
    </div>
  );
};

export default WorkflowControls;