"""
LINE MCP Server
LINEサービスをMCP経由で提供
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from src.core.mcp_base import BaseMCPServer, MCPConfig, MCPError
from src.services.line_service import LineService

logger = logging.getLogger(__name__)

@dataclass
class LineToolArgs:
    """LINE Tool Arguments"""
    user_id: str
    message: Optional[str] = None
    limit: Optional[int] = 10

class LineMCPServer(BaseMCPServer):
    """LINE MCP Server Implementation"""
    
    def __init__(self):
        config = MCPConfig(
            name="line-service",
            description="LINE Bot operations via MCP",
            version="1.0.0"
        )
        super().__init__(config)
        self.line_service = None
        
    async def initialize(self) -> None:
        """Initialize LINE service"""
        try:
            self.line_service = LineService()
            self.logger.info(f"LINE MCP Server {self.version} initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize LINE service: {e}")
            raise MCPError(f"LINE service initialization failed: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.logger.info("LINE MCP Server cleanup completed")
    
    # MCP Tools Implementation
    async def send_message_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: LINEユーザーにメッセージを送信
        Args:
            user_id (str): 送信先ユーザーID
            message (str): 送信メッセージ
        Returns:
            Dict: 送信結果
        """
        try:
            user_id = args.get("user_id")
            message = args.get("message")
            
            if not user_id or not message:
                raise MCPError("user_id and message are required")
            
            # LINE service call
            self.line_service.send_message(user_id, message)
            
            return {
                "success": True,
                "user_id": user_id,
                "message_sent": message,
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send LINE message: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def get_user_messages_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: ユーザーのメッセージ履歴を取得
        Args:
            user_id (str): ユーザーID
            limit (int): 取得件数 (default: 10)
        Returns:
            Dict: メッセージ履歴
        """
        try:
            user_id = args.get("user_id")
            limit = args.get("limit", 10)
            
            if not user_id:
                raise MCPError("user_id is required")
            
            # LINE service call
            messages = self.line_service.get_user_messages(user_id, limit)
            
            return {
                "success": True,
                "user_id": user_id,
                "messages": messages,
                "count": len(messages),
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get user messages: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def save_message_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: メッセージをDBに保存
        Args:
            message_id (str): LINE メッセージID
            user_id (str): ユーザーID
            message_type (str): メッセージタイプ
            content (str): コンテンツ
            file_path (str, optional): ファイルパス
        Returns:
            Dict: 保存結果
        """
        try:
            message_id = args.get("message_id")
            user_id = args.get("user_id")
            message_type = args.get("message_type")
            content = args.get("content")
            file_path = args.get("file_path")
            
            if not all([message_id, user_id, message_type]):
                raise MCPError("message_id, user_id, and message_type are required")
            
            # LINE service call
            result = self.line_service.save_message(
                message_id=message_id,
                user_id=user_id,
                message_type=message_type,
                content=content,
                file_path=file_path
            )
            
            return {
                "success": True,
                "message_saved": result,
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to save message: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

    # MCP Resources Implementation  
    async def get_user_context_resource(self, user_id: str) -> str:
        """
        Resource: ユーザーのコンテキスト情報を提供
        Args:
            user_id (str): ユーザーID
        Returns:
            str: ユーザーコンテキスト（テキスト形式）
        """
        try:
            messages = self.line_service.get_user_messages(user_id, limit=5)
            
            context_lines = [
                f"User ID: {user_id}",
                f"Recent Messages: {len(messages)}",
                "--- Message History ---"
            ]
            
            for msg in messages:
                msg_line = f"[{msg.get('created_at', 'Unknown')}] {msg.get('message_type', 'text')}: {msg.get('content', '')[:100]}"
                context_lines.append(msg_line)
            
            return "\\n".join(context_lines)
            
        except Exception as e:
            self.logger.error(f"Failed to get user context: {e}")
            return f"Error getting user context: {str(e)}"

    # Tool Registry for external access
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return [
            {
                "name": "send_message",
                "description": "LINEユーザーにメッセージを送信",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "送信先ユーザーID"},
                        "message": {"type": "string", "description": "送信メッセージ"}
                    },
                    "required": ["user_id", "message"]
                }
            },
            {
                "name": "get_user_messages", 
                "description": "ユーザーのメッセージ履歴を取得",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "ユーザーID"},
                        "limit": {"type": "integer", "description": "取得件数", "default": 10}
                    },
                    "required": ["user_id"]
                }
            },
            {
                "name": "save_message",
                "description": "メッセージをDBに保存",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "message_id": {"type": "string", "description": "LINE メッセージID"},
                        "user_id": {"type": "string", "description": "ユーザーID"},
                        "message_type": {"type": "string", "description": "メッセージタイプ"},
                        "content": {"type": "string", "description": "コンテンツ"},
                        "file_path": {"type": "string", "description": "ファイルパス（オプション）"}
                    },
                    "required": ["message_id", "user_id", "message_type"]
                }
            }
        ]
    
    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name"""
        tool_map = {
            "send_message": self.send_message_tool,
            "get_user_messages": self.get_user_messages_tool,
            "save_message": self.save_message_tool
        }
        
        if tool_name not in tool_map:
            raise MCPError(f"Unknown tool: {tool_name}")
        
        return await tool_map[tool_name](args)

# Standalone server runner
async def run_line_mcp_server():
    """Run LINE MCP Server as standalone"""
    server = LineMCPServer()
    
    try:
        await server.initialize()
        logger.info("LINE MCP Server started")
        
        # Keep server running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down LINE MCP Server")
    except Exception as e:
        logger.error(f"LINE MCP Server error: {e}")
    finally:
        await server.cleanup()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    asyncio.run(run_line_mcp_server())
