"""
データベース設定とモデル定義
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Message(db.Model):
    """LINEメッセージテーブル"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    line_message_id = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.String(255), nullable=False)
    message_type = db.Column(db.String(50), nullable=False)  # text, image, video
    content = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    
    # バッチ処理用フィールド
    processed_by_batch = db.Column(db.Boolean, default=False)
    batch_processed_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'line_message_id': self.line_message_id,
            'user_id': self.user_id,
            'message_type': self.message_type,
            'content': self.content,
            'file_path': self.file_path,
            'summary': self.summary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed': self.processed,
            'processed_by_batch': self.processed_by_batch,
            'batch_processed_at': self.batch_processed_at.isoformat() if self.batch_processed_at else None
        }

class Article(db.Model):
    """生成記事テーブル（フェイズ2対応）"""
    __tablename__ = 'articles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    tags = db.Column(db.Text)  # JSON形式で保存
    source_messages = db.Column(db.Text)  # メッセージIDのJSON配列
    gemini_prompt = db.Column(db.Text)
    gemini_response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    published = db.Column(db.Boolean, default=False)
    hatena_entry_id = db.Column(db.String(255))
    hatena_url = db.Column(db.String(500))
    published_at = db.Column(db.DateTime)
    
    # フェイズ2: 品質向上管理
    status = db.Column(db.String(50), default='draft')  # draft, enhanced, image_added, affiliate_added, completed
    enhancement_level = db.Column(db.Integer, default=0)
    last_enhanced_at = db.Column(db.DateTime)
    
    # メディア関連
    image_paths = db.Column(db.Text)  # JSON形式で保存
    video_path = db.Column(db.String(500))
    thumbnail_path = db.Column(db.String(500))
    
    def get_tags_list(self):
        """タグをリストとして取得"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except:
                return []
        return []
    
    def set_tags_list(self, tags_list):
        """タグをJSON形式で保存"""
        self.tags = json.dumps(tags_list, ensure_ascii=False)
    
    def get_source_messages_list(self):
        """ソースメッセージIDをリストとして取得"""
        if self.source_messages:
            try:
                return json.loads(self.source_messages)
            except:
                return []
        return []
    
    def set_source_messages_list(self, message_ids):
        """ソースメッセージIDをJSON形式で保存"""
        self.source_messages = json.dumps(message_ids)
    def get_image_paths_list(self):
        """画像パスをリストとして取得"""
        if self.image_paths:
            try:
                return json.loads(self.image_paths)
            except:
                return []
        return []
    
    def set_image_paths_list(self, paths_list):
        """画像パスをJSON形式で保存"""
        self.image_paths = json.dumps(paths_list, ensure_ascii=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'summary': self.summary,
            'tags': self.get_tags_list(),
            'source_messages': self.get_source_messages_list(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'published': self.published,
            'hatena_entry_id': self.hatena_entry_id,
            'hatena_url': self.hatena_url,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            # フェイズ2追加フィールド
            'status': self.status,
            'enhancement_level': self.enhancement_level,
            'last_enhanced_at': self.last_enhanced_at.isoformat() if self.last_enhanced_at else None,
            'image_paths': self.get_image_paths_list(),
            'video_path': self.video_path,
            'thumbnail_path': self.thumbnail_path
        }

class EnhancementLog(db.Model):
    """品質向上履歴テーブル"""
    __tablename__ = 'enhancement_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=False)
    enhancement_type = db.Column(db.String(100), nullable=False)  # text_quality, image_gen, affiliate, etc
    agent_name = db.Column(db.String(100), nullable=False)
    before_content = db.Column(db.Text)
    after_content = db.Column(db.Text)
    enhancement_data = db.Column(db.Text)  # JSON形式で追加データ
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    
    article = db.relationship('Article', backref='enhancement_logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'article_id': self.article_id,
            'enhancement_type': self.enhancement_type,
            'agent_name': self.agent_name,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'success': self.success,
            'error_message': self.error_message
        }

class ArticleLink(db.Model):
    """記事間リンクテーブル"""
    __tablename__ = 'article_links'
    
    id = db.Column(db.Integer, primary_key=True)
    source_article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=False)
    target_article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=False)
    link_context = db.Column(db.Text)  # リンクの文脈
    link_type = db.Column(db.String(50), default='related')  # related, similar, follow_up
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    source_article = db.relationship('Article', foreign_keys=[source_article_id], backref='outgoing_links')
    target_article = db.relationship('Article', foreign_keys=[target_article_id], backref='incoming_links')

class ProcessingQueue(db.Model):
    """処理キューテーブル"""
    __tablename__ = 'processing_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    retry_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    message = db.relationship('Message', backref='queue_items')

class MessageBuffer(db.Model):
    """1分間メッセージバッファテーブル"""
    __tablename__ = 'message_buffers'
    
    id = db.Column(db.Integer, primary_key=True)
    buffer_id = db.Column(db.String(255), nullable=False, unique=True)
    user_id = db.Column(db.String(255), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='collecting')  # collecting, processing, completed, failed
    message_count = db.Column(db.Integer, default=0)
    text_count = db.Column(db.Integer, default=0)
    image_count = db.Column(db.Integer, default=0)
    message_ids = db.Column(db.Text)  # JSON形式でメッセージIDを保存
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
    error_message = db.Column(db.Text)
    
    article = db.relationship('Article', backref='source_buffer')
    
    def get_message_ids_list(self):
        """メッセージIDをリストとして取得"""
        if self.message_ids:
            try:
                return json.loads(self.message_ids)
            except:
                return []
        return []
    
    def set_message_ids_list(self, ids_list):
        """メッセージIDをJSON形式で保存"""
        self.message_ids = json.dumps(ids_list)
    
    def to_dict(self):
        return {
            'id': self.id,
            'buffer_id': self.buffer_id,
            'user_id': self.user_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'message_count': self.message_count,
            'text_count': self.text_count,
            'image_count': self.image_count,
            'message_ids': self.get_message_ids_list(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'article_id': self.article_id,
            'error_message': self.error_message
        }

def init_db():
    """データベースの初期化"""
    db.create_all()
    print("✅ データベースが初期化されました")