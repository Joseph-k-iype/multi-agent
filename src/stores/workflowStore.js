// src/stores/workflowStore.js
import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import { workflowApi } from '../api/workflowApi';

export const useWorkflowStore = create((set, get) => ({
  // State
  nodes: [],
  edges: [],
  workflowId: uuidv4(),
  isRunning: false,
  workflowResult: null,
  error: null,
  
  // Actions
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  
  addNode: (nodeData, position) => {
    const newNode = {
      id: `${nodeData.type}-${uuidv4().substring(0, 8)}`,
      type: 'agentNode',
      position,
      data: {
        ...nodeData,
        label: nodeData.name || nodeData.type
      }
    };
    
    set((state) => ({
      nodes: [...state.nodes, newNode]
    }));
    
    return newNode;
  },
  
  updateNode: (nodeId, newData) => {
    set(state => {
      // Create a new nodes array with the updated node
      const updatedNodes = state.nodes.map(node => {
        if (node.id === nodeId) {
          // Create a completely new object to ensure React detects the change
          return {
            ...node,
            data: {
              ...node.data,
              ...newData
            }
          };
        }
        return node;
      });
      
      // Return a new state object
      return { nodes: updatedNodes };
    });
  },
  
  removeNode: (nodeId) => {
    set((state) => ({
      // Remove connected edges first
      edges: state.edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId),
      // Remove the node
      nodes: state.nodes.filter((node) => node.id !== nodeId)
    }));
  },
  
  connectNodes: (params, additionalData = {}) => {
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
    
    set((state) => ({
      edges: [...state.edges, newEdge]
    }));
    
    return newEdge;
  },
  
  removeEdge: (edgeId) => {
    set((state) => ({
      edges: state.edges.filter((edge) => edge.id !== edgeId)
    }));
  },
  
  validateWorkflow: () => {
    const { nodes, edges } = get();
    
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
  },
  
  convertWorkflowToApiFormat: (taskDescription) => {
    const { nodes, edges, workflowId } = get();
    
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
  },
  
  // Run workflow
  runWorkflow: async (taskDescription) => {
    set({ error: null, workflowResult: null, isRunning: true });
    
    try {
      // Validate workflow first
      const validation = get().validateWorkflow();
      if (!validation.valid) {
        set({ error: validation.error, isRunning: false });
        return { success: false, error: validation.error };
      }

      // Format data for the API
      const apiData = get().convertWorkflowToApiFormat(taskDescription);
      
      // Call the API
      const result = await workflowApi.runWorkflow(apiData);
      
      set({ workflowResult: result, isRunning: false });
      return { success: true, result };
    } catch (err) {
      console.error('Error running workflow:', err);
      
      const errorMessage = err.message || 'An unknown error occurred while running the workflow';
      set({ error: errorMessage, isRunning: false });
      
      return { success: false, error: errorMessage };
    }
  },
  
  // Save workflow to localStorage
  saveWorkflow: () => {
    try {
      const { nodes, edges, workflowId } = get();
      
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
      set({ error: err.message });
      return { success: false, error: err.message };
    }
  },
  
  // Load workflow from localStorage
  loadSavedWorkflow: () => {
    try {
      const savedWorkflow = localStorage.getItem('savedWorkflow');
      if (savedWorkflow) {
        const { nodes, edges, id } = JSON.parse(savedWorkflow);
        
        set({ 
          nodes: nodes || [], 
          edges: edges || [],
          ...(id && { workflowId: id })
        });
        
        return { success: true };
      }
      return { success: false, error: 'No saved workflow found' };
    } catch (err) {
      console.error('Error loading saved workflow:', err);
      set({ error: err.message });
      return { success: false, error: err.message };
    }
  },
  
  // Clear workflow
  clearWorkflow: () => {
    if (window.confirm('Are you sure you want to clear the current workflow?')) {
      set({ 
        nodes: [], 
        edges: [], 
        workflowResult: null, 
        error: null,
        workflowId: uuidv4()
      });
      
      localStorage.removeItem('savedWorkflow');
      return true;
    }
    return false;
  },
  
  // Export workflow as JSON
  exportWorkflow: () => {
    try {
      const { workflowId, nodes, edges } = get();
      
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
      set({ error: err.message });
      return { success: false, error: err.message };
    }
  },
  
  // Import workflow from JSON
  importWorkflow: (jsonData) => {
    try {
      const workflowData = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
      
      // Validate the imported data
      if (!workflowData.nodes || !workflowData.edges) {
        throw new Error('Invalid workflow data: missing nodes or edges');
      }
      
      // Confirm before replacing current workflow
      const { nodes } = get();
      if (nodes.length > 0 && !window.confirm('Importing will replace your current workflow. Continue?')) {
        return { success: false, cancelled: true };
      }
      
      // Update the state with imported data
      set({
        nodes: workflowData.nodes,
        edges: workflowData.edges
      });
      
      return { success: true };
    } catch (err) {
      console.error('Error importing workflow:', err);
      set({ error: err.message });
      return { success: false, error: err.message };
    }
  }
}));