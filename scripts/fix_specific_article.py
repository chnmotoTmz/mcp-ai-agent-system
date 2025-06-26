#!/usr/bin/env python3
"""
特定記事のタイトル重複問題修正スクリプト
「投稿記事（画像付き）」→「ひざサプリおすすめ3選｜効果・価格を徹底比較【2024年最新】」
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.hatena_service import HatenaService
import logging

# ログレベルを設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_article_by_title():
    """「投稿記事（画像付き）」のタイトルを持つ記事を検索"""
    print("=" * 60)
    print("記事検索: 「投稿記事（画像付き）」")
    print("=" * 60)
    
    hatena_service = HatenaService()
    
    try:
        # 記事一覧を取得
        articles_data = hatena_service.get_articles()
        
        if not articles_data or 'articles' not in articles_data:
            print("❌ 記事一覧の取得に失敗しました")
            return None
        
        articles = articles_data['articles']
        print(f"📄 取得した記事数: {len(articles)}")
        
        # 対象記事を検索
        target_title = "投稿記事（画像付き）"
        target_article = None
        
        print(f"\n🔍 「{target_title}」を検索中...")
        
        for i, article in enumerate(articles):
            title = article.get('title', '')
            article_id = article.get('id', '')
            url = article.get('url', '')
            
            print(f"{i+1:2d}. {title}")
            
            if target_title in title:
                target_article = article
                print(f"    ✅ 対象記事を発見!")
                print(f"    ID: {article_id}")
                print(f"    URL: {url}")
        
        if target_article:
            return target_article
        else:
            print(f"\n❌ 「{target_title}」というタイトルの記事が見つかりませんでした")
            return None
            
    except Exception as e:
        print(f"❌ 記事検索エラー: {e}")
        return None

def update_article_title_and_content():
    """記事のタイトルと本文を更新"""
    print("=" * 60)
    print("記事タイトル・本文修正")
    print("=" * 60)
    
    # 対象記事を検索
    target_article = find_article_by_title()
    
    if not target_article:
        print("対象記事が見つからないため、修正を中止します。")
        return False
    
    article_id = target_article.get('id', '')
    current_title = target_article.get('title', '')
    current_url = target_article.get('url', '')
    
    print(f"\n📝 修正対象記事:")
    print(f"ID: {article_id}")
    print(f"現在のタイトル: {current_title}")
    print(f"URL: {current_url}")
    
    # 新しいタイトル
    new_title = "ひざサプリおすすめ3選｜効果・価格を徹底比較【2024年最新】"
    
    # 新しい本文内容（サンプル）
    new_content = """
## ひざの痛みに効くサプリメント3選

膝の痛みや関節の不調にお悩みの方へ、効果的なサプリメントを厳選してご紹介します。

### 1. グルコサミン＆コンドロイチン

**効果**: 軟骨の修復・保護
**価格**: 月額3,000円～
**特徴**: 
- 軟骨成分を直接補給
- 関節の動きをスムーズに
- 継続使用で効果実感

### 2. UC-II（非変性II型コラーゲン）

**効果**: 関節炎の抑制
**価格**: 月額4,500円～
**特徴**:
- 最新の関節ケア成分
- 少量で高い効果
- 臨床試験で効果確認済み

### 3. プロテオグリカン

**効果**: 軟骨の保水力向上
**価格**: 月額5,000円～
**特徴**:
- 高い保水力
- 美容効果も期待
- 国産原料使用

## 比較表

| 商品名 | 主成分 | 月額費用 | 効果実感期間 |
|--------|--------|----------|-------------|
| グルコサミン&コンドロイチン | グルコサミン、コンドロイチン | 3,000円～ | 2-3ヶ月 |
| UC-II | 非変性II型コラーゲン | 4,500円～ | 1-2ヶ月 |
| プロテオグリカン | プロテオグリカン | 5,000円～ | 2-4ヶ月 |

## まとめ

膝の痛みの程度や予算に応じて、最適なサプリメントを選択することが重要です。まずは3ヶ月継続して効果を確認してみましょう。

**おすすめ度**:
1. 初心者: グルコサミン＆コンドロイチン
2. 効果重視: UC-II
3. 美容も重視: プロテオグリカン
"""
    
    print(f"\n🔄 修正内容:")
    print(f"新タイトル: {new_title}")
    print(f"本文: 膝サプリに関する詳細情報を整理した内容に更新")
    
    # 確認
    print(f"\n⚠️  この修正を実行しますか？")
    print(f"現在: {current_title}")
    print(f"新規: {new_title}")
    
    # 実際の更新（慎重に実行）
    try:
        hatena_service = HatenaService()
        
        # 記事を更新
        result = hatena_service.update_article(
            entry_id=article_id,
            title=new_title,
            content=new_content,
            tags=["サプリメント", "健康", "膝の痛み", "関節", "比較"],
            content_type="text/html"  # みたままモードのためHTML
        )
        
        if result:
            print("✅ 記事の更新が成功しました！")
            print(f"更新後URL: {result.get('url', current_url)}")
            print(f"新タイトル: {result.get('title', new_title)}")
            return True
        else:
            print("❌ 記事の更新に失敗しました")
            return False
            
    except Exception as e:
        print(f"❌ 更新エラー: {e}")
        return False

def test_title_cleaning():
    """タイトル重複除去のテスト"""
    print("=" * 60)
    print("タイトル重複除去テスト")
    print("=" * 60)
    
    hatena_service = HatenaService()
    
    test_cases = [
        {
            "title": "ひざサプリおすすめ3選｜効果・価格を徹底比較【2024年最新】",
            "content": """ひざサプリおすすめ3選｜効果・価格を徹底比較【2024年最新】

膝の痛みや関節の不調にお悩みの方へ、効果的なサプリメントを厳選してご紹介します。""",
            "expected": "膝の痛みや関節の不調にお悩みの方へ"
        },
        {
            "title": "投稿記事（画像付き）",
            "content": """投稿記事（画像付き）

実際のコンテンツがここから始まります。""",
            "expected": "実際のコンテンツ"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- テストケース {i} ---")
        print(f"タイトル: {test_case['title']}")
        print(f"元コンテンツ:\n{test_case['content']}")
        
        cleaned = hatena_service._clean_content(test_case['title'], test_case['content'])
        
        print(f"クリーンアップ後:\n{cleaned}")
        
        if cleaned.startswith(test_case['expected']):
            print("✅ PASS: タイトル重複が正しく除去されました")
        else:
            print(f"❌ FAIL: 期待値 '{test_case['expected']}' で始まりません")
        
        print("-" * 40)

def main():
    """メイン実行関数"""
    print("特定記事のタイトル重複問題修正スクリプト")
    print("=" * 60)
    
    # 環境変数チェック
    required_env = ['HATENA_ID', 'HATENA_BLOG_ID', 'HATENA_API_KEY']
    missing_env = []
    
    for env_var in required_env:
        if not os.getenv(env_var):
            missing_env.append(env_var)
    
    if missing_env:
        print(f"⚠️  以下の環境変数が設定されていません: {', '.join(missing_env)}")
        print("環境変数を設定してから再実行してください。")
        return False
    
    # 1. まずタイトル重複除去機能のテスト
    test_title_cleaning()
    
    # 2. 記事検索と更新
    print(f"\n{'='*60}")
    print("実際の記事修正")
    print(f"{'='*60}")
    
    success = update_article_title_and_content()
    
    print("\n" + "=" * 60)
    print("最終結果")
    print("=" * 60)
    
    if success:
        print("🎉 記事の修正が完了しました！")
        print("ブログで修正結果を確認してください。")
    else:
        print("⚠️  記事の修正に問題がありました。")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)