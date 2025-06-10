"""
ヘルスチェックエンドポイント
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify

from src.config import Config

# Blueprint の作成
health_bp = Blueprint('health', __name__)

logger = logging.getLogger(__name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    try:
        # 基本的なヘルスチェック
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'services': {
                'database': check_database_health(),
                'line': check_line_service_health(),
                'gemini': check_gemini_service_health(),
                'hatena': check_hatena_service_health()
            }
        }
        
        # すべてのサービスが正常かチェック
        all_healthy = all(
            service['status'] == 'healthy' 
            for service in health_status['services'].values()
        )
        
        if not all_healthy:
            health_status['status'] = 'degraded'
        
        status_code = 200 if all_healthy else 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 503


@health_bp.route('/ping', methods=['GET'])
def ping():
    """簡単な生存確認"""
    return jsonify({
        'message': 'pong',
        'timestamp': datetime.now().isoformat()
    }), 200


def check_database_health():
    """データベースの健全性チェック"""
    try:
        from src.database import db
        from sqlalchemy import text
        
        # 簡単なクエリを実行してデータベース接続をテスト
        with db.engine.connect() as connection:
            result = connection.execute(text('SELECT 1'))
            result.fetchone()
        
        return {
            'status': 'healthy',
            'message': 'Database connection successful'
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}'
        }


def check_line_service_health():
    """LINE サービスの健全性チェック"""
    try:
        # LINE の設定が正しく読み込まれているかチェック
        if not Config.LINE_CHANNEL_ACCESS_TOKEN or not Config.LINE_CHANNEL_SECRET:
            return {
                'status': 'unhealthy',
                'message': 'LINE configuration missing'
            }
        
        return {
            'status': 'healthy',
            'message': 'LINE service configuration OK'
        }
    except Exception as e:
        logger.error(f"LINE service health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'message': f'LINE service check failed: {str(e)}'
        }


def check_gemini_service_health():
    """Gemini サービスの健全性チェック"""
    try:
        # Gemini の設定が正しく読み込まれているかチェック
        if not Config.GEMINI_API_KEY:
            return {
                'status': 'unhealthy',
                'message': 'Gemini API key missing'
            }
        
        return {
            'status': 'healthy',
            'message': 'Gemini service configuration OK'
        }
    except Exception as e:
        logger.error(f"Gemini service health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'message': f'Gemini service check failed: {str(e)}'
        }


def check_hatena_service_health():
    """はてなサービスの健全性チェック"""
    try:
        # はてなの設定が正しく読み込まれているかチェック
        if not Config.HATENA_API_KEY or not Config.HATENA_BLOG_ID:
            return {
                'status': 'unhealthy',
                'message': 'Hatena configuration missing'
            }
        
        return {
            'status': 'healthy',
            'message': 'Hatena service configuration OK'
        }
    except Exception as e:
        logger.error(f"Hatena service health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'message': f'Hatena service check failed: {str(e)}'
        }
