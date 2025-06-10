"""
LangGraph エージェント状態定義
LINE→Gemini→Hatena 統合フローの状態管理
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class ProcessingStage(Enum):
    """処理段階の定義"""
    RECEIVED = "received"           # LINE メッセージ受信
    ANALYZING = "analyzing"         # Gemini で分析中
    GENERATING = "generating"       # 記事生成中
    UPLOADING_IMAGES = "uploading_images"  # 画像アップロード中
    PUBLISHING = "publishing"       # はてなブログ投稿中
    NOTIFYING = "notifying"        # LINE 通知中
    COMPLETED = "completed"         # 完了
    FAILED = "failed"              # 失敗

class MessageType(Enum):
    """メッセージタイプ"""
    TEXT = "text"
    IMAGE = "image" 
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"

@dataclass
class LineMessage:
    """LINE メッセージデータ"""
    message_id: str
    user_id: str
    message_type: MessageType
    content: Optional[str] = None
    file_path: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class GeminiAnalysis:
    """Gemini 分析結果"""
    title: str
    content: str
    summary: str
    tags: List[str]
    analysis_type: str  # text/image/video
    confidence: float = 0.0
    processing_time: float = 0.0

@dataclass
class ImgurUpload:
    """Imgur アップロード結果"""
    imgur_url: str
    imgur_id: str
    delete_hash: str
    title: str
    success: bool = True
    error: Optional[str] = None

@dataclass
class HatenaBlogPost:
    """はてなブログ投稿結果"""
    article_id: str
    url: str
    title: str
    tags: List[str]
    category: str
    draft: bool = False
    success: bool = True
    error: Optional[str] = None

@dataclass
class ProcessingError:
    """処理エラー情報"""
    stage: ProcessingStage
    error_type: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class AgentState:
    """LangGraph エージェントの状態"""
    
    # 基本情報
    session_id: str
    user_id: str
    stage: ProcessingStage = ProcessingStage.RECEIVED
    
    # 入力データ
    line_message: Optional[LineMessage] = None
    
    # 処理結果
    gemini_analysis: Optional[GeminiAnalysis] = None
    imgur_uploads: List[ImgurUpload] = field(default_factory=list)
    hatena_post: Optional[HatenaBlogPost] = None
    
    # 処理制御
    retry_count: int = 0
    max_retries: int = 3
    errors: List[ProcessingError] = field(default_factory=list)
    
    # メタデータ
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    processing_time: float = 0.0
    
    # 設定
    config: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, stage: ProcessingStage, error_type: str, error_message: str):
        """エラーを追加"""
        error = ProcessingError(
            stage=stage,
            error_type=error_type,
            error_message=error_message,
            retry_count=self.retry_count
        )
        self.errors.append(error)
        self.updated_at = datetime.utcnow()
    
    def can_retry(self) -> bool:
        """リトライ可能かチェック"""
        return self.retry_count < self.max_retries
    
    def increment_retry(self):
        """リトライカウンタを増加"""
        self.retry_count += 1
        self.updated_at = datetime.utcnow()
    
    def update_stage(self, new_stage: ProcessingStage):
        """処理段階を更新"""
        self.stage = new_stage
        self.updated_at = datetime.utcnow()
    
    def set_line_message(self, message_id: str, user_id: str, message_type: str, 
                        content: str = None, file_path: str = None):
        """LINE メッセージを設定"""
        self.line_message = LineMessage(
            message_id=message_id,
            user_id=user_id,
            message_type=MessageType(message_type),
            content=content,
            file_path=file_path
        )
        self.user_id = user_id
        self.updated_at = datetime.utcnow()
    
    def set_gemini_analysis(self, title: str, content: str, summary: str, 
                           tags: List[str], analysis_type: str, confidence: float = 0.0):
        """Gemini 分析結果を設定"""
        self.gemini_analysis = GeminiAnalysis(
            title=title,
            content=content,
            summary=summary,
            tags=tags,
            analysis_type=analysis_type,
            confidence=confidence
        )
        self.updated_at = datetime.utcnow()
    
    def add_imgur_upload(self, imgur_url: str, imgur_id: str, delete_hash: str, 
                        title: str, success: bool = True, error: str = None):
        """Imgur アップロード結果を追加"""
        upload = ImgurUpload(
            imgur_url=imgur_url,
            imgur_id=imgur_id,
            delete_hash=delete_hash,
            title=title,
            success=success,
            error=error
        )
        self.imgur_uploads.append(upload)
        self.updated_at = datetime.utcnow()
    
    def set_hatena_post(self, article_id: str, url: str, title: str, 
                       tags: List[str], category: str, draft: bool = False,
                       success: bool = True, error: str = None):
        """はてなブログ投稿結果を設定"""
        self.hatena_post = HatenaBlogPost(
            article_id=article_id,
            url=url,
            title=title,
            tags=tags,
            category=category,
            draft=draft,
            success=success,
            error=error
        )
        self.updated_at = datetime.utcnow()
    
    def get_summary(self) -> Dict[str, Any]:
        """状態サマリーを取得"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "stage": self.stage.value,
            "has_line_message": self.line_message is not None,
            "has_gemini_analysis": self.gemini_analysis is not None,
            "imgur_uploads_count": len(self.imgur_uploads),
            "has_hatena_post": self.hatena_post is not None,
            "error_count": len(self.errors),
            "retry_count": self.retry_count,
            "processing_time": self.processing_time,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "stage": self.stage.value,
            "line_message": self.line_message.__dict__ if self.line_message else None,
            "gemini_analysis": self.gemini_analysis.__dict__ if self.gemini_analysis else None,
            "imgur_uploads": [upload.__dict__ for upload in self.imgur_uploads],
            "hatena_post": self.hatena_post.__dict__ if self.hatena_post else None,
            "retry_count": self.retry_count,
            "errors": [error.__dict__ for error in self.errors],
            "processing_time": self.processing_time,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "config": self.config
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """辞書から状態を復元"""
        state = cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            stage=ProcessingStage(data["stage"]),
            retry_count=data.get("retry_count", 0),
            processing_time=data.get("processing_time", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            config=data.get("config", {})
        )
        
        # LINE メッセージ復元
        if data.get("line_message"):
            msg_data = data["line_message"]
            state.line_message = LineMessage(
                message_id=msg_data["message_id"],
                user_id=msg_data["user_id"],
                message_type=MessageType(msg_data["message_type"]),
                content=msg_data.get("content"),
                file_path=msg_data.get("file_path"),
                timestamp=datetime.fromisoformat(msg_data["timestamp"])
            )
        
        # Gemini 分析結果復元
        if data.get("gemini_analysis"):
            analysis_data = data["gemini_analysis"]
            state.gemini_analysis = GeminiAnalysis(**analysis_data)
        
        # Imgur アップロード結果復元
        for upload_data in data.get("imgur_uploads", []):
            state.imgur_uploads.append(ImgurUpload(**upload_data))
        
        # はてなブログ投稿結果復元
        if data.get("hatena_post"):
            post_data = data["hatena_post"]
            state.hatena_post = HatenaBlogPost(**post_data)
        
        # エラー情報復元
        for error_data in data.get("errors", []):
            error = ProcessingError(
                stage=ProcessingStage(error_data["stage"]),
                error_type=error_data["error_type"],
                error_message=error_data["error_message"],
                timestamp=datetime.fromisoformat(error_data["timestamp"]),
                retry_count=error_data["retry_count"],
                max_retries=error_data["max_retries"]
            )
            state.errors.append(error)
        
        return state
