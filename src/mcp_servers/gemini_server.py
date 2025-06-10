"""
Gemini MCP Server
Gemini AIサービスをMCP経由で提供
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from src.core.mcp_base import BaseMCPServer, MCPConfig, MCPError
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class GeminiMCPServer(BaseMCPServer):
    """Gemini MCP Server Implementation"""
    
    def __init__(self):
        config = MCPConfig(
            name="gemini-service",
            description="Gemini AI operations via MCP",
            version="1.0.0"
        )
        super().__init__(config)
        self.gemini_service = None
        
    async def initialize(self) -> None:
        """Initialize Gemini service"""
        try:
            self.gemini_service = GeminiService()
            self.logger.info(f"Gemini MCP Server {self.version} initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini service: {e}")
            raise MCPError(f"Gemini service initialization failed: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.logger.info("Gemini MCP Server cleanup completed")
    
    # MCP Tools Implementation
    async def generate_content_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: テキストからコンテンツを生成
        Args:
            text (str): 入力テキスト
            style (str, optional): 生成スタイル (default: "blog")
        Returns:
            Dict: 生成結果
        """
        try:
            text = args.get("text")
            style = args.get("style", "blog")
            
            if not text:
                raise MCPError("text is required")
            
            # Gemini service call
            generated_content = self.gemini_service.generate_content(text)
            
            if generated_content:
                return {
                    "success": True,
                    "input_text": text,
                    "style": style,
                    "generated_content": generated_content,
                    "timestamp": self._get_timestamp()
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to generate content",
                    "timestamp": self._get_timestamp()
                }
            
        except Exception as e:
            self.logger.error(f"Failed to generate content: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def analyze_image_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: 画像を分析してコンテンツ生成
        Args:
            image_path (str): 画像ファイルパス
            analysis_type (str, optional): 分析タイプ (default: "general")
        Returns:
            Dict: 分析結果
        """
        try:
            image_path = args.get("image_path")
            analysis_type = args.get("analysis_type", "general")
            
            if not image_path:
                raise MCPError("image_path is required")
            
            # Gemini service call
            analysis_result = self.gemini_service.analyze_image(image_path)
            
            if analysis_result:
                return {
                    "success": True,
                    "image_path": image_path,
                    "analysis_type": analysis_type,
                    "analysis_result": analysis_result,
                    "timestamp": self._get_timestamp()
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to analyze image",
                    "timestamp": self._get_timestamp()
                }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze image: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def generate_article_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: メッセージから記事を生成
        Args:
            message_id (int): メッセージID
            title_hint (str, optional): タイトルのヒント
        Returns:
            Dict: 記事生成結果
        """
        try:
            message_id = args.get("message_id")
            title_hint = args.get("title_hint", "")
            
            if not message_id:
                raise MCPError("message_id is required")
            
            # Get message from database
            from src.database import Message
            message = Message.query.get(message_id)
            
            if not message:
                raise MCPError(f"Message {message_id} not found")
            
            # Gemini service call
            article_data = self.gemini_service.generate_article_from_message(message)
            
            if article_data:
                return {
                    "success": True,
                    "message_id": message_id,
                    "article_data": article_data,
                    "timestamp": self._get_timestamp()
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to generate article",
                    "timestamp": self._get_timestamp()
                }
            
        except Exception as e:
            self.logger.error(f"Failed to generate article: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def generate_multi_article_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: 複数メッセージから記事を生成
        Args:
            message_ids (List[int]): メッセージIDリスト
            theme (str, optional): 記事のテーマ
        Returns:
            Dict: 記事生成結果
        """
        try:
            message_ids = args.get("message_ids", [])
            theme = args.get("theme", "")
            
            if not message_ids:
                raise MCPError("message_ids is required")
            
            # Gemini service call
            article_data = self.gemini_service.generate_article_from_messages(message_ids)
            
            if article_data:
                return {
                    "success": True,
                    "message_ids": message_ids,
                    "theme": theme,
                    "article_data": article_data,
                    "timestamp": self._get_timestamp()
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to generate multi-message article",
                    "timestamp": self._get_timestamp()
                }
            
        except Exception as e:
            self.logger.error(f"Failed to generate multi-message article: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

    # MCP Resources Implementation
    async def get_article_templates_resource(self) -> str:
        """
        Resource: 記事テンプレート情報を提供
        Returns:
            str: 利用可能なテンプレート情報
        """
        templates = [
            "Blog Article: 一般的なブログ記事形式",
            "News Report: ニュースレポート形式", 
            "Tutorial: チュートリアル形式",
            "Review: レビュー記事形式",
            "Essay: エッセイ形式"
        ]
        
        return "\\n".join([
            "Available Article Templates:",
            "=" * 30
        ] + templates)
    
    async def get_style_guide_resource(self) -> str:
        """
        Resource: スタイルガイド情報を提供
        Returns:
            str: スタイルガイド情報
        """
        style_guide = [
            "Style Guidelines:",
            "- Use clear and concise language",
            "- Include relevant examples",
            "- Structure with headers and subheaders",
            "- Add a compelling introduction",
            "- Conclude with actionable insights"
        ]
        
        return "\\n".join(style_guide)

    # Tool Registry for external access
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return [
            {
                "name": "generate_content",
                "description": "テキストからコンテンツを生成",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "入力テキスト"},
                        "style": {"type": "string", "description": "生成スタイル", "default": "blog"}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "analyze_image",
                "description": "画像を分析してコンテンツ生成",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string", "description": "画像ファイルパス"},
                        "analysis_type": {"type": "string", "description": "分析タイプ", "default": "general"}
                    },
                    "required": ["image_path"]
                }
            },
            {
                "name": "generate_article",
                "description": "メッセージから記事を生成",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "integer", "description": "メッセージID"},
                        "title_hint": {"type": "string", "description": "タイトルのヒント"}
                    },
                    "required": ["message_id"]
                }
            },
            {
                "name": "generate_multi_article",
                "description": "複数メッセージから記事を生成",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message_ids": {"type": "array", "items": {"type": "integer"}, "description": "メッセージIDリスト"},
                        "theme": {"type": "string", "description": "記事のテーマ"}
                    },
                    "required": ["message_ids"]
                }
            }
        ]
    
    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name"""
        tool_map = {
            "generate_content": self.generate_content_tool,
            "analyze_image": self.analyze_image_tool,
            "generate_article": self.generate_article_tool,
            "generate_multi_article": self.generate_multi_article_tool
        }
        
        if tool_name not in tool_map:
            raise MCPError(f"Unknown tool: {tool_name}")
        
        return await tool_map[tool_name](args)

# Standalone server runner
async def run_gemini_mcp_server():
    """Run Gemini MCP Server as standalone"""
    server = GeminiMCPServer()
    
    try:
        await server.initialize()
        logger.info("Gemini MCP Server started")
        
        # Keep server running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down Gemini MCP Server")
    except Exception as e:
        logger.error(f"Gemini MCP Server error: {e}")
    finally:
        await server.cleanup()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run server
    asyncio.run(run_gemini_mcp_server())
