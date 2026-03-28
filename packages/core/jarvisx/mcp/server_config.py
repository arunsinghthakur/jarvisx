from __future__ import annotations

import logging
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from jarvisx.config.configs import TAVILY_API_KEY
from jarvisx.config.constants import SystemMCPCodes

logger = logging.getLogger(__name__)


class MCPServerConfig(ABC):
    
    @abstractmethod
    def configure_environment(self, env: Dict[str, str]) -> Dict[str, str]:
        pass
    
    @abstractmethod
    def configure_args(self, args: List[str], workspace_root: Path) -> List[str]:
        pass
    
    def get_timeout(self) -> int:
        return 5


class DefaultMCPConfig(MCPServerConfig):
    
    def configure_environment(self, env: Dict[str, str]) -> Dict[str, str]:
        return env
    
    def configure_args(self, args: List[str], workspace_root: Path) -> List[str]:
        return args


class ShellConfig(MCPServerConfig):
    
    def configure_environment(self, env: Dict[str, str]) -> Dict[str, str]:
        return env
    
    def configure_args(self, args: List[str], workspace_root: Path) -> List[str]:
        resolved_args = []
        for arg in args:
            if "${workspace}" in arg:
                resolved_path = arg.replace("${workspace}", str(workspace_root))
                resolved_path = os.path.normpath(resolved_path)
                resolved_args.append(resolved_path)
                logger.debug("Resolved workspace path: %s -> %s", arg, resolved_path)
            elif arg.startswith("/") and not os.path.exists(arg):
                relative_path = workspace_root / arg.lstrip("/")
                if relative_path.exists():
                    resolved_args.append(str(relative_path))
                    logger.debug("Resolved absolute path: %s -> %s", arg, relative_path)
                else:
                    resolved_args.append(arg)
            else:
                resolved_args.append(arg)
        return resolved_args


class PlaywrightConfig(MCPServerConfig):
    
    def configure_environment(self, env: Dict[str, str]) -> Dict[str, str]:
        browser_cache_dir = os.path.join(tempfile.gettempdir(), f"browser-control-mcp-{os.getpid()}")
        env["PLAYWRIGHT_BROWSERS_PATH"] = browser_cache_dir
        env["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "0"
        os.makedirs(browser_cache_dir, exist_ok=True)
        logger.info("Configuring Playwright MCP cache at %s", browser_cache_dir)
        return env
    
    def configure_args(self, args: List[str], workspace_root: Path) -> List[str]:
        npmrc_path = self._get_npmrc_path(workspace_root)
        if npmrc_path:
            args = self._add_npmrc_config(args, npmrc_path)
            logger.info("Using .npmrc from %s for Playwright MCP", npmrc_path)
        return args
    
    def get_timeout(self) -> int:
        return 30
    
    def _get_npmrc_path(self, workspace_root: Path) -> Optional[str]:
        root_npmrc = workspace_root / ".npmrc"
        if root_npmrc.exists():
            return str(root_npmrc.absolute())
        
        home_npmrc = Path.home() / ".npmrc"
        if home_npmrc.exists():
            return str(home_npmrc.absolute())
        return None
    
    def _add_npmrc_config(self, args: List[str], npmrc_path: str) -> List[str]:
        new_args = []
        userconfig_added = False
        for arg in args:
            new_args.append(arg)
            if arg == "-y" and not userconfig_added:
                new_args.extend(["--userconfig", npmrc_path])
                userconfig_added = True
        if not userconfig_added:
            new_args = ["-y", "--userconfig", npmrc_path] + args
        return new_args


class TavilyConfig(MCPServerConfig):
    
    def configure_environment(self, env: Dict[str, str]) -> Dict[str, str]:
        if TAVILY_API_KEY:
            env["TAVILY_API_KEY"] = TAVILY_API_KEY
            logger.info("Configured Tavily MCP with API key from environment")
        else:
            logger.warning("TAVILY_API_KEY not found in environment. Tavily MCP may not work correctly.")
        return env
    
    def configure_args(self, args: List[str], workspace_root: Path) -> List[str]:
        npmrc_path = self._get_npmrc_path(workspace_root)
        if npmrc_path:
            args = self._add_npmrc_config(args, npmrc_path)
            logger.info("Using .npmrc from %s for Tavily MCP", npmrc_path)
        return args
    
    def get_timeout(self) -> int:
        return 30
    
    def _get_npmrc_path(self, workspace_root: Path) -> Optional[str]:
        root_npmrc = workspace_root / ".npmrc"
        if root_npmrc.exists():
            return str(root_npmrc.absolute())
        
        home_npmrc = Path.home() / ".npmrc"
        if home_npmrc.exists():
            return str(home_npmrc.absolute())
        return None
    
    def _add_npmrc_config(self, args: List[str], npmrc_path: str) -> List[str]:
        new_args = []
        userconfig_added = False
        for arg in args:
            new_args.append(arg)
            if arg == "-y" and not userconfig_added:
                new_args.extend(["--userconfig", npmrc_path])
                userconfig_added = True
        if not userconfig_added:
            new_args = ["-y", "--userconfig", npmrc_path] + args
        return new_args


from jarvisx.common.id_utils import mcp_uuid

MCP_SERVER_CONFIGS: Dict[str, MCPServerConfig] = {
    SystemMCPCodes.SHELL: ShellConfig(),
    SystemMCPCodes.PLAYWRIGHT: PlaywrightConfig(),
    SystemMCPCodes.TAVILY: TavilyConfig(),
}

_MCP_ID_TO_CONFIG: Dict[str, MCPServerConfig] = {
    mcp_uuid(code): config for code, config in MCP_SERVER_CONFIGS.items()
}


def get_mcp_server_config(server_id_or_code: str) -> MCPServerConfig:
    if server_id_or_code in MCP_SERVER_CONFIGS:
        return MCP_SERVER_CONFIGS[server_id_or_code]
    if server_id_or_code in _MCP_ID_TO_CONFIG:
        return _MCP_ID_TO_CONFIG[server_id_or_code]
    return DefaultMCPConfig()


__all__ = [
    "MCPServerConfig",
    "DefaultMCPConfig",
    "ShellConfig",
    "PlaywrightConfig",
    "TavilyConfig",
    "get_mcp_server_config",
    "MCP_SERVER_CONFIGS",
]
