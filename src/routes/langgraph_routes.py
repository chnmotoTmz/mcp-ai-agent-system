"""
LangGraph エージェント統合 API ルート
LINE Webhook と LangGraph エージェントを接続
"""

import asyncio
import logging
from flask import Blueprint, request, jsonify
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent, VideoMessageContent, AudioMessageContent

from src.core.webhook_handler import WebhookHandler
from src.langgraph_agents.agent import get_blog_agent, process_line_message_async
from src.services.line_service import LineService

logger = logging.getLogger(__name__)

# Blueprint 作成
langgraph_bp = Blueprint('langgraph', __name__, url_prefix='/api/langgraph')

# LangGraph エージェント統合 Webhook ハンドラー
webhook_handler = WebhookHandler()
line_service = LineService()

@langgraph_bp.route('/webhook', methods=['POST'])
def langgraph_webhook():
    """LangGraph エージェント統合 LINE Webhook エンドポイント"""
    
    # 署名検証
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    try:
        webhook_handler.handler.parse(body, signature)
    except InvalidSignatureError:
        logger.error("LINE Webhook 署名検証失敗")
        return jsonify({"error": "Invalid signature"}), 400
    
    # 非同期処理をバックグラウンドで実行
    asyncio.create_task(handle_webhook_async(body, signature))
    
    return jsonify({"status": "accepted"}), 200

async def handle_webhook_async(body: str, signature: str):
    """Webhook イベントの非同期処理"""
    try:
        events = webhook_handler.handler.parse(body, signature)
        
        for event in events:
            if isinstance(event, MessageEvent):
                await process_message_event(event)
            
    except Exception as e:
        logger.error(f"Webhook 非同期処理エラー: {e}")

async def process_message_event(event: MessageEvent):
    """メッセージイベント処理"""
    try:
        user_id = event.source.user_id
        message_id = event.message.id
        
        logger.info(f"LangGraph エージェント処理開始: ユーザー={user_id}, メッセージ={message_id}")
        
        # メッセージタイプに応じて処理
        content = None
        file_path = None
        message_type = None
        
        if isinstance(event.message, TextMessageContent):
            message_type = "text"
            content = event.message.text
            
        elif isinstance(event.message, ImageMessageContent):
            message_type = "image"
            # 画像ファイルをダウンロード
            file_path = await download_media_file(message_id, "image")
            
        elif isinstance(event.message, VideoMessageContent):
            message_type = "video"
            # 動画ファイルをダウンロード
            file_path = await download_media_file(message_id, "video")
            
        elif isinstance(event.message, AudioMessageContent):
            message_type = "audio"
            # 音声ファイルをダウンロード
            file_path = await download_media_file(message_id, "audio")
            
        else:
            logger.warning(f"サポートされていないメッセージタイプ: {type(event.message)}")
            return
        
        # ユーザー設定を読み込み
        config = {
            "article_style": "blog",  # デフォルトスタイル
            "publish_as_draft": False,  # 下書きとして投稿するか
            "blog_category": "日記",   # ブログカテゴリ
            "user_preferences": {}     # ユーザー固有設定
        }
        
        # LangGraph エージェントで処理
        result = await process_line_message_async(
            message_id=message_id,
            user_id=user_id,
            message_type=message_type,
            content=content,
            file_path=file_path,
            config=config
        )
        
        logger.info(f"LangGraph エージェント処理完了: {result.get('success')} - セッション: {result.get('session_id')}")
        
        # エラー時の直接通知（LangGraph内で通知されない場合のフォールバック）
        if not result.get('success') and result.get('errors'):
            error_message = f"❌ 処理中にエラーが発生しました:\\n{result['errors'][0]['message']}"
            line_service.send_message(user_id, error_message)
        
    except Exception as e:
        logger.error(f"メッセージイベント処理エラー: {e}")
        
        # エラー通知
        try:
            error_message = "申し訳ございません。処理中にエラーが発生しました。しばらく時間をおいて再度お試しください。"
            line_service.send_message(event.source.user_id, error_message)
        except Exception as notify_error:
            logger.error(f"エラー通知送信失敗: {notify_error}")

async def download_media_file(message_id: str, media_type: str) -> str:
    """メディアファイルをダウンロード"""
    try:
        import os
        import aiohttp
        import tempfile
        from src.config import LINE_CHANNEL_ACCESS_TOKEN
        
        # LINE API からファイル内容を取得
        headers = {'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'}
        
        async with aiohttp.ClientSession() as session:
            # ファイル内容を取得
            async with session.get(
                f'https://api-data.line.me/v2/bot/message/{message_id}/content',
                headers=headers
            ) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # 一時ファイルに保存
                    temp_dir = "/tmp/line_media"
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    # ファイル拡張子を決定
                    ext_map = {
                        "image": ".jpg",
                        "video": ".mp4", 
                        "audio": ".m4a"
                    }
                    ext = ext_map.get(media_type, ".bin")
                    
                    file_path = os.path.join(temp_dir, f"{message_id}{ext}")
                    
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    
                    logger.info(f"メディアファイルダウンロード完了: {file_path}")
                    return file_path
                else:
                    logger.error(f"ファイルダウンロード失敗: {response.status}")
                    return None
        
    except Exception as e:
        logger.error(f"メディアファイルダウンロードエラー: {e}")
        return None

@langgraph_bp.route('/sessions', methods=['GET'])
def get_sessions():
    """アクティブセッション一覧取得"""
    try:
        agent = get_blog_agent()
        sessions = asyncio.run(agent.list_active_sessions())
        
        return jsonify({
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        })
        
    except Exception as e:
        logger.error(f"セッション一覧取得エラー: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@langgraph_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """特定セッション状態取得"""
    try:
        agent = get_blog_agent()
        state = asyncio.run(agent.get_session_state(session_id))
        
        if state:
            return jsonify({
                "success": True,
                "session": state
            })
        else:
            return jsonify({
                "success": False,
                "error": "Session not found"
            }), 404
            
    except Exception as e:
        logger.error(f"セッション状態取得エラー: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@langgraph_bp.route('/sessions/<session_id>', methods=['DELETE'])
def cancel_session(session_id: str):
    """セッションキャンセル"""
    try:
        agent = get_blog_agent()
        success = asyncio.run(agent.cancel_session(session_id))
        
        return jsonify({
            "success": success,
            "message": f"Session {session_id} {'cancelled' if success else 'not found'}"
        })
        
    except Exception as e:
        logger.error(f"セッションキャンセルエラー: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@langgraph_bp.route('/graph', methods=['GET'])
def get_graph_visualization():
    """グラフ可視化取得"""
    try:
        agent = get_blog_agent()
        mermaid_graph = agent.get_graph_visualization()
        
        return jsonify({
            "success": True,
            "graph": mermaid_graph,
            "format": "mermaid"
        })
        
    except Exception as e:
        logger.error(f"グラフ可視化取得エラー: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@langgraph_bp.route('/test', methods=['POST'])
def test_agent():
    """エージェント機能テスト"""
    try:
        data = request.get_json()
        
        test_message_id = data.get('message_id', 'test_msg_001')
        test_user_id = data.get('user_id', 'test_user')
        test_message_type = data.get('message_type', 'text')
        test_content = data.get('content', 'これはテストメッセージです。')
        test_config = data.get('config', {})
        
        # テスト実行
        result = asyncio.run(process_line_message_async(
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
        logger.error(f"エージェントテストエラー: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@langgraph_bp.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    try:
        agent = get_blog_agent()
        
        # MCP サーバーヘルスチェック
        mcp_health = asyncio.run(agent.nodes.mcp_client.health_check_all())
        
        # 全体状態
        all_healthy = all(
            result.get('success', False) 
            for result in mcp_health.values()
        )
        
        return jsonify({
            "success": True,
            "status": "healthy" if all_healthy else "degraded",
            "langgraph_agent": "ready",
            "mcp_services": mcp_health,
            "timestamp": logging.time.time()
        })
        
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }), 500
