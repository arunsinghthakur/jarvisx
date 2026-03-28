from typing import Dict, List


class SystemAgentCodes:
    ORCHESTRATOR = "orchestrator"
    DEVELOPER = "developer"
    BROWSER = "browser"
    VOICE = "voice"
    RESEARCHER = "researcher"
    KNOWLEDGE = "knowledge"
    PII_GUARDIAN = "pii_guardian"
    AUDIT = "audit"
    POLICY = "policy"
    GOVERNANCE = "governance"

    @classmethod
    def all(cls) -> List[str]:
        return [
            cls.ORCHESTRATOR,
            cls.DEVELOPER,
            cls.BROWSER,
            cls.VOICE,
            cls.RESEARCHER,
            cls.KNOWLEDGE,
            cls.PII_GUARDIAN,
            cls.AUDIT,
            cls.POLICY,
            cls.GOVERNANCE,
        ]

    @classmethod
    def as_dict(cls) -> Dict[str, str]:
        return {
            "orchestrator": cls.ORCHESTRATOR,
            "developer": cls.DEVELOPER,
            "browser": cls.BROWSER,
            "voice": cls.VOICE,
            "researcher": cls.RESEARCHER,
            "knowledge": cls.KNOWLEDGE,
            "pii_guardian": cls.PII_GUARDIAN,
            "audit": cls.AUDIT,
            "policy": cls.POLICY,
            "governance": cls.GOVERNANCE,
        }


class SystemMCPCodes:
    SHELL = "shell"
    PLAYWRIGHT = "playwright"
    TAVILY = "tavily"

    @classmethod
    def all(cls) -> List[str]:
        return [
            cls.SHELL,
            cls.PLAYWRIGHT,
            cls.TAVILY,
        ]

    @classmethod
    def as_dict(cls) -> Dict[str, str]:
        return {
            "shell": cls.SHELL,
            "playwright": cls.PLAYWRIGHT,
            "tavily": cls.TAVILY,
        }


AGENT_IDS = SystemAgentCodes.as_dict()
MCP_IDS = SystemMCPCodes.as_dict()


__all__ = [
    "SystemAgentCodes",
    "SystemMCPCodes",
    "AGENT_IDS",
    "MCP_IDS",
]
