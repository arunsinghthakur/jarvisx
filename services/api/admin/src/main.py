from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

from services.api.admin.src.routers import organizations, workspaces, agents, mcps, workspace_config, billing, auth, teams, llm_configs, knowledge_base, workflows, dashboard, platform, compliance, tracing, integrations, chatbot, sso, encryption_keys, platform_settings, dead_letters, workflow_debug, workflow_templates
from services.api.admin.src.models import OrganizationResponse, WorkspaceResponse
from services.api.admin.src.middleware.csrf import CSRFMiddleware
from jarvisx.tracing import LangFuseTracingMiddleware
from jarvisx.tracing.litellm_integration import setup_litellm_langfuse_callback
from jarvisx.a2a.llm_config import LLMConfigNotFoundError

logger = logging.getLogger(__name__)

setup_litellm_langfuse_callback()

OrganizationResponse.model_rebuild()
WorkspaceResponse.model_rebuild()

app = FastAPI(title="JarvisX Admin API", version="1.0.0")


@app.exception_handler(LLMConfigNotFoundError)
async def llm_config_not_found_handler(request: Request, exc: LLMConfigNotFoundError):
    return JSONResponse(
        status_code=403,
        content={
            "error": "llm_config_required",
            "message": str(exc),
            "action": "Please configure LLM settings in the LLM Settings page."
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        messages = []
        for error in errors:
            field = error.get('loc', [])[-1] if error.get('loc') else 'field'
            msg = error.get('msg', 'Invalid value')
            messages.append(f"{field}: {msg}")
        detail = "; ".join(messages)
    else:
        detail = "Validation error"
    return JSONResponse(
        status_code=422,
        content={"detail": detail}
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5003",
        "http://localhost:5001",
        "http://127.0.0.1:5003",
        "http://127.0.0.1:5001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*", "x-csrf-token"],
    expose_headers=["*"],
)

app.add_middleware(CSRFMiddleware)
app.add_middleware(LangFuseTracingMiddleware, service_name="admin-api")

app.include_router(auth.router)
app.include_router(sso.router)
app.include_router(encryption_keys.router)
app.include_router(organizations.router)
app.include_router(workspaces.router)
app.include_router(agents.router)
app.include_router(mcps.router)
app.include_router(workspace_config.router)
app.include_router(billing.router)
app.include_router(teams.router)
app.include_router(llm_configs.router)
app.include_router(knowledge_base.router)
app.include_router(workflows.router)
app.include_router(workflows.webhooks_router)
app.include_router(dashboard.router)
app.include_router(platform.router)
app.include_router(platform_settings.router)
app.include_router(compliance.router)
app.include_router(tracing.router)
app.include_router(integrations.router)
app.include_router(chatbot.router)
app.include_router(dead_letters.router)
app.include_router(workflow_debug.router)
app.include_router(workflow_templates.router)


@app.get("/")
def root():
    return {"message": "JarvisX Admin API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
