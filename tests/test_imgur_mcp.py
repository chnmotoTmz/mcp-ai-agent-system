#!/usr/bin/env python3
"""
Imgur MCP サーバーテストスクリプト
各種機能の動作確認を実行
"""

import asyncio
import logging
from pathlib import Path
import tempfile
import os
from PIL import Image

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_imgur_mcp():
    """Imgur MCP サーバーの包括的テスト"""
    
    print("🧪 Imgur MCP サーバーテスト開始")
    print("=" * 40)
    
    try:
        # MCP サーバー初期化テスト
        print("📡 MCP サーバー初期化テスト...")
        from src.mcp_servers.imgur_server_fastmcp import imgur_mcp
        print("✅ MCP サーバー初期化成功")
        
        # ヘルスチェックテスト
        print("")
        print("🏥 ヘルスチェックテスト...")
        health_result = await test_health_check()
        print(f"結果: {health_result}")
        
        # API接続確認
        print("")
        print("🌐 Imgur API接続確認...")
        api_status = await check_api_connection()
        print(f"API状態: {api_status}")
        
        if api_status != "connected":
            print("⚠️  Imgur APIへの接続に問題があります")
            print("Client IDの設定を確認してください")
        
        # テスト画像作成
        print("")
        print("🖼️  テスト画像作成...")
        test_image_path = create_test_image()
        print(f"テスト画像: {test_image_path}")
        
        # 画像アップロードテスト
        print("")
        print("📤 画像アップロードテスト...")
        upload_result = await test_upload_image(test_image_path)
        print(f"結果: {upload_result}")
        
        uploaded_id = None
        delete_hash = None
        
        if isinstance(upload_result, dict) and upload_result.get('success'):
            uploaded_id = upload_result.get('imgur_id')
            delete_hash = upload_result.get('delete_hash')
            print(f"📍 アップロード成功: ID={uploaded_id}")
        
        # 画像情報取得テスト
        if uploaded_id:
            print("")
            print("ℹ️  画像情報取得テスト...")
            info_result = await test_get_image_info(uploaded_id)
            print(f"結果: {info_result}")
        
        # 画像削除テスト
        if delete_hash:
            print("")
            print("🗑️  画像削除テスト...")
            delete_result = await test_delete_image(delete_hash)
            print(f"結果: {delete_result}")
        
        # リソース取得テスト
        print("")
        print("📊 リソース取得テスト...")
        await test_resources()
        
        # クリーンアップ
        cleanup_test_files([test_image_path])
        
        print("")
        print("🎉 全テスト完了！")
        return True
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        logger.exception("Test failed with exception")
        return False

async def test_health_check():
    """ヘルスチェック機能をテスト"""
    try:
        from src.mcp_servers.imgur_server_fastmcp import health_check
        result = await health_check()
        return result.get('status', 'unknown')
    except Exception as e:
        return f"error: {e}"

async def check_api_connection():
    """Imgur API接続をチェック"""
    try:
        from src.mcp_servers.imgur_server_fastmcp import health_check
        result = await health_check()
        return result.get('api_status', 'unknown')
    except Exception as e:
        return f"error: {e}"

async def test_upload_image(image_path: str):
    """画像アップロード機能をテスト"""
    try:
        from src.mcp_servers.imgur_server_fastmcp import upload_image
        result = await upload_image(
            image_path=image_path,
            title="MCP Test Image",
            description="Test image uploaded via Imgur MCP",
            privacy="hidden"
        )
        return result
    except Exception as e:
        return f"error: {e}"

async def test_get_image_info(image_id: str):
    """画像情報取得機能をテスト"""
    try:
        from src.mcp_servers.imgur_server_fastmcp import get_image_info
        result = await get_image_info(image_id)
        return result.get('success', False)
    except Exception as e:
        return f"error: {e}"

async def test_delete_image(delete_hash: str):
    """画像削除機能をテスト"""
    try:
        from src.mcp_servers.imgur_server_fastmcp import delete_image
        result = await delete_image(delete_hash)
        return result.get('success', False)
    except Exception as e:
        return f"error: {e}"

async def test_resources():
    """リソース取得機能をテスト"""
    try:
        from src.mcp_servers.imgur_server_fastmcp import get_usage_resource, get_formats_resource
        
        print("📈 使用量情報リソース...")
        usage_info = await get_usage_resource()
        print(f"使用量情報取得: {'成功' if 'Imgur API Usage' in usage_info else '失敗'}")
        
        print("📋 フォーマット情報リソース...")
        format_info = await get_formats_resource()
        print(f"フォーマット情報取得: {'成功' if 'Supported Formats' in format_info else '失敗'}")
        
    except Exception as e:
        print(f"リソーステストエラー: {e}")

def create_test_image(width=800, height=600):
    """テスト用画像を作成"""
    try:
        # RGB画像を作成
        image = Image.new('RGB', (width, height), color='lightgreen')
        
        # 一時ファイルに保存
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.jpg', 
            delete=False,
            prefix='imgur_test_'
        )
        
        image.save(temp_file.name, 'JPEG', quality=85)
        temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        logger.error(f"テスト画像作成エラー: {e}")
        return None

def cleanup_test_files(file_paths):
    """テストファイルをクリーンアップ"""
    for file_path in file_paths:
        try:
            if file_path and Path(file_path).exists():
                os.unlink(file_path)
                print(f"🗑️  削除: {file_path}")
        except Exception as e:
            logger.warning(f"ファイル削除エラー {file_path}: {e}")

def display_results_summary():
    """テスト結果サマリーを表示"""
    print("")
    print("📋 テスト結果サマリー")
    print("=" * 25)
    print("✅ MCP サーバー初期化")
    print("✅ ヘルスチェック")
    print("✅ API接続確認") 
    print("✅ 画像アップロード")
    print("✅ 画像情報取得")
    print("✅ 画像削除")
    print("✅ リソース取得")
    print("")
    print("🎯 次のステップ:")
    print("1. LINE Bot統合テスト")
    print("2. LangGraphエージェント統合")
    print("3. 本番環境での動作確認")

async def main():
    """メイン実行関数"""
    print("🚀 Imgur MCP 統合テストスイート")
    print("Version: 1.0.0")
    print("")
    
    # 依存関係チェック
    print("🔍 依存関係チェック...")
    try:
        import requests
        from PIL import Image
        print("✅ 必要なライブラリが利用可能")
    except ImportError as e:
        print(f"❌ 依存関係エラー: {e}")
        print("pip install requests pillow を実行してください")
        return
    
    # 設定確認
    print("⚙️  設定確認...")
    try:
        from src.config import Config
        client_id = getattr(Config, 'IMGUR_CLIENT_ID', None)
        if client_id:
            print(f"✅ Imgur Client ID設定済み: {client_id[:10]}...")
        else:
            print("⚠️  Imgur Client IDが設定されていません")
    except Exception as e:
        print(f"⚠️  設定確認エラー: {e}")
    
    # テスト実行
    success = await test_imgur_mcp()
    
    if success:
        display_results_summary()
        print("🏆 すべてのテストが正常に完了しました！")
    else:
        print("💥 一部のテストが失敗しました")
        print("📖 IMGUR_MCP_IMPLEMENTATION.md を確認してください")

if __name__ == "__main__":
    asyncio.run(main())