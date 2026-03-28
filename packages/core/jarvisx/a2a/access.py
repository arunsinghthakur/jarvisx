from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from jarvisx.database.models import Agent, AgentMCP
from jarvisx.database.session import SessionLocal
from jarvisx.common.id_utils import agent_uuid

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentConfig:
    name: str
    allowed_mcp_servers: Optional[Tuple[str, ...]] = None
    max_parallel_mcp_runs: int = 5


def get_agent_config(agent_id: str, workspace_id: Optional[str] = None) -> AgentConfig:
    agent_db_id = agent_uuid(agent_id)
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.id == agent_db_id).first()
        if agent:
            enabled_mcps = db.query(AgentMCP).filter(
                AgentMCP.agent_id == agent_db_id,
                AgentMCP.is_enabled == True
            ).all()
            allowed_mcp_servers = tuple([mcp.mcp_server_id for mcp in enabled_mcps]) if enabled_mcps else tuple()
            return AgentConfig(
                name=agent.name,
                allowed_mcp_servers=allowed_mcp_servers,
                max_parallel_mcp_runs=5,
            )
        logger.warning(f"Agent {agent_id} not found in database")
        return AgentConfig(name=agent_id, allowed_mcp_servers=(), max_parallel_mcp_runs=0)
    except Exception as e:
        logger.error(f"Error loading agent {agent_id} from database: {e}")
        return AgentConfig(name=agent_id, allowed_mcp_servers=(), max_parallel_mcp_runs=0)
    finally:
        db.close()


__all__ = [
    "AgentConfig",
    "get_agent_config",
]
