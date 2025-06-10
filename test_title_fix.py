#!/usr/bin/env python3
"""
タイトル重複修正のテスト
"""

import sys
import asyncio

# プロジェクトパスを追加
sys.path.append('/home/moto/line-gemini-hatena-integration')

async def test_title_fix():
    """タイトル重複修正をテスト"""
    try:
        from src.services.hatena_service import HatenaService

        print("📝 タイトル重複修正テスト開始...")

        hatena_service = HatenaService()

        title = "タイトル重複修正テスト"

        # タイトルが重複している問題のあるコンテンツを作成
        content_with_title = f"""<h1>{title}</h1>

<p>これはタイトル重複修正のテストです。</p>

<p>本文の先頭にタイトルが表示されていた問題を修正しました。</p>

<ul>
<li>HTMLタグでのタイトル重複を検出・除去</li>
<li>プレーンテキストでのタイトル重複を検出・除去</li>
<li>先頭の空行も適切に処理</li>
</ul>

<p>この記事でタイトルが重複表示されていなければ、修正は成功です！</p>"""

        print("🔍 修正前のコンテンツ:")
        print(content_with_title[:200] + "...")

        # _clean_content メソッドを直接テスト
        cleaned = hatena_service._clean_content(title, content_with_title)
        print("\n🧹 修正後のコンテンツ:")
        print(cleaned[:200] + "...")

        # 実際にブログに投稿
        result = hatena_service.publish_article(
            title=title,
            content=content_with_title,  # 意図的にタイトル重複があるコンテンツを使用
            tags=['テスト', 'タイトル修正'],
            category='',
            draft=False
        )

        if result and result.get('url'):
            print(f"\n✅ タイトル重複修正テスト記事投稿成功!")
            print(f"🔗 URL: {result['url']}")
            print(f"🆔 ID: {result.get('id')}")
            print("")
            print("📖 この記事でタイトルが重複表示されていないかチェックしてください！")

            return result['url']
        else:
            print("❌ 記事投稿失敗")
            print(f"結果: {result}")
            return None

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_title_fix())
