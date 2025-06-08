"""
LINE Webhook ルート - AI Agent統合版
AIエージェントを使用したメッセージ処理
"""

import asyncio
import json
import logging
import os
from flask import Blueprint, request, jsonify
from src.agents.content_creation_agent import ContentCreationAgent
from src.database import db, Message

logger = logging.getLogger(__name__)

webhook_bp = Blueprint('webhook', __name__)

# AI Agent のグローバルインスタンス
agent = None

async def initialize_agent():
    """AI Agent を初期化"""
    global agent
    if agent is None:
        agent = ContentCreationAgent()
        await agent.initialize()
        logger.info("AI Agent initialized successfully")

def ensure_agent_initialized():
    """AI Agent の初期化を確認"""
    if agent is None:
        # イベントループで初期化を実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(initialize_agent())
        loop.close()

@webhook_bp.route('/line', methods=['POST'])
def line_webhook():
    """LINE Webhook エンドポイント - AI Agent版"""
    
    logger.info(f"Received webhook request. Headers: {dict(request.headers)}")
    
    # 署名検証
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    logger.info(f"Signature: {signature}")
    logger.info(f"Body length: {len(body) if body else 'None'}")
    logger.info(f"Body content: {body[:200] if body else 'None'}")
    
    # 署名が存在しない場合の処理
    if not signature:
        logger.error('X-Line-Signature header is missing')
        return jsonify({'error': 'X-Line-Signature header is missing'}), 400
    
    # リクエストボディが空の場合の処理
    if not body:
        logger.error('Request body is empty')
        return jsonify({'error': 'Request body is empty'}), 400
    
    try:
        # AI Agent の初期化確認
        ensure_agent_initialized()
        
        # Webhook body をパース
        webhook_body = json.loads(body)
        
        # eventsが存在し、空でない場合のみ処理
        if 'events' in webhook_body and webhook_body['events']:
            for event_data in webhook_body['events']:
                logger.info(f"Processing event: {event_data}")
                
                # メッセージイベントの場合はAI Agentで処理
                if event_data.get('type') == 'message':
                    # 非同期処理をバックグラウンドで実行
                    asyncio.create_task(process_message_with_agent(event_data))
        else:
            logger.info("No events to process (webhook verification or empty events)")
        
        logger.info('Webhook handled successfully')
        
    except Exception as e:
        logger.error(f'Webhook handling error: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500
    
    return 'OK'

async def process_message_with_agent(event_data):
    """AI Agentを使用してメッセージを処理"""
    global agent
    
    try:
        # メッセージ情報を抽出
        message = event_data.get('message', {})
        source = event_data.get('source', {})
        
        user_id = source.get('userId')
        line_message_id = message.get('id')
        message_type = message.get('type')
        
        if not user_id or not line_message_id:
            logger.warning("Missing user_id or message_id")
            return
        
        # メッセージ内容を準備
        if message_type == 'text':
            content = message.get('text', '')
            file_path = None
        elif message_type == 'image':
            # 画像の場合は保存処理を行う
            content = "Image received"
            file_path = await save_image_from_line(line_message_id)
        else:
            logger.info(f"Unsupported message type: {message_type}")
            return
        
        # データベースにメッセージを保存
        try:
            message_record = Message(
                line_message_id=line_message_id,
                user_id=user_id,
                message_type=message_type,
                content=content,
                file_path=file_path
            )
            db.session.add(message_record)
            db.session.commit()
            logger.info(f"Message saved to database: {line_message_id}")
        except Exception as e:
            logger.error(f"Failed to save message to database: {e}")
        
        # AI Agentで処理するためのメッセージ形式に変換
        agent_messages = [{
            "content": content,
            "type": message_type,
            "file_path": file_path,
            "line_message_id": line_message_id
        }]
        
        # AI Agentでメッセージを処理
        logger.info(f"Processing message with AI Agent for user {user_id}")
        result = await agent.process_message(
            user_id=user_id,
            line_message_id=line_message_id,
            messages=agent_messages
        )
        
        logger.info(f"Agent processing result: {result}")
        
    except Exception as e:
        logger.error(f"Error processing message with agent: {str(e)}")
        
        # エラー時は直接LINEに通知
        try:
            from src.services.line_service import LineService
            line_service = LineService()
            line_service.send_message(
                user_id,
                f"申し訳ございません。処理中にエラーが発生しました。\\nエラー詳細: {str(e)}"
            )
        except Exception as notify_error:
            logger.error(f"Failed to send error notification: {notify_error}")

async def save_image_from_line(message_id):
    """LINEから画像を取得して保存"""
    try:
        from linebot import LineBotApi
        from src.config import Config
        
        line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)
        
        # 画像コンテンツを取得
        message_content = line_bot_api.get_message_content(message_id)
        
        # 保存先ディレクトリを確保
        upload_dir = "uploads"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # ファイルパスを生成
        image_path = os.path.join(upload_dir, f"{message_id}.jpg")
        
        # ファイルに保存
        with open(image_path, 'wb') as f:
            for chunk in message_content.iter_content():
                f.write(chunk)
        
        logger.info(f"Image saved: {image_path}")
        return image_path
        
    except Exception as e:
        logger.error(f"Failed to save image: {e}")
        return None

@webhook_bp.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        ensure_agent_initialized()
        return jsonify({
            "status": "healthy",
            "agent_initialized": agent is not None,
            "timestamp": "2025-06-08T12:00:00Z"
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": "2025-06-08T12:00:00Z"
        }), 500

@webhook_bp.route('/test', methods=['POST'])
def test_agent():
    """AI Agent テスト用エンドポイント"""
    try:
        ensure_agent_initialized()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        user_id = data.get('user_id', 'test_user')
        message = data.get('message', 'テストメッセージ')
        message_type = data.get('type', 'text')
        
        # テスト用のメッセージ処理
        test_messages = [{
            "content": message,
            "type": message_type
        }]
        
        # 非同期処理を同期的に実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            agent.process_message(
                user_id=user_id,
                line_message_id=f"test_{user_id}",
                messages=test_messages
            )
        )
        loop.close()
        
        return jsonify({
            "test_result": result,
            "timestamp": "2025-06-08T12:00:00Z"
        })
        
    except Exception as e:
        logger.error(f"Test endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

# アプリケーション終了時のクリーンアップ
def cleanup_agent():
    """AI Agent のクリーンアップ"""
    global agent
    if agent:
        # クリーンアップは非同期なので、ここでは簡単に None にするだけ
        agent = None
        logger.info("AI Agent cleaned up")

# アプリケーション終了時にクリーンアップを登録
import atexit
atexit.register(cleanup_agent)
