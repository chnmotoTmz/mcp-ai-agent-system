#!/usr/bin/env python3
"""
Imgur簡単テストスクリプト
新しいClient IDでのテスト用
"""

import os
import base64
import requests
import tempfile
from PIL import Image
from pathlib import Path

def create_test_image():
    """シンプルなテスト画像を作成"""
    print("🖼️  テスト画像作成中...")
    
    # 小さな画像を作成（800x600 -> 200x150に縮小）
    image = Image.new('RGB', (200, 150), color='lightblue')
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    image.save(temp_file.name, 'JPEG', quality=80)
    temp_file.close()
    
    print(f"✅ テスト画像作成完了: {temp_file.name}")
    return temp_file.name

def test_imgur_upload(image_path, client_id):
    """Imgur APIに直接アップロードテスト"""
    print(f"📤 Imgur アップロードテスト開始...")
    print(f"Client ID: {client_id[:10]}..." if client_id else "Client ID未設定")
    
    try:
        # 画像をBase64エンコード
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # ファイルサイズ確認
        file_size = Path(image_path).stat().st_size
        print(f"📏 ファイルサイズ: {file_size} bytes ({file_size/1024:.1f}KB)")
        
        # Imgur API リクエスト
        headers = {
            'Authorization': f'Client-ID {client_id}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'image': image_data,
            'type': 'base64',
            'title': 'MCP Test Image',
            'description': 'Test upload from Imgur MCP',
            'privacy': 'hidden'
        }
        
        print("🌐 Imgur API呼び出し中...")
        response = requests.post(
            'https://api.imgur.com/3/upload',
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"📡 レスポンス: HTTP {response.status_code}")
        
        # レート制限情報表示
        if 'X-RateLimit-ClientRemaining' in response.headers:
            remaining = response.headers['X-RateLimit-ClientRemaining']
            limit = response.headers.get('X-RateLimit-ClientLimit', 'Unknown')
            print(f"🎯 レート制限: {remaining}/{limit} 残り")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                data = result['data']
                print(f"✅ アップロード成功!")
                print(f"🔗 URL: {data.get('link')}")
                print(f"🆔 ID: {data.get('id')}")
                print(f"🗑️  削除ハッシュ: {data.get('deletehash')}")
                print(f"📐 サイズ: {data.get('width')}x{data.get('height')}")
                return {
                    'success': True,
                    'url': data.get('link'),
                    'id': data.get('id'),
                    'delete_hash': data.get('deletehash')
                }
            else:
                error = result.get('data', {}).get('error', 'Unknown error')
                print(f"❌ アップロード失敗: {error}")
                return {'success': False, 'error': error}
        else:
            print(f"❌ HTTP エラー: {response.status_code}")
            print(f"レスポンス: {response.text[:200]}...")
            return {'success': False, 'error': f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"❌ 例外エラー: {e}")
        return {'success': False, 'error': str(e)}

def test_imgur_delete(delete_hash, client_id):
    """Imgur画像削除テスト"""
    if not delete_hash:
        print("⚠️  削除ハッシュがありません。削除テストをスキップ")
        return
    
    print(f"🗑️  削除テスト開始: {delete_hash}")
    
    try:
        headers = {
            'Authorization': f'Client-ID {client_id}'
        }
        
        response = requests.delete(
            f'https://api.imgur.com/3/image/{delete_hash}',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ 削除成功!")
            else:
                print(f"❌ 削除失敗: {result}")
        else:
            print(f"❌ 削除エラー: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ 削除例外: {e}")

def check_imgur_credits(client_id):
    """Imgur APIクレジット確認"""
    print("📊 Imgur APIクレジット確認...")
    
    try:
        headers = {
            'Authorization': f'Client-ID {client_id}'
        }
        
        response = requests.get(
            'https://api.imgur.com/3/credits',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                credits = result['data']
                print(f"✅ クレジット情報:")
                print(f"   Client残り: {credits.get('ClientRemaining', 'N/A')}")
                print(f"   Client制限: {credits.get('ClientLimit', 'N/A')}")
                print(f"   User残り: {credits.get('UserRemaining', 'N/A')}")
                print(f"   User制限: {credits.get('UserLimit', 'N/A')}")
                return True
        else:
            print(f"❌ クレジット確認エラー: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ クレジット確認例外: {e}")
        return False

def main():
    """メイン実行"""
    print("🚀 Imgur 簡単テストスクリプト")
    print("=" * 30)
    
    # Client ID確認
    client_id = os.getenv('IMGUR_CLIENT_ID')
    
    if not client_id:
        print("❌ IMGUR_CLIENT_IDが設定されていません")
        print("")
        print("📝 設定方法:")
        print("1. https://api.imgur.com/oauth2/addclient でAPIアプリケーション登録")
        print("2. Client IDを取得")
        print("3. export IMGUR_CLIENT_ID=your_client_id")
        print("4. または .env ファイルに IMGUR_CLIENT_ID=your_client_id")
        print("")
        print("📖 詳細: imgur_setup_guide.md を参照")
        return
    
    print(f"🔑 Client ID: {client_id[:10]}...")
    
    # APIクレジット確認
    if not check_imgur_credits(client_id):
        print("⚠️  API接続に問題があります。Client IDを確認してください")
        return
    
    # テスト画像作成
    test_image = create_test_image()
    
    try:
        # アップロードテスト
        result = test_imgur_upload(test_image, client_id)
        
        # 削除テスト
        if result.get('success'):
            print("\n⏰ 5秒待機後、削除テストを実行...")
            import time
            time.sleep(5)
            test_imgur_delete(result.get('delete_hash'), client_id)
        
        print("\n🎉 テスト完了!")
        
    finally:
        # クリーンアップ
        if Path(test_image).exists():
            os.unlink(test_image)
            print(f"🧹 テスト画像削除: {test_image}")

if __name__ == "__main__":
    main()