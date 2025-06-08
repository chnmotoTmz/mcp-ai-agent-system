"""
AI Agent Core - LangGraph Implementation
LangGraphを使用したメインのAIエージェント
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, TypedDict
from dataclasses import dataclass

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

# Agent State Definition
class AgentState(TypedDict):
    messages: List[Dict[str, Any]]
    user_id: str
    task_type: str
    content: Dict[str, Any]
    workflow_status: str
    line_message_id: str
    processing_results: Dict[str, Any]

@dataclass
class AgentConfig:
    """Agent Configuration"""
    model_name: str = "claude-3-5-sonnet-20241022"
    max_retries: int = 3
    timeout: int = 30

class ContentCreationAgent:
    """Main Content Creation Agent using LangGraph"""
    
    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()
        self.mcp_client = None
        self.tools = []
        self.agent = None
        self.workflow = None
        
    async def initialize(self):
        """Initialize the agent with MCP servers"""
        logger.info("Initializing Content Creation Agent...")
        
        # Setup MCP Client with our servers (using fixed versions)
        self.mcp_client = MultiServerMCPClient({
            "line": {
                "command": "python3",
                "args": ["/home/moto/line-gemini-hatena-integration/src/mcp_servers/line_server_fastmcp_fixed.py"],
                "transport": "stdio"
            },
            "gemini": {
                "command": "python3", 
                "args": ["/home/moto/line-gemini-hatena-integration/src/mcp_servers/gemini_server_fastmcp_fixed.py"],
                "transport": "stdio"
            },
            "hatena": {
                "command": "python3",
                "args": ["/home/moto/line-gemini-hatena-integration/src/mcp_servers/hatena_server_fastmcp_fixed.py"], 
                "transport": "stdio"
            }
        })
        
        # Get tools from MCP servers
        self.tools = await self.mcp_client.get_tools()
        logger.info(f"Loaded {len(self.tools)} MCP tools")
        
        # Create the agent workflow
        self._create_workflow()
        
        logger.info("Content Creation Agent initialized successfully")
    
    def _create_workflow(self):
        """Create the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("message_analysis", self._analyze_message_node)
        workflow.add_node("task_routing", self._task_routing_node)
        workflow.add_node("content_generation", self._content_generation_node)
        workflow.add_node("publication", self._publication_node)
        workflow.add_node("notification", self._notification_node)
        
        # Add edges
        workflow.add_edge("message_analysis", "task_routing")
        workflow.add_conditional_edges(
            "task_routing",
            self._determine_task_type,
            {
                "blog_article": "content_generation",
                "image_analysis": "content_generation",
                "simple_response": "notification",
                "error": "notification"
            }
        )
        workflow.add_edge("content_generation", "publication")
        workflow.add_edge("publication", "notification")
        
        # Set entry point
        workflow.set_entry_point("message_analysis")
        workflow.add_edge("notification", END)
        
        self.workflow = workflow.compile()
    
    async def _analyze_message_node(self, state: AgentState) -> AgentState:
        """Analyze incoming message"""
        logger.info("Analyzing message...")
        
        try:
            # Get message content
            messages = state["messages"]
            if not messages:
                raise ValueError("No messages to analyze")
            
            latest_message = messages[-1]
            content = latest_message.get("content", "")
            message_type = latest_message.get("type", "text")
            
            # Store analysis results
            state["content"] = {
                "text": content,
                "type": message_type,
                "analysis": "Message received and ready for processing"
            }
            state["workflow_status"] = "analyzed"
            
            logger.info(f"Message analyzed: type={message_type}, length={len(content)}")
            return state
            
        except Exception as e:
            logger.error(f"Message analysis failed: {e}")
            state["workflow_status"] = "error"
            state["processing_results"] = {"error": str(e)}
            return state
    
    async def _task_routing_node(self, state: AgentState) -> AgentState:
        """Route task based on content analysis"""
        logger.info("Routing task...")
        
        try:
            content = state["content"]
            message_type = content.get("type", "text")
            text_content = content.get("text", "")
            
            # Determine task type based on content
            if message_type == "image":
                task_type = "image_analysis"
            elif len(text_content) > 50:  # Substantial content for blog
                task_type = "blog_article"
            else:
                task_type = "simple_response"
            
            state["task_type"] = task_type
            state["workflow_status"] = "routed"
            
            logger.info(f"Task routed to: {task_type}")
            return state
            
        except Exception as e:
            logger.error(f"Task routing failed: {e}")
            state["task_type"] = "error"
            state["workflow_status"] = "error"
            state["processing_results"] = {"error": str(e)}
            return state
    
    def _determine_task_type(self, state: AgentState) -> str:
        """Determine next node based on task type"""
        return state["task_type"]
    
    async def _content_generation_node(self, state: AgentState) -> AgentState:
        """Generate content using Gemini"""
        logger.info("Generating content...")
        
        try:
            task_type = state["task_type"]
            content = state["content"]
            
            if task_type == "image_analysis":
                # Analyze image and generate article
                result = await self._analyze_image_and_generate(content)
            elif task_type == "blog_article":
                # Generate blog article from text
                result = await self._generate_blog_article(content)
            else:
                result = {"error": "Unknown task type"}
            
            state["processing_results"] = result
            state["workflow_status"] = "content_generated"
            
            logger.info("Content generation completed")
            return state
            
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            state["workflow_status"] = "error"
            state["processing_results"] = {"error": str(e)}
            return state
    
    async def _analyze_image_and_generate(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze image and generate blog article"""
        try:
            # Find analyze_image tool
            analyze_tool = None
            generate_tool = None
            
            for tool in self.tools:
                if tool.name == "analyze_image":
                    analyze_tool = tool
                elif tool.name == "create_blog_post":
                    generate_tool = tool
            
            if not analyze_tool or not generate_tool:
                raise ValueError("Required tools not found")
            
            # Analyze image
            image_path = content.get("file_path", "")
            if not image_path:
                raise ValueError("No image path provided")
            
            analysis_result = await analyze_tool.ainvoke({
                "image_path": image_path,
                "prompt": "この画像について詳しく分析し、ブログ記事の素材として活用できる要素を抽出してください"
            })
            
            if not analysis_result.get("success"):
                raise ValueError(f"Image analysis failed: {analysis_result.get('error')}")
            
            # Generate blog post from analysis
            analysis_text = analysis_result["analysis"]
            blog_result = await generate_tool.ainvoke({
                "content": analysis_text,
                "title_hint": "画像分析に基づく記事",
                "tags": ["AI", "画像解析", "ブログ"]
            })
            
            if not blog_result.get("success"):
                raise ValueError(f"Blog generation failed: {blog_result.get('error')}")
            
            return {
                "type": "image_analysis_article",
                "image_analysis": analysis_result["analysis"],
                "blog_post": blog_result["blog_post"],
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Image analysis and generation failed: {e}")
            return {"error": str(e), "success": False}
    
    async def _generate_blog_article(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate blog article from text content"""
        try:
            # Find blog generation tool
            generate_tool = None
            for tool in self.tools:
                if tool.name == "create_blog_post":
                    generate_tool = tool
                    break
            
            if not generate_tool:
                raise ValueError("Blog generation tool not found")
            
            # Generate blog post
            text_content = content.get("text", "")
            logger.info(f"Generating blog from text: {text_content[:100]}...")
            
            blog_result = await generate_tool.ainvoke({
                "content": text_content,
                "title_hint": "",
                "tags": ["ブログ", "AI生成"]
            })
            
            logger.info(f"Blog generation result type: {type(blog_result)}, content: {blog_result}")
            
            # Handle different response types
            if isinstance(blog_result, str):
                # If result is a string, wrap it in a dictionary
                return {
                    "type": "text_blog_article",
                    "blog_post": {
                        "title": "AI生成記事",
                        "content": blog_result,
                        "tags": ["ブログ", "AI生成"]
                    },
                    "success": True
                }
            elif isinstance(blog_result, dict):
                # If result is a dictionary, check its structure
                if not blog_result.get("success", True):
                    raise ValueError(f"Blog generation failed: {blog_result.get('error', 'Unknown error')}")
                
                return {
                    "type": "text_blog_article", 
                    "blog_post": blog_result.get("blog_post", blog_result),
                    "success": True
                }
            else:
                raise ValueError(f"Unexpected blog_result type: {type(blog_result)}")
            
        except Exception as e:
            logger.error(f"Blog article generation failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "success": False}
    
    async def _publication_node(self, state: AgentState) -> AgentState:
        """Publish content to Hatena Blog and save to database"""
        logger.info("Publishing content...")
        
        try:
            processing_results = state["processing_results"]
            
            if not processing_results.get("success"):
                # Skip publication if content generation failed
                logger.info("Skipping publication due to content generation failure")
                state["workflow_status"] = "publication_skipped"
                return state
            
            # Find publication tool
            publish_tool = None
            for tool in self.tools:
                if tool.name == "publish_article":
                    publish_tool = tool
                    break
            
            if not publish_tool:
                logger.warning("Publication tool not found - skipping publication")
                state["workflow_status"] = "publication_skipped"
                state["processing_results"]["publication_error"] = "Publication tool not available"
                return state
            
            # Extract blog post data - fix nested data structure
            blog_post = processing_results.get("blog_post", {})
            
            # Handle case where blog_post might be a JSON string
            if isinstance(blog_post, str):
                try:
                    import json
                    blog_post = json.loads(blog_post)
                    logger.info("Parsed blog_post from JSON string")
                except json.JSONDecodeError:
                    logger.warning("blog_post is string but not valid JSON, treating as content")
                    blog_post = {"title": "AI生成記事", "content": blog_post, "tags": []}
            
            if not blog_post:
                logger.warning("No blog post data to publish")
                state["workflow_status"] = "publication_skipped"
                state["processing_results"]["publication_error"] = "No blog post data available"
                return state
            
            logger.info(f"Publishing blog post: {blog_post.get('title', 'Unknown')}")
            
            # Extract actual content from nested structure
            title = blog_post.get("title", "AI Generated Article")
            content = blog_post.get("content", "")
            tags = blog_post.get("tags", [])
            category = blog_post.get("category", "")
            
            # Validate content is string
            if not isinstance(content, str):
                logger.warning(f"Content is not string type: {type(content)}")
                content = str(content) if content else "Generated content"
            
            if not isinstance(title, str):
                logger.warning(f"Title is not string type: {type(title)}")
                title = str(title) if title else "AI Generated Article"
            
            # Ensure tags is a list
            if not isinstance(tags, list):
                tags = [str(tags)] if tags else []
            
            logger.info(f"Publishing with title: {title}, content length: {len(content)}, tags: {tags}")
            
            # First save to database
            from flask import current_app
            from main import create_app
            from src.database import Article, db
            
            # Get Flask app context
            try:
                app = current_app._get_current_object()
            except RuntimeError:
                app = create_app()
            
            with app.app_context():
                # Create article record
                article = Article(
                    title=title,
                    content=content,
                    summary=blog_post.get("summary", ""),
                    status='draft',  # フェイズ2: 初期状態はdraft
                    enhancement_level=0
                )
                article.set_tags_list(tags)
                
                # Link to source message
                line_message_id = state.get("line_message_id")
                if line_message_id:
                    article.set_source_messages_list([line_message_id])
                
                db.session.add(article)
                db.session.commit()
                
                article_id = article.id
                logger.info(f"Article saved to database with ID: {article_id}")
            
            # Publish to Hatena - ensure all parameters are correct types
            publish_result = await publish_tool.ainvoke({
                "title": str(title),
                "content": str(content),  # Ensure content is string, not dict
                "tags": tags if isinstance(tags, list) else [str(tags)] if tags else [],
                "category": str(category) if category else "",
                "draft": False  # Publish immediately
            })
            
            logger.info(f"Publish result type: {type(publish_result)}, content: {publish_result}")
            
            # Handle different response types from publication
            if isinstance(publish_result, dict):
                with app.app_context():
                    # Update article with Hatena info
                    article = Article.query.get(article_id)
                    if article and publish_result.get("success", False):
                        article.published = True
                        article.hatena_entry_id = publish_result.get("id", "")
                        article.hatena_url = publish_result.get("url", "")
                        article.published_at = datetime.utcnow()
                        db.session.commit()
                        logger.info(f"Article {article_id} updated with Hatena info")
                
                state["processing_results"]["publication"] = publish_result
                state["processing_results"]["article_id"] = article_id  # フェイズ2用
                
                if publish_result.get("success", False):
                    state["workflow_status"] = "published"
                else:
                    state["workflow_status"] = "publication_error"
                    state["processing_results"]["publication_error"] = publish_result.get("error", "Unknown publication error")
            else:
                # If result is not a dict, treat as error
                logger.warning(f"Unexpected publish result type: {type(publish_result)}")
                state["workflow_status"] = "publication_error"
                state["processing_results"]["publication_error"] = f"Unexpected response: {publish_result}"
            
            logger.info(f"Publication completed with status: {state['workflow_status']}")
            return state
            
        except Exception as e:
            logger.error(f"Publication failed: {e}")
            import traceback
            traceback.print_exc()
            state["workflow_status"] = "publication_error"
            state["processing_results"]["publication_error"] = str(e)
            return state
    
    async def _notification_node(self, state: AgentState) -> AgentState:
        """Send notification back to LINE"""
        logger.info("Sending notification...")
        
        try:
            # Find LINE send message tool
            send_tool = None
            for tool in self.tools:
                if tool.name == "send_message":
                    send_tool = tool
                    break
            
            if not send_tool:
                raise ValueError("LINE send tool not found")
            
            # Create notification message
            user_id = state["user_id"]
            workflow_status = state["workflow_status"]
            processing_results = state["processing_results"]
            
            if workflow_status == "published":
                publication = processing_results.get("publication", {})
                if publication.get("success"):
                    message = f"✅ 記事を投稿しました！\\n\\nタイトル: {publication.get('title', 'Unknown')}\\nURL: {publication.get('url', 'N/A')}"
                else:
                    message = "❌ 記事の投稿に失敗しました。"
            elif workflow_status == "error":
                error = processing_results.get("error", "Unknown error")
                message = f"❌ 処理中にエラーが発生しました: {error}"
            else:
                message = "✅ 処理が完了しました。"
            
            # Send notification
            await send_tool.ainvoke({
                "user_id": user_id,
                "message": message
            })
            
            state["workflow_status"] = "completed"
            logger.info("Notification sent successfully")
            return state
            
        except Exception as e:
            logger.error(f"Notification failed: {e}")
            state["workflow_status"] = "notification_error"
            return state
    
    async def process_message(self, user_id: str, line_message_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process incoming message through the workflow"""
        logger.info(f"Processing message for user {user_id}")
        
        # ワークフローが初期化されていない場合はエラー
        if self.workflow is None:
            logger.error("Workflow not initialized")
            return {
                "success": False,
                "error": "AI Agent workflow not initialized. Please check MCP server connections."
            }
        
        # Initialize state
        initial_state = AgentState(
            messages=messages,
            user_id=user_id,
            task_type="",
            content={},
            workflow_status="initialized",
            line_message_id=line_message_id,
            processing_results={}
        )
        
        try:
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            logger.info(f"Workflow completed with status: {final_state['workflow_status']}")
            return {
                "success": True,
                "status": final_state["workflow_status"],
                "results": final_state["processing_results"]
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.mcp_client:
            await self.mcp_client.close()
        logger.info("Agent cleanup completed")

# Main execution for testing
if __name__ == "__main__":
    import sys
    import os
    
    # Add src to path for imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    async def test_agent():
        agent = ContentCreationAgent()
        
        try:
            await agent.initialize()
            
            # Test message processing
            test_messages = [{
                "content": "AI技術の最新動向について教えてください",
                "type": "text"
            }]
            
            result = await agent.process_message(
                user_id="test_user",
                line_message_id="test_msg_001",
                messages=test_messages
            )
            
            print(f"Processing result: {result}")
            
        finally:
            await agent.cleanup()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test
    asyncio.run(test_agent())
