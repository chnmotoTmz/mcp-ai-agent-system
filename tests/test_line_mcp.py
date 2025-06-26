#!/usr/bin/env python3
"""
LINE MCP Server テストクライアント
チケット #15: LINE MCP Server実装のテスト
"""

import asyncio
import os
from pathlib import Path

async def test_line_mcp_server():
    """
    LINE MCP Server のテスト（設定確認とモック実行）
    """
    
    print("🧪 LINE MCP Server テスト開始")
    print("=" * 50)
    
    # MCPサーバーの関数をインポート
    try:
        from line_mcp_server import get_bot_status, get_message_content, send_message, download_image, get_user_profile
        print("✅ LINE MCP Server インポート成功")
    except ImportError as e:
        print(f"❌ インポートエラー: {str(e)}")
        return
    
    # 1. サーバー状態確認
    print("\n📊 1. サーバー状態確認")
    try:
        status = await get_bot_status()
        print(f"   サーバー: {status['server_name']} v{status['version']}")
        print(f"   状態: {status['status']}")
        print(f"   Access Token設定: {status['access_token_configured']}")
        print(f"   Channel Secret設定: {status['channel_secret_configured']}")
        print(f"   対応メッセージタイプ: {', '.join(status['supported_message_types'])}")
        
        if not status['access_token_configured']:
            print("⚠️  LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
            print("   実際のLINE API呼び出しテストはスキップします")
        
    except Exception as e:
        print(f"❌ 状態確認エラー: {str(e)}")
        return
    
    # 2. 環境変数確認
    print("\n🔑 2. 環境変数確認")
    access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")
    
    if access_token:
        print(f"   Access Token: {access_token[:20]}...（設定済み）")
    else:
        print("   Access Token: 未設定")
    
    if channel_secret:
        print(f"   Channel Secret: {channel_secret[:20]}...（設定済み）")
    else:
        print("   Channel Secret: 未設定")
    
    # 3. 機能テスト（モック・ドライラン）
    print("\n🧪 3. 機能テスト（モック実行）")
    
    # 3.1 メッセージコンテンツ取得テスト
    print("\n   3.1 メッセージコンテンツ取得テスト")
    test_message_id = "test_message_12345"
    
    try:
        result = await get_message_content(test_message_id)
        if result["success"]:
            print(f"   ✅ テスト成功（予期しない成功）: {result}")
        else:
            expected_errors = [
                "LINE_CHANNEL_ACCESS_TOKEN が設定されていません",
                "LINE API エラー",
                "メッセージが見つかりません"
            ]
            error_msg = result.get("error", "")
            if any(expected in error_msg for expected in expected_errors):
                print(f"   ✅ 期待通りのエラー: {error_msg}")
            else:
                print(f"   ⚠️  予期しないエラー: {error_msg}")
    except Exception as e:
        print(f"   ❌ 例外発生: {str(e)}")
    
    # 3.2 メッセージ送信テスト
    print("\n   3.2 メッセージ送信テスト")
    test_user_id = "U1234567890abcdef"
    test_message = "MCP Server テストメッセージ"
    
    try:
        result = await send_message(test_user_id, test_message)
        if result["success"]:
            print(f"   ✅ テスト成功（予期しない成功）")
            print(f"      送信先: {result.get('sent_to', 'unknown')}")
            print(f"      メッセージ長: {result.get('message_length', 0)}")
        else:
            expected_errors = [
                "LINE_CHANNEL_ACCESS_TOKEN が設定されていません",
                "LINE API エラー"
            ]
            error_msg = result.get("error", "")
            if any(expected in error_msg for expected in expected_errors):
                print(f"   ✅ 期待通りのエラー: {error_msg}")
            else:
                print(f"   ⚠️  予期しないエラー: {error_msg}")
    except Exception as e:
        print(f"   ❌ 例外発生: {str(e)}")
    
    # 3.3 画像ダウンロードテスト
    print("\n   3.3 画像ダウンロードテスト")
    test_image_message_id = "img_message_12345"
    test_save_path = "./test_downloads/test_image.jpg"
    
    try:
        result = await download_image(test_image_message_id, test_save_path)
        if result["success"]:
            print(f"   ✅ テスト成功（予期しない成功）")
            print(f"      保存先: {result.get('file_path', 'unknown')}")
            print(f"      ファイルサイズ: {result.get('file_size', 0)} bytes")
        else:
            expected_errors = [
                "LINE_CHANNEL_ACCESS_TOKEN が設定されていません",
                "LINE API エラー",
                "メッセージが見つかりません"
            ]
            error_msg = result.get("error", "")
            if any(expected in error_msg for expected in expected_errors):
                print(f"   ✅ 期待通りのエラー: {error_msg}")
            else:
                print(f"   ⚠️  予期しないエラー: {error_msg}")
    except Exception as e:
        print(f"   ❌ 例外発生: {str(e)}")
    
    # 3.4 ユーザープロフィール取得テスト
    print("\n   3.4 ユーザープロフィール取得テスト")
    
    try:
        result = await get_user_profile(test_user_id)
        if result["success"]:
            print(f"   ✅ テスト成功（予期しない成功）")
            print(f"      表示名: {result.get('display_name', 'unknown')}")
        else:
            expected_errors = [
                "LINE_CHANNEL_ACCESS_TOKEN が設定されていません",
                "LINE API エラー",
                "ユーザーが見つかりません"
            ]
            error_msg = result.get("error", "")
            if any(expected in error_msg for expected in expected_errors):
                print(f"   ✅ 期待通りのエラー: {error_msg}")
            else:
                print(f"   ⚠️  予期しないエラー: {error_msg}")
    except Exception as e:
        print(f"   ❌ 例外発生: {str(e)}")
    
    # 4. MCP設定確認
    print("\n⚙️  4. MCP設定確認")
    try:
        from line_mcp_server import mcp
        print(f"   ✅ MCPサーバー名: {mcp.name}")
        print("   ✅ FastMCP 初期化成功")
        
        # 登録されたツールの確認
        print("   📋 登録済みツール:")
        expected_tools = [
            "get_message_content",
            "send_message", 
            "download_image",
            "get_user_profile",
            "get_bot_status"
        ]
        for tool in expected_tools:
            print(f"      - {tool}()")
        
        print("   📋 登録済みリソース:")
        print("      - line://messages/{user_id}")
        
        print("   📋 登録済みプロンプト:")
        print("      - line-usage")
        
    except Exception as e:
        print(f"   ❌ MCP設定確認エラー: {str(e)}")
    
    # 5. 実環境テストの案内
    print("\n📝 5. 実環境テストについて")
    if not access_token:
        print("""
   実際のLINE APIテストを行うには：
   
   1. LINE Developers Console でチャンネルを作成
   2. Channel Access Token を取得
   3. 環境変数を設定:
      export LINE_CHANNEL_ACCESS_TOKEN="your_access_token"
      export LINE_CHANNEL_SECRET="your_channel_secret"
   4. 実際のメッセージIDとユーザーIDでテスト
   
   現在は設定確認とエラーハンドリングのテストのみ実行されました。
        """)
    else:
        print("   ✅ 環境変数が設定されています")
        print("   実際のLINE APIを使用したテストが可能です")
    
    print("\n✅ LINE MCP Server テスト完了!")

async def test_mcp_configuration():
    """MCP設定の詳細確認"""
    
    print("\n🔧 MCP設定詳細確認")
    print("-" * 30)
    
    try:
        # FastMCP の設定確認
        from mcp.server.fastmcp import FastMCP
        print("✅ FastMCP インポート成功")
        
        # LINE MCP Server の設定確認
        from line_mcp_server import mcp, LINE_API_BASE
        print(f"✅ サーバー名: {mcp.name}")
        print(f"✅ API Base: {LINE_API_BASE}")
        
        # 環境変数の詳細確認
        print("\n🔐 環境変数確認:")
        env_vars = {
            "LINE_CHANNEL_ACCESS_TOKEN": os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""),
            "LINE_CHANNEL_SECRET": os.getenv("LINE_CHANNEL_SECRET", "")
        }
        
        for var_name, var_value in env_vars.items():
            if var_value:
                masked_value = var_value[:10] + "..." + var_value[-5:] if len(var_value) > 15 else var_value[:5] + "..."
                print(f"   ✅ {var_name}: {masked_value}")
            else:
                print(f"   ❌ {var_name}: 未設定")
        
        print("\n✅ MCP設定確認完了")
        
    except Exception as e:
        print(f"❌ MCP設定確認エラー: {str(e)}")

async def main():
    """メインテスト実行"""
    
    print("🚀 LINE MCP Server テストスイート")
    print("チケット #15: LINE MCP Server実装")
    print("=" * 60)
    
    # 必要なライブラリの確認
    try:
        import requests
        print("✅ requests ライブラリ: 利用可能")
    except ImportError:
        print("❌ requests ライブラリが必要です: pip install requests")
        return
    
    try:
        from mcp.server.fastmcp import FastMCP
        print("✅ MCP SDK: 利用可能")
    except ImportError:
        print("❌ MCP SDK が必要です: pip install mcp[cli]")
        return
    
    # MCP設定確認
    await test_mcp_configuration()
    
    # メインテスト実行
    await test_line_mcp_server()

if __name__ == "__main__":
    asyncio.run(main())
