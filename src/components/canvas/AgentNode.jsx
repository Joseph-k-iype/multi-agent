import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { FaRobot, FaMagic, FaSearch, FaPenFancy, FaCode } from 'react-icons/fa';

const AgentNode = ({ data, selected }) => {
  // Determine icon based on agent type
  const getAgentIcon = (type) => {
    switch (type) {
      case 'researcher':
        return <FaSearch className="agent-icon" />;
      case 'writer':
        return <FaPenFancy className="agent-icon" />;
      case 'coder':
        return <FaCode className="agent-icon" />;
      case 'orchestrator':
        return <FaMagic className="agent-icon" />;
      default:
        return <FaRobot className="agent-icon" />;
    }
  };

  // Determine node color based on agent type
  const getNodeColor = (type) => {
    switch (type) {
      case 'researcher':
        return '#6366f1'; // Indigo
      case 'writer':
        return '#10b981'; // Emerald
      case 'coder':
        return '#3b82f6'; // Blue
      case 'orchestrator': 
        return '#8b5cf6'; // Violet
      default:
        return '#64748b'; // Slate
    }
  };

  const nodeStyle = {
    borderColor: getNodeColor(data.type),
    borderWidth: selected ? '2px' : '1px',
    backgroundColor: selected ? `${getNodeColor(data.type)}15` : 'white',
    boxShadow: selected ? `0 0 0 2px ${getNodeColor(data.type)}` : 'none'
  };

  return (
    <div className="agent-node" style={nodeStyle}>
      {/* Source handle (top) */}
      <Handle
        type="source"
        position={Position.Top}
        id="top"
        className="handle source-handle"
      />
      
      <div className="agent-node-header" style={{ backgroundColor: getNodeColor(data.type) }}>
        {getAgentIcon(data.type)}
        <div className="agent-node-title">{data.label}</div>
      </div>
      
      <div className="agent-node-content">
        <div className="agent-node-role">{data.role}</div>
        <div className="agent-node-tools">
          {data.allowedTools && data.allowedTools.length > 0 ? (
            <div className="tools-list">
              <span className="tools-label">Tools:</span>
              {data.allowedTools.slice(0, 2).map((tool, idx) => (
                <span key={idx} className="tool-badge">{tool}</span>
              ))}
              {data.allowedTools.length > 2 && (
                <span className="tool-badge">+{data.allowedTools.length - 2}</span>
              )}
            </div>
          ) : (
            <span className="no-tools">No tools</span>
          )}
        </div>
      </div>
      
      {/* Target handle (bottom) */}
      <Handle
        type="target"
        position={Position.Bottom}
        id="bottom"
        className="handle target-handle"
      />
      
      {/* Alternative source handle (right) */}
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        className="handle source-handle"
      />
      
      {/* Alternative target handle (left) */}
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="handle target-handle"
      />
    </div>
  );
};

export default memo(AgentNode);