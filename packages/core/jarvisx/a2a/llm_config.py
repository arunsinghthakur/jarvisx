from __future__ import annotations

import logging
import base64
import hashlib
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from jarvisx.config.configs import LLM_ENCRYPTION_KEY
from jarvisx.database.session import get_engine

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    name: str
    provider: str
    api_base_url: Optional[str]
    api_key: Optional[str]
    model_name: str
    max_tokens: int
    temperature: float
    is_default: bool
    additional_config: Optional[dict] = None


def _decrypt_api_key(encrypted_key: Optional[str]) -> Optional[str]:
    if not encrypted_key:
        return None
    try:
        key = hashlib.sha256(LLM_ENCRYPTION_KEY.encode()).digest()[:32]
        encrypted = base64.b64decode(encrypted_key.encode())
        decrypted = bytes(a ^ b for a, b in zip(encrypted, key * (len(encrypted) // len(key) + 1)))
        return decrypted.decode()
    except Exception as e:
        logger.warning(f"Failed to decrypt API key: {e}")
        return None


def get_llm_config_from_db(
    organization_id: str,
    purpose: Optional[str] = None,
    provider: Optional[str] = None,
    get_default: bool = False,
) -> Optional[LLMConfig]:
    if not organization_id:
        logger.warning("organization_id is required to fetch LLM config from database")
        return None
    
    try:
        engine = get_engine()
        with engine.connect() as conn:
            query_parts = ["SELECT * FROM organization_llm_configs WHERE is_active = true AND organization_id = :organization_id"]
            params = {"organization_id": organization_id}
            
            if purpose:
                query_parts.append("AND additional_config->>'purpose' = :purpose")
                params["purpose"] = purpose
            
            if provider:
                query_parts.append("AND provider = :provider")
                params["provider"] = provider
            
            if get_default:
                query_parts.append("AND is_default = true")
            
            query_parts.append("ORDER BY is_default DESC, created_at ASC LIMIT 1")
            
            query = " ".join(query_parts)
            result = conn.execute(text(query), params).fetchone()
            
            if result:
                return LLMConfig(
                    name=result.name,
                    provider=result.provider,
                    api_base_url=result.api_base_url,
                    api_key=_decrypt_api_key(result.api_key_encrypted),
                    model_name=result.model_name,
                    max_tokens=result.max_tokens,
                    temperature=result.temperature / 10.0,
                    is_default=result.is_default,
                    additional_config=result.additional_config,
                )
    except SQLAlchemyError as e:
        logger.warning(f"Failed to fetch LLM config from database: {e}")
    
    return None


def get_llm_config_by_id(config_id: str) -> Optional[LLMConfig]:
    if not config_id:
        logger.warning("config_id is required to fetch LLM config from database")
        return None
    
    try:
        engine = get_engine()
        with engine.connect() as conn:
            query = "SELECT * FROM organization_llm_configs WHERE id = :config_id AND is_active = true"
            result = conn.execute(text(query), {"config_id": config_id}).fetchone()
            
            if result:
                return LLMConfig(
                    name=result.name,
                    provider=result.provider,
                    api_base_url=result.api_base_url,
                    api_key=_decrypt_api_key(result.api_key_encrypted),
                    model_name=result.model_name,
                    max_tokens=result.max_tokens,
                    temperature=result.temperature / 10.0,
                    is_default=result.is_default,
                    additional_config=result.additional_config,
                )
    except SQLAlchemyError as e:
        logger.warning(f"Failed to fetch LLM config from database: {e}")
    
    return None


class LLMConfigNotFoundError(Exception):
    pass


def create_llm_model(llm_config: LLMConfig):
    import os
    import litellm
    from google.adk.models.lite_llm import LiteLlm
    
    logger.info("[LLM CONFIG] Creating LLM model: provider=%s, model=%s, api_base=%s", 
                llm_config.provider, llm_config.model_name, llm_config.api_base_url)
    
    if llm_config.api_base_url:
            logger.info("[LLM CONFIG] Configuring LiteLLM proxy mode")
            # if llm_config.api_key:
            #     os.environ["LITELLM_PROXY_API_KEY"] = llm_config.api_key
            # os.environ["LITELLM_PROXY_API_BASE"] = llm_config.api_base_url
            litellm.use_litellm_proxy = True
        
    return LiteLlm(
        model=llm_config.model_name,
        api_key=llm_config.api_key,
        api_base=llm_config.api_base_url,
    )


def _get_any_active_llm_config(organization_id: str) -> Optional[LLMConfig]:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            query = """
                SELECT * FROM organization_llm_configs 
                WHERE is_active = true 
                AND organization_id = :organization_id 
                ORDER BY is_default DESC, created_at ASC 
                LIMIT 1
            """
            result = conn.execute(text(query), {"organization_id": organization_id}).fetchone()
            
            if result:
                return LLMConfig(
                    name=result.name,
                    provider=result.provider,
                    api_base_url=result.api_base_url,
                    api_key=_decrypt_api_key(result.api_key_encrypted),
                    model_name=result.model_name,
                    max_tokens=result.max_tokens,
                    temperature=result.temperature / 10.0,
                    is_default=result.is_default,
                    additional_config=result.additional_config,
                )
    except SQLAlchemyError as e:
        logger.warning(f"Failed to fetch any LLM config from database: {e}")
    
    return None


def get_agent_llm_config(organization_id: str, llm_config_id: Optional[str] = None) -> LLMConfig:
    logger.info("[LLM CONFIG] get_agent_llm_config() called for org: %s, config_id: %s", organization_id, llm_config_id)
    
    if not organization_id:
        raise LLMConfigNotFoundError(
            "Organization ID is required. Please provide a valid organization context."
        )
    
    if llm_config_id:
        logger.info("[LLM CONFIG] Fetching specific config by ID: %s", llm_config_id)
        config = get_llm_config_by_id(llm_config_id)
        if config and config.api_key:
            logger.info("[LLM CONFIG] Found config by ID: %s (model=%s)", config.name, config.model_name)
            return config
        logger.warning("[LLM CONFIG] Config ID %s not found or inactive, falling back to org defaults", llm_config_id)
    
    logger.info("[LLM CONFIG] Checking DB for a2a_agents purpose config...")
    config = get_llm_config_from_db(
        organization_id=organization_id,
        purpose="a2a_agents",
    )
    if config and config.api_key:
        logger.info("[LLM CONFIG] Found a2a_agents config in DB: %s (model=%s)", config.name, config.model_name)
        return config
    
    logger.info("[LLM CONFIG] Checking DB for default config...")
    config = get_llm_config_from_db(
        organization_id=organization_id,
        get_default=True,
    )
    if config and config.api_key:
        logger.info("[LLM CONFIG] Found default config in DB: %s (model=%s)", config.name, config.model_name)
        return config
    
    logger.info("[LLM CONFIG] Checking DB for any active config...")
    config = _get_any_active_llm_config(organization_id)
    if config and config.api_key:
        logger.info("[LLM CONFIG] Found active config in DB: %s (model=%s)", config.name, config.model_name)
        return config
    
    logger.error("[LLM CONFIG] No config found for org %s - LLM configuration required", organization_id)
    raise LLMConfigNotFoundError(
        f"Organization {organization_id} must configure LLM settings before using agents. "
        "Please add an LLM configuration in the LLM Settings page."
    )


def get_tts_config(organization_id: str, tts_config_id: Optional[str] = None) -> LLMConfig:
    if not organization_id:
        raise LLMConfigNotFoundError(
            "Organization ID is required for TTS configuration."
        )
    
    if tts_config_id:
        config = get_llm_config_by_id(tts_config_id)
        if config and config.api_key:
            return config
        logger.warning("[LLM CONFIG] TTS config ID %s not found, falling back to org defaults", tts_config_id)
    
    config = get_llm_config_from_db(
        organization_id=organization_id,
        purpose="tts",
    )
    if config and config.api_key:
        return config
    
    logger.error(f"No TTS config found for organization {organization_id} - TTS configuration required")
    raise LLMConfigNotFoundError(
        f"Organization {organization_id} must configure TTS settings before using voice features. "
        "Please add a TTS configuration in the LLM Settings page."
    )


def get_stt_config(organization_id: str, stt_config_id: Optional[str] = None) -> LLMConfig:
    if not organization_id:
        raise LLMConfigNotFoundError(
            "Organization ID is required for STT configuration."
        )
    
    if stt_config_id:
        config = get_llm_config_by_id(stt_config_id)
        if config and config.api_key:
            return config
        logger.warning("[LLM CONFIG] STT config ID %s not found, falling back to org defaults", stt_config_id)
    
    config = get_llm_config_from_db(
        organization_id=organization_id,
        purpose="stt",
    )
    if config and config.api_key:
        return config
    
    logger.error(f"No STT config found for organization {organization_id} - STT configuration required")
    raise LLMConfigNotFoundError(
        f"Organization {organization_id} must configure STT settings before using voice features. "
        "Please add an STT configuration in the LLM Settings page."
    )


def get_embedding_config(organization_id: str, embedding_config_id: Optional[str] = None) -> LLMConfig:
    if not organization_id:
        raise LLMConfigNotFoundError(
            "Organization ID is required for embedding configuration."
        )
    
    if embedding_config_id:
        config = get_llm_config_by_id(embedding_config_id)
        if config and config.api_key:
            return config
        logger.warning("[LLM CONFIG] Embedding config ID %s not found, falling back to org defaults", embedding_config_id)
    
    config = get_llm_config_from_db(
        organization_id=organization_id,
        purpose="embedding",
    )
    if config and config.api_key:
        return config
    
    config = get_llm_config_from_db(
        organization_id=organization_id,
        get_default=True,
    )
    if config and config.api_key:
        return config
    
    config = _get_any_active_llm_config(organization_id)
    if config and config.api_key:
        return config
    
    logger.error(f"No embedding config found for organization {organization_id}")
    raise LLMConfigNotFoundError(
        f"Organization {organization_id} must configure embedding settings for knowledge base features. "
        "Please add an LLM configuration in the LLM Settings page."
    )
