/**
 * Pre-configured agent templates for the multi-agent workflow.
 * Each template contains default settings that can be customized.
 */
export const agentTemplates = {
    researcher: {
      name: 'Researcher Agent',
      description: 'Retrieves and analyzes information using RAG',
      role: 'Research Assistant',
      goal: 'Find relevant information using retrieval tools and synthesize results',
      color: '#6366f1', // Indigo
      allowedTools: ['chromadb_retriever'],
      config: {
        temperature: 0.3,
        max_tokens: 1500,
        search_depth: 'comprehensive',
        output_format: 'markdown',
      }
    },
    
    writer: {
      name: 'Writer Agent',
      description: 'Creates content based on provided information',
      role: 'Content Creator',
      goal: 'Craft clear, engaging content based on research findings',
      color: '#10b981', // Emerald
      allowedTools: ['html_formatter', 'markdown_formatter'],
      config: {
        temperature: 0.7,
        max_tokens: 2000,
        tone: 'professional',
        audience: 'general',
        format: 'article'
      }
    },
    
    coder: {
      name: 'Coder Agent',
      description: 'Writes, explains, and debugs code',
      role: 'Software Developer',
      goal: 'Produce clean, efficient code or analyze existing code',
      color: '#3b82f6', // Blue
      allowedTools: ['code_formatter', 'chromadb_retriever'],
      config: {
        temperature: 0.2,
        max_tokens: 2000,
        language: 'python',
        include_comments: true,
        style: 'readable'
      }
    },
    
    orchestrator: {
      name: 'Orchestrator Agent',
      description: 'Coordinates other agents and manages workflow',
      role: 'Workflow Manager',
      goal: 'Plan tasks, delegate to specialized agents, and synthesize results',
      color: '#8b5cf6', // Violet
      allowedTools: [],
      config: {
        temperature: 0.5,
        max_tokens: 1000,
        planning_style: 'detailed',
        error_handling: 'adaptive'
      }
    },
    
    editor: {
      name: 'Editor Agent',
      description: 'Reviews and refines content from other agents',
      role: 'Content Editor',
      goal: 'Improve clarity, correctness, and style of content',
      color: '#ec4899', // Pink
      allowedTools: ['grammar_checker', 'markdown_formatter'],
      config: {
        temperature: 0.4,
        max_tokens: 1500,
        editing_style: 'thorough',
        focus_areas: ['clarity', 'accuracy', 'coherence']
      }
    },
    
    qa: {
      name: 'QA Agent',
      description: 'Tests outputs and verifies factual accuracy',
      role: 'Quality Assurance Specialist',
      goal: 'Verify information accuracy and identify potential errors',
      color: '#f59e0b', // Amber
      allowedTools: ['chromadb_retriever', 'fact_checker'],
      config: {
        temperature: 0.2,
        max_tokens: 1000,
        verification_depth: 'thorough',
        confidence_threshold: 0.8
      }
    }
  };
  
  /**
   * Get a list of all available tools that can be used by agents
   */
  export const availableTools = [
    {
      id: 'chromadb_retriever',
      name: 'RAG Knowledge Base',
      description: 'Retrieves information from the vector database',
      type: 'retriever'
    },
    {
      id: 'html_formatter',
      name: 'HTML Formatter',
      description: 'Formats content in HTML',
      type: 'formatter'
    },
    {
      id: 'markdown_formatter',
      name: 'Markdown Formatter',
      description: 'Formats content in Markdown',
      type: 'formatter'
    },
    {
      id: 'code_formatter',
      name: 'Code Formatter',
      description: 'Formats and prettifies code',
      type: 'formatter'
    },
    {
      id: 'grammar_checker',
      name: 'Grammar Checker',
      description: 'Checks and corrects grammar issues',
      type: 'checker'
    },
    {
      id: 'fact_checker',
      name: 'Fact Checker',
      description: 'Verifies factual information',
      type: 'checker'
    }
  ];
  
  /**
   * Returns the tool configuration object by ID
   */
  export const getToolById = (toolId) => {
    return availableTools.find(tool => tool.id === toolId);
  };