"""
LangGraph エージェント統合メインアプリケーション
LINE Webhook → LangGraph Agent → MCP Services フロー
"""

import asyncio
import logging
import sys
import os
from flask import Flask, jsonify
from flask_cors import CORS

# プロジェクトルートをPythonパスに追加
project_root = "/home/moto/line-gemini-hatena-integration"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import (
    LINE_CHANNEL_ACCESS_TOKEN, 
    LINE_CHANNEL_SECRET,
    GEMINI_API_KEY,
    IMGUR_CLIENT_ID,
    HATENA_ID, HATENA_BLOG_ID, HATENA_API_KEY
)
from src.routes.langgraph_routes import langgraph_bp

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/moto/line-gemini-hatena-integration/logs/langgraph_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def create_app():
    """Flask アプリケーション作成"""
    app = Flask(__name__)
    
    # CORS 有効化
    CORS(app)
    
    # 設定確認
    config_status = check_configuration()
    logger.info(f"設定確認結果: {config_status}")
    
    # Blueprint 登録
    app.register_blueprint(langgraph_bp)
    
    # ルートエンドポイント
    @app.route('/')
    def root():
        return jsonify({
            "service": "LangGraph Blog Generation Agent",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "webhook": "/api/langgraph/webhook",
                "sessions": "/api/langgraph/sessions",
                "graph": "/api/langgraph/graph",
                "test": "/api/langgraph/test",
                "health": "/api/langgraph/health"
            },
            "configuration": config_status
        })
    
    @app.route('/health')
    def health():
        """簡易ヘルスチェック"""
        return jsonify({
            "status": "healthy",
            "timestamp": os.times()[4]  # system time
        })
    
    # エラーハンドラー
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    return app

def check_configuration():
    """設定値確認"""
    config_checks = {
        "line_access_token": bool(LINE_CHANNEL_ACCESS_TOKEN),
        "line_channel_secret": bool(LINE_CHANNEL_SECRET), 
        "gemini_api_key": bool(GEMINI_API_KEY),
        "imgur_client_id": bool(IMGUR_CLIENT_ID),
        "hatena_id": bool(HATENA_ID),
        "hatena_blog_id": bool(HATENA_BLOG_ID),
        "hatena_api_key": bool(HATENA_API_KEY)
    }
    
    missing_configs = [key for key, value in config_checks.items() if not value]
    
    return {
        "all_configured": len(missing_configs) == 0,
        "missing": missing_configs,
        "configured": [key for key, value in config_checks.items() if value]
    }

async def test_langgraph_agent():
    """LangGraph エージェントテスト"""
    try:
        logger.info("LangGraph エージェント統合テスト開始")
        
        from src.langgraph_agents.agent import process_line_message_async
        
        # テストメッセージ処理
        test_result = await process_line_message_async(
            message_id="test_001",
            user_id="test_user",
            message_type="text",
            content="LangGraphエージェントのテストメッセージです。簡単なブログ記事を生成してください。",
            config={
                "article_style": "blog",
                "publish_as_draft": True,  # テストなので下書きで
                "blog_category": "テスト"
            }
        )
        
        logger.info(f"テスト結果: {test_result}")
        
        if test_result.get('success'):
            logger.info("✅ LangGraph エージェント統合テスト成功")
        else:
            logger.error("❌ LangGraph エージェント統合テスト失敗")
            
        return test_result
        
    except Exception as e:
        logger.error(f"LangGraph エージェントテストエラー: {e}")
        return {"success": False, "error": str(e)}

def main():
    """メイン実行"""
    logger.info("LangGraph エージェント統合アプリケーション開始")
    
    # 設定確認
    config_status = check_configuration()
    if not config_status["all_configured"]:
        logger.warning(f"設定不足: {config_status['missing']}")
        logger.info("不足している設定があります。動作に影響する可能性があります。")
    
    # Flask アプリ作成
    app = create_app()
    
    # 統合テスト実行（オプション）
    if "--test" in sys.argv:
        logger.info("統合テスト実行")
        test_result = asyncio.run(test_langgraph_agent())
        logger.info(f"統合テスト完了: {test_result}")
        return
    
    # アプリケーション起動
    port = int(os.environ.get('PORT', 8080))
    debug = "--debug" in sys.argv
    
    logger.info(f"LangGraph エージェントサーバー起動: ポート={port}, デバッグ={debug}")
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("アプリケーション停止")
    except Exception as e:
        logger.error(f"アプリケーション実行エラー: {e}")

if __name__ == "__main__":
    main()
