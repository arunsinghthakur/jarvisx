from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GOOGLE_VERTEX = "google_vertex"
    LITELLM = "litellm"
    CUSTOM = "custom"


class LLMConfigBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: LLMProvider = LLMProvider.OPENAI
    api_base_url: Optional[str] = None
    model_name: str = Field(..., min_length=1, max_length=100)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    is_default: bool = False
    is_active: bool = True
    additional_config: Optional[Dict[str, Any]] = None


class LLMConfigCreate(LLMConfigBase):
    api_key: Optional[str] = Field(None, description="API key for the LLM provider")


class LLMConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider: Optional[LLMProvider] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = Field(None, description="API key for the LLM provider (leave empty to keep existing)")
    model_name: Optional[str] = Field(None, min_length=1, max_length=100)
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    additional_config: Optional[Dict[str, Any]] = None


class LLMConfigResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    provider: str
    api_base_url: Optional[str]
    has_api_key: bool
    model_name: str
    max_tokens: int
    temperature: float
    is_default: bool
    is_active: bool
    additional_config: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LLMConfigListResponse(BaseModel):
    configs: List[LLMConfigResponse]
    total: int


class LLMProviderInfo(BaseModel):
    id: str
    name: str
    description: str
    requires_api_key: bool
    requires_base_url: bool
    default_models: List[str]


class LLMProvidersResponse(BaseModel):
    providers: List[LLMProviderInfo]

