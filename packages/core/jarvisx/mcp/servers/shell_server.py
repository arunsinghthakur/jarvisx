import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from jarvisx.config.configs import WORKSPACE_BASE_PATH

DEFAULT_TENANT = "default"
logger = logging.getLogger(__name__)


def get_tenant_workspace(workspace_id: str = None) -> Path:
    effective_workspace = workspace_id or DEFAULT_TENANT
    return Path(WORKSPACE_BASE_PATH) / effective_workspace


class WriteFileInput(BaseModel):
    filename: str = Field(..., description="Name of the file to write (e.g., 'index.html')")
    content: str = Field(..., description="Complete file content to write")
    workspace_id: str = Field(default=DEFAULT_TENANT, description="Tenant ID for workspace isolation")


class CommandInput(BaseModel):
    command: str = Field(..., description="Command to execute")
    workspace_id: str = Field(default=DEFAULT_TENANT, description="Tenant ID for workspace isolation")


def clear_dist_directory(workspace_id: str = None):
    dist_path = get_tenant_workspace(workspace_id)
    if dist_path.exists():
        for item in dist_path.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                logger.warning("Could not remove %s: %s", item, e)


def get_dist_files(workspace_id: str = None):
    dist_path = get_tenant_workspace(workspace_id)
    if not dist_path.exists():
        return []
    return [f for f in dist_path.rglob("*") if f.is_file()]


def detect_file_operations(command: str) -> bool:
    file_operation_patterns = [
        ">",
        ">>",
        "echo",
        "cat >",
        "touch",
        "mkdir",
        "write",
        ".html",
        ".css",
        ".js",
    ]
    command_lower = command.lower()
    return any(pattern in command_lower for pattern in file_operation_patterns)


mcp = FastMCP(name="shell_server")

@mcp.tool("write_file")
def write_file(input: WriteFileInput) -> str:
    try:
        dist_path = get_tenant_workspace(input.workspace_id)
        dist_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dist_path / input.filename
        file_path.write_text(input.content, encoding='utf-8')
        
        abs_path = file_path.absolute()
        logger.info("File saved via shell_server for tenant %s: %s", input.workspace_id, abs_path)
        
        return f"File written successfully: {abs_path}"
    except Exception as e:
        error_msg = f"Error writing file: {str(e)}"
        logger.error("[shell_server] %s", error_msg)
        return error_msg


@mcp.tool("shell_server")
async def run_command(command: str, workspace_id: str = DEFAULT_TENANT) -> str:
    try:
        workspace = get_tenant_workspace(workspace_id)
        workspace.mkdir(parents=True, exist_ok=True)
        
        result = subprocess.run(command, shell=True, cwd=str(workspace), text=True, capture_output=True)
        
        output = result.stdout or result.stderr
        if result.returncode != 0 and not result.stdout:
            output = f"Error: {result.stderr or 'Command failed'}"
        
        logger.info("Command executed for tenant %s: %s", workspace_id, command[:50])
        return output
    except Exception as e:
        return f"Error running command: {str(e)}"
    

if __name__ == "__main__":
    mcp.run(transport="stdio")
