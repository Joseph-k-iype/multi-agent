import React, { useCallback, useRef, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  addEdge,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useWorkflowStore } from '../../stores/workflowStore';
import AgentNode from './AgentNode';
import CustomEdge from './CustomEdge';
import NodeToolbar from './NodeToolbar';
import '../../styles/canvas.css';

// Custom node types
const nodeTypes = {
  agentNode: AgentNode,
};

// Custom edge types
const edgeTypes = {
  customEdge: CustomEdge,
};

const AgentCanvas = ({ onNodeSelect }) => {
  const reactFlowWrapper = useRef(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  
  // Use Zustand store instead of context
  const { 
    nodes, 
    edges, 
    setNodes, 
    setEdges,
    saveWorkflow 
  } = useWorkflowStore();
  
  // Use ReactFlow's state management for local manipulation
  const [localNodes, setLocalNodes, onNodesChange] = useNodesState(nodes || []);
  const [localEdges, setLocalEdges, onEdgesChange] = useEdgesState(edges || []);
  
  // Sync local state with Zustand store when nodes or edges change in store
  React.useEffect(() => {
    setLocalNodes(nodes || []);
  }, [nodes, setLocalNodes]);
  
  React.useEffect(() => {
    setLocalEdges(edges || []);
  }, [edges, setLocalEdges]);
  
  // Sync Zustand store when local state changes
  React.useEffect(() => {
    if (localNodes !== nodes) {
      setNodes(localNodes);
    }
  }, [localNodes, nodes, setNodes]);
  
  React.useEffect(() => {
    if (localEdges !== edges) {
      setEdges(localEdges);
    }
  }, [localEdges, edges, setEdges]);
  
  // Handle node select
  const onNodeClick = useCallback((_, node) => {
    onNodeSelect(node);
  }, [onNodeSelect]);

  // Handle edge connections
  const onConnect = useCallback((params) => {
    // Create a custom edge with the customEdge type
    const newEdge = {
      ...params,
      type: 'customEdge',
      animated: true,
      style: { stroke: '#555' },
      data: { label: 'Connection' }
    };
    setLocalEdges((eds) => addEdge(newEdge, eds));
  }, [setLocalEdges]);

  // Handle drag over for new nodes
  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle drop of new agent from palette
  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      if (!reactFlowInstance) return;

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const agentType = event.dataTransfer.getData('application/agentType');
      
      let agentData;
      try {
        agentData = JSON.parse(event.dataTransfer.getData('application/agentData'));
      } catch (error) {
        console.error('Failed to parse agent data:', error);
        return;
      }
      
      // Get position from drop coordinates
      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      // Create a new node
      const newNode = {
        id: `${agentType}-${Date.now()}`,
        type: 'agentNode',
        position,
        data: {
          label: agentData.name || agentType,
          type: agentType,
          role: agentData.role || 'Default Role',
          goal: agentData.goal || 'Process information',
          allowedTools: agentData.allowedTools || [],
          config: {
            ...agentData.config
          }
        },
      };

      setLocalNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setLocalNodes]
  );

  // Handle node deletion
  const onNodesDelete = useCallback((deleted) => {
    setLocalEdges(localEdges.filter(edge => 
      !deleted.some(node => node.id === edge.source || node.id === edge.target)
    ));
  }, [localEdges, setLocalEdges]);

  // Handle canvas panning to prevent accidental node movement
  const onPaneClick = useCallback(() => {
    onNodeSelect(null); // Deselect node when clicking on the canvas
  }, [onNodeSelect]);

  return (
    <div className="agent-canvas-container" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={localNodes}
        edges={localEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={setReactFlowInstance}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={onNodeClick}
        onNodesDelete={onNodesDelete}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        snapToGrid={true}
        snapGrid={[15, 15]}
      >
        <Background color="#aaa" gap={16} />
        <Controls />
        <Panel position="top-right" className="canvas-controls">
          <NodeToolbar 
            onSave={saveWorkflow}
            hasNodes={localNodes.length > 0}
          />
        </Panel>
      </ReactFlow>
    </div>
  );
};

export default AgentCanvas;