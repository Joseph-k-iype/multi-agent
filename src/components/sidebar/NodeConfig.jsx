import React, { useState, useEffect } from 'react';
import { useWorkflow } from '../../hooks/useAgentWorkflow';
import { availableTools, getToolById } from '../../utils/agentTemplates';

const NodeConfig = ({ node }) => {
  const { setNodes } = useWorkflow();
  const [formData, setFormData] = useState({
    label: '',
    role: '',
    goal: '',
    allowedTools: [],
    config: {
      temperature: 0.7,
      max_tokens: 1000
    }
  });
  
  // Update form data when selected node changes
  useEffect(() => {
    if (node) {
      setFormData({
        label: node.data.label || '',
        role: node.data.role || '',
        goal: node.data.goal || '',
        allowedTools: node.data.allowedTools || [],
        config: {
          temperature: node.data.config?.temperature || 0.7,
          max_tokens: node.data.config?.max_tokens || 1000,
          // Include additional config properties
          ...(node.data.config || {})
        }
      });
    }
  }, [node]);

  // Handle form changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name.startsWith('config.')) {
      // Handle nested config properties
      const configKey = name.split('.')[1];
      setFormData(prev => ({
        ...prev,
        config: {
          ...prev.config,
          [configKey]: value
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  // Handle checkbox changes for tools
  const handleToolChange = (e) => {
    const { value, checked } = e.target;
    setFormData(prev => {
      if (checked) {
        return {
          ...prev,
          allowedTools: [...prev.allowedTools, value]
        };
      } else {
        return {
          ...prev,
          allowedTools: prev.allowedTools.filter(tool => tool !== value)
        };
      }
    });
  };

  // Handle form submission (update node data)
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!node) return;

    setNodes(nds => 
      nds.map(n => {
        if (n.id === node.id) {
          // Update node with new data
          return {
            ...n,
            data: {
              ...n.data,
              label: formData.label,
              role: formData.role,
              goal: formData.goal,
              allowedTools: formData.allowedTools,
              config: formData.config
            }
          };
        }
        return n;
      })
    );
  };

  // If no node is selected, don't render the form
  if (!node) {
    return null;
  }

  return (
    <div className="node-config">
      <h3 className="config-title">Configure Agent</h3>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="label">Name</label>
          <input
            type="text"
            id="label"
            name="label"
            value={formData.label}
            onChange={handleChange}
            placeholder="Agent Name"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="role">Role</label>
          <input
            type="text"
            id="role"
            name="role"
            value={formData.role}
            onChange={handleChange}
            placeholder="Agent Role"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="goal">Goal</label>
          <textarea
            id="goal"
            name="goal"
            value={formData.goal}
            onChange={handleChange}
            placeholder="Agent Goal"
            rows={3}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="config.temperature">Temperature</label>
          <div className="range-input">
            <input
              type="range"
              id="config.temperature"
              name="config.temperature"
              min="0.0"
              max="1.0"
              step="0.1"
              value={formData.config.temperature}
              onChange={handleChange}
            />
            <span>{formData.config.temperature}</span>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="config.max_tokens">Max Tokens</label>
          <input
            type="number"
            id="config.max_tokens"
            name="config.max_tokens"
            min="100"
            max="4000"
            value={formData.config.max_tokens}
            onChange={handleChange}
          />
        </div>

        <div className="form-group">
          <label>Available Tools</label>
          <div className="tools-checkbox-group">
            {availableTools.map(tool => (
              <div className="tool-checkbox" key={tool.id}>
                <input
                  type="checkbox"
                  id={`tool-${tool.id}`}
                  name="allowedTools"
                  value={tool.id}
                  checked={formData.allowedTools.includes(tool.id)}
                  onChange={handleToolChange}
                />
                <label htmlFor={`tool-${tool.id}`}>
                  <strong>{tool.name}</strong>
                  <span className="tool-description">{tool.description}</span>
                </label>
              </div>
            ))}
          </div>
        </div>

        <button type="submit" className="save-button">
          Update Agent
        </button>
      </form>
    </div>
  );
};

export default NodeConfig;