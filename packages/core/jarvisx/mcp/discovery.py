import logging
from typing import Any, Dict, Optional

from jarvisx.config.configs import MCP_CACHE_TTL
from jarvisx.database.models import MCPServer
from jarvisx.database.session import get_db_session
from jarvisx.common.cache import GlobalTTLCache

logger = logging.getLogger(__name__)


class MCPDiscovery:

    _config_cache: GlobalTTLCache[Dict[str, Any]] = GlobalTTLCache("mcp_config", MCP_CACHE_TTL)
    _metadata_cache: GlobalTTLCache[list[dict]] = GlobalTTLCache("mcp_metadata", MCP_CACHE_TTL)
    _name_cache: GlobalTTLCache[Dict[str, str]] = GlobalTTLCache("mcp_names", MCP_CACHE_TTL)

    def __init__(self, cache_ttl: Optional[int] = None):
        self.cache_ttl = cache_ttl or MCP_CACHE_TTL
        self._cache_key = "database_mcp_servers"

    def _load_mcp_config(self) -> Dict[str, Any]:
        with get_db_session() as db:
            try:
                servers = db.query(MCPServer).all()
                mcp_servers = {}
                id_to_name = {}
                
                for server in servers:
                    server_config = {}
                    id_to_name[server.id] = server.name
                    
                    if server.default_config:
                        if isinstance(server.default_config, dict):
                            if "command" in server.default_config:
                                server_config["command"] = server.default_config["command"]
                            if "args" in server.default_config:
                                server_config["args"] = server.default_config["args"]
                            if "env" in server.default_config:
                                server_config["env"] = server.default_config["env"]
                            if not server_config:
                                server_config = server.default_config
                        else:
                            logger.warning("Invalid default_config format for MCP server %s", server.name)
                            continue
                    else:
                        logger.warning("No default_config for MCP server %s, skipping", server.name)
                        continue
                    
                    mcp_servers[server.id] = server_config
                
                self._name_cache.set(self._cache_key, id_to_name)
                config = {"mcpServers": mcp_servers}
                logger.info("Loaded %d MCP servers from database", len(mcp_servers))
                return config
            except Exception as e:
                logger.error("Error loading MCP config from database: %s", e)
                return {"mcpServers": {}}

    def list_servers(self, force_refresh: bool = False) -> Dict[str, Any]:
        if not force_refresh:
            cached = self._config_cache.get(self._cache_key)
            if cached is not None:
                return cached["mcpServers"]
        config = self._load_mcp_config()
        self._config_cache.set(self._cache_key, config)
        return config["mcpServers"]

    def get_cached_tool_metadata(self) -> Optional[list[dict]]:
        return self._metadata_cache.get(self._cache_key)

    def store_tool_metadata(self, metadata: list[dict]) -> None:
        self._metadata_cache.set(self._cache_key, metadata.copy())

    def invalidate_metadata_cache(self) -> None:
        self._metadata_cache.invalidate(self._cache_key)

    def get_server_name(self, server_id: str) -> str:
        names = self._name_cache.get(self._cache_key)
        if names and server_id in names:
            return names[server_id]
        self.list_servers(force_refresh=True)
        names = self._name_cache.get(self._cache_key)
        return names.get(server_id, server_id) if names else server_id
