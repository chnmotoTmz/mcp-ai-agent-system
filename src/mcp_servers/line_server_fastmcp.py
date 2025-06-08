"""
LINE MCP Server - FastMCP Implementation
FastMCPを使用したLINEサービスのMCP実装
"""

import asyncio
import logging
import sys
import os
from typing import Any, Dict
from contextlib import asynccontextmanager
from dataclasses import dataclass

# パスを追加
sys.path.append('/home/moto/line-gemini-hatena-integration')

from mcp.server.fastmcp import FastMCP
from src.services.line_service import LineService

logger = logging.getLogger(__name__)

# Server Context Data
@dataclass
class ServerContext:
    line_service: LineService

# Create FastMCP server
line_mcp = FastMCP("LINE Service")

@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Manage application lifecycle"""
    logger.info("Initializing LINE MCP Server...")
    
    # Initialize LINE service
    line_service = LineService()
    
    try:
        yield ServerContext(line_service=line_service)
    finally:
        logger.info("LINE MCP Server cleanup completed")

# Set lifespan
line_mcp = FastMCP("LINE Service", lifespan=app_lifespan)

# MCP Tools
@line_mcp.tool()
async def send_message(user_id: str, message: str) -> dict:
    """LINEユーザーにメッセージを送信
    
    Args:
        user_id: 送信先ユーザーID
        message: 送信メッセージ
    
    Returns:
        dict: 送信結果
    """
    try:
        ctx = line_mcp.get_context()
        ctx.line_service.send_message(user_id, message)
        
        return {
            "success": True,
            "user_id": user_id,
            "message_sent": message,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to send LINE message: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@line_mcp.tool()
async def get_user_messages(user_id: str, limit: int = 10) -> dict:
    """ユーザーのメッセージ履歴を取得
    
    Args:
        user_id: ユーザーID
        limit: 取得件数
    
    Returns:
        dict: メッセージ履歴
    """
    try:
        ctx = line_mcp.get_context()
        messages = ctx.line_service.get_user_messages(user_id, limit)
        
        return {
            "success": True,
            "user_id": user_id,
            "messages": messages,
            "count": len(messages),
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to get user messages: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@line_mcp.tool()
async def save_message(
    message_id: str,
    user_id: str, 
    message_type: str,
    content: str = "",
    file_path: str = None
) -> dict:
    """メッセージをDBに保存
    
    Args:
        message_id: LINE メッセージID
        user_id: ユーザーID
        message_type: メッセージタイプ
        content: コンテンツ
        file_path: ファイルパス（オプション）
    
    Returns:
        dict: 保存結果
    """
    try:
        ctx = line_mcp.get_context()
        result = ctx.line_service.save_message(
            message_id=message_id,
            user_id=user_id,
            message_type=message_type,
            content=content,
            file_path=file_path
        )
        
        return {
            "success": True,
            "message_saved": result,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to save message: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

# MCP Resources
@line_mcp.resource("line://messages/{user_id}")
async def get_user_context(user_id: str) -> str:
    """ユーザーのコンテキスト情報を提供
    
    Args:
        user_id: ユーザーID
    
    Returns:
        str: ユーザーコンテキスト
    """
    try:
        ctx = line_mcp.get_context()
        messages = ctx.line_service.get_user_messages(user_id, limit=5)
        
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
        logger.error(f"Failed to get user context: {e}")
        return f"Error getting user context: {str(e)}"

# Utility functions
def _get_timestamp() -> str:
    """Get current timestamp"""
    from datetime import datetime
    return datetime.utcnow().isoformat()

# Health check
@line_mcp.tool()
async def health_check() -> dict:
    """MCPサーバーのヘルスチェック"""
    return {
        "status": "healthy",
        "service": "LINE MCP Server",
        "version": "1.0.0",
        "timestamp": _get_timestamp()
    }

# Main execution
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting LINE MCP Server...")
    line_mcp.run(transport="stdio")
