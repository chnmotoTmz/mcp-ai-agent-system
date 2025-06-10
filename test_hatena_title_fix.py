#!/usr/bin/env python3
"""
はてなブログタイトル重複修正テストスクリプト
改良版 _clean_content メソッドの包括的テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.hatena_service import HatenaService
import logging

# ログレベルを設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_clean_content_method():
    """_clean_content メソッドの包括的テスト"""
    print("=" * 60)
    print("はてなブログタイトル重複修正テスト")
    print("=" * 60)
    
    hatena_service = HatenaService()
    
    # テストケース定義
    test_cases = [
        {
            "name": "基本的なタイトル重複",
            "title": "今日の料理レシピ",
            "content": "今日の料理レシピ\n\n美味しいパスタの作り方をご紹介します。\n材料：パスタ、トマト、チーズ",
            "expected_starts_with": "美味しいパスタの作り方"
        },
        {
            "name": "【】で囲まれたタイトル",
            "title": "AI技術の進歩",
            "content": "【AI技術の進歩】\n\n人工知能の最新動向について解説します。\n機械学習とディープラーニングの違い",
            "expected_starts_with": "人工知能の最新動向"
        },
        {
            "name": "HTMLタグ付きタイトル",
            "title": "プログラミング入門",
            "content": "<h1>プログラミング入門</h1>\n\nPythonの基礎を学びましょう。\n変数の使い方から始めます。",
            "expected_starts_with": "Pythonの基礎"
        },
        {
            "name": "強調タグ付きタイトル",
            "title": "データ分析の手法",
            "content": "<p><strong>データ分析の手法</strong></p>\n\n統計学の基本概念を説明します。\n平均値と中央値の違い",
            "expected_starts_with": "統計学の基本概念"
        },
        {
            "name": "句読点付きタイトル",
            "title": "旅行記録",
            "content": "旅行記録。\n\n京都への旅行について書きます。\n清水寺を訪れました。",
            "expected_starts_with": "京都への旅行"
        },
        {
            "name": "「」で囲まれたタイトル",
            "title": "読書感想文",
            "content": "「読書感想文」\n\n最近読んだ本の感想を書きます。\nとても面白い内容でした。",
            "expected_starts_with": "最近読んだ本"
        },
        {
            "name": "マークダウン形式タイトル",
            "title": "ウェブ開発",
            "content": "# ウェブ開発\n\nHTML、CSS、JavaScriptの基礎を学習します。\nレスポンシブデザインについて",
            "expected_starts_with": "HTML、CSS、JavaScript"
        },
        {
            "name": "複数行にわたるタイトル",
            "title": "長いタイトル\nの例",
            "content": "長いタイトル\nの例\n\n実際の内容はここから始まります。\n複数行タイトルの処理テスト",
            "expected_starts_with": "実際の内容"
        },
        {
            "name": "タイトルが含まれない場合",
            "title": "存在しないタイトル",
            "content": "このコンテンツにはタイトルが含まれていません。\n普通の本文内容です。",
            "expected_starts_with": "このコンテンツ"
        },
        {
            "name": "空のタイトル",
            "title": "",
            "content": "タイトルが空の場合のテスト\n内容はそのまま保持されるべきです。",
            "expected_starts_with": "タイトルが空"
        }
    ]
    
    # テスト実行
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- テストケース {i}: {test_case['name']} ---")
        print(f"タイトル: '{test_case['title']}'")
        print(f"元のコンテンツ:\n{test_case['content']}")
        
        # _clean_content メソッドを実行
        cleaned_content = hatena_service._clean_content(test_case['title'], test_case['content'])
        
        print(f"クリーンアップ後:\n{cleaned_content}")
        
        # 期待値チェック
        if cleaned_content.startswith(test_case['expected_starts_with']):
            print("✅ PASS: タイトル重複が正しく除去されました")
            success_count += 1
        else:
            print(f"❌ FAIL: 期待値 '{test_case['expected_starts_with']}' で始まりません")
        
        print("-" * 40)
    
    # 結果サマリー
    print(f"\n{'='*60}")
    print(f"テスト結果: {success_count}/{total_count} PASS")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("🎉 すべてのテストが成功しました！")
    else:
        print("⚠️  一部のテストが失敗しました。")
    
    return success_count == total_count

def test_actual_blog_post():
    """実際のブログ投稿テスト"""
    print("\n" + "=" * 60)
    print("実際のブログ投稿テスト")
    print("=" * 60)
    
    hatena_service = HatenaService()
    
    # テスト用記事データ
    test_article = {
        "title": "【テスト】タイトル重複修正テスト",
        "content": """【テスト】タイトル重複修正テスト

このテストでは、改良された _clean_content メソッドが正しく動作することを確認します。

## テスト内容
1. タイトルの重複除去
2. 様々なフォーマットへの対応
3. HTMLタグの適切な処理

## 期待される結果
- タイトルが本文から適切に除去される
- 本文の内容が保持される
- HTMLタグが正しく処理される

テスト実行日時: """ + str(datetime.now()),
        "tags": ["テスト", "AI", "プログラミング"],
        "draft": True  # 下書きとして投稿
    }
    
    try:
        print(f"テスト記事を投稿中...")
        print(f"タイトル: {test_article['title']}")
        print(f"下書きフラグ: {test_article['draft']}")
        
        result = hatena_service.publish_article(
            title=test_article['title'],
            content=test_article['content'],
            tags=test_article['tags'],
            draft=test_article['draft'],
            content_type="text/x-markdown"
        )
        
        if result:
            print("✅ ブログ投稿成功!")
            print(f"記事ID: {result.get('id', 'N/A')}")
            print(f"記事URL: {result.get('url', 'N/A')}")
            print(f"ステータス: {result.get('status', 'N/A')}")
            
            # 実際に投稿された内容を確認
            if result.get('url'):
                print(f"\n📄 投稿内容確認:")
                print(f"タイトル: {result.get('title', 'N/A')}")
                print(f"コンテンツ（先頭100文字）: {result.get('content', 'N/A')}")
            
            return True
        else:
            print("❌ ブログ投稿失敗")
            return False
            
    except Exception as e:
        print(f"❌ ブログ投稿エラー: {e}")
        return False

def main():
    """メイン実行関数"""
    print("はてなブログタイトル重複修正テストスクリプト")
    print("=" * 60)
    
    # 環境変数チェック
    required_env = ['HATENA_ID', 'HATENA_BLOG_ID', 'HATENA_API_KEY']
    missing_env = []
    
    for env_var in required_env:
        if not os.getenv(env_var):
            missing_env.append(env_var)
    
    if missing_env:
        print(f"⚠️  以下の環境変数が設定されていません: {', '.join(missing_env)}")
        print("_clean_content メソッドのテストのみ実行します。")
        
        # メソッドテストのみ実行
        method_test_success = test_clean_content_method()
        
        print("\n" + "=" * 60)
        print("テスト完了")
        print("=" * 60)
        
        if method_test_success:
            print("✅ _clean_content メソッドのテストが成功しました")
        else:
            print("❌ _clean_content メソッドのテストが失敗しました")
            
        return method_test_success
    
    # 両方のテストを実行
    print("1. _clean_content メソッドのテスト")
    method_test_success = test_clean_content_method()
    
    print("\n2. 実際のブログ投稿テスト")
    blog_test_success = test_actual_blog_post()
    
    # 最終結果
    print("\n" + "=" * 60)
    print("最終テスト結果")
    print("=" * 60)
    
    if method_test_success and blog_test_success:
        print("🎉 すべてのテストが成功しました！")
        print("タイトル重複修正機能が正常に動作しています。")
    elif method_test_success:
        print("✅ メソッドテストは成功しましたが、ブログ投稿テストが失敗しました。")
    else:
        print("❌ テストが失敗しました。修正が必要です。")
    
    return method_test_success and blog_test_success

if __name__ == "__main__":
    from datetime import datetime
    success = main()
    sys.exit(0 if success else 1)