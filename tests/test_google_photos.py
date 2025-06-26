#!/usr/bin/env python3
"""
Google Photos統合テスト
"""

import sys
import os
import logging
from PIL import Image
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.google_photos_service import GooglePhotosService

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_test_image():
    """テスト用画像を作成"""
    test_image_path = "test_google_photos.png"
    
    # 100x100の青い画像を作成
    img = Image.new('RGB', (100, 100), color='blue')
    img.save(test_image_path)
    
    print(f"✅ テスト画像作成: {test_image_path}")
    return test_image_path

def test_google_photos():
    """Google Photosテスト"""
    print("📸 Google Photos統合テスト")
    print("=" * 50)
    
    try:
        # Google Photosサービス初期化
        service = GooglePhotosService()
        
        if not service.service:
            print("❌ Google Photos認証が必要です")
            print("以下のコマンドで認証を実行してください:")
            print("python -c \"from src.services.google_photos_service import GooglePhotosService; GooglePhotosService().setup_authentication()\"")
            return False
        
        print("✅ Google Photos認証済み")
        
        # テスト画像作成
        test_image_path = create_test_image()
        
        # アップロード実行
        print("📤 Google Photosにアップロード中...")
        result = service.upload_image(
            test_image_path,
            title="Test Upload from LINE Bot",
            description="Google Photos統合テスト画像"
        )
        
        print(f"📊 アップロード結果:")
        print(f"   成功: {result.get('success')}")
        
        if result.get('success'):
            print(f"   🔗 共有URL: {result.get('share_url')}")
            print(f"   📱 Google Photos URL: {result.get('google_photos_url')}")
            print(f"   🆔 メディアID: {result.get('media_item_id')}")
            
            # HTMLタグ作成テスト
            share_url = result.get('share_url') or result.get('google_photos_url')
            html_tag = f'<img src="{share_url}" alt="Test Image">'
            print(f"   🏷️  HTMLタグ: {html_tag}")
            
            return True
        else:
            print(f"   ❌ エラー: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        return False
    finally:
        # テストファイルクリーンアップ
        if os.path.exists("test_google_photos.png"):
            os.remove("test_google_photos.png")

def main():
    """メインテスト実行"""
    print("🧪 Google Photos統合テスト")
    print("=" * 60)
    
    success = test_google_photos()
    
    print("\n📊 テスト結果")
    print("=" * 60)
    
    if success:
        print("🎉 Google Photos統合が正常に動作しています！")
        print("\n📋 次のステップ:")
        print("1. システムを再起動")
        print("2. LINEで画像付きメッセージを送信")
        print("3. はてなブログ記事を確認")
    else:
        print("❌ Google Photos統合に問題があります。")
        print("\n🔧 確認項目:")
        print("1. Google Photos認証が完了しているか")
        print("2. Photos Library APIが有効になっているか")
        print("3. インターネット接続が正常か")

if __name__ == "__main__":
    main()
