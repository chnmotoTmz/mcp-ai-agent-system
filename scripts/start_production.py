#!/usr/bin/env python3
"""
本番環境用起動スクリプト
Line-Gemini-Hatena Integration System (Production)
"""

import os
import sys
import logging
import signal
import uvicorn
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_production_logging():
    """本番環境用ログ設定"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', '/app/logs/app.log')
    
    # ログディレクトリ作成
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # ログフォーマット
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # ログ設定
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 外部ライブラリのログレベル調整
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.INFO)
    
    return logging.getLogger(__name__)

def signal_handler(signum, frame):
    """シグナルハンドラー"""
    logger = logging.getLogger(__name__)
    logger.info(f"受信シグナル: {signum}")
    logger.info("アプリケーションを正常終了中...")
    sys.exit(0)

def validate_environment():
    """本番環境の環境変数検証"""
    logger = logging.getLogger(__name__)
    
    required_vars = [
        'LINE_CHANNEL_ACCESS_TOKEN',
        'LINE_CHANNEL_SECRET', 
        'GEMINI_API_KEY',
        'HATENA_ID',
        'HATENA_BLOG_ID',
        'HATENA_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"必須環境変数が設定されていません: {', '.join(missing_vars)}")
        sys.exit(1)
    
    logger.info("環境変数検証完了")

def main():
    """メイン起動処理"""
    # シグナルハンドラー設定
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # ログ設定
    logger = setup_production_logging()
    logger.info("=" * 50)
    logger.info("Line-Gemini-Hatena Integration System (Production)")
    logger.info("=" * 50)
    
    # 環境変数検証
    validate_environment()
    
    # FastAPI アプリケーション起動
    try:
        from start_mcp_system import create_app
        
        app = create_app()
        
        # 本番環境設定
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 8000))
        workers = int(os.getenv('WORKERS', 4))
        
        logger.info(f"サーバー起動: {host}:{port}")
        logger.info(f"ワーカー数: {workers}")
        
        # Uvicorn設定
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            workers=workers if workers > 1 else 1,
            log_level=os.getenv('LOG_LEVEL', 'info').lower(),
            access_log=True,
            use_colors=False,  # 本番環境では色なし
            server_header=False,  # サーバーヘッダー非表示
            date_header=False,    # 日付ヘッダー非表示
        )
        
        server = uvicorn.Server(config)
        
        logger.info("🚀 アプリケーション起動完了")
        server.run()
        
    except Exception as e:
        logger.error(f"起動エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()