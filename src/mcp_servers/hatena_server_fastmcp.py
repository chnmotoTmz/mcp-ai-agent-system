"""
Hatena MCP Server - FastMCP Implementation
FastMCPを使用したはてなブログサービスのMCP実装
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
from src.services.hatena_service import HatenaService

logger = logging.getLogger(__name__)

# Server Context Data
@dataclass
class ServerContext:
    hatena_service: HatenaService

# Create FastMCP server
hatena_mcp = FastMCP("Hatena Service")

@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Manage application lifecycle"""
    logger.info("Initializing Hatena MCP Server...")
    
    # Initialize Hatena service
    hatena_service = HatenaService()
    
    try:
        yield ServerContext(hatena_service=hatena_service)
    finally:
        logger.info("Hatena MCP Server cleanup completed")

# Set lifespan
hatena_mcp = FastMCP("Hatena Service", lifespan=app_lifespan)

# MCP Tools
@hatena_mcp.tool()
async def publish_article(
    title: str,
    content: str,
    tags: list = None,
    category: str = "",
    draft: bool = False
) -> dict:
    """はてなブログに記事を投稿
    
    Args:
        title: 記事タイトル
        content: 記事内容
        tags: タグリスト
        category: カテゴリ
        draft: 下書きフラグ
    
    Returns:
        dict: 投稿結果
    """
    try:
        ctx = hatena_mcp.get_context()
        
        # Publish article to Hatena Blog
        result = ctx.hatena_service.publish_article(
            title=title,
            content=content,
            tags=tags or [],
            category=category,
            draft=draft
        )
        
        return {
            "success": True,
            "article_id": result.get("id"),
            "url": result.get("url"),
            "title": title,
            "tags": tags or [],
            "category": category,
            "draft": draft,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to publish article: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@hatena_mcp.tool()
async def update_article(
    entry_id: str,
    title: str = None,
    content: str = None,
    tags: list = None,
    category: str = None
) -> dict:
    """既存記事を更新
    
    Args:
        entry_id: 記事ID
        title: 新しいタイトル（オプション）
        content: 新しい内容（オプション）
        tags: 新しいタグリスト（オプション）
        category: 新しいカテゴリ（オプション）
    
    Returns:
        dict: 更新結果
    """
    try:
        ctx = hatena_mcp.get_context()
        
        # Update existing article
        result = ctx.hatena_service.update_article(
            entry_id=entry_id,
            title=title,
            content=content,
            tags=tags,
            category=category
        )
        
        return {
            "success": True,
            "article_id": entry_id,
            "updated_fields": {
                "title": title is not None,
                "content": content is not None,
                "tags": tags is not None,
                "category": category is not None
            },
            "url": result.get("url"),
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to update article: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@hatena_mcp.tool()
async def get_article(entry_id: str) -> dict:
    """記事を取得
    
    Args:
        entry_id: 記事ID
    
    Returns:
        dict: 記事情報
    """
    try:
        ctx = hatena_mcp.get_context()
        
        # Get article details
        article = ctx.hatena_service.get_article(entry_id)
        
        return {
            "success": True,
            "article": article,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to get article: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@hatena_mcp.tool()
async def delete_article(entry_id: str) -> dict:
    """記事を削除
    
    Args:
        entry_id: 記事ID
    
    Returns:
        dict: 削除結果
    """
    try:
        ctx = hatena_mcp.get_context()
        
        # Delete article
        result = ctx.hatena_service.delete_article(entry_id)
        
        return {
            "success": True,
            "deleted_article_id": entry_id,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to delete article: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@hatena_mcp.tool()
async def list_articles(limit: int = 10, page: int = 1) -> dict:
    """記事一覧を取得
    
    Args:
        limit: 取得件数
        page: ページ番号
    
    Returns:
        dict: 記事一覧
    """
    try:
        ctx = hatena_mcp.get_context()
        
        # Get articles list
        articles = ctx.hatena_service.list_articles(limit=limit, page=page)
        
        return {
            "success": True,
            "articles": articles,
            "count": len(articles),
            "limit": limit,
            "page": page,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to list articles: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@hatena_mcp.tool()
async def get_blog_info() -> dict:
    """ブログ情報を取得
    
    Returns:
        dict: ブログ情報
    """
    try:
        ctx = hatena_mcp.get_context()
        
        # Get blog information
        blog_info = ctx.hatena_service.get_blog_info()
        
        return {
            "success": True,
            "blog_info": blog_info,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Failed to get blog info: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

# MCP Resources
@hatena_mcp.resource("hatena://articles")
async def get_published_articles() -> str:
    """投稿済み記事一覧を取得
    
    Returns:
        str: 記事一覧（テキスト形式）
    """
    try:
        ctx = hatena_mcp.get_context()
        articles = ctx.hatena_service.list_articles(limit=20)
        
        article_lines = [
            "=== Published Articles ===",
            f"Total: {len(articles)} articles",
            ""
        ]
        
        for article in articles:
            article_line = f"[{article.get('published', 'Unknown')}] {article.get('title', 'No Title')}"
            article_lines.append(article_line)
            article_lines.append(f"  ID: {article.get('id', 'Unknown')}")
            article_lines.append(f"  URL: {article.get('url', 'Unknown')}")
            article_lines.append("")
        
        return "\\n".join(article_lines)
        
    except Exception as e:
        logger.error(f"Failed to get articles resource: {e}")
        return f"Error getting articles: {str(e)}"

@hatena_mcp.resource("hatena://blog/stats")
async def get_blog_stats() -> str:
    """ブログ統計情報を取得
    
    Returns:
        str: ブログ統計（テキスト形式）
    """
    try:
        ctx = hatena_mcp.get_context()
        blog_info = ctx.hatena_service.get_blog_info()
        articles = ctx.hatena_service.list_articles(limit=100)  # Get more for stats
        
        # Calculate basic stats
        total_articles = len(articles)
        published_articles = len([a for a in articles if not a.get('draft', False)])
        draft_articles = total_articles - published_articles
        
        stats_lines = [
            "=== Blog Statistics ===",
            f"Blog Title: {blog_info.get('title', 'Unknown')}",
            f"Blog URL: {blog_info.get('url', 'Unknown')}",
            "",
            "Article Stats:",
            f"  Total Articles: {total_articles}",
            f"  Published: {published_articles}",
            f"  Drafts: {draft_articles}",
            "",
            "Recent Activity:",
            f"  Last Updated: {_get_timestamp()}"
        ]
        
        return "\\n".join(stats_lines)
        
    except Exception as e:
        logger.error(f"Failed to get blog stats: {e}")
        return f"Error getting blog stats: {str(e)}"

# MCP Prompts
@hatena_mcp.prompt("article-publishing")
async def article_publishing_prompt() -> str:
    """記事投稿用のプロンプトテンプレート"""
    return '''はてなブログに記事を投稿する際の最適化ガイドライン：

1. **SEO最適化**:
   - タイトルは32文字以内でキーワードを含める
   - メタディスクリプション相当の導入文を100-150文字で作成

2. **読みやすさ**:
   - 見出し（##, ###）を適切に使用
   - 段落を3-5行で区切る
   - 箇条書きや番号リストを活用

3. **はてなブログ特有の機能**:
   - カテゴリーは1つに絞る
   - タグは3-5個程度に制限
   - 画像の alt テキストを設定

4. **エンゲージメント向上**:
   - 冒頭で記事の価値を明示
   - 最後に行動を促すCTAを配置
   - 関連記事への内部リンクを含める

記事タイトル: {title}
想定読者: {target_audience}
キーワード: {keywords}'''

# Utility functions
def _get_timestamp() -> str:
    """Get current timestamp"""
    from datetime import datetime
    return datetime.utcnow().isoformat()

# Health check
@hatena_mcp.tool()
async def health_check() -> dict:
    """MCPサーバーのヘルスチェック"""
    return {
        "status": "healthy",
        "service": "Hatena MCP Server",
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
    
    logger.info("Starting Hatena MCP Server...")
    hatena_mcp.run(transport="stdio")
