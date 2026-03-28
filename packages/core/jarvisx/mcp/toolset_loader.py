import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams, StreamableHTTPServerParams

from jarvisx.mcp.discovery import MCPDiscovery
from jarvisx.mcp.server_config import get_mcp_server_config

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent.parent


async def load_mcp_toolsets(allowed_servers: Optional[tuple[str, ...]] = None) -> list[MCPToolset]:
    discovery = MCPDiscovery()
    all_servers = discovery.list_servers()
    
    if allowed_servers is not None:
        allowed_set = set(allowed_servers)
        servers = [
            (server_id, server, discovery.get_server_name(server_id))
            for server_id, server in all_servers.items()
            if server_id in allowed_set
        ]
    else:
        servers = [
            (server_id, server, discovery.get_server_name(server_id))
            for server_id, server in all_servers.items()
        ]
    
    async def _load_server(server_id: str, server: dict, server_name: str) -> Optional[MCPToolset]:
        try:
            server_config = get_mcp_server_config(server_id)
            
            if server.get("command") == "streamable_http":
                conn = StreamableHTTPServerParams(url=server["args"][0])
                timeout_value = 5
            else:
                args = server["args"].copy()
                env = os.environ.copy()
                if "env" in server:
                    env.update(server["env"])

                env = server_config.configure_environment(env)
                args = server_config.configure_args(args, WORKSPACE_ROOT)
                timeout_value = server_config.get_timeout()

                conn = StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command=server["command"],
                        args=args,
                        env=env,
                    ),
                    timeout=timeout_value,
                )
            
            mcp_toolset = MCPToolset(connection_params=conn)
            toolset = await asyncio.wait_for(mcp_toolset.get_tools(), timeout=timeout_value + 5)
            
            if toolset:
                tool_names = [tool.name for tool in toolset]
                logger.info("Loaded tools from server '%s': %s", server_name, ", ".join(tool_names))
                return mcp_toolset
            return None
        except asyncio.TimeoutError:
            logger.warning("Timeout connecting to MCP server %s", server_name)
        except FileNotFoundError as e:
            logger.warning("MCP server %s skipped: file or directory not found: %s", server_name, e)
        except Exception as e:
            error_msg = str(e)
            if "No such file or directory" in error_msg or "os error 2" in error_msg.lower():
                logger.warning("MCP server %s skipped: file or directory not found: %s", server_name, e)
            elif "npm" in error_msg.lower() or "E401" in error_msg or "authentication" in error_msg.lower():
                logger.warning("MCP server %s skipped due to npm/auth error: %s", server_name, e)
            elif "ConnectError" in error_msg or "connection" in error_msg.lower() or "Connection closed" in error_msg:
                logger.warning("Could not connect to MCP server %s: %s", server_name, e)
            else:
                logger.warning("Error loading tools from %s: %s", server_name, e)
        return None

    load_results = await asyncio.gather(
        *[_load_server(server_id, server, server_name) for server_id, server, server_name in servers],
        return_exceptions=True
    )

    toolsets = []
    for result in load_results:
        if isinstance(result, BaseException):
            logger.error("Exception loading MCP server: %s", result)
            continue
        if result is not None:
            toolsets.append(result)

    logger.info("Loaded %d MCP toolsets", len(toolsets))
    return toolsets
