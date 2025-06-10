"""
LINE Bot Service
LINEメッセージの受信・処理・ファイルダウンロードを担当
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage

from src.config import Config
from src.database import db, Message

logger = logging.getLogger(__name__)

class LineService:
    def __init__(self):
        self.line_bot_api = LineBotApi(Config.LINE_CHANNEL_ACCESS_TOKEN)
        self.upload_dir = Path(Config.UPLOAD_FOLDER)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def send_message(self, user_id: str, text: str):
        """ユーザーにテキストメッセージを送信"""
        try:
            # ユーザーIDの妥当性チェック
            if not user_id or not isinstance(user_id, str):
                raise ValueError(f"Invalid user_id: {user_id}")
            
            # テスト用ユーザーIDの場合はログのみ
            if user_id.startswith('test_') or user_id == 'test_user':
                logger.info(f"テストメッセージ送信（実際の送信はスキップ）: {user_id} -> {text}")
                return
            
            # LINE ユーザーIDの形式チェック（UまたはCで始まる）
            if not (user_id.startswith('U') or user_id.startswith('C')):
                logger.warning(f"Possible invalid LINE user_id format: {user_id}")
            
            message = TextSendMessage(text=text)
            self.line_bot_api.push_message(user_id, message)
            logger.info(f"メッセージ送信完了: {user_id}")
            
        except LineBotApiError as e:
            logger.error(f"LINE API エラー: {e}")
            logger.error(f"エラー詳細 - user_id: {user_id}, message: {text[:100]}")
            
            # テスト環境でのエラーは無視
            if user_id.startswith('test_') or user_id == 'test_user':
                logger.info("テスト環境のため、LINE APIエラーを無視します")
                return
            raise
            
        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}")
            raise
    
    def save_message(self, message_id: str, user_id: str, message_type: str, 
                    content: str = None, file_path: str = None) -> dict:
        """メッセージをデータベースに保存"""
        try:
            # 既存メッセージチェック
            existing = Message.query.filter_by(line_message_id=message_id).first()
            if existing:
                logger.info(f"メッセージ {message_id} は既に保存済み")
                return existing.to_dict()
            
            # 新規メッセージ作成
            message = Message(
                line_message_id=message_id,
                user_id=user_id,
                message_type=message_type,
                content=content,
                file_path=file_path
            )
            
            # 簡易要約生成
            if message_type == 'text' and content:
                message.summary = self._summarize_text(content)
            elif message_type in ['image', 'video'] and file_path:
                message.summary = f"{message_type}ファイル: {os.path.basename(file_path)}"
            
            db.session.add(message)
            db.session.commit()
            
            logger.info(f"メッセージ保存完了: {message_id}")
            return message.to_dict()
            
        except Exception as e:
            logger.error(f"メッセージ保存エラー: {e}")
            db.session.rollback()
            raise
    
    def download_content(self, message_id: str, content_type: str) -> str:
        """LINEからファイルをダウンロード"""
        try:
            # ファイル保存パス生成
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            extension = self._get_extension(content_type)
            filename = f"{timestamp}_{message_id}{extension}"
            file_path = self.upload_dir / filename
            
            # LINEからコンテンツ取得
            message_content = self.line_bot_api.get_message_content(message_id)
            
            # ファイル保存
            with open(file_path, 'wb') as f:
                for chunk in message_content.iter_content():
                    f.write(chunk)
            
            logger.info(f"ファイルダウンロード完了: {file_path}")
            return str(file_path)
            
        except LineBotApiError as e:
            logger.error(f"LINE API エラー: {e}")
            raise
        except Exception as e:
            logger.error(f"ファイルダウンロードエラー: {e}")
            raise
    
    def _get_extension(self, content_type: str) -> str:
        """コンテンツタイプから拡張子を取得"""
        extensions = {
            'image': '.jpg',
            'video': '.mp4',
            'audio': '.m4a'
        }
        return extensions.get(content_type, '.bin')
    
    def _summarize_text(self, text: str) -> str:
        """テキストの簡易要約"""
        if len(text) <= 50:
            return f"短文: {text}"
        else:
            # 最初の50文字を要約として使用
            return f"長文: {text[:50]}..."
    
    def get_user_messages(self, user_id: str, limit: int = 10) -> list:
        """ユーザーの最新メッセージを取得"""
        try:
            messages = Message.query.filter_by(user_id=user_id)\
                           .order_by(Message.created_at.desc())\
                           .limit(limit).all()
            
            return [msg.to_dict() for msg in messages]
            
        except Exception as e:
            logger.error(f"ユーザーメッセージ取得エラー: {e}")
            return []
    
    def get_unprocessed_messages(self) -> list:
        """未処理メッセージの取得"""
        try:
            messages = Message.query.filter_by(processed=False)\
                           .order_by(Message.created_at.asc()).all()
            
            return [msg.to_dict() for msg in messages]
            
        except Exception as e:
            logger.error(f"未処理メッセージ取得エラー: {e}")
            return []