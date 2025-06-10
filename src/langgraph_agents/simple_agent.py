"""
簡易ブログ生成エージェント
LangGraphなしで基本的なフロー処理を実現
"""

import asyncio
import logging
import uuid
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class ProcessingStage(Enum):
    """処理段階の定義"""
    RECEIVED = "received"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    UPLOADING_IMAGES = "uploading_images"
    PUBLISHING = "publishing"
    NOTIFYING = "notifying"
    COMPLETED = "completed"
    FAILED = "failed"

class SimpleAgentState:
    """簡易エージェント状態"""
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.stage = ProcessingStage.RECEIVED
        self.errors = []
        self.results = {}
        self.processing_time = 0.0
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def update_stage(self, new_stage: ProcessingStage):
        self.stage = new_stage
        self.updated_at = datetime.utcnow()
    
    def add_error(self, error_message: str):
        self.errors.append({
            "stage": self.stage.value,
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.updated_at = datetime.utcnow()
    
    def set_result(self, key: str, value: Any):
        self.results[key] = value
        self.updated_at = datetime.utcnow()

class SimpleBlogAgent:
    """簡易ブログ生成エージェント"""
    
    def __init__(self):
        self.active_sessions = {}
    
    async def process_line_message(self, message_id: str, user_id: str, 
                                 message_type: str, content: str = None, 
                                 file_path: str = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """LINE メッセージを処理してブログ記事を生成・投稿"""
        session_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            logger.info(f"簡易エージェント処理開始: {session_id}")
            
            # 状態初期化
            state = SimpleAgentState(session_id, user_id)
            self.active_sessions[session_id] = state
            
            # 1. メッセージ受信処理
            await self._receive_message(state, message_id, user_id, message_type, content, file_path)
            
            # 2. Gemini分析・記事生成
            await self._analyze_and_generate(state, message_type, content, file_path, config or {})
            
            # 3. 画像アップロード（必要時）
            await self._upload_images_if_needed(state, message_type, file_path)
            
            # 4. はてなブログ投稿
            await self._publish_to_hatena(state, config or {})
            
            # 5. ユーザー通知
            await self._notify_user(state)
            
            # 処理完了
            state.update_stage(ProcessingStage.COMPLETED)
            state.processing_time = time.time() - start_time
            
            logger.info(f"簡易エージェント処理完了: {session_id} ({state.processing_time:.2f}秒)")
            
            return {
                "success": True,
                "session_id": session_id,
                "stage": state.stage.value,
                "processing_time": state.processing_time,
                "blog_post": state.results.get("hatena_post"),
                "errors": state.errors
            }
            
        except Exception as e:
            logger.error(f"簡易エージェント処理エラー: {session_id} - {e}")
            
            if session_id in self.active_sessions:
                state = self.active_sessions[session_id]
                state.update_stage(ProcessingStage.FAILED)
                state.add_error(str(e))
                state.processing_time = time.time() - start_time
            
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e),
                "stage": "failed"
            }
    
    async def _receive_message(self, state: SimpleAgentState, message_id: str, user_id: str, 
                             message_type: str, content: str, file_path: str):
        """メッセージ受信処理"""
        try:
            state.update_stage(ProcessingStage.RECEIVED)
            logger.info(f"メッセージ受信: タイプ={message_type}")
            
            state.set_result("message", {
                "message_id": message_id,
                "user_id": user_id,
                "message_type": message_type,
                "content": content,
                "file_path": file_path
            })
            
        except Exception as e:
            state.add_error(f"メッセージ受信エラー: {e}")
            raise
    
    async def _analyze_and_generate(self, state: SimpleAgentState, message_type: str, 
                                  content: str, file_path: str, config: Dict[str, Any]):
        """分析・記事生成処理"""
        try:
            state.update_stage(ProcessingStage.ANALYZING)
            logger.info("Gemini分析・記事生成開始")
            
            from src.services.gemini_service import GeminiService
            gemini_service = GeminiService()
            
            # メッセージタイプに応じた処理
            if message_type == "text":
                result = gemini_service.generate_article_from_content(
                    content=content,
                    style=config.get("article_style", "blog")
                )
            elif message_type == "image" and file_path:
                # 画像分析 + 記事生成
                analysis = gemini_service.analyze_image(
                    file_path, 
                    "この画像について詳しく分析し、ブログ記事のネタを提供してください"
                )
                if analysis:
                    result = gemini_service.generate_article_from_content(
                        content=analysis,
                        style=config.get("article_style", "blog")
                    )
                else:
                    raise Exception("画像分析に失敗しました")
            else:
                # その他のファイルタイプ
                result = gemini_service.generate_article_from_content(
                    content=f"{message_type}ファイルが投稿されました",
                    style=config.get("article_style", "blog")
                )
            
            if not result:
                raise Exception("記事生成に失敗しました")
            
            state.set_result("article", result)
            logger.info(f"記事生成成功: {result.get('title', 'No title')}")
            
        except Exception as e:
            state.add_error(f"分析・記事生成エラー: {e}")
            raise
    
    async def _upload_images_if_needed(self, state: SimpleAgentState, message_type: str, file_path: str):
        """画像アップロード処理"""
        try:
            if message_type != "image" or not file_path:
                logger.info("画像アップロード不要")
                return
            
            state.update_stage(ProcessingStage.UPLOADING_IMAGES)
            logger.info("画像アップロード開始")
            
            from src.services.imgur_service import ImgurService
            imgur_service = ImgurService()
            
            article = state.results.get("article", {})
            
            result = imgur_service.upload_image(
                image_path=file_path,
                title=article.get("title", "LINE画像"),
                description=article.get("summary", ""),
                privacy="hidden"
            )
            
            if result and result.get("success"):
                state.set_result("imgur_upload", result)
                
                # 記事に画像URLを追加
                if article:
                    img_url = result.get("imgur_url")
                    article["content"] += f"\n\n![画像]({img_url})"
                    state.set_result("article", article)
                
                logger.info(f"画像アップロード成功: {result.get('imgur_url')}")
            else:
                logger.warning(f"画像アップロード失敗: {result.get('error') if result else 'Unknown error'}")
            
        except Exception as e:
            state.add_error(f"画像アップロードエラー: {e}")
            # 画像アップロードは非致命的なので処理を続行
            logger.warning(f"画像アップロードエラー（処理続行）: {e}")
    
    async def _publish_to_hatena(self, state: SimpleAgentState, config: Dict[str, Any]):
        """はてなブログ投稿処理"""
        try:
            state.update_stage(ProcessingStage.PUBLISHING)
            logger.info("はてなブログ投稿開始")
            
            article = state.results.get("article")
            if not article:
                raise Exception("投稿する記事がありません")
            
            from src.services.hatena_service import HatenaService
            hatena_service = HatenaService()
            
            result = hatena_service.publish_article(
                title=article.get("title", "AI生成記事"),
                content=article.get("content", ""),
                tags=article.get("tags", ["AI生成", "LINE Bot"]),
                category=config.get("blog_category", "日記"),
                draft=config.get("publish_as_draft", False)
            )
            
            if not result:
                raise Exception("はてなブログ投稿に失敗しました")
            
            state.set_result("hatena_post", {
                "title": article.get("title"),
                "url": result.get("url"),
                "tags": article.get("tags"),
                "success": True
            })
            
            logger.info(f"はてなブログ投稿成功: {result.get('url')}")
            
        except Exception as e:
            state.add_error(f"はてなブログ投稿エラー: {e}")
            raise
    
    async def _notify_user(self, state: SimpleAgentState):
        """ユーザー通知処理"""
        try:
            state.update_stage(ProcessingStage.NOTIFYING)
            logger.info("ユーザー通知開始")
            
            from src.services.line_service import LineService
            line_service = LineService()
            
            hatena_post = state.results.get("hatena_post")
            if hatena_post and hatena_post.get("success"):
                message = f"""🎉 ブログ記事が投稿されました！

📝 タイトル: {hatena_post.get('title', '')}
🔗 URL: {hatena_post.get('url', '')}
🏷️ タグ: {', '.join(hatena_post.get('tags', []))}
⏱️ 処理時間: {state.processing_time:.1f}秒

記事をお楽しみください！"""
            else:
                message = "記事の投稿処理が完了しましたが、詳細を確認できませんでした。"
            
            line_service.send_message(state.user_id, message)
            logger.info("ユーザー通知完了")
            
        except Exception as e:
            state.add_error(f"ユーザー通知エラー: {e}")
            # 通知は非致命的なので処理を続行
            logger.warning(f"ユーザー通知エラー（処理続行）: {e}")
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッション状態取得"""
        if session_id in self.active_sessions:
            state = self.active_sessions[session_id]
            return {
                "session_id": session_id,
                "user_id": state.user_id,
                "stage": state.stage.value,
                "processing_time": state.processing_time,
                "errors": state.errors,
                "results": state.results,
                "created_at": state.created_at.isoformat(),
                "updated_at": state.updated_at.isoformat()
            }
        return None
    
    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """アクティブセッション一覧取得"""
        sessions = []
        for session_id, state in self.active_sessions.items():
            sessions.append({
                "session_id": session_id,
                "user_id": state.user_id,
                "stage": state.stage.value,
                "created_at": state.created_at.isoformat(),
                "updated_at": state.updated_at.isoformat()
            })
        return sessions

# シングルトンインスタンス
_simple_agent_instance = None

def get_simple_agent() -> SimpleBlogAgent:
    """簡易ブログ生成エージェントのシングルトンインスタンスを取得"""
    global _simple_agent_instance
    if _simple_agent_instance is None:
        _simple_agent_instance = SimpleBlogAgent()
    return _simple_agent_instance

async def process_line_message_simple(message_id: str, user_id: str, 
                                    message_type: str, content: str = None,
                                    file_path: str = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """簡易LINE メッセージ処理エントリーポイント"""
    agent = get_simple_agent()
    return await agent.process_line_message(
        message_id=message_id,
        user_id=user_id,
        message_type=message_type,
        content=content,
        file_path=file_path,
        config=config
    )
