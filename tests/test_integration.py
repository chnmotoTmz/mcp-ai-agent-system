#!/usr/bin/env python3
"""
統合テストスクリプト - Imgur・はてなブログ連携機能のテスト
"""

import sys
import os
import logging
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.imgur_service import ImgurService
from src.services.hatena_service import HatenaService
from src.services.gemini_service import GeminiService

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_environment_variables():
    """環境変数の確認"""
    print("\n🔍 環境変数の確認")
    print("=" * 50)
    
    required_vars = [
        'IMGUR_CLIENT_ID',
        'HATENA_ID',
        'HATENA_BLOG_ID', 
        'HATENA_API_KEY',
        'GEMINI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 10)}{'...' if len(value) > 10 else ''}")
        else:
            print(f"❌ {var}: 未設定")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  不足している環境変数: {', '.join(missing_vars)}")
        return False
    else:
        print("\n✅ 全ての環境変数が設定されています")
        return True

def test_imgur_service():
    """ImgurServiceのテスト"""
    print("\n🖼️  ImgurServiceのテスト")
    print("=" * 50)
    
    try:
        imgur_service = ImgurService()
        
        # サービス初期化確認
        if imgur_service.client_id:
            print(f"✅ ImgurService初期化成功 (Client ID: {imgur_service.client_id[:10]}...)")
        else:
            print("❌ ImgurService初期化失敗 - Client IDが設定されていません")
            return False
        
        # テスト画像の作成（簡単な1x1ピクセル画像）
        test_image_path = "test_image.png"
        try:
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(test_image_path)
            print(f"✅ テスト画像作成: {test_image_path}")
        except ImportError:
            print("⚠️  PIL/Pillowがインストールされていません。テスト画像をスキップします。")
            return True
        
        # 画像アップロードテスト
        print("📤 Imgurアップロードテスト中...")
        upload_result = imgur_service.upload_image(
            test_image_path,
            title="Test Upload",
            description="統合テスト用の画像"
        )
        
        if upload_result and upload_result.get('success'):
            print(f"✅ Imgurアップロード成功!")
            print(f"   URL: {upload_result.get('imgur_url')}")
            print(f"   ID: {upload_result.get('imgur_id')}")
            
            # クリーンアップ
            delete_hash = upload_result.get('delete_hash')
            if delete_hash:
                print("🗑️  テスト画像を削除中...")
                delete_result = imgur_service.delete_image(delete_hash)
                if delete_result and delete_result.get('success'):
                    print("✅ テスト画像削除成功")
                else:
                    print("⚠️  テスト画像削除失敗")
        else:
            print(f"❌ Imgurアップロード失敗: {upload_result.get('error', '不明なエラー')}")
            return False
        
        # ファイルクリーンアップ
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
            
        return True
        
    except Exception as e:
        print(f"❌ ImgurServiceテストエラー: {e}")
        return False

def test_gemini_service():
    """GeminiServiceのテスト"""
    print("\n🤖 GeminiServiceのテスト")
    print("=" * 50)
    
    try:
        gemini_service = GeminiService()
        print("✅ GeminiService初期化成功")
        
        # create_integrated_articleメソッドのテスト
        print("📝 create_integrated_articleメソッドテスト中...")
        test_text = "今日は良い天気です。散歩に行きました。"
        test_image_analyses = ["青空と緑の公園の写真", "散歩道の美しい景色"]
        
        result = gemini_service.create_integrated_article(test_text, test_image_analyses)
        
        if result:
            print("✅ create_integrated_article成功")
            print(f"   生成された記事の長さ: {len(result)}文字")
            print(f"   記事の最初の100文字: {result[:100]}...")
            return True
        else:
            print("❌ create_integrated_article失敗")
            return False
            
    except Exception as e:
        print(f"❌ GeminiServiceテストエラー: {e}")
        return False

def test_hatena_service():
    """HatenaServiceのテスト（記事投稿なし）"""
    print("\n📝 HatenaServiceのテスト")
    print("=" * 50)
    
    try:
        hatena_service = HatenaService()
        print("✅ HatenaService初期化成功")
        
        # 認証情報の確認
        print(f"   Hatena ID: {hatena_service.hatena_id}")
        print(f"   Blog ID: {hatena_service.blog_id}")
        print(f"   API Key: {'*' * 10}...")
        
        # 記事一覧取得テスト（読み取り専用）
        print("📖 記事一覧取得テスト中...")
        articles = hatena_service.get_articles()
        
        if articles:
            print(f"✅ 記事一覧取得成功 - {articles.get('total', 0)}件の記事")
            return True
        else:
            print("⚠️  記事一覧取得失敗（認証エラーの可能性）")
            return False
            
    except Exception as e:
        print(f"❌ HatenaServiceテストエラー: {e}")
        return False

def test_integration():
    """統合テストシミュレーション"""
    print("\n🔗 統合テストシミュレーション")
    print("=" * 50)
    
    try:
        # サービス初期化
        imgur_service = ImgurService()
        gemini_service = GeminiService()
        hatena_service = HatenaService()
        
        print("✅ 全サービス初期化完了")
        
        # テストデータ
        test_text = "今日は素晴らしい一日でした！"
        test_image_analyses = ["美しい夕焼けの写真"]
        
        # 1. Geminiで統合記事生成
        print("🤖 Geminiで統合記事生成中...")
        article_content = gemini_service.create_integrated_article(test_text, test_image_analyses)
        
        if not article_content:
            print("❌ 記事生成失敗")
            return False
        
        print("✅ 記事生成成功")
        
        # 2. はてなブログへの投稿テスト（実際には投稿しない）
        print("📝 はてなブログ投稿テスト（シミュレーション）")
        
        # XMLフォーマットのテスト
        test_xml = hatena_service._create_entry_xml(
            title="テスト記事",
            content=article_content[:200] + "...",
            tags=["テスト", "統合テスト"]
        )
        
        if test_xml and "entry" in test_xml:
            print("✅ はてなブログXML生成成功")
        else:
            print("❌ はてなブログXML生成失敗")
            return False
        
        print("🎉 統合テストシミュレーション完了")
        return True
        
    except Exception as e:
        print(f"❌ 統合テストエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("🧪 LINE-Gemini-Hatena統合テスト開始")
    print("=" * 60)
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # テスト実行
    test_results.append(("環境変数確認", test_environment_variables()))
    test_results.append(("ImgurService", test_imgur_service()))
    test_results.append(("GeminiService", test_gemini_service()))
    test_results.append(("HatenaService", test_hatena_service()))
    test_results.append(("統合テスト", test_integration()))
    
    # 結果サマリー
    print("\n📊 テスト結果サマリー")
    print("=" * 60)
    
    success_count = 0
    for test_name, result in test_results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            success_count += 1
    
    print(f"\n🎯 総合結果: {success_count}/{len(test_results)} テスト成功")
    
    if success_count == len(test_results):
        print("🎉 全てのテストが成功しました！")
        print("\n📋 次のステップ:")
        print("1. 実際のLINEメッセージでテスト")
        print("2. 画像付きメッセージの送信")
        print("3. バッチ処理の動作確認")
    else:
        print("⚠️  一部のテストが失敗しました。上記の詳細を確認してください。")

if __name__ == "__main__":
    main()
