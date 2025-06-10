"""
バッチ処理システム
一定時間内のメッセージを蓄積し、統合して記事化
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from sqlalchemy import and_
from src.database import db, Message
# Imgurを使用するため、はてなフォトライフは不要
from src.services.hatena_service import HatenaService
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

@dataclass
class BatchMessage:
    """バッチ処理用メッセージ"""
    message_id: str
    user_id: str
    content: str
    message_type: str
    timestamp: datetime
    file_path: Optional[str] = None
    processed: bool = False

@dataclass
class BatchSession:
    """バッチセッション"""
    user_id: str
    start_time: datetime
    end_time: datetime
    messages: List[BatchMessage] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    texts: List[str] = field(default_factory=list)
    
    def add_message(self, message: BatchMessage):
        """メッセージを追加"""
        self.messages.append(message)
        
        if message.message_type == 'text' and message.content.strip():
            self.texts.append(message.content)
        elif message.message_type == 'image' and message.file_path:
            self.images.append(message.file_path)
    
    def has_content(self) -> bool:
        """処理可能なコンテンツがあるかチェック"""
        return len(self.texts) > 0 or len(self.images) > 0
    
    def get_summary(self) -> str:
        """セッション要約を取得"""
        return f"テキスト: {len(self.texts)}件, 画像: {len(self.images)}件"

class BatchProcessor:
    """バッチ処理システム"""
    
    def __init__(self, batch_interval_minutes: int = 15):
        self.batch_interval_minutes = batch_interval_minutes
        # Imgurを使用するため、はてなフォトライフは不要
        self.hatena_service = HatenaService()
        self.gemini_service = GeminiService()
        
        # バッチセッション管理
        self.active_sessions: Dict[str, BatchSession] = {}
        self.processing = False
        
        logger.info(f"バッチ処理システム初期化完了 (間隔: {batch_interval_minutes}分)")
    
    def start_batch_processing(self):
        """バッチ処理を開始"""
        logger.info("バッチ処理システム開始")
        self.processing = True
        
        # 定期実行のループ
        asyncio.create_task(self._batch_loop())
    
    def stop_batch_processing(self):
        """バッチ処理を停止"""
        logger.info("バッチ処理システム停止")
        self.processing = False
    
    async def _batch_loop(self):
        """バッチ処理のメインループ"""
        while self.processing:
            try:
                await self._process_batch_cycle()
                # 次のサイクルまで待機
                await asyncio.sleep(self.batch_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"バッチ処理サイクルエラー: {e}")
                await asyncio.sleep(60)  # エラー時は1分待機
    
    async def _process_batch_cycle(self):
        """1回のバッチ処理サイクル"""
        logger.info("バッチ処理サイクル開始")
        
        # 処理対象時間範囲を設定
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=self.batch_interval_minutes)
        
        logger.info(f"処理対象期間: {start_time} 〜 {end_time}")
        
        # 対象メッセージを取得
        messages = self._get_messages_in_timeframe(start_time, end_time)
        
        if not messages:
            logger.info("処理対象メッセージなし")
            return
        
        logger.info(f"処理対象メッセージ: {len(messages)}件")
        
        # ユーザー別にグループ化
        user_messages = self._group_messages_by_user(messages)
        
        # ユーザー別に処理
        for user_id, user_msg_list in user_messages.items():
            try:
                await self._process_user_messages(user_id, user_msg_list, start_time, end_time)
            except Exception as e:
                logger.error(f"ユーザー {user_id} の処理エラー: {e}")
        
        logger.info("バッチ処理サイクル完了")
    
    def _get_messages_in_timeframe(self, start_time: datetime, end_time: datetime) -> List[Message]:
        """指定時間範囲のメッセージを取得"""
        try:
            messages = db.session.query(Message).filter(
                and_(
                    Message.created_at >= start_time,
                    Message.created_at <= end_time,
                    Message.processed_by_batch == False  # バッチ未処理
                )
            ).order_by(Message.created_at.asc()).all()
            
            return messages
            
        except Exception as e:
            logger.error(f"メッセージ取得エラー: {e}")
            return []
    
    def _group_messages_by_user(self, messages: List[Message]) -> Dict[str, List[Message]]:
        """メッセージをユーザー別にグループ化"""
        user_messages = defaultdict(list)
        
        for message in messages:
            user_messages[message.user_id].append(message)
        
        return dict(user_messages)
    
    async def _process_user_messages(self, user_id: str, messages: List[Message], 
                                   start_time: datetime, end_time: datetime):
        """ユーザーのメッセージを処理"""
        logger.info(f"ユーザー {user_id} のメッセージ処理開始: {len(messages)}件")
        
        # バッチセッション作成
        session = BatchSession(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # メッセージをセッションに追加
        for message in messages:
            batch_message = BatchMessage(
                message_id=message.line_message_id,
                user_id=message.user_id,
                content=message.content or "",
                message_type=message.message_type,
                timestamp=message.created_at,
                file_path=message.file_path
            )
            session.add_message(batch_message)
        
        # コンテンツがない場合はスキップ
        if not session.has_content():
            logger.info(f"ユーザー {user_id}: 処理可能コンテンツなし")
            self._mark_messages_as_processed(messages)
            return
        
        logger.info(f"ユーザー {user_id}: {session.get_summary()}")
        
        try:
            # 記事を生成・投稿
            article_result = await self._create_and_publish_article(session)
            
            if article_result.get('success'):
                logger.info(f"ユーザー {user_id}: 記事投稿成功")
                
                # LINEに結果通知
                await self._send_success_notification(user_id, article_result)
            else:
                logger.error(f"ユーザー {user_id}: 記事投稿失敗 - {article_result.get('error')}")
                await self._send_error_notification(user_id, article_result.get('error'))
            
            # メッセージを処理済みとしてマーク
            self._mark_messages_as_processed(messages)
            
        except Exception as e:
            logger.error(f"ユーザー {user_id} の記事処理エラー: {e}")
            await self._send_error_notification(user_id, str(e))
    
    async def _create_and_publish_article(self, session: BatchSession) -> Dict:
        """記事を作成して投稿"""
        try:
            # 1. 画像をImgurにアップロード
            image_tags = []
            if session.images:
                logger.info(f"画像アップロード開始: {len(session.images)}枚")
                
                for image_path in session.images:
                    try:
                        import time
                        import sys
                        sys.path.append('/home/moto/line-gemini-hatena-integration')
                        from src.mcp_servers.imgur_server_fastmcp import upload_image
                        
                        # Imgurにアップロード  
                        import asyncio
                        upload_result = asyncio.run(upload_image(
                            image_path=image_path,
                            title=f"Image_{int(time.time())}",
                            description="LINE Bot経由でアップロード",
                            privacy="hidden"
                        ))
                        
                        if upload_result.get('success'):
                            # Imgur URLを使用してHTMLタグを作成
                            image_url = upload_result.get('url')
                            image_tag = f'<div style="text-align: center; margin: 20px 0;"><img src="{image_url}" alt="アップロード画像" style="max-width: 80%; height: auto; border: 1px solid #ddd; border-radius: 8px;" /></div>'
                            image_tags.append(image_tag)
                            logger.info(f"画像アップロード成功: {image_url}")
                        else:
                            logger.error(f"画像アップロード失敗: {upload_result.get('error')}")
                            
                    except Exception as e:
                        logger.error(f"Imgur upload error: {e}")
            
            # 2. テキストと画像を統合してコンテンツ作成
            combined_content = self._create_combined_content(session.texts, image_tags)
            
            # 3. AIで記事を生成
            article_content = await self._generate_article_with_ai(combined_content, session)
            
            if not article_content:
                return {'success': False, 'error': '記事生成に失敗しました'}
            
            # 4. はてなブログに投稿
            publish_result = self.hatena_service.publish_article(
                title=article_content.get('title', f"ライフログ {session.start_time.strftime('%Y/%m/%d %H:%M')}"),
                content=article_content.get('content', ''),
                categories=article_content.get('categories', ['ライフログ']),
                draft=False
            )
            
            if publish_result.get('success'):
                return {
                    'success': True,
                    'title': article_content.get('title'),
                    'url': publish_result.get('url'),
                    'image_count': len(image_tags),
                    'text_count': len(session.texts)
                }
            else:
                return {'success': False, 'error': publish_result.get('error')}
                
        except Exception as e:
            logger.error(f"記事作成・投稿エラー: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_combined_content(self, texts: List[str], image_tags: List[str]) -> str:
        """テキストと画像タグを統合したコンテンツを作成"""
        content_parts = []
        
        # テキストを時系列順に追加
        for text in texts:
            if text.strip():
                content_parts.append(text.strip())
        
        # 画像タグを追加
        if image_tags:
            content_parts.append("\n## 写真\n")
            for tag in image_tags:
                if tag:
                    content_parts.append(tag)
        
        return "\n\n".join(content_parts)
    
    async def _generate_article_with_ai(self, content: str, session: BatchSession) -> Optional[Dict]:
        """AIを使って記事を生成"""
        try:
            # プロンプトを作成
            prompt = f"""
以下のライフログから、読みやすいブログ記事を作成してください。

## ライフログデータ
期間: {session.start_time.strftime('%Y年%m月%d日 %H:%M')} - {session.end_time.strftime('%H:%M')}
内容:
{content}

## 記事作成要件
- 自然で読みやすい文章にしてください
- 画像がある場合は適切な位置に配置してください
- タイトルは内容を適切に表現してください
- カテゴリは内容に基づいて設定してください

JSON形式で以下のように出力してください:
{{
    "title": "記事タイトル",
    "content": "記事本文（Markdown形式）",
    "categories": ["カテゴリ1", "カテゴリ2"]
}}
"""
            
            # Geminiで記事生成
            response = await self.gemini_service.generate_content(prompt)
            
            if response.get('success'):
                # JSONレスポンスをパース
                import json
                try:
                    article_data = json.loads(response.get('content', '{}'))
                    return article_data
                except json.JSONDecodeError:
                    # JSON形式でない場合は直接使用
                    return {
                        'title': f"ライフログ {session.start_time.strftime('%Y/%m/%d')}",
                        'content': response.get('content', ''),
                        'categories': ['ライフログ']
                    }
            else:
                logger.error(f"AI記事生成エラー: {response.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"AI記事生成エラー: {e}")
            return None
    
    def _mark_messages_as_processed(self, messages: List[Message]):
        """メッセージを処理済みとしてマーク"""
        try:
            for message in messages:
                message.processed_by_batch = True
                message.batch_processed_at = datetime.now()
            
            db.session.commit()
            logger.info(f"メッセージ処理済みマーク完了: {len(messages)}件")
            
        except Exception as e:
            logger.error(f"メッセージ処理済みマークエラー: {e}")
            db.session.rollback()
    
    async def _send_success_notification(self, user_id: str, result: Dict):
        """成功通知をLINEに送信"""
        try:
            from src.services.line_service import LineService
            line_service = LineService()
            
            message = f"""✅ ライフログ記事を投稿しました！

📝 タイトル: {result.get('title', 'N/A')}
🔗 URL: {result.get('url', 'N/A')}
📊 統合データ: テキスト{result.get('text_count', 0)}件、画像{result.get('image_count', 0)}枚

次のバッチ処理まで約{self.batch_interval_minutes}分です。"""
            
            line_service.send_message(user_id, message)
            
        except Exception as e:
            logger.error(f"成功通知送信エラー: {e}")
    
    async def _send_error_notification(self, user_id: str, error_message: str):
        """エラー通知をLINEに送信"""
        try:
            from src.services.line_service import LineService
            line_service = LineService()
            
            message = f"""❌ ライフログ記事の投稿でエラーが発生しました

エラー内容: {error_message}

次のバッチ処理で再試行されます。"""
            
            line_service.send_message(user_id, message)
            
        except Exception as e:
            logger.error(f"エラー通知送信エラー: {e}")

# 使用例とテスト
if __name__ == "__main__":
    import sys
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test_batch_processor():
        processor = BatchProcessor(batch_interval_minutes=1)  # テスト用に1分間隔
        
        # テスト実行
        await processor._process_batch_cycle()
    
    # テスト実行
    asyncio.run(test_batch_processor())
