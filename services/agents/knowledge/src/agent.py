import logging
from pathlib import Path
from typing import Any, Dict, Optional

from google.adk.tools.function_tool import FunctionTool
from google.genai import types

from jarvisx.common.utils import read_file
from jarvisx.database.session import SessionLocal
from jarvisx.services.knowledge_base import KnowledgeBaseService
from jarvisx.a2a.lazy_agent import LazyLlmAgent
from jarvisx.a2a.agent_defaults import DEFAULT_SAFETY_SETTINGS

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
DESCRIPTION = read_file(str(PROMPTS_DIR / "description.txt"))
INSTRUCTION = read_file(str(PROMPTS_DIR / "instruction.txt"))


def _create_knowledge_tools(organization_id: str):
    def search_knowledge_base(query: str, limit: int = 5) -> Dict[str, Any]:
        try:
            db = SessionLocal()
            try:
                service = KnowledgeBaseService(db)
                results = service.search(
                    organization_id=organization_id,
                    query=query,
                    limit=limit,
                    similarity_threshold=0.6
                )
                
                if not results:
                    return {
                        "query": query,
                        "message": "No relevant information found in the knowledge base",
                        "results": []
                    }
                
                formatted_results = []
                for r in results:
                    formatted_results.append({
                        "title": r["entry_title"],
                        "content": r["chunk_content"],
                        "relevance": f"{r['similarity_score']*100:.0f}%",
                        "type": r["entry_type"]
                    })
                
                return {
                    "query": query,
                    "total_results": len(formatted_results),
                    "results": formatted_results
                }
            finally:
                db.close()
        except Exception as e:
            return {
                "error": str(e),
                "results": []
            }

    return [FunctionTool(func=search_knowledge_base)]


def create_knowledge_agent(
    organization_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    sub_agent_config: Optional[Dict[str, Any]] = None,
    llm_config_id: Optional[str] = None,
) -> LazyLlmAgent:
    if not organization_id:
        raise ValueError("organization_id is required to create knowledge agent")
    
    logger.info("[KNOWLEDGE] Creating lazy agent for org: %s (llm_config_id: %s)", organization_id, llm_config_id)
    
    tools = _create_knowledge_tools(organization_id)
    
    sub_agent_loader = None
    sub_agent_codes = []
    
    if sub_agent_config:
        enabled_subs = [k for k, v in sub_agent_config.items() if v.get("enabled", True)]
        if enabled_subs:
            sub_agent_codes = enabled_subs
            logger.info("[KNOWLEDGE] Configured with sub-agents: %s", enabled_subs)
            
            async def load_sub_agents(org_id, _codes):
                from jarvisx.a2a.system_agent_factory import load_selected_agents
                sub_hierarchy = {k: v for k, v in sub_agent_config.items() if v.get("enabled", True)}
                return await load_selected_agents(org_id, enabled_subs, workflow_id, sub_hierarchy)
            
            sub_agent_loader = load_sub_agents
    
    return LazyLlmAgent(
        name="knowledge",
        organization_id=organization_id,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        generate_content_config=types.GenerateContentConfig(
            safety_settings=DEFAULT_SAFETY_SETTINGS,
        ),
        tools=tools,
        sub_agent_codes=sub_agent_codes,
        sub_agent_loader=sub_agent_loader,
        llm_config_id=llm_config_id,
    )
