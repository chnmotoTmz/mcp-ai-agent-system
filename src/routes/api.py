"""
REST APIエンドポイント
"""

from flask import Blueprint, jsonify, request
from src.database import db, Message, Article
from datetime import datetime

api_bp = Blueprint('api', __name__)

@api_bp.route('/articles', methods=['GET'])
def get_articles():
    """記事一覧取得"""
    
    # クエリパラメータ
    user_id = request.args.get('user_id')
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # クエリ構築
    query = Article.query
    
    if user_id:
        # ユーザーIDでフィルタリング
        message_ids = db.session.query(Message.id).filter_by(user_id=user_id).subquery()
        query = query.filter(
            Article.source_messages.any(Message.id.in_(message_ids))
        )
    
    # ページネーション
    articles = query.order_by(Article.created_at.desc())\
                   .limit(limit)\
                   .offset(offset)\
                   .all()
    
    return jsonify({
        'articles': [article.to_dict() for article in articles],
        'total': query.count(),
        'limit': limit,
        'offset': offset
    })

@api_bp.route('/articles/<int:article_id>', methods=['GET'])
def get_article(article_id):
    """個別記事取得"""
    article = Article.query.get_or_404(article_id)
    return jsonify(article.to_dict())

@api_bp.route('/messages', methods=['GET'])
def get_messages():
    """メッセージ一覧取得"""
    
    # クエリパラメータ
    user_id = request.args.get('user_id')
    message_type = request.args.get('type')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # クエリ構築
    query = Message.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if message_type:
        query = query.filter_by(message_type=message_type)
    
    # ページネーション
    messages = query.order_by(Message.created_at.desc())\
                   .limit(limit)\
                   .offset(offset)\
                   .all()
    
    return jsonify({
        'messages': [msg.to_dict() for msg in messages],
        'total': query.count(),
        'limit': limit,
        'offset': offset
    })

@api_bp.route('/users/<user_id>/stats', methods=['GET'])
def get_user_stats(user_id):
    """ユーザー統計情報取得"""
    
    # メッセージ統計
    message_count = Message.query.filter_by(user_id=user_id).count()
    
    # 記事統計
    article_ids = db.session.query(Article.id).join(
        Article.source_messages
    ).filter(
        Message.user_id == user_id
    ).distinct()
    
    article_count = article_ids.count()
    
    # 最新のアクティビティ
    last_message = Message.query.filter_by(user_id=user_id)\
                                .order_by(Message.created_at.desc())\
                                .first()
    
    return jsonify({
        'user_id': user_id,
        'message_count': message_count,
        'article_count': article_count,
        'last_activity': last_message.created_at.isoformat() if last_message else None
    })

@api_bp.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    try:
        # データベース接続確認
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    return jsonify({
        'status': 'healthy' if db_status == 'healthy' else 'unhealthy',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    })

@api_bp.route('/batch/status', methods=['GET'])
def batch_status():
    """バッチ処理状況確認"""
    from src.database import MessageBuffer
    
    try:
        # アクティブなバッファを取得
        active_buffers = MessageBuffer.query.filter_by(status='collecting').all()
        processing_buffers = MessageBuffer.query.filter_by(status='processing').all()
        
        # 最近完了したバッファ
        completed_buffers = MessageBuffer.query.filter_by(status='completed')\
                                               .order_by(MessageBuffer.processed_at.desc())\
                                               .limit(5).all()
        
        return jsonify({
            'status': 'active',
            'active_batches': len(active_buffers),
            'processing_batches': len(processing_buffers),
            'recent_completed': len(completed_buffers),
            'batch_details': {
                'active': [{
                    'buffer_id': buf.buffer_id,
                    'user_id': buf.user_id,
                    'message_count': buf.message_count,
                    'start_time': buf.start_time.isoformat()
                } for buf in active_buffers],
                'processing': [{
                    'buffer_id': buf.buffer_id,
                    'user_id': buf.user_id,
                    'message_count': buf.message_count,
                    'start_time': buf.start_time.isoformat()
                } for buf in processing_buffers],
                'completed': [{
                    'buffer_id': buf.buffer_id,
                    'user_id': buf.user_id,
                    'message_count': buf.message_count,
                    'article_id': buf.article_id,
                    'processed_at': buf.processed_at.isoformat() if buf.processed_at else None
                } for buf in completed_buffers]
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api_bp.route('/batch/force/<user_id>', methods=['POST'])
def force_batch_processing(user_id):
    """指定ユーザーのバッチを強制処理"""
    from src.services.batch_processing_service import BatchProcessingService
    
    try:
        batch_service = BatchProcessingService()
        
        # アクティブなバッファを取得
        buffer = batch_service.get_active_buffer(user_id)
        
        if buffer and buffer.message_count > 0:
            # バッチ処理を実行
            result = batch_service.process_buffer(buffer)
            
            return jsonify({
                'success': True,
                'message': f'Forced batch processing for user {user_id}',
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'message': f'No active batch found for user {user_id}'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500