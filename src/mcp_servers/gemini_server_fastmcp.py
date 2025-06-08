"""
Gemini MCP Server - FastMCP Implementation
FastMCPを使用したGeminiサービスのMCP実装
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
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# Server Context Data
@dataclass
class ServerContext:
    gemini_service: GeminiService

# Create FastMCP server
gemini_mcp = FastMCP("Gemini Service")

@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Manage application lifecycle"""
    logger.info("Initializing Gemini MCP Server...")
    
    # Initialize Gemini service
    gemini_service = GeminiService()
    
    try:
        yield ServerContext(gemini_service=gemini_service)
    finally:
        logger.info("Gemini MCP Server cleanup completed")

# Set lifespan
gemini_mcp = FastMCP("Gemini Service", lifespan=app_lifespan)

# MCP Tools
@gemini_mcp.tool()
async def generate_article(content: str, style: str = "blog") -> dict:
    """コンテンツから記事を生成
    
    Args:
        content: 元となるコンテンツ
        style: 記事のスタイル（blog, news, casual等）
    
    Returns:
        dict: 生成された記事
    """
    try:
        ctx = gemini_mcp.get_context()
        
        # Generate article using Gemini
        article = ctx.gemini_service.generate_article_from_content(content, style)
        
        return {
            "success": True,
            "article": article,
            "style": style,
            "original_content_length": len(content),
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to generate article: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@gemini_mcp.tool()
async def analyze_image(image_path: str, prompt: str = "この画像について詳しく説明してください") -> dict:
    """画像を分析して説明を生成
    
    Args:
        image_path: 分析対象の画像パス
        prompt: 分析用のプロンプト
    
    Returns:
        dict: 画像分析結果
    """
    try:
        ctx = gemini_mcp.get_context()
        
        # Analyze image using Gemini Vision
        analysis = ctx.gemini_service.analyze_image(image_path, prompt)
        
        return {
            "success": True,
            "analysis": analysis,
            "image_path": image_path,
            "prompt_used": prompt,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to analyze image: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@gemini_mcp.tool()
async def chat_with_gemini(message: str, context: str = "") -> dict:
    """Geminiとチャット形式で対話
    
    Args:
        message: ユーザーメッセージ
        context: 追加のコンテキスト情報
    
    Returns:
        dict: Geminiの応答
    """
    try:
        ctx = gemini_mcp.get_context()
        
        # Chat with Gemini
        response = ctx.gemini_service.chat(message, context)
        
        return {
            "success": True,
            "response": response,
            "original_message": message,
            "context_provided": bool(context),
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to chat with Gemini: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@gemini_mcp.tool()
async def create_blog_post(
    content: str,
    title_hint: str = "",
    tags: list = None
) -> dict:
    """ブログ記事を作成
    
    Args:
        content: 記事の元となるコンテンツ
        title_hint: タイトルのヒント
        tags: 記事のタグリスト
    
    Returns:
        dict: 作成されたブログ記事
    """
    try:
        ctx = gemini_mcp.get_context()
        
        # Create comprehensive blog post
        blog_post = ctx.gemini_service.create_blog_post(
            content=content,
            title_hint=title_hint,
            tags=tags or []
        )
        
        return {
            "success": True,
            "blog_post": blog_post,
            "title_hint": title_hint,
            "tags": tags or [],
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to create blog post: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

# MCP Resources
@gemini_mcp.resource("gemini://models/info")
async def get_model_info() -> str:
    """Geminiモデルの情報を提供
    
    Returns:
        str: モデル情報
    """
    try:
        ctx = gemini_mcp.get_context()
        model_info = ctx.gemini_service.get_model_info()
        
        info_lines = [
            "=== Gemini Model Information ===",
            f"Model: {model_info.get('model_name', 'Unknown')}",
            f"Version: {model_info.get('version', 'Unknown')}",
            f"Max Tokens: {model_info.get('max_tokens', 'Unknown')}",
            f"Capabilities: {', '.join(model_info.get('capabilities', []))}"
        ]
        
        return "\\n".join(info_lines)
        
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        return f"Error getting model info: {str(e)}"

# MCP Prompts
@gemini_mcp.prompt("article-generation")
async def article_generation_prompt() -> str:
    """記事生成用のプロンプトテンプレート"""
    return '''あなたは優秀なブログライターです。以下の要件で記事を作成してください：

1. **魅力的なタイトル**: SEOを意識した検索されやすいタイトル
2. **構造化された内容**: 見出し、段落を適切に使用
3. **読みやすさ**: 親しみやすい文体で、専門用語には説明を追加
4. **価値提供**: 読者にとって実用的で興味深い情報を含める
5. **結論**: まとめと次のアクションを明確に示す

元となるコンテンツ: {content}
記事スタイル: {style}
ターゲット読者: {target_audience}'''

@gemini_mcp.prompt("image-analysis")
async def image_analysis_prompt() -> str:
    """画像分析用のプロンプトテンプレート"""
    return '''画像を詳細に分析し、以下の観点から説明してください：

1. **主要な要素**: 画像の中心となる被写体や物体
2. **構図と配色**: レイアウトや色彩の特徴
3. **雰囲気・印象**: 画像が与える感情や印象
4. **技術的側面**: 撮影技法や画質について（該当する場合）
5. **活用提案**: この画像をブログ記事等でどう活用できるか

分析対象: {image_description}
目的: {analysis_purpose}'''

# Utility functions
def _get_timestamp() -> str:
    """Get current timestamp"""
    from datetime import datetime
    return datetime.utcnow().isoformat()

# Health check
@gemini_mcp.tool()
async def health_check() -> dict:
    """MCPサーバーのヘルスチェック"""
    return {
        "status": "healthy",
        "service": "Gemini MCP Server",
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
    
    logger.info("Starting Gemini MCP Server...")
    gemini_mcp.run(transport="stdio")
