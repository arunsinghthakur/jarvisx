from abc import ABC, abstractmethod
from typing import Any


class BaseNodeExecutor(ABC):
    @abstractmethod
    async def execute(
        self,
        config: dict,
        input_data: dict,
        node_data: dict
    ) -> dict:
        pass
    
    def interpolate_variables(self, text: str, context: dict) -> str:
        import re
        
        def replace_var(match):
            var_path = match.group(1)
            parts = var_path.split(".")
            value = context
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                else:
                    return ""
            return str(value) if value else ""
        
        return re.sub(r"\{\{([^}]+)\}\}", replace_var, text)
