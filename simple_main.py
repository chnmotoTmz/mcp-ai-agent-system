"""
簡易ブログ生成エージェント メインアプリケーション
LangGraphなしでの基本統合フロー
"""

import asyncio
import logging
import sys
import os
from flask import Flask, jsonify, request
from flask_cors import CORS

# プロジェクトルートをPythonパスに追加
project_root = "/home/moto/line-gemini-hatena-integration"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.config import (
        LINE_CHANNEL_ACCESS_TOKEN, 
        LINE_CHANNEL_SECRET,
        GEMINI_API_KEY,
        IMGUR_CLIENT_ID,
        HATENA_ID, HATENA_BLOG_ID, HATENA_API_KEY
    )
    from src.core.webhook_handler import WebhookHandler
    from src.langgraph_agents.simple_agent import get_simple_agent, process_line_message_simple
    from src.services.line_service import LineService
except ImportError as e:
    print(f"インポートエラー: {e}")
    print("設定ファイルまたは依存関係を確認してください")
    sys.exit(1)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/moto/line-gemini-hatena-integration/logs/simple_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def create_app():
    """Flask アプリケーション作成"""
    app = Flask(__name__)
    CORS(app)
    
    # 設定確認
    config_status = check_configuration()
    logger.info(f"設定確認結果: {config_status}")
    
    # Webhook ハンドラー
    webhook_handler = WebhookHandler()
    line_service = LineService()
    
    @app.route('/')
    def root():
        return jsonify({
            "service": "Simple Blog Generation Agent",
            "version": "1.0.0",
            "status": "running",
            "type": "simplified_without_langgraph",
            "endpoints": {
                "webhook": "/webhook",
                "sessions": "/sessions",
                "test": "/test",
                "health": "/health"
            },
            "configuration": config_status
        })
    
    @app.route('/webhook', methods=['POST'])
    def webhook():
        """簡易版 LINE Webhook エンドポイント"""
        signature = request.headers.get('X-Line-Signature', '')
        body = request.get_data(as_text=True)
        
        try:
            # 署名検証
            from linebot.v3.exceptions import InvalidSignatureError
            webhook_handler.handler.parse(body, signature)
            
            # 非同期処理をバックグラウンドで実行
            asyncio.create_task(handle_webhook_async(body, signature))
            
            return jsonify({"status": "accepted"}), 200
            
        except InvalidSignatureError:
            logger.error("LINE Webhook 署名検証失敗")
            return jsonify({"error": "Invalid signature"}), 400
        except Exception as e:
            logger.error(f"Webhook処理エラー: {e}")
            return jsonify({"error": str(e)}), 500
    
    async def handle_webhook_async(body: str, signature: str):
        """Webhook イベントの非同期処理"""
        try:
            from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent
            
            events = webhook_handler.handler.parse(body, signature)
            
            for event in events:
                if isinstance(event, MessageEvent):
                    await process_message_event_simple(event)
                    
        except Exception as e:
            logger.error(f"Webhook 非同期処理エラー: {e}")
    
    async def process_message_event_simple(event):
        """簡易メッセージイベント処理"""
        try:
            user_id = event.source.user_id
            message_id = event.message.id
            
            logger.info(f"簡易エージェント処理開始: ユーザー={user_id}")
            
            # メッセージタイプ判定
            content = None
            file_path = None
            message_type = None
            
            if isinstance(event.message, TextMessageContent):
                message_type = "text"
                content = event.message.text
            elif isinstance(event.message, ImageMessageContent):
                message_type = "image"
                file_path = await download_media_file(message_id, "image")
            else:
                logger.warning(f"サポートされていないメッセージタイプ: {type(event.message)}")
                return
            
            # 簡易エージェントで処理
            result = await process_line_message_simple(
                message_id=message_id,
                user_id=user_id,
                message_type=message_type,
                content=content,
                file_path=file_path,
                config={
                    "article_style": "blog",
                    "publish_as_draft": False,
                    "blog_category": "AI生成"
                }
            )
            
            logger.info(f"簡易エージェント処理完了: 成功={result.get('success')}")
            
            # エラー時の通知
            if not result.get('success'):
                error_message = "申し訳ございません。処理中にエラーが発生しました。"
                line_service.send_message(user_id, error_message)
            
        except Exception as e:
            logger.error(f"簡易メッセージイベント処理エラー: {e}")
            
            try:
                error_message = "システムエラーが発生しました。しばらく時間をおいて再度お試しください。"
                line_service.send_message(event.source.user_id, error_message)
            except:
                pass
    
    async def download_media_file(message_id: str, media_type: str) -> str:
        """メディアファイルダウンロード"""
        try:
            import aiohttp
            import tempfile
            
            headers = {'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'https://api-data.line.me/v2/bot/message/{message_id}/content',
                    headers=headers
                ) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # 一時ファイルに保存
                        temp_dir = "/tmp/line_media"
                        os.makedirs(temp_dir, exist_ok=True)
                        
                        ext = ".jpg" if media_type == "image" else ".bin"
                        file_path = os.path.join(temp_dir, f"{message_id}{ext}")
                        
                        with open(file_path, 'wb') as f:
                            f.write(content)
                        
                        return file_path
            
            return None
            
        except Exception as e:
            logger.error(f"メディアファイルダウンロードエラー: {e}")
            return None
    
    @app.route('/sessions', methods=['GET'])
    def get_sessions():
        """アクティブセッション一覧"""
        try:
            agent = get_simple_agent()
            sessions = agent.list_active_sessions()
            
            return jsonify({
                "success": True,
                "sessions": sessions,
                "count": len(sessions)
            })
            
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/sessions/<session_id>', methods=['GET'])
    def get_session(session_id: str):
        """特定セッション状態取得"""
        try:
            agent = get_simple_agent()
            state = agent.get_session_state(session_id)
            
            if state:
                return jsonify({"success": True, "session": state})
            else:
                return jsonify({"success": False, "error": "Session not found"}), 404
                
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/test', methods=['POST'])
    def test_agent():
        """簡易エージェントテスト"""
        try:
            data = request.get_json() or {}
            
            test_message_id = data.get('message_id', 'test_simple_001')
            test_user_id = data.get('user_id', 'test_user_simple')
            test_message_type = data.get('message_type', 'text')
            test_content = data.get('content', '簡易エージェントのテストメッセージです。')
            test_config = data.get('config', {"publish_as_draft": True})
            
            # テスト実行
            result = asyncio.run(process_line_message_simple(
                message_id=test_message_id,
                user_id=test_user_id,
                message_type=test_message_type,
                content=test_content,
                config=test_config
            ))
            
            return jsonify({
                "success": True,
                "test_result": result
            })
            
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/health', methods=['GET'])
    def health():
        """ヘルスチェック"""
        try:
            # 簡易ヘルスチェック
            health_status = {
                "status": "healthy",
                "agent_type": "simple",
                "timestamp": time.time(),
                "services": {}
            }
            
            # サービス確認
            try:
                from src.services.gemini_service import GeminiService
                GeminiService()
                health_status["services"]["gemini"] = "ok"
            except:
                health_status["services"]["gemini"] = "error"
            
            try:
                from src.services.line_service import LineService
                LineService()
                health_status["services"]["line"] = "ok"
            except:
                health_status["services"]["line"] = "error"
            
            return jsonify(health_status)
            
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 500
    
    return app

def check_configuration():
    """設定確認"""
    configs = {
        "line_access_token": bool(LINE_CHANNEL_ACCESS_TOKEN),
        "line_channel_secret": bool(LINE_CHANNEL_SECRET),
        "gemini_api_key": bool(GEMINI_API_KEY),
        "imgur_client_id": bool(IMGUR_CLIENT_ID),
        "hatena_id": bool(HATENA_ID),
        "hatena_blog_id": bool(HATENA_BLOG_ID),
        "hatena_api_key": bool(HATENA_API_KEY)
    }
    
    missing = [key for key, value in configs.items() if not value]
    
    return {
        "all_configured": len(missing) == 0,
        "missing": missing,
        "configured": [key for key, value in configs.items() if value]
    }

def main():
    """メイン実行"""
    import time
    
    logger.info("簡易ブログ生成エージェント起動")
    
    # 設定確認
    config_status = check_configuration()
    if not config_status["all_configured"]:
        logger.warning(f"設定不足: {config_status['missing']}")
        logger.info("不足している設定がありますが、起動を続行します")
    
    # テスト実行
    if "--test" in sys.argv:
        logger.info("テスト実行")
        try:
            import subprocess
            result = subprocess.run([sys.executable, "test_simple_agent.py"], 
                                  cwd="/home/moto/line-gemini-hatena-integration")
            return
        except Exception as e:
            logger.error(f"テスト実行エラー: {e}")
            return
    
    # アプリ起動
    app = create_app()
    port = int(os.environ.get('PORT', 8080))
    debug = "--debug" in sys.argv
    
    logger.info(f"簡易エージェントサーバー起動: ポート={port}")
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("サービス停止")
    except Exception as e:
        logger.error(f"アプリケーション実行エラー: {e}")

if __name__ == "__main__":
    main()
