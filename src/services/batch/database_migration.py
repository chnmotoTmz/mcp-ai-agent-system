"""
バッチ処理用データベースモデル拡張
"""

from sqlalchemy import Column, Boolean, DateTime
from src.database import db

# Messageモデルにバッチ処理用フィールドを追加するマイグレーション用SQL
BATCH_MIGRATION_SQL = """
-- バッチ処理用フィールドを追加
ALTER TABLE messages ADD COLUMN processed_by_batch BOOLEAN DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN batch_processed_at DATETIME NULL;

-- バッチ処理状況確認用インデックス
CREATE INDEX idx_messages_batch_status ON messages(processed_by_batch, created_at);
CREATE INDEX idx_messages_user_batch ON messages(user_id, processed_by_batch, created_at);
"""

def upgrade_database_for_batch():
    """バッチ処理用にデータベースをアップグレード"""
    try:
        # SQLAlchemy 2.0 対応: text() を使用
        from sqlalchemy import text
        
        # 個別のSQL文を実行
        with db.engine.connect() as connection:
            # バッチ処理用フィールドを追加
            try:
                connection.execute(text("ALTER TABLE messages ADD COLUMN processed_by_batch BOOLEAN DEFAULT FALSE"))
            except Exception:
                pass  # 既に存在する場合は無視
            
            try:
                connection.execute(text("ALTER TABLE messages ADD COLUMN batch_processed_at DATETIME NULL"))
            except Exception:
                pass  # 既に存在する場合は無視
            
            # インデックスを作成
            try:
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_batch_status ON messages(processed_by_batch, created_at)"))
            except Exception:
                pass
            
            try:
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_user_batch ON messages(user_id, processed_by_batch, created_at)"))
            except Exception:
                pass
            
            connection.commit()
        
        print("✅ バッチ処理用データベースアップグレード完了")
        
    except Exception as e:
        print(f"⚠️ データベースアップグレード: {e} (既に適用済みの可能性)")
        # エラーでも続行（既に適用済みの可能性）
        pass

if __name__ == "__main__":
    from src.database import init_db
    
    # データベース初期化
    init_db()
    
    # バッチ処理用アップグレード
    upgrade_database_for_batch()
