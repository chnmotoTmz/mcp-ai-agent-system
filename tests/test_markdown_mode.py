#!/usr/bin/env python3
"""
はてなブログ マークダウンモード設定テスト
異なるcontent_typeでの投稿テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.hatena_service import HatenaService
from datetime import datetime
import logging

# ログレベルを設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_different_content_types():
    """異なるcontent_typeでの投稿テスト"""
    print("=" * 60)
    print("はてなブログ マークダウンモード設定テスト")
    print("=" * 60)
    
    hatena_service = HatenaService()
    
    # テスト用記事データ（マークダウン形式）
    markdown_content = """
## テスト概要
このテストでは以下を確認します：

### 1. マークダウン記法の動作
- **太字テキスト**
- *斜体テキスト*
- `インラインコード`

### 2. リスト表示
1. 番号付きリスト1
2. 番号付きリスト2
3. 番号付きリスト3

- 箇条書き1
- 箇条書き2
- 箇条書き3

### 3. コードブロック
```python
def hello_world():
    print("Hello, World!")
    return True
```

### 4. リンクテスト
[Google](https://www.google.com)

> 引用ブロックのテスト
> マークダウンが正しく動作するかを確認

**テスト実行日時**: """ + str(datetime.now())

    # HTMLコンテンツ
    html_content = """
<h2>テスト概要</h2>
<p>このテストでは以下を確認します：</p>

<h3>1. HTML記法の動作</h3>
<ul>
<li><strong>太字テキスト</strong></li>
<li><em>斜体テキスト</em></li>
<li><code>インラインコード</code></li>
</ul>

<h3>2. リスト表示</h3>
<ol>
<li>番号付きリスト1</li>
<li>番号付きリスト2</li>
<li>番号付きリスト3</li>
</ol>

<h3>3. コードブロック</h3>
<pre><code>def hello_world():
    print("Hello, World!")
    return True</code></pre>

<h3>4. リンクテスト</h3>
<p><a href="https://www.google.com">Google</a></p>

<blockquote>
<p>引用ブロックのテスト<br>
HTMLが正しく動作するかを確認</p>
</blockquote>

<p><strong>テスト実行日時</strong>: """ + str(datetime.now()) + "</p>"

    test_cases = [
        {
            "name": "マークダウンモード投稿",
            "title": "【テスト】マークダウンモード確認",
            "content": markdown_content,
            "content_type": "text/x-markdown",
            "tags": ["テスト", "マークダウン", "API"]
        },
        {
            "name": "HTMLモード投稿", 
            "title": "【テスト】HTMLモード確認",
            "content": html_content,
            "content_type": "text/html",
            "tags": ["テスト", "HTML", "API"]
        },
        {
            "name": "はてな記法モード投稿",
            "title": "【テスト】はてな記法モード確認", 
            "content": markdown_content,  # はてな記法も基本的にはマークダウンベース
            "content_type": "text/x-hatena-syntax",
            "tags": ["テスト", "はてな記法", "API"]
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- テストケース {i}: {test_case['name']} ---")
        print(f"Content-Type: {test_case['content_type']}")
        print(f"タイトル: {test_case['title']}")
        
        try:
            result = hatena_service.publish_article(
                title=test_case['title'],
                content=test_case['content'],
                tags=test_case['tags'],
                draft=True,  # 下書きとして投稿
                content_type=test_case['content_type']
            )
            
            if result:
                print("✅ 投稿成功!")
                print(f"記事ID: {result.get('id', 'N/A')}")
                print(f"記事URL: {result.get('url', 'N/A')}")
                
                results.append({
                    'test_name': test_case['name'],
                    'content_type': test_case['content_type'],
                    'success': True,
                    'url': result.get('url', ''),
                    'id': result.get('id', '')
                })
            else:
                print("❌ 投稿失敗")
                results.append({
                    'test_name': test_case['name'],
                    'content_type': test_case['content_type'],
                    'success': False,
                    'url': '',
                    'id': ''
                })
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            results.append({
                'test_name': test_case['name'],
                'content_type': test_case['content_type'],
                'success': False,
                'error': str(e),
                'url': '',
                'id': ''
            })
        
        print("-" * 40)
    
    # 結果サマリー
    print(f"\n{'='*60}")
    print("テスト結果サマリー")
    print(f"{'='*60}")
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    
    print(f"成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    for result in results:
        status = "✅ 成功" if result['success'] else "❌ 失敗"
        print(f"{status} | {result['test_name']} | {result['content_type']}")
        if result['success']:
            print(f"         URL: {result['url']}")
    
    print(f"\n{'='*60}")
    print("注意事項")
    print(f"{'='*60}")
    print("※ はてなブログのAPI仕様により、実際の表示形式は")
    print("   ブログの「基本設定」→「編集モード」の設定に依存します。")
    print("※ API経由では個別記事ごとの編集モード指定は効果がない可能性があります。")
    print("※ 投稿後にブログで確認して、実際の表示を検証してください。")
    
    return success_count == total_count

def main():
    """メイン実行関数"""
    print("はてなブログ マークダウンモード設定テストスクリプト")
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
    
    # テスト実行
    success = test_different_content_types()
    
    print("\n" + "=" * 60)
    print("最終結果")
    print("=" * 60)
    
    if success:
        print("🎉 すべてのテストが成功しました！")
    else:
        print("⚠️  一部のテストが失敗しました。")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)