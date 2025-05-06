import React, { useCallback, useRef, useState } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  addEdge,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useWorkflow } from '../../hooks/useAgentWorkflow';
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
  const { nodes, setNodes, edges, setEdges, onSaveWorkflow } = useWorkflow();
  
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
    setEdges((eds) => addEdge(newEdge, eds));
  }, [setEdges]);

  // Handle drag over for new nodes
  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle drop of new agent from palette
  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const agentType = event.dataTransfer.getData('application/agentType');
      const agentData = JSON.parse(event.dataTransfer.getData('application/agentData'));
      
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

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes]
  );

  // Handle node deletion
  const onNodesDelete = useCallback((deleted) => {
    setEdges(edges.filter(edge => 
      !deleted.some(node => node.id === edge.source || node.id === edge.target)
    ));
  }, [edges, setEdges]);

  // Handle canvas panning to prevent accidental node movement
  const onPaneClick = useCallback(() => {
    onNodeSelect(null); // Deselect node when clicking on the canvas
  }, [onNodeSelect]);

  return (
    <div className="agent-canvas-container" ref={reactFlowWrapper}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={(changes) => {
            setNodes((nds) => {
              const updatedNodes = [...nds];
              changes.forEach(change => {
                if (change.type === 'position' && change.dragging) {
                  const index = updatedNodes.findIndex(n => n.id === change.id);
                  if (index !== -1) {
                    updatedNodes[index] = {
                      ...updatedNodes[index],
                      position: {
                        x: change.position?.x || updatedNodes[index].position.x,
                        y: change.position?.y || updatedNodes[index].position.y
                      }
                    };
                  }
                }
              });
              return updatedNodes;
            });
          }}
          onEdgesChange={(changes) => {
            // Handle edge changes
            setEdges((eds) => {
              return eds.map(edge => {
                const change = changes.find(c => c.id === edge.id);
                if (change) {
                  return { ...edge, ...change };
                }
                return edge;
              });
            });
          }}
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
              onSave={onSaveWorkflow}
              hasNodes={nodes.length > 0}
            />
          </Panel>
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
};

export default AgentCanvas;