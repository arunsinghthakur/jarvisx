import React, { useState, useCallback, useEffect } from 'react';
import { agentsApi } from '../../services/api';
import './AgentHierarchyConfig.css';

const AgentItem = ({ 
  agentCode, 
  config, 
  onChange, 
  definitions,
  depth = 0,
  maxDepth = 10
}) => {
  const [expanded, setExpanded] = useState(false);
  const agentDef = definitions[agentCode];
  
  if (!agentDef) {
    return null;
  }
  
  const isEnabled = config[agentCode]?.enabled || false;
  const subAgentConfig = config[agentCode]?.sub_agents || {};
  const hasPossibleSubAgents = agentDef.possible_sub_agents && agentDef.possible_sub_agents.length > 0;
  const canExpand = isEnabled && hasPossibleSubAgents && depth < maxDepth;
  
  const handleToggle = useCallback((e) => {
    e.stopPropagation();
    const newEnabled = !isEnabled;
    
    onChange({
      ...config,
      [agentCode]: {
        enabled: newEnabled,
        sub_agents: newEnabled ? (config[agentCode]?.sub_agents || {}) : {}
      }
    });
  }, [agentCode, config, isEnabled, onChange]);
  
  const handleSubAgentChange = useCallback((newSubConfig) => {
    onChange({
      ...config,
      [agentCode]: {
        ...config[agentCode],
        enabled: true,
        sub_agents: newSubConfig
      }
    });
  }, [agentCode, config, onChange]);
  
  const handleExpandClick = useCallback((e) => {
    e.stopPropagation();
    if (canExpand) {
      setExpanded(!expanded);
    }
  }, [canExpand, expanded]);
  
  return (
    <div className={`agent-hierarchy-item depth-${depth}`}>
      <div className="agent-row">
        <div 
          className={`expand-icon ${canExpand ? 'clickable' : 'disabled'}`}
          onClick={handleExpandClick}
        >
          {canExpand ? (
            expanded ? '▼' : '▶'
          ) : (
            <span className="no-children" />
          )}
        </div>
        
        <label className="agent-checkbox-label">
          <input
            type="checkbox"
            checked={isEnabled}
            onChange={handleToggle}
          />
          <span className="agent-icon">
            {hasPossibleSubAgents ? '👥' : '👤'}
          </span>
          <span className="agent-name">{agentDef.name}</span>
        </label>
        
        {hasPossibleSubAgents && (
          <span className="sub-agent-count">
            ({agentDef.possible_sub_agents.length} sub-agents)
          </span>
        )}
      </div>
      
      <div className="agent-description">{agentDef.description}</div>
      
      {expanded && canExpand && (
        <div className="sub-agents-container">
          <AgentHierarchyList
            agentCodes={agentDef.possible_sub_agents}
            config={subAgentConfig}
            onChange={handleSubAgentChange}
            definitions={definitions}
            depth={depth + 1}
            maxDepth={maxDepth}
          />
        </div>
      )}
    </div>
  );
};

const AgentHierarchyList = ({ 
  agentCodes,
  config = {},
  onChange,
  definitions,
  depth = 0,
  maxDepth = 10,
}) => {
  if (!agentCodes || agentCodes.length === 0) {
    return null;
  }
  
  return (
    <div className={`agent-hierarchy-config depth-${depth}`}>
      {agentCodes.map(agentCode => (
        <AgentItem
          key={agentCode}
          agentCode={agentCode}
          config={config}
          onChange={onChange}
          definitions={definitions}
          depth={depth}
          maxDepth={maxDepth}
        />
      ))}
    </div>
  );
};

const AgentHierarchyConfig = ({ 
  agentCodes,
  config = {},
  onChange,
  depth = 0,
  maxDepth = 10,
  title
}) => {
  const [definitions, setDefinitions] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [rootAgentCodes, setRootAgentCodes] = useState(agentCodes || []);

  useEffect(() => {
    const fetchDefinitions = async () => {
      try {
        setLoading(true);
        const response = await agentsApi.getHierarchyDefinitions();
        const defs = {};
        const rootCodes = [];
        
        response.data.forEach(def => {
          defs[def.code] = def;
          rootCodes.push(def.code);
        });
        
        setDefinitions(defs);
        if (!agentCodes || agentCodes.length === 0) {
          setRootAgentCodes(rootCodes);
        }
        setError(null);
      } catch (err) {
        console.error('Failed to fetch agent hierarchy definitions:', err);
        setError('Failed to load agent definitions');
      } finally {
        setLoading(false);
      }
    };

    fetchDefinitions();
  }, [agentCodes]);

  if (loading) {
    return (
      <div className="agent-hierarchy-loading">
        <span className="spinner">⏳</span>
        <span>Loading agent definitions...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="agent-hierarchy-error">
        {error}
      </div>
    );
  }

  if (!rootAgentCodes || rootAgentCodes.length === 0) {
    return (
      <div className="agent-hierarchy-empty">
        No agents available
      </div>
    );
  }

  return (
    <div className="agent-hierarchy-wrapper">
      {title && depth === 0 && (
        <h4 className="hierarchy-title">{title}</h4>
      )}
      <AgentHierarchyList
        agentCodes={rootAgentCodes}
        config={config}
        onChange={onChange}
        definitions={definitions}
        depth={depth}
        maxDepth={maxDepth}
      />
    </div>
  );
};

export const SYSTEM_AGENTS_FOR_HIERARCHY = [];

export const convertFlatToHierarchy = (connectedAgents) => {
  if (!connectedAgents || !Array.isArray(connectedAgents)) {
    return {};
  }
  
  const hierarchy = {};
  connectedAgents.forEach(code => {
    hierarchy[code] = { enabled: true, sub_agents: {} };
  });
  return hierarchy;
};

export const convertHierarchyToFlat = (hierarchy) => {
  if (!hierarchy || typeof hierarchy !== 'object') {
    return [];
  }
  
  const codes = [];
  Object.entries(hierarchy).forEach(([code, config]) => {
    if (config?.enabled) {
      codes.push(code);
    }
  });
  return codes;
};

export const getEnabledAgentCodes = (hierarchy, prefix = '') => {
  const codes = [];
  
  Object.entries(hierarchy || {}).forEach(([code, config]) => {
    if (config?.enabled) {
      const fullCode = prefix ? `${prefix}.${code}` : code;
      codes.push(fullCode);
      
      if (config.sub_agents && Object.keys(config.sub_agents).length > 0) {
        codes.push(...getEnabledAgentCodes(config.sub_agents, fullCode));
      }
    }
  });
  
  return codes;
};

export default AgentHierarchyConfig;
