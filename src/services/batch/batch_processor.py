"""
バッチ処理システム
一定時間内のメッセージを蓄積して統合記事を作成
"""

import asyncio
import threading
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

@dataclass
class BatchMessage:
    """バッチ処理用メッセージ"""
    message_id: str
    user_id: str
    message_type: str  # 'text' or 'image'
    content: str = ""
    file_path: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    processed: bool = False

@dataclass
class BatchData:
    """バッチデータ"""
    user_id: str
    messages: List[BatchMessage] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    
    def add_message(self, message: BatchMessage):
        """メッセージを追加"""
        self.messages.append(message)
        logger.info(f"バッチにメッセージ追加: {message.message_type} (総数: {len(self.messages)})")
    
    def get_text_messages(self) -> List[BatchMessage]:
        """テキストメッセージのみを取得"""
        return [msg for msg in self.messages if msg.message_type == 'text']
    
    def get_image_messages(self) -> List[BatchMessage]:
        """画像メッセージのみを取得"""
        return [msg for msg in self.messages if msg.message_type == 'image']
    
    def is_expired(self, interval_minutes: int = 1) -> bool:
        """バッチが期限切れかチェック"""
        expiry_time = self.start_time + timedelta(minutes=interval_minutes)
        return datetime.now() > expiry_time
    
    def has_content(self) -> bool:
        """コンテンツが存在するかチェック"""
        return len(self.messages) > 0

class BatchProcessor:
    """バッチ処理システム"""
    
    def __init__(self, interval_minutes: int = 1):
        self.interval_minutes = interval_minutes
        self.batch_data: Dict[str, BatchData] = {}  # user_id -> BatchData
        self.processing_lock = threading.Lock()
        self.is_running = False
        self.processor_thread = None
        
        logger.info(f"バッチ処理システム初期化 (間隔: {interval_minutes}分)")
    
    def start(self):
        """バッチ処理を開始"""
        if self.is_running:
            logger.warning("バッチ処理は既に実行中です")
            return
        
        self.is_running = True
        self.processor_thread = threading.Thread(target=self._batch_loop, daemon=True)
        self.processor_thread.start()
        logger.info("バッチ処理スレッド開始")
    
    def stop(self):
        """バッチ処理を停止"""
        self.is_running = False
        if self.processor_thread:
            self.processor_thread.join(timeout=5)
        logger.info("バッチ処理停止")
    
    def add_message(self, user_id: str, message_id: str, message_type: str, 
                   content: str = "", file_path: Optional[str] = None):
        """メッセージをバッチに追加"""
        with self.processing_lock:
            # ユーザーのバッチデータが存在しない場合は作成
            if user_id not in self.batch_data:
                self.batch_data[user_id] = BatchData(user_id=user_id)
            
            # メッセージを作成してバッチに追加
            message = BatchMessage(
                message_id=message_id,
                user_id=user_id,
                message_type=message_type,
                content=content,
                file_path=file_path
            )
            
            self.batch_data[user_id].add_message(message)
            
            logger.info(f"メッセージをバッチに追加: {user_id} - {message_type}")
    
    def _batch_loop(self):
        """バッチ処理のメインループ"""
        logger.info("バッチ処理ループ開始")
        
        while self.is_running:
            try:
                # 期限切れのバッチを処理
                expired_batches = self._get_expired_batches()
                
                for user_id, batch_data in expired_batches:
                    if batch_data.has_content():
                        logger.info(f"期限切れバッチを処理開始: {user_id} ({len(batch_data.messages)}件)")
                        self._process_batch(user_id, batch_data)
                    
                    # 処理済みバッチを削除
                    with self.processing_lock:
                        if user_id in self.batch_data:
                            del self.batch_data[user_id]
                
                # 10秒間隔でチェック
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"バッチ処理ループエラー: {e}")
                time.sleep(10)
    
    def _get_expired_batches(self) -> List[tuple]:
        """期限切れのバッチを取得"""
        expired = []
        
        with self.processing_lock:
            for user_id, batch_data in list(self.batch_data.items()):
                if batch_data.is_expired(self.interval_minutes):
                    expired.append((user_id, batch_data))
        
        return expired
    
    def _process_batch(self, user_id: str, batch_data: BatchData):
        """バッチを処理して記事を作成"""
        try:
            # Imgur を使用
            logger.info("Imgur画像アップロードを使用")
            
            from src.agents.content_creation_agent_fixed import ContentCreationAgent
            
            logger.info(f"バッチ処理開始: {user_id}")
            
            # 画像をImgurにアップロード
            image_tags = []
            
            for image_msg in batch_data.get_image_messages():
                if image_msg.file_path and os.path.exists(image_msg.file_path):
                    try:
                        import asyncio
                        import sys
                        sys.path.append('/home/moto/line-gemini-hatena-integration')
                        from src.mcp_servers.imgur_server_fastmcp import upload_image
                        
                        # 非同期でImgurにアップロード
                        upload_result = asyncio.run(upload_image(
                            image_path=image_msg.file_path,
                            title=f"Image_{image_msg.message_id}",
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
            
            # テキストメッセージを結合
            text_messages = batch_data.get_text_messages()
            combined_text = ""
            
            if text_messages:
                combined_text = "\\n".join([msg.content for msg in text_messages])
            
            # AI Agentで統合記事を作成
            agent_messages = [{
                "content": self._create_integrated_content(combined_text, image_tags),
                "type": "text",
                "batch_info": {
                    "text_count": len(text_messages),
                    "image_count": len(image_tags),
                    "start_time": batch_data.start_time.isoformat()
                }
            }]
            
            # 非同期でAI Agentを実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                agent = ContentCreationAgent()
                loop.run_until_complete(agent.initialize())
                
                result = loop.run_until_complete(agent.process_message(
                    user_id=user_id,
                    line_message_id=f"batch_{int(time.time())}",
                    messages=agent_messages
                ))
                
                logger.info(f"バッチ処理完了: {user_id} - {result}")
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"バッチ処理エラー: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_integrated_content(self, text_content: str, image_tags: List[str]) -> str:
        """統合コンテンツを作成"""
        content_parts = []
        
        # テキストがある場合は追加
        if text_content.strip():
            content_parts.append(text_content.strip())
        
        # 画像タグがある場合は追加
        if image_tags:
            content_parts.append("\\n画像:")
            for i, tag in enumerate(image_tags, 1):
                content_parts.append(f"{tag}")
        
        # バッチ処理の指示を追加
        integrated_content = "\\n".join(content_parts)
        
        instruction = f"""
以下の内容で統合記事を作成してください：

{integrated_content}

※この内容は複数のメッセージから統合されたものです。
自然で読みやすい記事として整理してブログ投稿してください。
画像がある場合は適切な位置に配置してください。
        """
        
        return instruction.strip()
    
    def get_status(self) -> Dict[str, Any]:
        """バッチ処理の状態を取得"""
        with self.processing_lock:
            return {
                "is_running": self.is_running,
                "interval_minutes": self.interval_minutes,
                "active_batches": len(self.batch_data),
                "batch_details": {
                    user_id: {
                        "message_count": len(batch.messages),
                        "start_time": batch.start_time.isoformat(),
                        "text_count": len(batch.get_text_messages()),
                        "image_count": len(batch.get_image_messages())
                    }
                    for user_id, batch in self.batch_data.items()
                }
            }
    
    def force_process_user(self, user_id: str) -> bool:
        """指定ユーザーのバッチを強制処理"""
        with self.processing_lock:
            if user_id in self.batch_data:
                batch_data = self.batch_data[user_id]
                if batch_data.has_content():
                    logger.info(f"強制バッチ処理: {user_id}")
                    self._process_batch(user_id, batch_data)
                    del self.batch_data[user_id]
                    return True
        return False

# グローバルバッチプロセッサー
batch_processor = None

def get_batch_processor() -> BatchProcessor:
    """バッチプロセッサーのシングルトンインスタンスを取得"""
    global batch_processor
    if batch_processor is None:
        interval = int(os.getenv('BATCH_INTERVAL_MINUTES', '1'))
        batch_processor = BatchProcessor(interval_minutes=interval)
        batch_processor.start()
    return batch_processor

def cleanup_batch_processor():
    """バッチプロセッサーのクリーンアップ"""
    global batch_processor
    if batch_processor:
        batch_processor.stop()
        batch_processor = None

# アプリケーション終了時のクリーンアップ
import atexit
atexit.register(cleanup_batch_processor)
