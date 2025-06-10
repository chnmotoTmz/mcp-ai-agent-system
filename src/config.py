"""
設定管理モジュール
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """アプリケーション設定"""
    
    # Flask設定
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///integration.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # LINE Bot設定
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    
    # Gemini AI設定
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')  # デフォルト値設定
    
    # Imgur設定
    IMGUR_CLIENT_ID = os.getenv('IMGUR_CLIENT_ID')
    
    # はてなブログ設定
    HATENA_ID = os.getenv('HATENA_ID')
    HATENA_BLOG_ID = os.getenv('HATENA_BLOG_ID')
    HATENA_API_KEY = os.getenv('HATENA_API_KEY')
    
    # はてなOAuth設定（フォトライフ用）
    HATENA_CONSUMER_KEY = os.getenv('HATENA_CONSUMER_KEY')
    HATENA_CONSUMER_SECRET = os.getenv('HATENA_CONSUMER_SECRET')
    HATENA_ACCESS_TOKEN = os.getenv('HATENA_ACCESS_TOKEN')
    HATENA_ACCESS_TOKEN_SECRET = os.getenv('HATENA_ACCESS_TOKEN_SECRET')
    
    # バッチ処理設定
    BATCH_INTERVAL_MINUTES = int(os.getenv('BATCH_INTERVAL_MINUTES', '1'))  # デフォルト1分
    
    # ログ設定
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # ファイル保存設定
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    @classmethod
    def validate(cls):
        """必須設定項目の検証"""
        required_vars = [
            'LINE_CHANNEL_SECRET',
            'LINE_CHANNEL_ACCESS_TOKEN', 
            'GEMINI_API_KEY',
            'HATENA_ID',
            'HATENA_BLOG_ID',
            'HATENA_API_KEY',
            'HATENA_CONSUMER_KEY',
            'HATENA_CONSUMER_SECRET',
            'HATENA_ACCESS_TOKEN',
            'HATENA_ACCESS_TOKEN_SECRET'
        ]
        
        missing = []
        for var in required_vars:
            if not getattr(cls, var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"必須環境変数が設定されていません: {', '.join(missing)}")
        
        return True

# LangGraphエージェント用の互換性のために個別変数をエクスポート
LINE_CHANNEL_SECRET = Config.LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN = Config.LINE_CHANNEL_ACCESS_TOKEN
GEMINI_API_KEY = Config.GEMINI_API_KEY
GEMINI_MODEL = Config.GEMINI_MODEL
IMGUR_CLIENT_ID = Config.IMGUR_CLIENT_ID
HATENA_ID = Config.HATENA_ID
HATENA_BLOG_ID = Config.HATENA_BLOG_ID
HATENA_API_KEY = Config.HATENA_API_KEY
HATENA_CONSUMER_KEY = Config.HATENA_CONSUMER_KEY
HATENA_CONSUMER_SECRET = Config.HATENA_CONSUMER_SECRET
HATENA_ACCESS_TOKEN = Config.HATENA_ACCESS_TOKEN
HATENA_ACCESS_TOKEN_SECRET = Config.HATENA_ACCESS_TOKEN_SECRET
