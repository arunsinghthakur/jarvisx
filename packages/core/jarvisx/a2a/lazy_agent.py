import logging
from typing import Optional, List, Callable, Any, AsyncGenerator, Dict

from google.adk.agents import LlmAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from pydantic import PrivateAttr

from jarvisx.a2a.llm_config import get_agent_llm_config, create_llm_model, LLMConfig

logger = logging.getLogger(__name__)


def _log_before_agent(callback_context: CallbackContext) -> Optional[types.Content]:
    logger.info("[AGENT] >> %s started", callback_context.agent_name)
    return None


def _log_after_agent(callback_context: CallbackContext) -> Optional[types.Content]:
    logger.info("[AGENT] << %s completed", callback_context.agent_name)
    return None


def _log_before_tool(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> Optional[Dict]:
    logger.info("[TOOL] %s -> %s", tool_context.agent_name, tool.name)
    logger.info("[TOOL] Args: %s", args)
    return None


def _log_after_tool(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict) -> Optional[Dict]:
    response_str = str(tool_response)
    logger.info("[TOOL] %s returned: %s", tool.name, response_str[:300] + ('...' if len(response_str) > 300 else ''))
    return None


class LazyLlmAgent(LlmAgent):
    """
    An LlmAgent with lazy sub-agent loading.
    
    The LLM model is initialized at creation time (required by Pydantic validation),
    but sub-agents are loaded lazily when delegation occurs. This allows for
    workflow-driven agent hierarchy at runtime.
    """
    
    _organization_id: str = PrivateAttr()
    _sub_agents_loaded: bool = PrivateAttr(default=False)
    _sub_agent_codes: List[str] = PrivateAttr(default_factory=list)
    _sub_agent_loader: Optional[Callable] = PrivateAttr(default=None)
    
    def __init__(
        self,
        name: str,
        organization_id: str,
        description: str = "",
        instruction: str = "",
        generate_content_config: Optional[types.GenerateContentConfig] = None,
        tools: Optional[list] = None,
        sub_agent_codes: Optional[List[str]] = None,
        sub_agent_loader: Optional[Callable] = None,
        sub_agents: Optional[List[BaseAgent]] = None,
        llm_config_id: Optional[str] = None,
        **kwargs
    ):
        logger.info("[LAZY AGENT] Creating %s (org=%s, llm_config_id=%s) - initializing LLM model", 
                    name, organization_id, llm_config_id)
        
        llm_config = get_agent_llm_config(organization_id, llm_config_id)
        model = create_llm_model(llm_config)
        
        logger.info("[LAZY AGENT] %s: LLM model created - %s", name, llm_config.model_name)
        
        super().__init__(
            name=name,
            model=model,
            description=description,
            instruction=instruction,
            generate_content_config=generate_content_config,
            tools=tools or [],
            sub_agents=sub_agents or [],
            before_agent_callback=_log_before_agent,
            after_agent_callback=_log_after_agent,
            before_tool_callback=_log_before_tool,
            after_tool_callback=_log_after_tool,
            **kwargs
        )
        
        self._organization_id = organization_id
        self._sub_agents_loaded = False
        self._sub_agent_codes = sub_agent_codes or []
        self._sub_agent_loader = sub_agent_loader
    
    async def _ensure_sub_agents_loaded(self):
        if not self._sub_agents_loaded and self._sub_agent_codes and self._sub_agent_loader:
            loaded_agents = await self._sub_agent_loader(
                self._organization_id,
                self._sub_agent_codes
            )
            
            if loaded_agents:
                self.sub_agents = list(self.sub_agents) + loaded_agents if self.sub_agents else loaded_agents
                logger.info("[LAZY AGENT] %s: Loaded sub-agents: %s", self.name, [a.name for a in loaded_agents])
                
                self._append_sub_agent_capabilities(loaded_agents)
            
            self._sub_agents_loaded = True
    
    def _append_sub_agent_capabilities(self, agents: List[BaseAgent]):
        if not agents:
            return
        
        capabilities_section = "\n\n## Connected Sub-Agents and Their Capabilities\n\n"
        capabilities_section += "**CRITICAL**: You MUST delegate to these agents for tasks matching their capabilities. Do NOT answer from memory.\n\n"
        
        for agent in agents:
            name = agent.name
            description = getattr(agent, 'description', '') or 'No description available'
            capabilities_section += f"### {name}\n{description}\n\n"
        
        capabilities_section += "**MANDATORY DELEGATION**: If a user's query matches ANY sub-agent's described capabilities, you MUST call `transfer_to_agent` to delegate. NEVER answer questions about current date, time, weather, news, or real-time data yourself - your training data is outdated. The sub-agents have live tools.\n"
        
        if self.instruction:
            self.instruction = self.instruction + capabilities_section
        else:
            self.instruction = capabilities_section
        
        logger.info("[LAZY AGENT] %s: Appended %d sub-agent capabilities to instruction", self.name, len(agents))
    
    @property
    def is_sub_agents_loaded(self) -> bool:
        return self._sub_agents_loaded
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        await self._ensure_sub_agents_loaded()
        
        async for event in super()._run_async_impl(ctx):
            yield event


__all__ = ["LazyLlmAgent"]
