"""
MCP Base Server Configuration
共通設定とベースクラス
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MCPConfig:
    """MCP Server Configuration"""
    name: str
    description: str
    version: str = "1.0.0"
    
class BaseMCPServer(ABC):
    """Base class for all MCP servers"""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.name = config.name
        self.description = config.description
        self.version = config.version
        self.logger = logging.getLogger(f"mcp.{self.name}")
        
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the MCP server"""
        pass
    
    @abstractmethod 
    async def cleanup(self) -> None:
        """Cleanup resources"""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Basic health check"""
        return {
            "status": "healthy",
            "name": self.name,
            "version": self.version,
            "timestamp": self._get_timestamp()
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()

# Shared utilities
class MCPError(Exception):
    """Base exception for MCP operations"""
    pass

class MCPConnectionError(MCPError):
    """Connection-related MCP errors"""
    pass

class MCPValidationError(MCPError):
    """Validation-related MCP errors"""
    pass
