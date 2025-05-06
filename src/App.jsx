import React, { useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { WorkflowProvider } from './contexts/WorkflowContext';
import { ChatProvider } from './contexts/ChatContext';
import Navbar from './components/common/Navbar';
import AgentCanvas from './components/canvas/AgentCanvas';
import AgentPalette from './components/sidebar/AgentPalette';
import NodeConfig from './components/sidebar/NodeConfig';
import WorkflowControls from './components/sidebar/WorkflowControls';
import ChatInterface from './components/chat/ChatInterface';
import './styles/main.css';

function App() {
  const [selectedNode, setSelectedNode] = useState(null);
  const [showChat, setShowChat] = useState(false);

  return (
    <WorkflowProvider>
      <ChatProvider>
        <div className="app-container">
          <Navbar toggleChat={() => setShowChat(!showChat)} />
          
          <div className="main-content">
            <PanelGroup direction="horizontal">
              {/* Left sidebar with agent palette and configuration */}
              <Panel defaultSize={20} minSize={15}>
                <div className="sidebar">
                  <AgentPalette />
                  {selectedNode && <NodeConfig node={selectedNode} />}
                  <WorkflowControls />
                </div>
              </Panel>
              
              <PanelResizeHandle className="resize-handle" />
              
              {/* Main canvas area */}
              <Panel defaultSize={showChat ? 50 : 80} minSize={40}>
                <div className="canvas-container">
                  <AgentCanvas 
                    onNodeSelect={setSelectedNode}
                  />
                </div>
              </Panel>
              
              {/* Chat interface (conditional) */}
              {showChat && (
                <>
                  <PanelResizeHandle className="resize-handle" />
                  <Panel defaultSize={30} minSize={20}>
                    <ChatInterface />
                  </Panel>
                </>
              )}
            </PanelGroup>
          </div>
        </div>
      </ChatProvider>
    </WorkflowProvider>
  );
}

export default App;