import { useState, useCallback, useContext, useEffect } from 'react';
import { useReactFlow } from 'reactflow';
import { WorkflowContext } from '../contexts/WorkflowContext';
import { workflowApi } from '../api/workflowApi';
import { v4 as uuidv4 } from 'uuid';

/**
 * Custom hook for managing agent workflow functionality
 * - Provides methods for workflow manipulation
 * - Handles API interactions
 * - Manages workflow execution state
 */
export const useWorkflow = () => {
  // Get the workflow context
  const workflowContext = useContext(WorkflowContext);
  
  // Get ReactFlow instance for additional operations
  const reactFlowInstance = useReactFlow();
  
  // Local state for workflow execution
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionError, setExecutionError] = useState(null);
  const [executionResult, setExecutionResult] = useState(null);
  const [lastRunTaskDescription, setLastRunTaskDescription] = useState('');
  
  // Execution history for tracking runs
  const [executionHistory, setExecutionHistory] = useState([]);
  
  // Extract values from context
  const {
    nodes,
    setNodes,
    edges,
    setEdges,
    workflowId,
    saveWorkflow: contextSaveWorkflow,
    clearWorkflow: contextClearWorkflow,
    error,
    setError,
  } = workflowContext;

  /**
   * Add a new node to the workflow
   */
  const addNode = useCallback((nodeData, position) => {
    const newNode = {
      id: `${nodeData.type}-${uuidv4().substring(0, 8)}`,
      type: 'agentNode',
      position,
      data: {
        ...nodeData,
        label: nodeData.name || nodeData.type
      }
    };
    
    setNodes((nds) => [...nds, newNode]);
    return newNode;
  }, [setNodes]);

  /**
   * Update a node's data
   */
  const updateNode = useCallback((nodeId, newData) => {
    setNodes((nds) =>
      nds.map((node) => 
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...newData } }
          : node
      )
    );
  }, [setNodes]);

  /**
   * Remove a node from the workflow
   */
  const removeNode = useCallback((nodeId) => {
    // Remove connected edges first
    setEdges((eds) =>
      eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId)
    );
    
    // Remove the node
    setNodes((nds) => nds.filter((node) => node.id !== nodeId));
  }, [setNodes, setEdges]);

  /**
   * Connect two nodes with an edge
   */
  const connectNodes = useCallback((params, additionalData = {}) => {
    const newEdge = {
      id: `edge-${params.source}-${params.target}`,
      source: params.source,
      target: params.target,
      type: 'customEdge',
      animated: true,
      data: {
        label: additionalData.label || '',
        edgeType: additionalData.edgeType || 'bezier',
        ...additionalData
      }
    };
    
    setEdges((eds) => [...eds, newEdge]);
    return newEdge;
  }, [setEdges]);

  /**
   * Remove an edge from the workflow
   */
  const removeEdge = useCallback((edgeId) => {
    setEdges((eds) => eds.filter((edge) => edge.id !== edgeId));
  }, [setEdges]);

  /**
   * Validate the workflow before running
   * Returns { valid: boolean, error: string }
   */
  const validateWorkflow = useCallback(() => {
    // Check if we have nodes
    if (nodes.length === 0) {
      return { valid: false, error: 'Workflow must contain at least one agent node.' };
    }

    // Check if we have entry points (nodes with no incoming edges)
    const entryNodes = nodes.filter(node => 
      !edges.some(edge => edge.target === node.id)
    );

    if (entryNodes.length === 0) {
      return { valid: false, error: 'Workflow must have at least one entry point (node with no incoming connections).' };
    }

    // Check if we have exit points (nodes with no outgoing edges)
    const exitNodes = nodes.filter(node => 
      !edges.some(edge => edge.source === node.id)
    );

    if (exitNodes.length === 0) {
      return { valid: false, error: 'Workflow must have at least one exit point (node with no outgoing connections).' };
    }

    // Check for circular dependencies (simplified check)
    // A more robust check would use a graph algorithm like depth-first search
    const nodeMap = new Map(nodes.map(node => [node.id, { visited: false, stack: false }]));
    
    const checkCycle = (nodeId) => {
      const nodeInfo = nodeMap.get(nodeId);
      
      if (!nodeInfo) return false;
      if (nodeInfo.stack) return true; // Back edge found, there's a cycle
      
      if (!nodeInfo.visited) {
        nodeInfo.visited = true;
        nodeInfo.stack = true;
        
        // Check all adjacent nodes (nodes this node points to)
        const outgoingEdges = edges.filter(edge => edge.source === nodeId);
        
        for (const edge of outgoingEdges) {
          if (checkCycle(edge.target)) {
            return true;
          }
        }
      }
      
      nodeInfo.stack = false; // Remove from recursion stack
      return false;
    };
    
    // Check for cycles starting from each entry point
    for (const entryNode of entryNodes) {
      if (checkCycle(entryNode.id)) {
        return { valid: false, error: 'Workflow contains a circular reference, which is not allowed.' };
      }
    }

    return { valid: true };
  }, [nodes, edges]);

  /**
   * Convert the workflow to the format expected by the backend API
   */
  const convertWorkflowToApiFormat = useCallback((taskDescription) => {
    // Convert nodes to agent configs
    const agentsConfig = nodes.map(node => ({
      id: node.id,
      name: node.data.label,
      role: node.data.role || 'Default Role',
      goal: node.data.goal || 'Process information',
      allowed_tools: node.data.allowedTools || [],
      initial_state: node.data.config || {},
      llm_config: {
        temperature: node.data.config?.temperature || 0.7,
        max_tokens: node.data.config?.max_tokens || 1000
      }
    }));

    // Identify entry and exit points
    const entryPoints = nodes.filter(node => 
      !edges.some(edge => edge.target === node.id)
    ).map(node => node.id);

    const exitPoints = nodes.filter(node => 
      !edges.some(edge => edge.source === node.id)
    ).map(node => node.id);

    // Format edges
    const formattedEdges = edges.map(edge => ({
      source: edge.source,
      target: edge.target,
      // Include any edge-specific data if needed
      ...(edge.data && { data: edge.data })
    }));

    // Build orchestrator config
    const orchestratorConfig = {
      entry_point: entryPoints[0], // Use first entry point
      finish_point: exitPoints,
      nodes: nodes.map(node => ({ id: node.id })),
      edges: formattedEdges
    };

    return {
      initial_task: taskDescription,
      workflow_id: workflowId,
      agents_config: agentsConfig,
      orchestrator_config: orchestratorConfig
    };
  }, [nodes, edges, workflowId]);

  /**
   * Run the workflow with a given task description
   */
  const runWorkflow = useCallback(async (taskDescription) => {
    try {
      setExecutionError(null);
      setExecutionResult(null);
      setIsExecuting(true);
      setLastRunTaskDescription(taskDescription);

      // Validate workflow first
      const validation = validateWorkflow();
      if (!validation.valid) {
        setExecutionError(validation.error);
        setIsExecuting(false);
        return { success: false, error: validation.error };
      }

      // Format data for the API
      const apiData = convertWorkflowToApiFormat(taskDescription);
      
      // Call the API
      const result = await workflowApi.runWorkflow(apiData);
      
      setExecutionResult(result);
      
      // Add to execution history
      const historyEntry = {
        id: uuidv4(),
        timestamp: new Date().toISOString(),
        task: taskDescription,
        result: {
          success: true,
          data: result
        }
      };
      
      setExecutionHistory(prev => [historyEntry, ...prev]);
      
      setIsExecuting(false);
      return { success: true, result };
    } catch (err) {
      console.error('Error running workflow:', err);
      
      const errorMessage = err.message || 'An unknown error occurred while running the workflow';
      setExecutionError(errorMessage);
      
      // Add failed execution to history
      const historyEntry = {
        id: uuidv4(),
        timestamp: new Date().toISOString(),
        task: taskDescription,
        result: {
          success: false,
          error: errorMessage
        }
      };
      
      setExecutionHistory(prev => [historyEntry, ...prev]);
      
      setIsExecuting(false);
      return { success: false, error: errorMessage };
    }
  }, [validateWorkflow, convertWorkflowToApiFormat, workflowId]);

  /**
   * Save the current workflow
   */
  const saveWorkflow = useCallback(() => {
    try {
      // Get the current viewport from ReactFlow
      const flowData = reactFlowInstance ? reactFlowInstance.toObject() : { viewport: { x: 0, y: 0, zoom: 1 } };
      
      // Create a workflow object with additional metadata
      const workflowData = {
        id: workflowId,
        nodes,
        edges,
        viewport: flowData.viewport,
        lastModified: new Date().toISOString()
      };
      
      // Call the context save function
      const result = contextSaveWorkflow(workflowData);
      
      return result;
    } catch (err) {
      console.error('Error saving workflow:', err);
      setError(`Failed to save workflow: ${err.message}`);
      return { success: false, error: err.message };
    }
  }, [reactFlowInstance, workflowId, nodes, edges, contextSaveWorkflow, setError]);

  /**
   * Clear the current workflow
   */
  const clearWorkflow = useCallback(() => {
    if (window.confirm('Are you sure you want to clear the current workflow? This cannot be undone.')) {
      contextClearWorkflow();
      setExecutionResult(null);
      setExecutionError(null);
      return true;
    }
    return false;
  }, [contextClearWorkflow]);

  /**
   * Export the workflow as JSON
   */
  const exportWorkflow = useCallback(() => {
    try {
      const workflowData = {
        id: workflowId,
        nodes,
        edges,
        metadata: {
          createdAt: new Date().toISOString(),
          version: "1.0"
        }
      };
      
      const dataStr = JSON.stringify(workflowData, null, 2);
      const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
      
      // Create a download link and trigger it
      const exportName = `workflow-${workflowId.substring(0, 8)}.json`;
      const downloadLink = document.createElement('a');
      downloadLink.setAttribute('href', dataUri);
      downloadLink.setAttribute('download', exportName);
      downloadLink.click();
      
      return { success: true };
    } catch (err) {
      console.error('Error exporting workflow:', err);
      setError(`Failed to export workflow: ${err.message}`);
      return { success: false, error: err.message };
    }
  }, [workflowId, nodes, edges, setError]);

  /**
   * Import a workflow from JSON
   */
  const importWorkflow = useCallback((jsonData) => {
    try {
      const workflowData = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
      
      // Validate the imported data
      if (!workflowData.nodes || !workflowData.edges) {
        throw new Error('Invalid workflow data: missing nodes or edges');
      }
      
      // Confirm before replacing current workflow
      if (nodes.length > 0 && !window.confirm('Importing will replace your current workflow. Continue?')) {
        return { success: false, cancelled: true };
      }
      
      // Update the state with imported data
      setNodes(workflowData.nodes);
      setEdges(workflowData.edges);
      
      // If there's a viewport, set it
      if (workflowData.viewport && reactFlowInstance) {
        reactFlowInstance.setViewport(workflowData.viewport);
      } else {
        // Otherwise fit the view to the new nodes
        setTimeout(() => {
          if (reactFlowInstance) {
            reactFlowInstance.fitView({ padding: 0.2 });
          }
        }, 100);
      }
      
      return { success: true };
    } catch (err) {
      console.error('Error importing workflow:', err);
      setError(`Failed to import workflow: ${err.message}`);
      return { success: false, error: err.message };
    }
  }, [nodes, setNodes, setEdges, reactFlowInstance, setError]);

  /**
   * Auto-layout the workflow nodes
   */
  const autoLayoutWorkflow = useCallback(() => {
    if (!reactFlowInstance || nodes.length === 0) return false;
    
    try {
      // Simple auto-layout implementation (layered approach)
      // More sophisticated algorithms could be implemented
      
      const startX = 50;
      const startY = 50;
      const horizontalGap = 300;
      const verticalGap = 200;
      
      // Find entry nodes (no incoming edges)
      const entryNodes = nodes.filter(node => 
        !edges.some(edge => edge.target === node.id)
      );
      
      // Find all other nodes
      const otherNodes = nodes.filter(node => 
        !entryNodes.includes(node)
      );
      
      // Start with entry nodes at the top
      const newPositions = new Map();
      entryNodes.forEach((node, index) => {
        newPositions.set(node.id, {
          x: startX + (index * horizontalGap),
          y: startY
        });
      });
      
      // Process remaining nodes by layers
      const processedIds = new Set(entryNodes.map(node => node.id));
      let currentY = startY + verticalGap;
      
      // Keep going until all nodes are processed or we can't make progress
      while (processedIds.size < nodes.length) {
        const nodesInThisLayer = [];
        
        // Find nodes that have all their incoming edges from processed nodes
        otherNodes.forEach(node => {
          if (processedIds.has(node.id)) return;
          
          const incomingEdges = edges.filter(edge => edge.target === node.id);
          
          // If no incoming edges or all sources are processed, add to this layer
          const allSourcesProcessed = incomingEdges.length === 0 || 
            incomingEdges.every(edge => processedIds.has(edge.source));
            
          if (allSourcesProcessed) {
            nodesInThisLayer.push(node);
          }
        });
        
        // If we couldn't find any nodes for this layer, we might have a cycle
        // Just place remaining nodes in a grid
        if (nodesInThisLayer.length === 0) {
          const remainingNodes = nodes.filter(node => !processedIds.has(node.id));
          let gridCol = 0;
          let gridRow = 0;
          
          remainingNodes.forEach(node => {
            newPositions.set(node.id, {
              x: startX + (gridCol * horizontalGap / 2),
              y: currentY + (gridRow * verticalGap / 2)
            });
            
            processedIds.add(node.id);
            gridCol++;
            
            if (gridCol >= 4) {
              gridCol = 0;
              gridRow++;
            }
          });
          
          break;
        }
        
        // Position nodes in this layer
        nodesInThisLayer.forEach((node, index) => {
          newPositions.set(node.id, {
            x: startX + (index * horizontalGap),
            y: currentY
          });
          
          processedIds.add(node.id);
        });
        
        currentY += verticalGap;
      }
      
      // Update node positions
      const updatedNodes = nodes.map(node => ({
        ...node,
        position: newPositions.get(node.id) || node.position
      }));
      
      setNodes(updatedNodes);
      
      // Fit view to the updated layout
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.2 });
      }, 100);
      
      return true;
    } catch (err) {
      console.error('Error applying auto-layout:', err);
      setError(`Failed to apply auto-layout: ${err.message}`);
      return false;
    }
  }, [reactFlowInstance, nodes, edges, setNodes, setError]);

  // Return all the functions and state
  return {
    // State
    nodes,
    edges,
    workflowId,
    isExecuting,
    executionError,
    executionResult,
    lastRunTaskDescription,
    executionHistory,
    error,
    
    // State setters
    setNodes,
    setEdges,
    setError,
    
    // Node and edge operations
    addNode,
    updateNode,
    removeNode,
    connectNodes,
    removeEdge,
    
    // Workflow operations
    validateWorkflow,
    runWorkflow,
    saveWorkflow,
    clearWorkflow,
    exportWorkflow,
    importWorkflow,
    autoLayoutWorkflow,
  };
};

// For backward compatibility
export const useAgentWorkflow = useWorkflow;