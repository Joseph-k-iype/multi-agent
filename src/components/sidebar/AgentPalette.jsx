import React from 'react';
import { FaRobot, FaSearch, FaPenFancy, FaCode, FaMagic } from 'react-icons/fa';
import { agentTemplates } from '../../utils/agentTemplates';

const AgentPalette = () => {
  const onDragStart = (event, agentType, agentData) => {
    event.dataTransfer.setData('application/agentType', agentType);
    event.dataTransfer.setData('application/agentData', JSON.stringify(agentData));
    event.dataTransfer.effectAllowed = 'move';
  };

  // Function to get icon based on agent type
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

  return (
    <div className="agent-palette">
      <h3 className="palette-title">Agent Types</h3>
      <p className="palette-description">Drag and drop agents onto the canvas to build your workflow</p>
      
      <div className="agent-templates">
        {Object.entries(agentTemplates).map(([type, template]) => (
          <div
            key={type}
            className="agent-template"
            draggable
            onDragStart={(e) => onDragStart(e, type, template)}
          >
            <div className="agent-template-icon" style={{ backgroundColor: template.color }}>
              {getAgentIcon(type)}
            </div>
            <div className="agent-template-info">
              <div className="agent-template-name">{template.name}</div>
              <div className="agent-template-description">{template.description}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="palette-footer">
        <h4 className="custom-agent-title">Custom Agent</h4>
        <div
          className="agent-template custom-agent"
          draggable
          onDragStart={(e) => onDragStart(e, 'custom', {
            name: 'Custom Agent',
            role: 'Custom Role',
            goal: 'Custom goal',
            allowedTools: [],
            config: {}
          })}
        >
          <div className="agent-template-icon" style={{ backgroundColor: '#64748b' }}>
            <FaRobot className="agent-icon" />
          </div>
          <div className="agent-template-info">
            <div className="agent-template-name">Custom Agent</div>
            <div className="agent-template-description">Create a custom agent with your own configuration</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentPalette;