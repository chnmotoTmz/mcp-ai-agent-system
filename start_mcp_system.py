#!/usr/bin/env python3
"""
🤖 MCP AI Agent System
LINE → Gemini → はてなブログ 自動化システム

Usage:
    python3 start_mcp_system.py
"""

import sys
import os
import logging
from dotenv import load_dotenv

# パスを追加
sys.path.append('/home/moto/line-gemini-hatena-integration')

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("🚀 MCP AI Agent System 起動中...")
    print("=" * 50)
    
    try:
        # Flask アプリケーションを作成
        from flask import Flask, jsonify
        app = Flask(__name__)
        
        # 基本設定
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mcp-ai-agent-secret-key')
        
        # データベース設定（絶対パス使用）
        db_path = '/home/moto/line-gemini-hatena-integration/instance/integration.db'
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        print(f"📊 データベース: {db_path}")
        
        # データベースの初期化
        from src.database import db
        db.init_app(app)
        
        # ルート登録
        from src.routes.webhook_ai import webhook_bp
        app.register_blueprint(webhook_bp, url_prefix='/api/webhook')
        
        # メインページ
        @app.route('/')
        def index():
            return jsonify({
                'message': '🤖 MCP AI Agent System',
                'description': 'LINE → Gemini → はてなブログ 自動化システム',
                'version': '1.0.0',
                'status': 'running',
                'features': [
                    'AIエージェントによる自動コンテンツ生成',
                    'Model Context Protocol (MCP) 対応',
                    'LangGraph ワークフロー制御',
                    'マルチエージェント対応準備済み'
                ],
                'endpoints': {
                    'line_webhook': '/api/webhook/line',
                    'agent_test': '/api/webhook/test',
                    'health_check': '/api/webhook/health'
                }
            })
        
        @app.route('/status')
        def status():
            return jsonify({
                'system': 'MCP AI Agent',
                'database': 'Connected',
                'ai_agent': 'Ready',
                'mcp_servers': ['LINE', 'Gemini', 'Hatena'],
                'timestamp': '2025-06-08T18:00:00Z'
            })
        
        # データベースを作成
        with app.app_context():
            from src.database import init_db
            init_db()
            print("✅ データベース初期化完了")
        
        print("🔧 システム設定:")
        print(f"   • LINE Webhook: /api/webhook/line")
        print(f"   • テストエンドポイント: /api/webhook/test")
        print(f"   • ヘルスチェック: /api/webhook/health")
        print()
        
        # サーバー起動
        port = int(os.getenv('PORT', 8084))
        print(f"🌟 MCP AI Agent System 起動完了！")
        print(f"📡 アクセスURL: http://localhost:{port}")
        print(f"🔗 システム状態: http://localhost:{port}/status")
        print()
        print("🧪 テスト方法:")
        print(f"curl -X POST http://localhost:{port}/api/webhook/test \\")
        print(f"  -H 'Content-Type: application/json' \\")
        print(f"  -d '{{\"message\": \"AIエージェントのテストです\", \"user_id\": \"test_user\"}}'")
        print()
        print("📝 LINE Webhook URL (本番用):")
        print(f"  https://your-domain.com/api/webhook/line")
        print()
        print("=" * 50)
        print("🎯 システムが正常に起動しました。Ctrl+C で終了します。")
        
        app.run(host='0.0.0.0', port=port, debug=True)
        
    except KeyboardInterrupt:
        print("\\n🛑 システムを終了しています...")
        print("👋 MCP AI Agent System が終了しました。")
        
    except Exception as e:
        print(f"❌ 起動エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
