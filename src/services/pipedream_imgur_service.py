"""
Pipedream Imgur MCP Service
Pipedream を経由して Imgur API を利用するサービス
"""

import asyncio
import logging
import os
import subprocess
import json
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PipedreamImgurService:
    """Pipedream Imgur MCP Service"""
    
    def __init__(self):
        self.mcp_config = self._load_mcp_config()
        self.mcp_process = None
        logger.info("Pipedream Imgur MCPサービス初期化完了")
    
    def _load_mcp_config(self) -> Dict[str, Any]:
        """MCP設定ファイルを読み込み"""
        try:
            config_path = '/home/moto/line-gemini-hatena-integration/mcp_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info("MCP設定ファイル読み込み完了")
            return config
        except Exception as e:
            logger.error(f"MCP設定ファイル読み込みエラー: {e}")
            return {}
    
    async def upload_image(self, image_path: str, title: str = "", 
                          description: str = "", privacy: str = "hidden") -> Dict[str, Any]:
        """
        Pipedream MCP 経由で画像をアップロード
        
        Args:
            image_path: アップロードする画像のパス
            title: 画像のタイトル
            description: 画像の説明
            privacy: プライバシー設定
            
        Returns:
            dict: アップロード結果
        """
        try:
            logger.info(f"Pipedream MCP経由で画像アップロード開始: {image_path}")
            
            # ファイル存在確認
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": f"画像ファイルが存在しません: {image_path}",
                    "timestamp": self._get_timestamp()
                }
            
            # MCP呼び出し用のスクリプトを作成
            mcp_call_result = await self._call_mcp_upload(
                image_path, title, description, privacy
            )
            
            return mcp_call_result
            
        except Exception as e:
            logger.error(f"Pipedream MCP アップロードエラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def _call_mcp_upload(self, image_path: str, title: str, 
                              description: str, privacy: str) -> Dict[str, Any]:
        """MCP経由でのアップロード実行"""
        try:
            # Pipedream MCP の imgur コマンドを構築
            imgur_config = self.mcp_config.get("mcpServers", {}).get("imgur", {})
            
            if not imgur_config:
                raise ValueError("Imgur MCP設定が見つかりません")
            
            # MCPコマンドを実行
            cmd = imgur_config["command"]
            args = imgur_config["args"] + [
                "--tool", "upload_image",
                "--input", json.dumps({
                    "image_path": image_path,
                    "title": title,
                    "description": description,
                    "privacy": privacy
                })
            ]
            
            logger.info(f"MCP呼び出しコマンド: {cmd} {' '.join(args)}")
            
            # 非同期でプロセス実行
            process = await asyncio.create_subprocess_exec(
                cmd, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # 成功時の処理
                try:
                    result = json.loads(stdout.decode('utf-8'))
                    logger.info(f"Pipedream MCP アップロード成功: {result.get('url', 'N/A')}")
                    return {
                        "success": True,
                        "url": result.get("url"),
                        "imgur_url": result.get("url"),
                        "imgur_id": result.get("id"),
                        "delete_hash": result.get("delete_hash"),
                        "title": title,
                        "description": description,
                        "timestamp": self._get_timestamp(),
                        "source": "pipedream_mcp"
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"MCP応答のJSON解析エラー: {e}")
                    return {
                        "success": False,
                        "error": f"応答解析エラー: {e}",
                        "raw_output": stdout.decode('utf-8'),
                        "timestamp": self._get_timestamp()
                    }
            else:
                # エラー時の処理
                error_msg = stderr.decode('utf-8') if stderr else "不明なエラー"
                logger.error(f"Pipedream MCP エラー: {error_msg}")
                return {
                    "success": False,
                    "error": f"MCP実行エラー: {error_msg}",
                    "return_code": process.returncode,
                    "timestamp": self._get_timestamp()
                }
                
        except Exception as e:
            logger.error(f"MCP呼び出しで予期しないエラー: {e}")
            return {
                "success": False,
                "error": f"予期しないエラー: {str(e)}",
                "timestamp": self._get_timestamp()
            }
    
    async def get_account_images(self, limit: int = 10) -> Dict[str, Any]:
        """アカウントの画像一覧を取得（Pipedream MCP経由）"""
        try:
            logger.info(f"Pipedream MCP経由でアカウント画像取得: limit={limit}")
            
            # TODO: Pipedream MCPの実際のツール名に合わせて調整
            result = await self._call_mcp_tool("get_account_images", {
                "limit": limit
            })
            
            return result
            
        except Exception as e:
            logger.error(f"アカウント画像取得エラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def _call_mcp_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """汎用MCP ツール呼び出し"""
        try:
            imgur_config = self.mcp_config.get("mcpServers", {}).get("imgur", {})
            
            cmd = imgur_config["command"]
            args = imgur_config["args"] + [
                "--tool", tool_name,
                "--input", json.dumps(params)
            ]
            
            process = await asyncio.create_subprocess_exec(
                cmd, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return json.loads(stdout.decode('utf-8'))
            else:
                error_msg = stderr.decode('utf-8') if stderr else "不明なエラー"
                return {
                    "success": False,
                    "error": error_msg,
                    "timestamp": self._get_timestamp()
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    def _get_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        return datetime.utcnow().isoformat()
    
    async def health_check(self) -> Dict[str, Any]:
        """Pipedream MCP の接続チェック"""
        try:
            logger.info("Pipedream MCP ヘルスチェック開始")
            
            # MCP設定確認
            if not self.mcp_config:
                return {
                    "status": "error",
                    "error": "MCP設定が見つかりません",
                    "timestamp": self._get_timestamp()
                }
            
            # TODO: 実際のヘルスチェック用ツールがあれば呼び出し
            result = await self._call_mcp_tool("health_check", {})
            
            return {
                "status": "healthy",
                "service": "Pipedream Imgur MCP",
                "mcp_result": result,
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            logger.error(f"ヘルスチェックエラー: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }

# 使用例
if __name__ == "__main__":
    async def test_pipedream_imgur():
        service = PipedreamImgurService()
        
        # ヘルスチェック
        health = await service.health_check()
        print(f"Health Check: {health}")
        
        # 画像アップロードテスト（テスト画像があれば）
        test_image = "/home/moto/line-gemini-hatena-integration/uploads/564948801136361784.jpg"
        if os.path.exists(test_image):
            result = await service.upload_image(
                test_image,
                title="Pipedream MCP テスト",
                description="Pipedream経由でのアップロードテスト"
            )
            print(f"Upload Result: {result}")
        else:
            print("テスト画像が見つかりません")
    
    # テスト実行
    asyncio.run(test_pipedream_imgur())