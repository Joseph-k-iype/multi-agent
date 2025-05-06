import React, { createContext, useContext, useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { workflowApi } from '../api/workflowApi';

const WorkflowContext = createContext(null);

export const WorkflowProvider = ({ children }) => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [workflowId, setWorkflowId] = useState(uuidv4());
  const [isRunning, setIsRunning] = useState(false);
  const [workflowResult, setWorkflowResult] = useState(null);
  const [error, setError] = useState(null);

  // Load any saved workflow from localStorage on mount
  useEffect(() => {
    try {
      const savedWorkflow = localStorage.getItem('savedWorkflow');
      if (savedWorkflow) {
        const { nodes: savedNodes, edges: savedEdges, id } = JSON.parse(savedWorkflow);
        setNodes(savedNodes || []);
        setEdges(savedEdges || []);
        if (id) setWorkflowId(id);
      }
    } catch (err) {
      console.error('Error loading saved workflow:', err);
    }
  }, []);

  // Function to validate workflow before running
  const validateWorkflow = () => {
    // Check if we have nodes
    if (nodes.length === 0) {
      return { valid: false, error: 'Workflow must contain at least one agent node.' };
    }

    // Check if we have at least one entry point (node with no incoming edges)
    const entryNodes = nodes.filter(node => 
      !edges.some(edge => edge.target === node.id)
    );

    if (entryNodes.length === 0) {
      return { valid: false, error: 'Workflow must have at least one entry point (node with no incoming connections).' };
    }

    // Check if we have at least one exit point (node with no outgoing edges)
    const exitNodes = nodes.filter(node => 
      !edges.some(edge => edge.source === node.id)
    );

    if (exitNodes.length === 0) {
      return { valid: false, error: 'Workflow must have at least one exit point (node with no outgoing connections).' };
    }

    // Check for circular references
    // Implementation of cycle detection would go here
    // For now we'll assume no cycles

    return { valid: true };
  };

  // Function to save workflow to localStorage
  const saveWorkflow = () => {
    try {
      const workflow = {
        id: workflowId,
        nodes,
        edges,
        timestamp: new Date().toISOString()
      };
      localStorage.setItem('savedWorkflow', JSON.stringify(workflow));
      return { success: true };
    } catch (err) {
      console.error('Error saving workflow:', err);
      return { success: false, error: err.message };
    }
  };

  // Function to convert workflow to backend format
  const workflowToApiFormat = (initialTask) => {
    // Convert nodes to agent configs
    const agentsConfig = nodes.map(node => ({
      id: node.id,
      name: node.data.label,
      role: node.data.role,
      goal: node.data.goal,
      allowed_tools: node.data.allowedTools || [],
      initial_state: node.data.config || {},
      llm_config: {
        temperature: node.data.config?.temperature || 0.7,
        max_tokens: node.data.config?.max_tokens || 1000
      }
    }));

    // Determine entry and exit points
    const entryPoints = nodes.filter(node => 
      !edges.some(edge => edge.target === node.id)
    ).map(node => node.id);

    const exitPoints = nodes.filter(node => 
      !edges.some(edge => edge.source === node.id)
    ).map(node => node.id);

    // Convert edges
    const formattedEdges = edges.map(edge => ({
      source: edge.source,
      target: edge.target
    }));

    // Build orchestrator config
    const orchestratorConfig = {
      entry_point: entryPoints[0], // Use first entry point
      finish_point: exitPoints,
      nodes: nodes.map(node => ({ id: node.id })),
      edges: formattedEdges
    };

    return {
      initial_task: initialTask,
      agents_config: agentsConfig,
      orchestrator_config: orchestratorConfig
    };
  };

  // Function to run the workflow
  const runWorkflow = async (initialTask) => {
    try {
      setIsRunning(true);
      setError(null);
      setWorkflowResult(null);

      // Validate workflow first
      const validation = validateWorkflow();
      if (!validation.valid) {
        setError(validation.error);
        setIsRunning(false);
        return { success: false, error: validation.error };
      }

      // Convert workflow to API format
      const workflowData = workflowToApiFormat(initialTask);
      
      // Call the API
      const result = await workflowApi.runWorkflow(workflowData);
      
      setWorkflowResult(result);
      setIsRunning(false);
      return { success: true, result };
    } catch (err) {
      console.error('Error running workflow:', err);
      setError(err.message || 'An error occurred while running the workflow.');
      setIsRunning(false);
      return { success: false, error: err.message };
    }
  };

  // Function to clear the current workflow
  const clearWorkflow = () => {
    if (window.confirm('Are you sure you want to clear the current workflow?')) {
      setNodes([]);
      setEdges([]);
      setWorkflowResult(null);
      setError(null);
      setWorkflowId(uuidv4());
      localStorage.removeItem('savedWorkflow');
    }
  };

  const value = {
    nodes,
    setNodes,
    edges, 
    setEdges,
    workflowId,
    isRunning,
    workflowResult,
    error,
    saveWorkflow,
    runWorkflow,
    clearWorkflow,
  };

  return (
    <WorkflowContext.Provider value={value}>
      {children}
    </WorkflowContext.Provider>
  );
};

export const useWorkflow = () => {
  const context = useContext(WorkflowContext);
  if (!context) {
    throw new Error('useWorkflow must be used within a WorkflowProvider');
  }
  return context;
};