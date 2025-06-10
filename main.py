#!/usr/bin/env python3
"""
LINE → Gemini → はてな統合システム
メインエントリーポイント
"""

import os
import logging
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from src.config import Config
from src.database import db, init_db
from src.routes import register_routes

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_app():
    """Flaskアプリケーションの作成と設定"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # データベース初期化
    db.init_app(app)
    
    # ルート登録
    register_routes(app)
    
    with app.app_context():
        init_db()
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 8084))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"🚀 LINE → Gemini → はてな統合システム起動中...")
    print(f"📡 ポート: {port}")
    print(f"🐛 デバッグモード: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)