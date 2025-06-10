"""
バッチ処理システム統合
Webhookとの連携設定
"""

import logging
from flask import Blueprint, jsonify, request
from src.services.batch.batch_scheduler import get_batch_scheduler, start_batch_system, stop_batch_system

logger = logging.getLogger(__name__)

batch_bp = Blueprint('batch_system_api', __name__)

@batch_bp.route('/start', methods=['POST'])
def start_batch():
    """バッチ処理システムを開始"""
    try:
        data = request.get_json() or {}
        interval_minutes = data.get('interval_minutes', 15)
        
        scheduler = start_batch_system(interval_minutes)
        
        return jsonify({
            'success': True,
            'message': f'バッチ処理システムが開始されました (間隔: {interval_minutes}分)',
            'status': scheduler.get_status()
        })
        
    except Exception as e:
        logger.error(f"バッチ開始エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@batch_bp.route('/stop', methods=['POST'])
def stop_batch():
    """バッチ処理システムを停止"""
    try:
        stop_batch_system()
        
        return jsonify({
            'success': True,
            'message': 'バッチ処理システムが停止されました'
        })
        
    except Exception as e:
        logger.error(f"バッチ停止エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@batch_bp.route('/status', methods=['GET'])
def get_batch_status():
    """バッチ処理システムの状態を取得"""
    try:
        scheduler = get_batch_scheduler()
        status = scheduler.get_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"バッチ状態取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@batch_bp.route('/manual', methods=['POST'])
def run_manual_batch():
    """手動でバッチ処理を実行"""
    try:
        scheduler = get_batch_scheduler()
        scheduler.run_manual_batch()
        
        return jsonify({
            'success': True,
            'message': '手動バッチ処理が開始されました'
        })
        
    except Exception as e:
        logger.error(f"手動バッチエラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@batch_bp.route('/config', methods=['GET', 'POST'])
def batch_config():
    """バッチ処理設定の取得・更新"""
    if request.method == 'GET':
        try:
            scheduler = get_batch_scheduler()
            status = scheduler.get_status()
            
            return jsonify({
                'success': True,
                'config': {
                    'interval_minutes': status.get('interval_minutes'),
                    'running': status.get('running'),
                    'next_run': status.get('next_run').isoformat() if status.get('next_run') else None
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            interval_minutes = data.get('interval_minutes', 15)
            
            # 既存システムを停止
            stop_batch_system()
            
            # 新しい設定で開始
            scheduler = start_batch_system(interval_minutes)
            
            return jsonify({
                'success': True,
                'message': f'バッチ処理設定が更新されました (間隔: {interval_minutes}分)',
                'status': scheduler.get_status()
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

# Webhookシステムとの統合
def integrate_batch_with_webhook():
    """Webhookシステムにバッチ処理を統合"""
    
    # 即座の処理を無効化し、バッチ処理モードに切り替える設定
    batch_config = {
        'enabled': True,
        'interval_minutes': 15,
        'immediate_processing': False  # 即座処理を無効化
    }
    
    return batch_config

def should_process_immediately() -> bool:
    """即座処理を行うかどうかを判定"""
    # バッチ処理が有効な場合は即座処理しない
    try:
        scheduler = get_batch_scheduler()
        status = scheduler.get_status()
        return not status.get('running', False)
    except:
        return True  # エラー時は即座処理

# バッチ処理システム初期化
def initialize_batch_system(app):
    """Flaskアプリケーションにバッチ処理システムを統合"""
    
    # ルート登録
    app.register_blueprint(batch_bp, url_prefix='/api/batch')
    
    # アプリケーション終了時にバッチシステムを停止
    import atexit
    atexit.register(stop_batch_system)
    
    logger.info("バッチ処理システム統合完了")
    
    # 環境変数から設定を読み込み、自動開始
    try:
        import os
        interval = int(os.getenv('BATCH_INTERVAL_MINUTES', 15))
        auto_start = os.getenv('BATCH_AUTO_START', 'true').lower() == 'true'
        
        if auto_start:
            # アプリケーションコンテキスト内でバッチシステムを開始
            with app.app_context():
                start_batch_system(interval)
                logger.info(f"バッチ処理システム自動開始 (間隔: {interval}分)")
                
    except Exception as e:
        logger.error(f"バッチシステム自動開始エラー: {e}")

# 使用例
if __name__ == "__main__":
    from flask import Flask
    
    app = Flask(__name__)
    
    # バッチ処理システムを統合
    initialize_batch_system(app)
    
    # テスト用ルート
    @app.route('/')
    def index():
        return jsonify({
            'message': 'バッチ処理システム統合テスト',
            'endpoints': {
                'start': '/api/batch/start',
                'stop': '/api/batch/stop',
                'status': '/api/batch/status',
                'manual': '/api/batch/manual',
                'config': '/api/batch/config'
            }
        })
    
    app.run(debug=True, port=5000)
