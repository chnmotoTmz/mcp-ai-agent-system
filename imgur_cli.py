#!/usr/bin/env python3
"""
Imgur MCP コマンドライン実行ツール
画像アップロード・削除・情報取得をコマンドラインから実行
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path

# プロジェクトパスを追加
sys.path.append('/home/moto/line-gemini-hatena-integration')

async def upload_command(args):
    """画像アップロードコマンド"""
    try:
        from src.mcp_servers.imgur_server_fastmcp import upload_image
        
        print(f"📤 画像アップロード開始: {args.image}")
        
        # パス検証
        if not Path(args.image).exists():
            print(f"❌ ファイルが見つかりません: {args.image}")
            return 1
        
        result = await upload_image(
            image_path=args.image,
            title=args.title or "",
            description=args.description or "",
            privacy=args.privacy
        )
        
        if result.get('success'):
            print("✅ アップロード成功!")
            print(f"🔗 URL: {result.get('url')}")
            print(f"🆔 ID: {result.get('imgur_id')}")
            print(f"🗑️  削除ハッシュ: {result.get('delete_hash')}")
            
            if args.size:
                print(f"📐 サイズ: {result.get('width')}x{result.get('height')}")
                print(f"📏 ファイルサイズ: {result.get('file_size_mb')}MB")
            
            # URLのみ出力オプション
            if args.url_only:
                print(result.get('url'))
            
            return 0
        else:
            print(f"❌ アップロード失敗: {result.get('error')}")
            return 1
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1

async def info_command(args):
    """画像情報取得コマンド"""
    try:
        from src.mcp_servers.imgur_server_fastmcp import get_image_info
        
        print(f"ℹ️  画像情報取得: {args.image_id}")
        
        result = await get_image_info(args.image_id)
        
        if result.get('success'):
            print("✅ 情報取得成功!")
            print(f"🆔 ID: {result.get('id')}")
            print(f"📝 タイトル: {result.get('title') or '(なし)'}")
            print(f"📄 説明: {result.get('description') or '(なし)'}")
            print(f"🔗 URL: {result.get('url')}")
            print(f"📐 サイズ: {result.get('width')}x{result.get('height')}")
            print(f"📏 ファイルサイズ: {result.get('size')} bytes")
            print(f"👁️  ビュー数: {result.get('views')}")
            
            return 0
        else:
            print(f"❌ 情報取得失敗: {result.get('error')}")
            return 1
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1

async def delete_command(args):
    """画像削除コマンド"""
    try:
        from src.mcp_servers.imgur_server_fastmcp import delete_image
        
        # 確認プロンプト
        if not args.force:
            confirm = input(f"🗑️  本当に削除しますか？ (削除ハッシュ: {args.delete_hash[:10]}...) [y/N]: ")
            if confirm.lower() not in ['y', 'yes']:
                print("❌ キャンセルされました")
                return 0
        
        print(f"🗑️  画像削除開始: {args.delete_hash}")
        
        result = await delete_image(args.delete_hash)
        
        if result.get('success'):
            print("✅ 削除成功!")
            return 0
        else:
            print(f"❌ 削除失敗: {result.get('error')}")
            return 1
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1

async def health_command(args):
    """ヘルスチェックコマンド"""
    try:
        from src.mcp_servers.imgur_server_fastmcp import health_check
        
        print("🏥 Imgur MCP ヘルスチェック...")
        
        result = await health_check()
        
        print(f"📊 ステータス: {result.get('status')}")
        print(f"🔧 サービス: {result.get('service')}")
        print(f"📱 バージョン: {result.get('version')}")
        print(f"🌐 API状態: {result.get('api_status')}")
        print(f"🔑 Client ID: {'設定済み' if result.get('client_id_configured') else '未設定'}")
        
        # レート制限情報
        rate_limit = result.get('rate_limit', {})
        if rate_limit:
            print(f"📈 レート制限:")
            print(f"   Client残り: {rate_limit.get('client_remaining')}")
            print(f"   Client制限: {rate_limit.get('client_limit')}")
        
        return 0 if result.get('status') == 'healthy' else 1
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1

async def usage_command(args):
    """使用量確認コマンド"""
    try:
        from src.mcp_servers.imgur_server_fastmcp import get_usage_resource
        
        print("📊 Imgur API使用量確認...")
        
        usage_info = await get_usage_resource()
        print(usage_info)
        
        return 0
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Imgur MCP コマンドラインツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 画像アップロード
  python imgur_cli.py upload image.jpg --title "テスト画像"
  
  # URLのみ取得
  python imgur_cli.py upload image.jpg --url-only
  
  # 画像情報取得
  python imgur_cli.py info k1dYn2A
  
  # 画像削除
  python imgur_cli.py delete cwtxe1MEImcgxog
  
  # ヘルスチェック
  python imgur_cli.py health
  
  # 使用量確認
  python imgur_cli.py usage
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='利用可能なコマンド')
    
    # アップロードコマンド
    upload_parser = subparsers.add_parser('upload', help='画像をアップロード')
    upload_parser.add_argument('image', help='アップロードする画像ファイルのパス')
    upload_parser.add_argument('--title', '-t', help='画像のタイトル')
    upload_parser.add_argument('--description', '-d', help='画像の説明')
    upload_parser.add_argument('--privacy', '-p', choices=['public', 'hidden', 'secret'], 
                              default='hidden', help='プライバシー設定 (デフォルト: hidden)')
    upload_parser.add_argument('--size', '-s', action='store_true', help='サイズ情報も表示')
    upload_parser.add_argument('--url-only', '-u', action='store_true', help='URLのみ出力')
    
    # 情報取得コマンド
    info_parser = subparsers.add_parser('info', help='画像情報を取得')
    info_parser.add_argument('image_id', help='画像ID')
    
    # 削除コマンド
    delete_parser = subparsers.add_parser('delete', help='画像を削除')
    delete_parser.add_argument('delete_hash', help='削除ハッシュ')
    delete_parser.add_argument('--force', '-f', action='store_true', help='確認なしで削除')
    
    # ヘルスチェックコマンド
    health_parser = subparsers.add_parser('health', help='ヘルスチェック')
    
    # 使用量確認コマンド
    usage_parser = subparsers.add_parser('usage', help='API使用量確認')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 環境変数確認
    if not os.getenv('IMGUR_CLIENT_ID'):
        print("❌ IMGUR_CLIENT_IDが設定されていません")
        print("export IMGUR_CLIENT_ID=your_client_id を実行してください")
        return 1
    
    # コマンド実行
    command_map = {
        'upload': upload_command,
        'info': info_command,
        'delete': delete_command,
        'health': health_command,
        'usage': usage_command
    }
    
    try:
        result = asyncio.run(command_map[args.command](args))
        return result
    except KeyboardInterrupt:
        print("\n❌ ユーザーによってキャンセルされました")
        return 1
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())