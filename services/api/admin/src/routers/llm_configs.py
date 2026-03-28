import logging
import uuid
import base64
import hashlib
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from services.api.admin.src.dependencies import get_db, get_current_user
from services.api.admin.src.models.llm_configs import (
    LLMProvider,
    LLMConfigCreate,
    LLMConfigUpdate,
    LLMConfigResponse,
    LLMConfigListResponse,
    LLMProviderInfo,
    LLMProvidersResponse,
)
from jarvisx.database.models import OrganizationLLMConfig, Organization, User
from jarvisx.config.configs import LLM_ENCRYPTION_KEY

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations/{organization_id}/llm-configs", tags=["LLM Configs"])


def _encrypt_api_key(api_key: str) -> str:
    key = hashlib.sha256(LLM_ENCRYPTION_KEY.encode()).digest()[:32]
    key_bytes = api_key.encode()
    encrypted = bytes(a ^ b for a, b in zip(key_bytes, key * (len(key_bytes) // len(key) + 1)))
    return base64.b64encode(encrypted).decode()


def _decrypt_api_key(encrypted_key: str) -> str:
    key = hashlib.sha256(LLM_ENCRYPTION_KEY.encode()).digest()[:32]
    encrypted = base64.b64decode(encrypted_key.encode())
    decrypted = bytes(a ^ b for a, b in zip(encrypted, key * (len(encrypted) // len(key) + 1)))
    return decrypted.decode()


def _to_response(config: OrganizationLLMConfig) -> LLMConfigResponse:
    return LLMConfigResponse(
        id=config.id,
        organization_id=config.organization_id,
        name=config.name,
        provider=config.provider,
        api_base_url=config.api_base_url,
        has_api_key=bool(config.api_key_encrypted),
        model_name=config.model_name,
        max_tokens=config.max_tokens,
        temperature=config.temperature / 10.0,
        is_default=config.is_default,
        is_active=config.is_active,
        additional_config=config.additional_config,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


LLM_PROVIDERS = [
    LLMProviderInfo(
        id="openai",
        name="OpenAI",
        description="OpenAI GPT models (GPT-4, GPT-3.5, etc.)",
        requires_api_key=True,
        requires_base_url=False,
        default_models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    ),
    LLMProviderInfo(
        id="anthropic",
        name="Anthropic",
        description="Anthropic Claude models",
        requires_api_key=True,
        requires_base_url=False,
        default_models=["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
    ),
    LLMProviderInfo(
        id="azure_openai",
        name="Azure OpenAI",
        description="Azure-hosted OpenAI models",
        requires_api_key=True,
        requires_base_url=True,
        default_models=["gpt-4o", "gpt-4", "gpt-35-turbo"],
    ),
    LLMProviderInfo(
        id="google_vertex",
        name="Google Vertex AI",
        description="Google Gemini models via Vertex AI",
        requires_api_key=False,
        requires_base_url=False,
        default_models=["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    ),
    LLMProviderInfo(
        id="litellm",
        name="LiteLLM Proxy",
        description="LiteLLM proxy for unified access to multiple providers",
        requires_api_key=True,
        requires_base_url=True,
        default_models=["gpt-4o", "claude-3-5-sonnet", "gemini-pro"],
    ),
    LLMProviderInfo(
        id="custom",
        name="Custom Provider",
        description="Custom OpenAI-compatible endpoint",
        requires_api_key=True,
        requires_base_url=True,
        default_models=[],
    ),
]


@router.get("/providers", response_model=LLMProvidersResponse)
async def get_llm_providers(
    current_user: User = Depends(get_current_user),
):
    return LLMProvidersResponse(providers=LLM_PROVIDERS)


@router.get("", response_model=LLMConfigListResponse)
async def list_llm_configs(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    configs = db.query(OrganizationLLMConfig).filter(
        OrganizationLLMConfig.organization_id == organization_id
    ).order_by(OrganizationLLMConfig.created_at.desc()).all()
    
    return LLMConfigListResponse(
        configs=[_to_response(c) for c in configs],
        total=len(configs),
    )


@router.get("/{config_id}", response_model=LLMConfigResponse)
async def get_llm_config(
    organization_id: str,
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    config = db.query(OrganizationLLMConfig).filter(
        OrganizationLLMConfig.id == config_id,
        OrganizationLLMConfig.organization_id == organization_id,
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    
    return _to_response(config)


@router.post("", response_model=LLMConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_config(
    organization_id: str,
    config_data: LLMConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    existing = db.query(OrganizationLLMConfig).filter(
        OrganizationLLMConfig.organization_id == organization_id,
        OrganizationLLMConfig.name == config_data.name,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="LLM config with this name already exists")
    
    if config_data.is_default:
        db.query(OrganizationLLMConfig).filter(
            OrganizationLLMConfig.organization_id == organization_id,
            OrganizationLLMConfig.is_default == True,
        ).update({"is_default": False})
    
    config = OrganizationLLMConfig(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        name=config_data.name,
        provider=config_data.provider.value,
        api_base_url=config_data.api_base_url,
        api_key_encrypted=_encrypt_api_key(config_data.api_key) if config_data.api_key else None,
        model_name=config_data.model_name,
        max_tokens=config_data.max_tokens,
        temperature=int(config_data.temperature * 10),
        is_default=config_data.is_default,
        is_active=config_data.is_active,
        additional_config=config_data.additional_config,
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    logger.info(f"Created LLM config '{config.name}' for organization {organization_id}")
    return _to_response(config)


@router.put("/{config_id}", response_model=LLMConfigResponse)
async def update_llm_config(
    organization_id: str,
    config_id: str,
    config_data: LLMConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    config = db.query(OrganizationLLMConfig).filter(
        OrganizationLLMConfig.id == config_id,
        OrganizationLLMConfig.organization_id == organization_id,
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    
    if config_data.name and config_data.name != config.name:
        existing = db.query(OrganizationLLMConfig).filter(
            OrganizationLLMConfig.organization_id == organization_id,
            OrganizationLLMConfig.name == config_data.name,
            OrganizationLLMConfig.id != config_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="LLM config with this name already exists")
    
    if config_data.is_default:
        db.query(OrganizationLLMConfig).filter(
            OrganizationLLMConfig.organization_id == organization_id,
            OrganizationLLMConfig.is_default == True,
            OrganizationLLMConfig.id != config_id,
        ).update({"is_default": False})
    
    update_data = config_data.model_dump(exclude_unset=True)
    
    if "api_key" in update_data:
        api_key = update_data.pop("api_key")
        if api_key:
            config.api_key_encrypted = _encrypt_api_key(api_key)
    
    if "temperature" in update_data:
        update_data["temperature"] = int(update_data["temperature"] * 10)
    
    if "provider" in update_data:
        update_data["provider"] = update_data["provider"].value
    
    for key, value in update_data.items():
        setattr(config, key, value)
    
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    
    logger.info(f"Updated LLM config '{config.name}' for organization {organization_id}")
    return _to_response(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config(
    organization_id: str,
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    config = db.query(OrganizationLLMConfig).filter(
        OrganizationLLMConfig.id == config_id,
        OrganizationLLMConfig.organization_id == organization_id,
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    
    db.delete(config)
    db.commit()
    
    logger.info(f"Deleted LLM config '{config.name}' from organization {organization_id}")


@router.post("/{config_id}/set-default", response_model=LLMConfigResponse)
async def set_default_llm_config(
    organization_id: str,
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    config = db.query(OrganizationLLMConfig).filter(
        OrganizationLLMConfig.id == config_id,
        OrganizationLLMConfig.organization_id == organization_id,
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    
    db.query(OrganizationLLMConfig).filter(
        OrganizationLLMConfig.organization_id == organization_id,
        OrganizationLLMConfig.is_default == True,
    ).update({"is_default": False})
    
    config.is_default = True
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    
    logger.info(f"Set LLM config '{config.name}' as default for organization {organization_id}")
    return _to_response(config)


@router.post("/{config_id}/test")
async def test_llm_config(
    organization_id: str,
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    config = db.query(OrganizationLLMConfig).filter(
        OrganizationLLMConfig.id == config_id,
        OrganizationLLMConfig.organization_id == organization_id,
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    
    try:
        import litellm
        
        api_key = _decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else None
        
        model = config.model_name
        if config.provider in ["litellm", "custom"]:
            model = f"openai/{config.model_name}"
        elif config.provider == "azure_openai":
            model = f"azure/{config.model_name}"
        elif config.provider == "anthropic":
            model = f"anthropic/{config.model_name}"
        elif config.provider == "google_vertex":
            model = f"vertex_ai/{config.model_name}"
        
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": "Say 'Hello' in one word."}],
            api_key=api_key,
            api_base=config.api_base_url,
            max_tokens=10,
            temperature=0.1,
        )
        
        return {
            "success": True,
            "message": "LLM connection successful",
            "response": response.choices[0].message.content if response.choices else None,
            "model": response.model,
        }
    except Exception as e:
        logger.error(f"LLM test failed for config {config_id}: {e}")
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
        }
