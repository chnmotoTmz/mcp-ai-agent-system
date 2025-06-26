#!/usr/bin/env python3
"""
はてなブログ画像埋め込み修正ツール
画像URLを正しいHTMLタグに変換
"""

import re
import sys
import os

# プロジェクトパスを追加
sys.path.append('/home/moto/line-gemini-hatena-integration')

def fix_image_urls_in_content(content):
    """
    コンテンツ内の画像URLを正しいHTMLタグに変換
    
    Args:
        content (str): 記事コンテンツ
    
    Returns:
        str: 修正後のコンテンツ
    """
    
    # Imgurの画像URL pattern
    imgur_pattern = r'https://i\.imgur\.com/[a-zA-Z0-9]+\.(jpg|jpeg|png|gif)'
    
    def replace_with_img_tag(match):
        url = match.group(0)
        return f'<img src="{url}" alt="アップロード画像" style="max-width:100%; height:auto;" />'
    
    # URLをimgタグに置換
    fixed_content = re.sub(imgur_pattern, replace_with_img_tag, content)
    
    return fixed_content

def create_proper_image_html(image_url, alt_text="", caption="", max_width="100%"):
    """
    はてなブログ用の適切な画像HTMLを生成
    
    Args:
        image_url (str): 画像URL
        alt_text (str): alt属性
        caption (str): キャプション
        max_width (str): 最大幅
    
    Returns:
        str: 画像HTML
    """
    
    html_parts = []
    
    # 画像タグ
    img_tag = f'<img src="{image_url}" alt="{alt_text}" style="max-width:{max_width}; height:auto; display:block; margin:10px auto;" />'
    html_parts.append(img_tag)
    
    # キャプション
    if caption:
        caption_tag = f'<p style="text-align:center; font-size:0.9em; color:#666; margin:5px 0;">{caption}</p>'
        html_parts.append(caption_tag)
    
    return '\n'.join(html_parts)

def test_image_embedding():
    """画像埋め込みテスト"""
    
    print("🖼️  はてなブログ画像埋め込みテスト")
    print("=" * 40)
    
    # テスト用コンテンツ
    test_content = """
今日の写真です！

https://i.imgur.com/GfL9ffP.jpeg

この画像は CLI でアップロードしました。
    """
    
    print("📝 修正前のコンテンツ:")
    print(test_content)
    print("\n" + "=" * 40)
    
    # 修正処理
    fixed_content = fix_image_urls_in_content(test_content)
    
    print("✨ 修正後のコンテンツ:")
    print(fixed_content)
    print("\n" + "=" * 40)
    
    # 手動画像HTML生成例
    print("🎨 手動生成例:")
    manual_html = create_proper_image_html(
        image_url="https://i.imgur.com/GfL9ffP.jpeg",
        alt_text="CLIテストアップロード画像",
        caption="コマンドライン経由でアップロードされた画像",
        max_width="80%"
    )
    print(manual_html)
    
    return fixed_content

def create_sample_blog_post():
    """サンプルブログ記事作成"""
    
    title = "画像テスト記事（修正版）"
    
    content = """
<h3>🖼️ 画像表示テスト</h3>

<p>このテストでは、Imgur経由でアップロードした画像が正しく表示されるかを確認します。</p>

<img src="https://i.imgur.com/GfL9ffP.jpeg" alt="CLIテストアップロード画像" style="max-width:80%; height:auto; display:block; margin:20px auto;" />

<p style="text-align:center; font-size:0.9em; color:#666; margin:5px 0;">コマンドライン経由でアップロードされた画像</p>

<h4>📊 画像情報</h4>
<ul>
<li>アップロード方法: Imgur MCP CLI</li>
<li>サイズ: 958x1708ピクセル</li>
<li>ファイルサイズ: 約472KB</li>
<li>形式: JPEG</li>
</ul>

<h4>🛠️ 技術的詳細</h4>
<p>この画像は以下の手順でアップロードされました：</p>
<ol>
<li>LINE Bot経由で画像を受信</li>
<li>Imgur MCPサーバーで処理</li>
<li>自動でHTMLタグに変換</li>
<li>はてなブログに投稿</li>
</ol>

<p><strong>✅ 画像が正常に表示されていれば、システムは正常に動作しています！</strong></p>
    """
    
    return title, content

async def post_fixed_article():
    """修正された記事を投稿"""
    try:
        from src.services.hatena_service import HatenaService
        
        print("📝 修正版記事投稿開始...")
        
        hatena_service = HatenaService()
        title, content = create_sample_blog_post()
        
        result = hatena_service.publish_article(
            title=title,
            content=content,
            tags=['画像テスト', 'Imgur', 'MCP', 'CLI'],
            category='テクノロジー',
            draft=False
        )
        
        if result and result.get('url'):
            print(f"✅ 修正版記事投稿成功!")
            print(f"🔗 URL: {result['url']}")
            print(f"🆔 ID: {result.get('id')}")
            return result['url']
        else:
            print("❌ 記事投稿失敗")
            return None
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

def main():
    """メイン実行"""
    
    print("🔧 はてなブログ画像埋め込み修正ツール")
    print("Version: 1.0.0")
    print("")
    
    # 修正テスト
    test_image_embedding()
    
    print("\n" + "=" * 50)
    print("📌 修正のポイント:")
    print("1. 画像URLを <img> タグに変換")
    print("2. レスポンシブデザイン対応 (max-width: 100%)")
    print("3. 中央揃え表示")
    print("4. 適切なalt属性とキャプション")
    print("5. はてなブログのHTML形式に準拠")
    
    print("\n🚀 修正版記事を投稿しますか？ (y/N): ", end="")
    user_input = input().strip().lower()
    
    if user_input in ['y', 'yes']:
        import asyncio
        result_url = asyncio.run(post_fixed_article())
        if result_url:
            print(f"\n🎉 修正版記事が投稿されました: {result_url}")
            print("この記事で画像が正しく表示されているか確認してください！")
    else:
        print("❌ 投稿をキャンセルしました")

if __name__ == "__main__":
    main()