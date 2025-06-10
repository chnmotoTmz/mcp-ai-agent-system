"""
Imgur MCP Server - FastMCP Implementation
Imgurを使用した画像アップロード・管理サービス
"""

import asyncio
import base64
import logging
import sys
import os
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import requests

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

from src.config import Config

# Imgur API設定
IMGUR_API_URL = "https://api.imgur.com/3"
IMGUR_CLIENT_ID = getattr(Config, 'IMGUR_CLIENT_ID', 'd4eee0876721149')
IMGUR_ACCESS_TOKEN = os.getenv('IMGUR_ACCESS_TOKEN')  # OAuth アクセストークン
IMGUR_REFRESH_TOKEN = os.getenv('IMGUR_REFRESH_TOKEN')  # リフレッシュトークン

# Create FastMCP server
imgur_mcp = FastMCP("Imgur Enhanced Service")

@imgur_mcp.tool()
async def upload_image(
    image_path: str,
    title: str = "",
    description: str = "",
    privacy: str = "hidden"
) -> Dict[str, Any]:
    """
    画像をImgurにアップロード
    
    Args:
        image_path: アップロードする画像のパス
        title: 画像のタイトル
        description: 画像の説明
        privacy: プライバシー設定 ("public", "hidden", "secret")
    
    Returns:
        dict: アップロード結果
    """
    try:
        logger.info(f"Imgur アップロード開始: {image_path}")
        
        # パス検証
        if not Path(image_path).exists():
            return {
                "success": False,
                "error": f"Image file not found: {image_path}",
                "timestamp": _get_timestamp()
            }
        
        # ファイルサイズチェック（20MB制限）
        file_size = Path(image_path).stat().st_size
        if file_size > 20 * 1024 * 1024:  # 20MB
            return {
                "success": False,
                "error": "File size exceeds 20MB limit",
                "file_size_mb": round(file_size / 1024 / 1024, 2),
                "timestamp": _get_timestamp()
            }
        
        # 画像をBase64エンコード
        with open(image_path, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # 認証方法を選択（OAuth優先）
        if IMGUR_ACCESS_TOKEN:
            # OAuth認証（個人アカウント）
            headers = {
                'Authorization': f'Bearer {IMGUR_ACCESS_TOKEN}',
                'Content-Type': 'application/json'
            }
            logger.info("OAuth認証（個人アカウント）でアップロード")
        else:
            # Client-ID認証（匿名）
            headers = {
                'Authorization': f'Client-ID {IMGUR_CLIENT_ID}',
                'Content-Type': 'application/json'
            }
            logger.info("Client-ID認証（匿名）でアップロード")
        
        data = {
            'image': image_data,
            'type': 'base64',
            'title': title,
            'description': description,
            'privacy': privacy
        }
        
        response = requests.post(
            f"{IMGUR_API_URL}/upload",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                upload_data = result['data']
                logger.info(f"Imgur アップロード成功: {upload_data.get('link')}")
                
                return {
                    "success": True,
                    "url": upload_data.get('link'),
                    "imgur_url": upload_data.get('link'),
                    "imgur_id": upload_data.get('id'),
                    "delete_hash": upload_data.get('deletehash'),
                    "title": upload_data.get('title', title),
                    "description": upload_data.get('description', description),
                    "size": upload_data.get('size'),
                    "width": upload_data.get('width'),
                    "height": upload_data.get('height'),
                    "file_size_mb": round(file_size / 1024 / 1024, 2),
                    "timestamp": _get_timestamp()
                }
            else:
                return {
                    "success": False,
                    "error": result.get('data', {}).get('error', 'Upload failed'),
                    "timestamp": _get_timestamp()
                }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "timestamp": _get_timestamp()
            }
            
    except Exception as e:
        logger.error(f"Imgur アップロードエラー: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@imgur_mcp.tool()
async def delete_image(delete_hash: str) -> Dict[str, Any]:
    """
    Imgurから画像を削除
    
    Args:
        delete_hash: 削除用ハッシュ
    
    Returns:
        dict: 削除結果
    """
    try:
        if not delete_hash:
            return {
                "success": False,
                "error": "delete_hash is required",
                "timestamp": _get_timestamp()
            }
        
        logger.info(f"Imgur 画像削除開始: {delete_hash}")
        
        headers = {
            'Authorization': f'Client-ID {IMGUR_CLIENT_ID}'
        }
        
        response = requests.delete(
            f"{IMGUR_API_URL}/image/{delete_hash}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                logger.info(f"Imgur 画像削除成功: {delete_hash}")
                return {
                    "success": True,
                    "delete_hash": delete_hash,
                    "message": "Image deleted successfully",
                    "timestamp": _get_timestamp()
                }
            else:
                return {
                    "success": False,
                    "error": result.get('data', {}).get('error', 'Delete failed'),
                    "timestamp": _get_timestamp()
                }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "timestamp": _get_timestamp()
            }
            
    except Exception as e:
        logger.error(f"Imgur 削除エラー: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@imgur_mcp.tool()
async def get_image_info(image_id: str) -> Dict[str, Any]:
    """
    Imgur画像の情報を取得
    
    Args:
        image_id: 画像ID
    
    Returns:
        dict: 画像情報
    """
    try:
        if not image_id:
            return {
                "success": False,
                "error": "image_id is required",
                "timestamp": _get_timestamp()
            }
        
        logger.info(f"Imgur 画像情報取得: {image_id}")
        
        headers = {
            'Authorization': f'Client-ID {IMGUR_CLIENT_ID}'
        }
        
        response = requests.get(
            f"{IMGUR_API_URL}/image/{image_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                image_data = result['data']
                return {
                    "success": True,
                    "id": image_data.get('id'),
                    "title": image_data.get('title'),
                    "description": image_data.get('description'),
                    "url": image_data.get('link'),
                    "size": image_data.get('size'),
                    "width": image_data.get('width'),
                    "height": image_data.get('height'),
                    "views": image_data.get('views'),
                    "datetime": image_data.get('datetime'),
                    "timestamp": _get_timestamp()
                }
            else:
                return {
                    "success": False,
                    "error": result.get('data', {}).get('error', 'Failed to get image info'),
                    "timestamp": _get_timestamp()
                }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "timestamp": _get_timestamp()
            }
            
    except Exception as e:
        logger.error(f"Imgur 画像情報取得エラー: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@imgur_mcp.tool()
async def get_account_images(limit: int = 10) -> Dict[str, Any]:
    """
    アカウントの画像一覧を取得（認証が必要）
    
    Args:
        limit: 取得する画像数
    
    Returns:
        dict: 画像一覧
    """
    try:
        # Note: この機能にはOAuth認証が必要
        # 現在はClient-IDのみなので基本機能のみ提供
        return {
            "success": False,
            "error": "Account images require OAuth authentication. Use individual image operations instead.",
            "note": "This feature requires OAuth setup with Imgur",
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Imgur アカウント画像取得エラー: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": _get_timestamp()
        }

@imgur_mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Imgur MCP サーバーのヘルスチェック"""
    try:
        # Imgur API接続テスト
        headers = {
            'Authorization': f'Client-ID {IMGUR_CLIENT_ID}'
        }
        
        # 軽量なAPI呼び出しでテスト
        response = requests.get(
            f"{IMGUR_API_URL}/credits",
            headers=headers,
            timeout=10
        )
        
        api_status = "connected" if response.status_code == 200 else "error"
        
        # レート制限情報取得
        rate_limit_info = {}
        if response.status_code == 200:
            rate_limit_info = {
                "client_limit": response.headers.get('X-RateLimit-ClientLimit'),
                "client_remaining": response.headers.get('X-RateLimit-ClientRemaining'),
                "reset_time": response.headers.get('X-RateLimit-ClientReset')
            }
        
        return {
            "status": "healthy",
            "service": "Imgur MCP Server",
            "version": "1.0.0",
            "features": {
                "upload_image": True,
                "delete_image": True,
                "get_image_info": True,
                "account_images": False  # OAuth required
            },
            "api_status": api_status,
            "client_id_configured": bool(IMGUR_CLIENT_ID),
            "rate_limit": rate_limit_info,
            "limits": {
                "max_file_size_mb": 20,
                "supported_formats": ["JPEG", "PNG", "GIF", "APNG", "TIFF", "PDF", "XCFBMP"]
            },
            "timestamp": _get_timestamp()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "service": "Imgur MCP Server",
            "error": str(e),
            "timestamp": _get_timestamp()
        }

# MCP Resources
@imgur_mcp.resource("imgur://usage")
async def get_usage_resource() -> str:
    """
    Imgur使用量情報をテキスト形式で取得
    
    Returns:
        str: 使用量情報（テキスト形式）
    """
    try:
        headers = {
            'Authorization': f'Client-ID {IMGUR_CLIENT_ID}'
        }
        
        response = requests.get(
            f"{IMGUR_API_URL}/credits",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            credits = data.get('data', {})
            
            usage_lines = [
                "=== Imgur API Usage ===",
                "",
                f"Client Remaining: {credits.get('ClientRemaining', 'N/A')}",
                f"Client Limit: {credits.get('ClientLimit', 'N/A')}",
                f"User Remaining: {credits.get('UserRemaining', 'N/A')}",
                f"User Limit: {credits.get('UserLimit', 'N/A')}",
                f"Reset Time: {credits.get('UserReset', 'N/A')}",
                "",
                "Rate Limits:",
                "  - Client: 12,500 requests/day",
                "  - User: 500 requests/hour",
                "  - File Size: 20MB max",
                "",
                f"Last Updated: {_get_timestamp()}"
            ]
            
            return "\\n".join(usage_lines)
        else:
            return f"Error getting usage info: HTTP {response.status_code}"
        
    except Exception as e:
        logger.error(f"Failed to get usage resource: {e}")
        return f"Error getting usage info: {str(e)}"

@imgur_mcp.resource("imgur://formats")
async def get_formats_resource() -> str:
    """
    サポートされている画像フォーマット情報を取得
    
    Returns:
        str: フォーマット情報（テキスト形式）
    """
    format_lines = [
        "=== Imgur Supported Formats ===",
        "",
        "Image Formats:",
        "  ✅ JPEG (.jpg, .jpeg)",
        "  ✅ PNG (.png)",
        "  ✅ GIF (.gif) - Static and Animated",
        "  ✅ APNG (.apng) - Animated PNG",
        "  ✅ TIFF (.tiff, .tif)",
        "  ✅ BMP (.bmp)",
        "  ✅ PDF (.pdf)",
        "  ✅ XCF (.xcf) - GIMP format",
        "",
        "Limitations:",
        "  📏 Max Size: 20MB",
        "  📐 Max Dimensions: 15000x15000 pixels",
        "  ⏱️  Upload Timeout: 30 seconds",
        "",
        "Privacy Options:",
        "  🌍 public - Visible in gallery",
        "  👁️  hidden - Not in gallery, but accessible via link",
        "  🔒 secret - Only accessible with direct link",
        "",
        f"Last Updated: {_get_timestamp()}"
    ]
    
    return "\\n".join(format_lines)

def _get_timestamp() -> str:
    """現在のタイムスタンプを取得"""
    return datetime.utcnow().isoformat()

# Main execution
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Imgur MCP Server...")
    imgur_mcp.run(transport="stdio")