"""
Simple Agent Core
MCPサーバーを統合するシンプルなエージェントコア
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from src.mcp_servers.line_server import LineMCPServer
from src.mcp_servers.gemini_server import GeminiMCPServer
from src.mcp_servers.hatena_server import HatenaMCPServer
from src.core.mcp_base import MCPError

logger = logging.getLogger(__name__)

@dataclass
class TaskContext:
    """Task execution context"""
    user_id: str
    message_id: Optional[str] = None
    task_type: str = "unknown"
    input_data: Optional[Dict[str, Any]] = None
    workflow_state: str = "initialized"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SimpleAgentCore:
    """Simple Agent Core for MCP integration"""
    
    def __init__(self):
        self.name = "simple-agent-core"
        self.version = "1.0.0"
        self.logger = logging.getLogger(f"agent.{self.name}")
        
        # MCP Servers
        self.line_server = None
        self.gemini_server = None
        self.hatena_server = None
        
        # Server status
        self.servers_initialized = False
    
    async def initialize(self) -> None:
        """Initialize all MCP servers"""
        try:
            self.logger.info("Initializing Simple Agent Core...")
            
            # Initialize MCP servers
            self.line_server = LineMCPServer()
            await self.line_server.initialize()
            
            self.gemini_server = GeminiMCPServer()
            await self.gemini_server.initialize()
            
            self.hatena_server = HatenaMCPServer()
            await self.hatena_server.initialize()
            
            self.servers_initialized = True
            self.logger.info(f"Simple Agent Core {self.version} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Agent Core: {e}")
            raise MCPError(f"Agent Core initialization failed: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup all resources"""
        try:
            if self.line_server:
                await self.line_server.cleanup()
            if self.gemini_server:
                await self.gemini_server.cleanup()
            if self.hatena_server:
                await self.hatena_server.cleanup()
            
            self.logger.info("Simple Agent Core cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all servers"""
        health_status = {
            "agent_core": {
                "status": "healthy",
                "version": self.version,
                "initialized": self.servers_initialized
            }
        }
        
        if self.servers_initialized:
            try:
                if self.line_server:
                    health_status["line_server"] = await self.line_server.health_check()
                if self.gemini_server:
                    health_status["gemini_server"] = await self.gemini_server.health_check()
                if self.hatena_server:
                    health_status["hatena_server"] = await self.hatena_server.health_check()
            except Exception as e:
                health_status["error"] = str(e)
        
        return health_status
    
    async def process_line_message(self, message_data: Dict[str, Any]) -> TaskContext:
        """
        Process incoming LINE message (main workflow)
        Args:
            message_data: LINE message data
        Returns:
            TaskContext: Processing result
        """
        context = TaskContext(
            user_id=message_data.get("user_id", "unknown"),
            message_id=message_data.get("message_id"),
            task_type="line_message_processing",
            input_data=message_data
        )
        
        try:
            self.logger.info(f"Processing LINE message from user {context.user_id}")
            
            # Step 1: Save message to database
            context.workflow_state = "saving_message"
            save_result = await self._save_line_message(message_data)
            
            if not save_result.get("success"):
                context.error = f"Failed to save message: {save_result.get('error')}"
                context.workflow_state = "failed"
                return context
            
            # Step 2: Generate content with Gemini
            context.workflow_state = "generating_content"
            content_result = await self._generate_content(message_data)
            
            if not content_result.get("success"):
                context.error = f"Failed to generate content: {content_result.get('error')}"
                context.workflow_state = "failed"
                return context
            
            # Step 3: Publish to Hatena
            context.workflow_state = "publishing_article"
            publish_result = await self._publish_article(content_result)
            
            if not publish_result.get("success"):
                context.error = f"Failed to publish article: {publish_result.get('error')}"
                context.workflow_state = "failed"
                return context
            
            # Step 4: Send notification to LINE
            context.workflow_state = "sending_notification"
            notification_result = await self._send_notification(
                context.user_id, 
                publish_result
            )
            
            # Complete workflow
            context.workflow_state = "completed"
            context.result = {
                "save_result": save_result,
                "content_result": content_result,
                "publish_result": publish_result,
                "notification_result": notification_result
            }
            
            self.logger.info(f"Successfully processed message from user {context.user_id}")
            return context
            
        except Exception as e:
            self.logger.error(f"Error processing LINE message: {e}")
            context.error = str(e)
            context.workflow_state = "failed"
            return context
    
    async def _save_line_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save LINE message to database"""
        try:
            args = {
                "message_id": message_data.get("message_id"),
                "user_id": message_data.get("user_id"),
                "message_type": message_data.get("message_type", "text"),
                "content": message_data.get("content"),
                "file_path": message_data.get("file_path")
            }
            
            return await self.line_server.call_tool("save_message", args)
            
        except Exception as e:
            self.logger.error(f"Failed to save LINE message: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_content(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate content using Gemini"""
        try:
            message_type = message_data.get("message_type", "text")
            
            if message_type == "text":
                args = {
                    "text": message_data.get("content", ""),
                    "style": "blog"
                }
                return await self.gemini_server.call_tool("generate_content", args)
                
            elif message_type == "image":
                args = {
                    "image_path": message_data.get("file_path", ""),
                    "analysis_type": "blog_article"
                }
                return await self.gemini_server.call_tool("analyze_image", args)
                
            else:
                # For other types, use simple text generation
                args = {
                    "text": f"New {message_type} content received",
                    "style": "blog"
                }
                return await self.gemini_server.call_tool("generate_content", args)
                
        except Exception as e:
            self.logger.error(f"Failed to generate content: {e}")
            return {"success": False, "error": str(e)}
    
    async def _publish_article(self, content_result: Dict[str, Any]) -> Dict[str, Any]:
        """Publish article to Hatena"""
        try:
            generated_content = content_result.get("generated_content") or content_result.get("analysis_result")
            
            if not generated_content:
                return {"success": False, "error": "No content to publish"}
            
            # Parse content to extract title and body
            title, content = self._parse_generated_content(generated_content)
            
            args = {
                "title": title,
                "content": content
            }
            
            return await self.hatena_server.call_tool("post_simple_article", args)
            
        except Exception as e:
            self.logger.error(f"Failed to publish article: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_notification(self, user_id: str, publish_result: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification to LINE user"""
        try:
            if publish_result.get("success"):
                url = publish_result.get("url", "")
                title = publish_result.get("title", "")
                message = f"記事を投稿しました！\\n\\nタイトル: {title}\\nURL: {url}"
            else:
                message = "記事の投稿に失敗しました。しばらくしてからお試しください。"
            
            args = {
                "user_id": user_id,
                "message": message
            }
            
            return await self.line_server.call_tool("send_message", args)
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_generated_content(self, content: str) -> tuple[str, str]:
        """Parse generated content to extract title and body"""
        lines = content.strip().split("\\n")
        
        title = "AI生成記事"
        body = content
        
        # Look for title pattern
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("タイトル:") or line.startswith("Title:"):
                title = line.replace("タイトル:", "").replace("Title:", "").strip()
                # Rest is body
                body = "\\n".join(lines[i+1:]).strip()
                break
            elif line.startswith("# "):
                title = line.replace("# ", "").strip()
                body = "\\n".join(lines[i+1:]).strip()
                break
        
        # Ensure we have content
        if not title:
            title = "AI生成記事"
        if not body:
            body = content
        
        return title, body
    
    # Tool discovery methods
    async def get_available_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all available tools from all servers"""
        tools = {}
        
        if self.servers_initialized:
            if self.line_server:
                tools["line"] = self.line_server.get_available_tools()
            if self.gemini_server:
                tools["gemini"] = self.gemini_server.get_available_tools()
            if self.hatena_server:
                tools["hatena"] = self.hatena_server.get_available_tools()
        
        return tools
    
    async def call_tool_by_server(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool on a specific server"""
        server_map = {
            "line": self.line_server,
            "gemini": self.gemini_server,
            "hatena": self.hatena_server
        }
        
        server = server_map.get(server_name)
        if not server:
            raise MCPError(f"Unknown server: {server_name}")
        
        return await server.call_tool(tool_name, args)

# Standalone agent runner
async def run_simple_agent():
    """Run Simple Agent Core as standalone"""
    agent = SimpleAgentCore()
    
    try:
        await agent.initialize()
        logger.info("Simple Agent Core started and ready for requests")
        
        # Keep agent running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down Simple Agent Core")
    except Exception as e:
        logger.error(f"Simple Agent Core error: {e}")
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run agent
    asyncio.run(run_simple_agent())
