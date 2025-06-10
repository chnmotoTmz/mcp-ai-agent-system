"""
LINE Webhook ハンドラー
LINE Bot からのメッセージを受信・処理
"""

import logging
from linebot.v3 import WebhookHandler as LineWebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent, VideoMessageContent, AudioMessageContent

from src.config import LINE_CHANNEL_SECRET

logger = logging.getLogger(__name__)

class WebhookHandler:
    """LINE Webhook ハンドラー"""
    
    def __init__(self):
        if not LINE_CHANNEL_SECRET:
            raise ValueError("LINE_CHANNEL_SECRET が設定されていません")
        
        self.handler = LineWebhookHandler(LINE_CHANNEL_SECRET)
        logger.info("WebhookHandler 初期化完了")
    
    def parse_events(self, body: str, signature: str):
        """Webhook イベントをパース"""
        try:
            events = self.handler.parse(body, signature)
            logger.info(f"受信イベント数: {len(events)}")
            return events
        except InvalidSignatureError:
            logger.error("LINE Webhook 署名検証失敗")
            raise
        except Exception as e:
            logger.error(f"Webhook イベントパースエラー: {e}")
            raise
    
    def extract_message_info(self, event):
        """メッセージイベントから情報を抽出"""
        if not isinstance(event, MessageEvent):
            return None
        
        user_id = event.source.user_id
        message_id = event.message.id
        timestamp = event.timestamp
        
        message_info = {
            "user_id": user_id,
            "message_id": message_id,
            "timestamp": timestamp,
            "message_type": None,
            "content": None,
            "file_path": None
        }
        
        # メッセージタイプに応じた処理
        if isinstance(event.message, TextMessageContent):
            message_info["message_type"] = "text"
            message_info["content"] = event.message.text
            
        elif isinstance(event.message, ImageMessageContent):
            message_info["message_type"] = "image"
            
        elif isinstance(event.message, VideoMessageContent):
            message_info["message_type"] = "video"
            
        elif isinstance(event.message, AudioMessageContent):
            message_info["message_type"] = "audio"
            
        else:
            logger.warning(f"サポートされていないメッセージタイプ: {type(event.message)}")
            return None
        
        return message_info
