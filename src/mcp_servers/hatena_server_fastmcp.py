"""
Hatena MCP Server - FastMCP Implementation (Enhanced)
FastMCPを使用したはてなブログサービスのMCP実装（高機能版）
"""

import asyncio
import hashlib
import json
import logging
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager
from dataclasses import dataclass

import requests
from lxml import etree

# パスを追加
sys.path.append('/home/moto/line-gemini-hatena-integration')

# Setup logger first
logger = logging.getLogger(__name__)

try:
    from fastmcp import FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        # Fallback for FastMCP not available
        logger.warning("FastMCP not available, using mock implementation")
        class FastMCP:
            def __init__(self, name, lifespan=None):
                self.name = name
                self.lifespan = lifespan
                self.tools = {}
                self.resources = {}
                self.prompts = {}
                self.context = None
            
            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator
            
            def resource(self, uri):
                def decorator(func):
                    self.resources[uri] = func
                    return func
                return decorator
            
            def prompt(self, name):
                def decorator(func):
                    self.prompts[name] = func
                    return func
                return decorator
            
            def get_context(self):
                return self.context
            
            def run(self, transport="stdio"):
                logger.info(f"Mock FastMCP server {self.name} would run with {transport}")
            
from src.services.hatena_service import HatenaService
from src.config import Config

# Cache settings
CACHE_DIR = Path.home() / ".cache" / "hatena-blog-mcp"
CACHE_EXPIRY_HOURS = 24 * 365  # Cache expiration (1 year)

# Server Context Data
@dataclass
class ServerContext:
    hatena_service: HatenaService
    hatena_id: str = None
    hatena_blog_id: str = None
    hatena_api_key: str = None

@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Manage application lifecycle with enhanced cache setup"""
    logger.info("Initializing Enhanced Hatena MCP Server...")
    
    # Initialize Hatena service
    hatena_service = HatenaService()
    
    # Setup cache directory
    CACHE_DIR.mkdir(exist_ok=True)
    
    # Get credentials from config
    hatena_id = getattr(Config, 'HATENA_ID', None)
    hatena_blog_id = getattr(Config, 'HATENA_BLOG_ID', None)
    hatena_api_key = getattr(Config, 'HATENA_API_KEY', None)
    
    context = ServerContext(
        hatena_service=hatena_service,
        hatena_id=hatena_id,
        hatena_blog_id=hatena_blog_id,
        hatena_api_key=hatena_api_key
    )
    
    try:
        # Set context for mock implementation
        if hasattr(server, 'context'):
            server.context = context
        yield context
    finally:
        logger.info("Enhanced Hatena MCP Server cleanup completed")

# Create FastMCP server
hatena_mcp = FastMCP("Enhanced Hatena Service", lifespan=app_lifespan)

# Enhanced Cache Management Functions
def get_cache_path(key: str) -> Path:
    """Generate cache file path"""
    hashed = hashlib.md5(key.encode()).hexdigest()
    return CACHE_DIR / f"{hashed}.json"

def load_cache(key: str) -> Optional[Dict[str, Any]]:
    """Load data from cache"""
    cache_path = get_cache_path(key)
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        # Check cache expiry
        cached_at = datetime.fromisoformat(cache_data["cached_at"])
        if datetime.now() - cached_at > timedelta(hours=CACHE_EXPIRY_HOURS):
            cache_path.unlink()  # Remove expired cache
            return None
        
        return cache_data["data"]
    except (json.JSONDecodeError, KeyError, ValueError):
        cache_path.unlink()  # Remove corrupted cache
        return None

def save_cache(key: str, data: Dict[str, Any]):
    """Save data to cache"""
    cache_path = get_cache_path(key)
    cache_data = {
        "cached_at": datetime.now().isoformat(),
        "data": data
    }
    
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

def get_auth(ctx):
    """Get authentication tuple"""
    return (ctx.hatena_id, ctx.hatena_api_key)

def get_collection_uri(ctx):
    """Generate collection URI"""
    return f"https://blog.hatena.ne.jp/{ctx.hatena_id}/{ctx.hatena_blog_id}/atom/entry"

def get_entry_uri(ctx, entry_id: str):
    """Generate entry URI"""
    return f"https://blog.hatena.ne.jp/{ctx.hatena_id}/{ctx.hatena_blog_id}/atom/entry/{entry_id}"

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
async def search_entries(keyword: str, max_results: int = 10) -> dict:
    """キーワードで記事を検索
    
    Args:
        keyword: 検索キーワード
        max_results: 最大取得数
    
    Returns:
        dict: 検索結果
    """
    try:
        if not keyword:
            return {
                "success": False,
                "error": "keyword is required",
                "timestamp": _get_timestamp()
            }
        
        if not CACHE_DIR.exists():
            return {
                "success": False,
                "error": "Cache not available. Please update cache first.",
                "timestamp": _get_timestamp()
            }
        
        keyword_lower = keyword.lower()
        matched_entries = []
        
        # Search through cached entries
        for cache_file in CACHE_DIR.glob("*.json"):
            try:
                cached = load_cache(cache_file.stem)
                if not cached:
                    continue
                
                # Search in title, categories, and content
                if (keyword_lower in cached.get("title", "").lower() or
                    any(keyword_lower in cat.lower() for cat in cached.get("categories", [])) or
                    keyword_lower in cached.get("content", "").lower()):
                    matched_entries.append(cached)
                
                if len(matched_entries) >= max_results:
                    break
                    
            except Exception as e:
                logger.warning(f"Error reading cache file {cache_file}: {e}")
                continue
        
        return {
            "success": True,
            "entries": matched_entries[:max_results],
            "count": len(matched_entries[:max_results]),
            "keyword": keyword,
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Failed to search entries: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@hatena_mcp.tool()
async def list_entries_enhanced(page_url: str = None, max_results: int = 10) -> dict:
    """ブログ記事一覧を取得（拡張版）
    
    Args:
        page_url: ページネーション用URL
        max_results: 最大取得数
    
    Returns:
        dict: 記事一覧
    """
    try:
        ctx = hatena_mcp.get_context()
        
        if not all([ctx.hatena_id, ctx.hatena_blog_id, ctx.hatena_api_key]):
            return {
                "success": False,
                "error": "Hatena credentials not configured",
                "timestamp": _get_timestamp()
            }
        
        url = page_url or get_collection_uri(ctx)
        response = requests.get(url, auth=get_auth(ctx))
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API request failed: {response.status_code}",
                "timestamp": _get_timestamp()
            }
        
        # Parse XML response
        root = etree.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        
        entries = []
        for entry in root.xpath("//atom:entry", namespaces=ns)[:max_results]:
            entry_data = {
                "id": entry.find("atom:id", ns).text,
                "title": entry.find("atom:title", ns).text,
                "link": entry.find("atom:link[@rel='alternate']", ns).get("href"),
                "published": entry.find("atom:published", ns).text,
                "updated": entry.find("atom:updated", ns).text,
                "categories": [cat.get("term") for cat in entry.findall("atom:category", ns)]
            }
            entries.append(entry_data)
        
        # Get next page link
        next_link = root.find("atom:link[@rel='next']", ns)
        next_page_url = next_link.get("href") if next_link is not None else None
        
        return {
            "success": True,
            "entries": entries,
            "next_page_url": next_page_url,
            "count": len(entries),
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Failed to list entries: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@hatena_mcp.tool()
async def get_entry_detail(entry_id: str) -> dict:
    """記事詳細を取得（キャッシュ対応）
    
    Args:
        entry_id: エントリID
    
    Returns:
        dict: 記事詳細
    """
    try:
        ctx = hatena_mcp.get_context()
        
        if not entry_id:
            return {
                "success": False,
                "error": "entry_id is required",
                "timestamp": _get_timestamp()
            }
        
        # Check cache first
        cache_key = f"entry_{entry_id}"
        cached = load_cache(cache_key)
        if cached:
            return {
                "success": True,
                "entry": cached,
                "from_cache": True,
                "timestamp": _get_timestamp()
            }
        
        # Fetch from API if not cached
        if not all([ctx.hatena_id, ctx.hatena_blog_id, ctx.hatena_api_key]):
            return {
                "success": False,
                "error": "Hatena credentials not configured",
                "timestamp": _get_timestamp()
            }
        
        url = get_entry_uri(ctx, entry_id)
        response = requests.get(url, auth=get_auth(ctx))
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Entry not found: {response.status_code}",
                "timestamp": _get_timestamp()
            }
        
        # Parse entry details
        root = etree.fromstring(response.content)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "hatena": "http://www.hatena.ne.jp/info/xmlns#"
        }
        
        entry_detail = {
            "id": root.find("atom:id", ns).text,
            "title": root.find("atom:title", ns).text,
            "content": root.find("atom:content", ns).text,
            "content_type": root.find("atom:content", ns).get("type", "text"),
            "published": root.find("atom:published", ns).text,
            "updated": root.find("atom:updated", ns).text,
            "categories": [cat.get("term") for cat in root.findall("atom:category", ns)],
            "draft": root.find("hatena:draft", ns).text == "yes" 
                    if root.find("hatena:draft", ns) is not None else False
        }
        
        # Cache the result
        save_cache(cache_key, entry_detail)
        
        return {
            "success": True,
            "entry": entry_detail,
            "from_cache": False,
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Failed to get entry detail: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@hatena_mcp.tool()
async def sync_cache() -> dict:
    """全記事をキャッシュに同期
    
    Returns:
        dict: 同期結果
    """
    try:
        ctx = hatena_mcp.get_context()
        
        if not all([ctx.hatena_id, ctx.hatena_blog_id, ctx.hatena_api_key]):
            return {
                "success": False,
                "error": "Hatena credentials not configured",
                "timestamp": _get_timestamp()
            }
        
        synced_count = 0
        error_count = 0
        next_url = None
        
        # Sync all entries to cache
        while True:
            result = await list_entries_enhanced(page_url=next_url, max_results=50)
            if not result.get("success"):
                return result
            
            for entry in result["entries"]:
                # Extract entry ID from tag format
                entry_id = entry["id"].split("-")[-1]
                try:
                    detail_result = await get_entry_detail(entry_id)
                    if detail_result.get("success"):
                        synced_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    logger.error(f"Error syncing entry {entry_id}: {e}")
                    error_count += 1
            
            next_url = result.get("next_page_url")
            if not next_url:
                break
        
        return {
            "success": True,
            "synced": synced_count,
            "errors": error_count,
            "message": f"Synced {synced_count} entries to cache",
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Failed to sync cache: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

# Legacy compatibility tools
@hatena_mcp.tool()
async def list_articles(limit: int = 10, page: int = 1) -> dict:
    """記事一覧を取得（レガシー互換）"""
    return await list_entries_enhanced(max_results=limit)

@hatena_mcp.tool()
async def get_article(entry_id: str) -> dict:
    """記事を取得（レガシー互換）"""
    return await get_entry_detail(entry_id)

# Enhanced Health check
@hatena_mcp.tool()
async def health_check() -> dict:
    """MCPサーバーのヘルスチェック（拡張版）"""
    try:
        ctx = hatena_mcp.get_context()
        cache_files = len(list(CACHE_DIR.glob("*.json"))) if CACHE_DIR.exists() else 0
        
        return {
            "status": "healthy",
            "service": "Enhanced Hatena MCP Server",
            "version": "2.0.0",
            "features": {
                "cache_enabled": True,
                "search_enabled": True,
                "category_support": True,
                "cached_entries": cache_files
            },
            "credentials_configured": all([ctx.hatena_id, ctx.hatena_blog_id, ctx.hatena_api_key]) if ctx else False,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": _get_timestamp()
        }

# Utility functions
def _get_timestamp() -> str:
    """Get current timestamp"""
    return datetime.utcnow().isoformat()

# Main execution
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Enhanced Hatena MCP Server...")
    hatena_mcp.run(transport="stdio")