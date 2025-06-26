#!/usr/bin/env python3
"""
はてなブログ みたままモード確認テスト
設定変更後の動作確認
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

def test_visual_mode():
    """みたままモード設定後のテスト"""
    print("=" * 60)
    print("はてなブログ みたままモード確認テスト")
    print("=" * 60)
    
    hatena_service = HatenaService()
    
    # マークダウン記法のテストコンテンツ
    markdown_content = """
## みたままモード テスト

ブログの設定を「みたままモード」に変更しました。

### 1. マークダウン記法のテスト
- **太字テキスト**
- *斜体テキスト*
- `インラインコード`

### 2. リスト
1. 項目1
2. 項目2
3. 項目3

### 3. コードブロック
```python
def hello():
    print("Hello, World!")
    return True
```

### 4. リンク
[Google](https://www.google.com)

> 引用ブロック
> みたままモードでの表示を確認

**テスト実行日時**: """ + str(datetime.now()) + """

**期待される動作**:
- みたままモードではマークダウン記法が解釈されない
- 記号がそのまま表示される
"""

    # HTMLのテストコンテンツ
    html_content = """
<h2>みたままモード HTMLテスト</h2>

<p>ブログの設定を「みたままモード」に変更しました。</p>

<h3>1. HTML記法のテスト</h3>
<ul>
<li><strong>太字テキスト</strong></li>
<li><em>斜体テキスト</em></li>
<li><code>インラインコード</code></li>
</ul>

<h3>2. リスト</h3>
<ol>
<li>項目1</li>
<li>項目2</li>
<li>項目3</li>
</ol>

<h3>3. コードブロック</h3>
<pre><code>def hello():
    print("Hello, World!")
    return True</code></pre>

<h3>4. リンク</h3>
<p><a href="https://www.google.com">Google</a></p>

<blockquote>
<p>引用ブロック<br>
みたままモードでの表示を確認</p>
</blockquote>

<p><strong>テスト実行日時</strong>: """ + str(datetime.now()) + """</p>

<p><strong>期待される動作</strong>:</p>
<ul>
<li>みたままモードではHTMLタグが正しく解釈される</li>
<li>見た目に近い形で表示される</li>
</ul>
"""

    test_cases = [
        {
            "name": "マークダウン記法 (みたままモード)",
            "title": "【確認】みたままモード マークダウンテスト",
            "content": markdown_content,
            "content_type": "text/x-markdown",
            "tags": ["テスト", "みたままモード", "マークダウン"]
        },
        {
            "name": "HTML記法 (みたままモード)",
            "title": "【確認】みたままモード HTMLテスト", 
            "content": html_content,
            "content_type": "text/html",
            "tags": ["テスト", "みたままモード", "HTML"]
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
                    'title': test_case['title']
                })
            else:
                print("❌ 投稿失敗")
                results.append({
                    'test_name': test_case['name'],
                    'content_type': test_case['content_type'],
                    'success': False
                })
                
        except Exception as e:
            print(f"❌ エラー: {e}")
            results.append({
                'test_name': test_case['name'],
                'content_type': test_case['content_type'],
                'success': False,
                'error': str(e)
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
        if result['success']:
            status = "✅ 成功"
            print(f"{status} | {result['test_name']}")
            print(f"         URL: {result['url']}")
            print(f"         実際の表示を確認してください")
        else:
            status = "❌ 失敗"
            print(f"{status} | {result['test_name']}")
    
    print(f"\n{'='*60}")
    print("確認項目")
    print(f"{'='*60}")
    print("📝 ブログで確認すべき項目:")
    print("1. マークダウン記法の記号がそのまま表示されているか")
    print("2. HTMLタグが正しく解釈されているか")
    print("3. タイトルの重複が適切に除去されているか")
    print("4. 全体的な見た目が期待通りか")
    
    print(f"\n💡 みたままモードの特徴:")
    print("- マークダウン記法: 記号がそのまま表示される")
    print("- HTML記法: タグが正しく解釈される")
    print("- WYSIWYG（見た目通り）の編集・表示")
    
    return success_count == total_count

def main():
    """メイン実行関数"""
    print("はてなブログ みたままモード確認テストスクリプト")
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
    success = test_visual_mode()
    
    print("\n" + "=" * 60)
    print("最終結果")
    print("=" * 60)
    
    if success:
        print("🎉 すべてのテストが成功しました！")
        print("投稿されたブログ記事で実際の表示を確認してください。")
    else:
        print("⚠️  一部のテストが失敗しました。")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)