"""
MCP クライアント統合ユーティリティ
各MCPサーバーとの通信を管理
"""

import asyncio
import logging
import json
import subprocess
import tempfile
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class MCPClientManager:
    """MCP サーバーとの通信を管理するクライアント"""
    
    def __init__(self):
        self.base_path = "/home/moto/line-gemini-hatena-integration"
        self.mcp_servers = {
            "imgur": f"{self.base_path}/src/mcp_servers/imgur_server_fastmcp.py",
            "gemini": f"{self.base_path}/src/mcp_servers/gemini_server_fastmcp_fixed.py", 
            "line": f"{self.base_path}/src/mcp_servers/line_server_fastmcp_fixed.py",
            "hatena": f"{self.base_path}/src/mcp_servers/hatena_server_fastmcp_fixed.py"
        }
        self.active_connections = {}
    
    async def call_imgur_upload(self, image_path: str, title: str = "", 
                               description: str = "", privacy: str = "hidden") -> Dict[str, Any]:
        """Imgur MCP サーバーで画像をアップロード"""
        try:
            logger.info(f"Imgur画像アップロード開始: {image_path}")
            
            # 直接サービスクラスを使用（MCP経由は複雑なため）
            from src.services.imgur_service import ImgurService
            
            imgur_service = ImgurService()
            result = imgur_service.upload_image(
                image_path=image_path,
                title=title,
                description=description,
                privacy=privacy
            )
            
            if result and result.get('success'):
                logger.info(f"Imgur アップロード成功: {result.get('imgur_url')}")
                return {
                    "success": True,
                    "imgur_url": result.get('imgur_url'),
                    "imgur_id": result.get('imgur_id'),
                    "delete_hash": result.get('delete_hash'),
                    "title": title
                }
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result'
                logger.error(f"Imgur アップロード失敗: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            logger.error(f"Imgur MCP 呼び出しエラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def call_gemini_generate_article(self, content: str, style: str = "blog", 
                                         context: str = "") -> Dict[str, Any]:
        """Gemini MCP サーバーで記事生成"""
        try:
            logger.info(f"Gemini 記事生成開始: スタイル={style}")
            
            from src.services.gemini_service import GeminiService
            
            gemini_service = GeminiService()
            
            # コンテキストがある場合は追加
            if context:
                full_content = f"コンテキスト: {context}\\n\\n{content}"
            else:
                full_content = content
            
            result = gemini_service.generate_article_from_content(
                content=full_content,
                style=style
            )
            
            if result:
                logger.info(f"Gemini 記事生成成功: {result.get('title', 'No title')}")
                return {
                    "success": True,
                    "title": result.get('title', ''),
                    "content": result.get('content', ''),
                    "summary": result.get('summary', ''),
                    "tags": result.get('tags', []),
                    "style": result.get('style', style)
                }
            else:
                logger.error("Gemini 記事生成失敗: 結果が空")
                return {
                    "success": False,
                    "error": "No result generated"
                }
                
        except Exception as e:
            logger.error(f"Gemini MCP 呼び出しエラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def call_gemini_analyze_image(self, image_path: str, 
                                       prompt: str = "この画像について詳しく説明してください") -> Dict[str, Any]:
        """Gemini MCP サーバーで画像分析"""
        try:
            logger.info(f"Gemini 画像分析開始: {image_path}")
            
            from src.services.gemini_service import GeminiService
            
            gemini_service = GeminiService()
            result = gemini_service.analyze_image(image_path, prompt)
            
            if result:
                logger.info("Gemini 画像分析成功")
                return {
                    "success": True,
                    "analysis": result,
                    "image_path": image_path
                }
            else:
                logger.error("Gemini 画像分析失敗")
                return {
                    "success": False,
                    "error": "Image analysis failed"
                }
                
        except Exception as e:
            logger.error(f"Gemini 画像分析エラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def call_line_send_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """LINE MCP サーバーでメッセージ送信"""
        try:
            logger.info(f"LINE メッセージ送信開始: {user_id}")
            
            from src.services.line_service import LineService
            
            line_service = LineService()
            line_service.send_message(user_id, message)
            
            logger.info("LINE メッセージ送信成功")
            return {
                "success": True,
                "user_id": user_id,
                "message": message[:100] + "..." if len(message) > 100 else message
            }
            
        except Exception as e:
            logger.error(f"LINE MCP 呼び出しエラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def call_hatena_publish_article(self, title: str, content: str, 
                                         tags: List[str] = None, category: str = "",
                                         draft: bool = False) -> Dict[str, Any]:
        """Hatena MCP サーバーで記事投稿"""
        try:
            logger.info(f"Hatena 記事投稿開始: {title}")
            
            from src.services.hatena_service import HatenaService
            
            hatena_service = HatenaService()
            result = hatena_service.publish_article(
                title=title,
                content=content,
                tags=tags or [],
                category=category,
                draft=draft
            )
            
            if result:
                logger.info(f"Hatena 記事投稿成功: {result.get('url')}")
                return {
                    "success": True,
                    "article_id": result.get('id', ''),
                    "url": result.get('url', ''),
                    "title": title,
                    "tags": tags or [],
                    "category": category,
                    "draft": draft
                }
            else:
                logger.error("Hatena 記事投稿失敗")
                return {
                    "success": False,
                    "error": "Article publishing failed"
                }
                
        except Exception as e:
            logger.error(f"Hatena MCP 呼び出しエラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def health_check_all(self) -> Dict[str, Any]:
        """全MCPサーバーのヘルスチェック"""
        results = {}
        
        services = [
            ("imgur", self.call_imgur_health_check),
            ("gemini", self.call_gemini_health_check),
            ("line", self.call_line_health_check),
            ("hatena", self.call_hatena_health_check)
        ]
        
        for service_name, health_check_func in services:
            try:
                result = await health_check_func()
                results[service_name] = result
            except Exception as e:
                results[service_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    async def call_imgur_health_check(self) -> Dict[str, Any]:
        """Imgur ヘルスチェック"""
        try:
            from src.services.imgur_service import ImgurService
            imgur_service = ImgurService()
            
            return {
                "success": True,
                "service": "Imgur",
                "status": "healthy",
                "client_id_configured": bool(imgur_service.client_id)
            }
        except Exception as e:
            return {
                "success": False,
                "service": "Imgur",
                "error": str(e)
            }
    
    async def call_gemini_health_check(self) -> Dict[str, Any]:
        """Gemini ヘルスチェック"""
        try:
            from src.services.gemini_service import GeminiService
            gemini_service = GeminiService()
            model_info = gemini_service.get_model_info()
            
            return {
                "success": True,
                "service": "Gemini",
                "status": "healthy",
                "model_info": model_info
            }
        except Exception as e:
            return {
                "success": False,
                "service": "Gemini", 
                "error": str(e)
            }
    
    async def call_line_health_check(self) -> Dict[str, Any]:
        """LINE ヘルスチェック"""
        try:
            from src.services.line_service import LineService
            line_service = LineService()
            
            return {
                "success": True,
                "service": "LINE",
                "status": "healthy",
                "api_configured": bool(line_service.line_bot_api)
            }
        except Exception as e:
            return {
                "success": False,
                "service": "LINE",
                "error": str(e)
            }
    
    async def call_hatena_health_check(self) -> Dict[str, Any]:
        """Hatena ヘルスチェック"""
        try:
            from src.services.hatena_service import HatenaService
            hatena_service = HatenaService()
            
            return {
                "success": True,
                "service": "Hatena",
                "status": "healthy",
                "config": {
                    "hatena_id": bool(hatena_service.hatena_id),
                    "blog_id": bool(hatena_service.blog_id),
                    "api_key": bool(hatena_service.api_key)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "service": "Hatena",
                "error": str(e)
            }
    
    def _create_temp_image(self) -> str:
        """テスト用の一時画像ファイルを作成"""
        try:
            from PIL import Image
            
            # 10x10の小さなテスト画像
            image = Image.new('RGB', (10, 10), color='red')
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            image.save(temp_file.name)
            temp_file.close()
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"テスト画像作成エラー: {e}")
            raise
    
    def cleanup_temp_files(self, file_paths: List[str]):
        """一時ファイルをクリーンアップ"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.info(f"一時ファイル削除: {file_path}")
            except Exception as e:
                logger.warning(f"一時ファイル削除失敗: {file_path} - {e}")
