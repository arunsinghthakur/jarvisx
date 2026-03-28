import logging
from google.adk.runners import Runner
from google.genai import types
from jarvisx.workflows.nodes.base import BaseNodeExecutor
from jarvisx.a2a.storage import get_session_service, get_artifact_service, get_memory_service
from jarvisx.common.multimedia import create_multimodal_parts

logger = logging.getLogger(__name__)


class AgentNodeExecutor(BaseNodeExecutor):
    _runners = {}
    
    @classmethod
    async def _get_runner(cls, agent_type: str, workflow_id: str, tenant_id: str = None, workspace_id: str = None, llm_config_id: str = None):
        if not workflow_id:
            raise ValueError("workflow_id is required for agent node execution")
        
        effective_tenant_id = tenant_id or "default"
        effective_workspace_id = workspace_id or "default"
        cache_key = f"{effective_tenant_id}:{effective_workspace_id}:{workflow_id}:{agent_type}:{llm_config_id or 'default'}"
        
        if cache_key not in cls._runners:
            if agent_type == "orchestrator":
                from services.agents.orchestrator.src.agent import create_orchestrator_agent
                
                logger.info("[AgentNode] Creating lazy orchestrator for workflow: %s (llm_config_id: %s)", workflow_id, llm_config_id)
                agent = create_orchestrator_agent(
                    workflow_id=workflow_id,
                    organization_id=tenant_id,
                    llm_config_id=llm_config_id
                )
            else:
                agent = await cls._create_specific_agent(agent_type, tenant_id, llm_config_id)
            
            logger.info("[AgentNode] Lazy agent '%s' created - NO LLM initialized yet", agent_type)
            
            session_service = get_session_service(tenant_id=effective_tenant_id, workspace_id=effective_workspace_id)
            artifact_service = get_artifact_service(tenant_id=effective_tenant_id, workspace_id=effective_workspace_id)
            memory_service = get_memory_service(tenant_id=effective_tenant_id, workspace_id=effective_workspace_id)
            
            cls._runners[cache_key] = Runner(
                agent=agent,
                app_name=f"workflow-{effective_tenant_id}",
                session_service=session_service,
                artifact_service=artifact_service,
                memory_service=memory_service
            )
        return cls._runners[cache_key]
    
    @classmethod
    async def _create_specific_agent(cls, agent_type: str, organization_id: str, llm_config_id: str = None):
        from jarvisx.config.constants import SystemAgentCodes
        
        agent_creators = {
            SystemAgentCodes.DEVELOPER: lambda org, llm_id: cls._import_and_create("services.agents.developer.src.agent", "create_developer_agent", org, llm_id),
            SystemAgentCodes.BROWSER: lambda org, llm_id: cls._import_and_create("services.agents.browser.src.agent", "create_browser_agent", org, llm_id),
            SystemAgentCodes.RESEARCHER: lambda org, llm_id: cls._import_and_create("services.agents.researcher.src.agent", "create_researcher_agent", org, llm_id),
            SystemAgentCodes.KNOWLEDGE: lambda org, llm_id: cls._import_and_create("services.agents.knowledge.src.agent", "create_knowledge_agent", org, llm_id),
            SystemAgentCodes.PII_GUARDIAN: lambda org, llm_id: cls._import_and_create("services.agents.pii_guardian.src.agent", "create_pii_guardian_agent", org, llm_id),
            SystemAgentCodes.AUDIT: lambda org, llm_id: cls._import_and_create("services.agents.audit.src.agent", "create_audit_agent", org, llm_id),
            SystemAgentCodes.POLICY: lambda org, llm_id: cls._import_and_create("services.agents.policy.src.agent", "create_policy_agent", org, llm_id),
            SystemAgentCodes.GOVERNANCE: lambda org, llm_id: cls._import_and_create("services.agents.governance.src.agent", "create_governance_agent", org, llm_id),
        }
        
        if agent_type not in agent_creators:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        return agent_creators[agent_type](organization_id, llm_config_id)
    
    @staticmethod
    def _import_and_create(module_path: str, func_name: str, organization_id: str, llm_config_id: str = None):
        import importlib
        module = importlib.import_module(module_path)
        create_func = getattr(module, func_name)
        return create_func(organization_id=organization_id, llm_config_id=llm_config_id)
    
    def _has_multimodal_content(self, input_data: dict) -> bool:
        if input_data.get("is_binary"):
            return True
        if input_data.get("files"):
            return True
        if input_data.get("mime_type") and not input_data.get("mime_type", "").startswith("text/"):
            return True
        return False
    
    def _build_content_parts(self, prompt: str, input_data: dict) -> list:
        if self._has_multimodal_content(input_data):
            parts = create_multimodal_parts(input_data, prompt)
            content_type = input_data.get("content_category", "unknown")
            file_name = input_data.get("filename", "file")
            logger.info(f"[AgentNode] Built multimodal content with {len(parts)} parts ({content_type}: {file_name})")
            return parts
        
        return [types.Part.from_text(text=prompt)]
    
    async def execute(
        self,
        config: dict,
        input_data: dict,
        node_data: dict
    ) -> dict:
        agent_name = config.get("agent", "orchestrator")
        prompt_template = config.get("prompt", "")
        llm_config_id = config.get("llm_config_id")
        tenant_id = node_data.get("organization_id") or node_data.get("tenant_id")
        workspace_id = node_data.get("workspace_id")
        workflow_id = node_data.get("workflow_id")
        include_file_content = config.get("include_file_content", True)
        
        if not workflow_id:
            raise ValueError("workflow_id is required in node_data for agent execution")
        
        context = {"input": input_data}
        prompt = self.interpolate_variables(prompt_template, context)
        
        if not prompt:
            if input_data.get("extracted_text"):
                prompt = f"Please analyze this content:\n\n{input_data['extracted_text']}"
            elif input_data.get("is_binary"):
                prompt = f"Please analyze this {input_data.get('content_category', 'file')}: {input_data.get('filename', 'uploaded file')}"
            else:
                prompt = str(input_data)
        
        try:
            runner = await self._get_runner(
                agent_type=agent_name,
                workflow_id=workflow_id,
                tenant_id=tenant_id, 
                workspace_id=workspace_id,
                llm_config_id=llm_config_id
            )
            
            user_id = node_data.get("user_id", "workflow-system")
            effective_tenant_id = tenant_id or "default"
            session = await runner.session_service.create_session(
                app_name=f"workflow-{effective_tenant_id}",
                user_id=user_id
            )
            
            if include_file_content and self._has_multimodal_content(input_data):
                parts = self._build_content_parts(prompt, input_data)
            else:
                parts = [types.Part.from_text(text=prompt)]
            
            content = types.Content(
                role="user",
                parts=parts
            )
            
            response_text = ""
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content
            ):
                if hasattr(event, 'content') and event.content:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
            
            return {
                "response": response_text,
                "agent": agent_name,
                "session_id": session.id,
                "multimodal": self._has_multimodal_content(input_data),
                "content_type": input_data.get("content_category", "text")
            }
                
        except Exception as e:
            logger.error(f"Error calling agent {agent_name}: {e}")
            raise
