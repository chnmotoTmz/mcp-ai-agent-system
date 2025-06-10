"""
APIルート定義
"""

from flask import jsonify
from .webhook_enhanced import webhook_bp  # バッチ処理強化版を使用（修正済み）
from .api import api_bp
from .health import health_bp

def register_routes(app):
    """ルートの登録"""
    
    # Webhook エンドポイント
    app.register_blueprint(webhook_bp, url_prefix='/api/webhook')
    
    # API エンドポイント
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # ヘルスチェック
    app.register_blueprint(health_bp)
    
    # ルートエンドポイント
    @app.route('/')
    def index():
        return jsonify({
            'message': 'LINE → Gemini → はてな統合システム',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'webhook_line': '/api/webhook/line',
                'api_articles': '/api/articles',
                'api_messages': '/api/messages',
                'health': '/health'
            }
        })
    
    # エラーハンドラー
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'エンドポイントが見つかりません'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': '内部サーバーエラーが発生しました'}), 500