import React from 'react';
import { FaSave, FaPlay, FaImage, FaUndo, FaRedo } from 'react-icons/fa';
import { useReactFlow } from 'reactflow';

const NodeToolbar = ({ onSave, hasNodes }) => {
  const reactFlowInstance = useReactFlow();
  
  // Layout nodes in a more organized way
  const handleAutoLayout = () => {
    if (!reactFlowInstance || !hasNodes) return;
    
    const nodes = reactFlowInstance.getNodes();
    const edges = reactFlowInstance.getEdges();
    
    // Simple auto-layout algorithm for demonstration
    // In a real app, you might want to use a more sophisticated algorithm
    const startX = 50;
    const startY = 50;
    const horizontalGap = 300;
    const verticalGap = 200;
    
    // Find nodes with no incoming edges (entry points)
    const entryNodes = nodes.filter(node => 
      !edges.some(edge => edge.target === node.id)
    );
    
    // Find all other nodes
    const remainingNodes = nodes.filter(node => 
      !entryNodes.includes(node)
    );
    
    // Position entry nodes at the top
    const updatedNodes = entryNodes.map((node, index) => ({
      ...node,
      position: {
        x: startX + (index * horizontalGap),
        y: startY
      }
    }));
    
    // Position remaining nodes below
    const processedIds = new Set(entryNodes.map(n => n.id));
    let currentY = startY + verticalGap;
    
    // Process nodes level by level based on connections
    while (remainingNodes.length > processedIds.size) {
      let nodesInCurrentLevel = 0;
      
      // Find nodes that connect to already processed nodes
      remainingNodes.forEach(node => {
        if (processedIds.has(node.id)) return;
        
        const hasProcessedSource = edges.some(edge => 
          edge.target === node.id && processedIds.has(edge.source)
        );
        
        if (hasProcessedSource) {
          updatedNodes.push({
            ...node,
            position: {
              x: startX + (nodesInCurrentLevel * horizontalGap),
              y: currentY
            }
          });
          
          processedIds.add(node.id);
          nodesInCurrentLevel++;
        }
      });
      
      // If no nodes were processed in this level, break to avoid infinite loop
      if (nodesInCurrentLevel === 0) {
        // Place remaining nodes in a grid
        let row = 0;
        let col = 0;
        remainingNodes.forEach(node => {
          if (!processedIds.has(node.id)) {
            updatedNodes.push({
              ...node,
              position: {
                x: startX + (col * horizontalGap),
                y: currentY + (row * verticalGap)
              }
            });
            
            processedIds.add(node.id);
            col++;
            if (col > 3) { // Start a new row after 4 columns
              col = 0;
              row++;
            }
          }
        });
        break;
      }
      
      currentY += verticalGap;
    }
    
    // Update node positions
    reactFlowInstance.setNodes(updatedNodes);
    
    // Center view on the updated layout
    window.setTimeout(() => {
      reactFlowInstance.fitView({ padding: 0.2 });
    }, 50);
  };
  
  // Save the workflow as an image
  const handleExportImage = () => {
    if (!reactFlowInstance || !hasNodes) return;
    
    // Extract PNG image from reactFlowInstance
    const dataUrl = reactFlowInstance.toImage({ download: true, backgroundColor: '#f9fafb' });
    console.log('Image export initiated');
  };
  
  // Undo/Redo functionality (placeholder)
  const handleUndo = () => {
    alert('Undo functionality will be implemented in a future update');
  };
  
  const handleRedo = () => {
    alert('Redo functionality will be implemented in a future update');
  };
  
  return (
    <div className="node-toolbar">
      {/* Save workflow button */}
      <button
        className="toolbar-button primary"
        onClick={onSave}
        disabled={!hasNodes}
        title="Save Workflow"
      >
        <FaSave size={16} />
      </button>
      
      {/* Auto-layout button */}
      <button
        className="toolbar-button secondary"
        onClick={handleAutoLayout}
        disabled={!hasNodes}
        title="Auto Layout"
      >
        <FaPlay size={16} />
      </button>
      
      {/* Export as image button */}
      <button
        className="toolbar-button secondary"
        onClick={handleExportImage}
        disabled={!hasNodes}
        title="Export as Image"
      >
        <FaImage size={16} />
      </button>
      
      {/* Undo button */}
      <button
        className="toolbar-button"
        onClick={handleUndo}
        disabled={true} // Disabled for now
        title="Undo"
      >
        <FaUndo size={16} />
      </button>
      
      {/* Redo button */}
      <button
        className="toolbar-button"
        onClick={handleRedo}
        disabled={true} // Disabled for now
        title="Redo"
      >
        <FaRedo size={16} />
      </button>
    </div>
  );
};

export default NodeToolbar;