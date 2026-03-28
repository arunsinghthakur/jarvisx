export const SystemAgentCodes = Object.freeze({
  ORCHESTRATOR: 'orchestrator',
  DEVELOPER: 'developer',
  BROWSER: 'browser',
  VOICE: 'voice',
  RESEARCHER: 'researcher',
  KNOWLEDGE: 'knowledge',
  PII_GUARDIAN: 'pii_guardian',
  AUDIT: 'audit',
  POLICY: 'policy',
  GOVERNANCE: 'governance',
})

export const SystemAgentNames = Object.freeze({
  [SystemAgentCodes.ORCHESTRATOR]: 'Orchestrator',
  [SystemAgentCodes.DEVELOPER]: 'Developer',
  [SystemAgentCodes.BROWSER]: 'Browser',
  [SystemAgentCodes.VOICE]: 'Voice',
  [SystemAgentCodes.RESEARCHER]: 'Researcher',
  [SystemAgentCodes.KNOWLEDGE]: 'Knowledge',
  [SystemAgentCodes.PII_GUARDIAN]: 'PII Guardian',
  [SystemAgentCodes.AUDIT]: 'Audit',
  [SystemAgentCodes.POLICY]: 'Policy',
  [SystemAgentCodes.GOVERNANCE]: 'Governance',
})

export const SYSTEM_AGENTS = Object.freeze([
  {
    code: SystemAgentCodes.DEVELOPER,
    name: 'Developer',
    description: 'Assists with coding tasks, debugging, and software development',
  },
  {
    code: SystemAgentCodes.BROWSER,
    name: 'Browser',
    description: 'Browses the web, extracts information, and interacts with web pages',
  },
  {
    code: SystemAgentCodes.RESEARCHER,
    name: 'Researcher',
    description: 'Performs research, gathers information, and analyzes data',
  },
  {
    code: SystemAgentCodes.KNOWLEDGE,
    name: 'Knowledge',
    description: 'Accesses and manages knowledge bases and documentation',
  },
  {
    code: SystemAgentCodes.PII_GUARDIAN,
    name: 'PII Guardian',
    description: 'Detects and protects personally identifiable information',
  },
  {
    code: SystemAgentCodes.AUDIT,
    name: 'Audit',
    description: 'Tracks and logs activities for compliance and auditing',
  },
  {
    code: SystemAgentCodes.POLICY,
    name: 'Policy',
    description: 'Enforces organizational policies and rules',
  },
  {
    code: SystemAgentCodes.GOVERNANCE,
    name: 'Governance',
    description: 'Ensures compliance with governance standards and regulations',
  },
])

export const CoreAgentCodes = Object.freeze([
  SystemAgentCodes.ORCHESTRATOR,
  SystemAgentCodes.VOICE,
])

export const CoreAgentNames = Object.freeze([
  SystemAgentNames[SystemAgentCodes.ORCHESTRATOR],
  SystemAgentNames[SystemAgentCodes.VOICE],
])

export const isSystemAgent = (agentIdOrName) => {
  if (!agentIdOrName) return false
  const lowerValue = agentIdOrName.toLowerCase()
  return Object.values(SystemAgentCodes).includes(lowerValue) ||
    Object.values(SystemAgentNames).some(name => name.toLowerCase() === lowerValue)
}

export const isOrchestratorAgent = (agent) => {
  if (!agent) return false
  return agent.id === SystemAgentCodes.ORCHESTRATOR ||
    agent.name === SystemAgentNames[SystemAgentCodes.ORCHESTRATOR]
}

export const isCoreAgent = (agent) => {
  if (!agent) return false
  return CoreAgentCodes.includes(agent.id) || CoreAgentNames.includes(agent.name)
}

export default {
  SystemAgentCodes,
  SystemAgentNames,
  SYSTEM_AGENTS,
  CoreAgentCodes,
  CoreAgentNames,
  isSystemAgent,
  isOrchestratorAgent,
  isCoreAgent,
}
