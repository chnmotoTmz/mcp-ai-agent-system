#!/usr/bin/env python3
"""
Google Photos API 初回認証セットアップスクリプト
OAuth 2.0フローを実行してトークンを取得
"""

import os
import json
import logging
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Photos APIスコープ
SCOPES = [
    'https://www.googleapis.com/auth/photoslibrary.appendonly',  # アップロード
    'https://www.googleapis.com/auth/photoslibrary.readonly'     # 読み取り
]

# ファイルパス
CREDENTIALS_FILE = 'google_photos_credentials.json'
TOKEN_FILE = 'google_photos_token.json'

def setup_google_photos_auth():
    """Google Photos API認証の初回セットアップ"""
    
    print("🔐 Google Photos API 認証セットアップ")
    print("=" * 50)
    
    try:
        from google_auth_oauthlib.flow import Flow
        
        # OAuth設定（読み書き両方のスコープ）
        SCOPES = [
            'https://www.googleapis.com/auth/photoslibrary.appendonly',
            'https://www.googleapis.com/auth/photoslibrary.readonly'
        ]
        client_secrets_file = 'google_photos_credentials.json'
        
        if not os.path.exists(client_secrets_file):
            print(f"❌ {client_secrets_file}が見つかりません")
            return False
        
        # Web Application用のフローを作成
        flow = Flow.from_client_secrets_file(
            client_secrets_file, 
            scopes=SCOPES,
            redirect_uri='http://localhost:8080'
        )
        
        # 認証URLを生成
        auth_url, _ = flow.authorization_url(
            prompt='consent',
            include_granted_scopes='true'
        )
        
        print("📋 認証手順:")
        print("1. 以下のURLをWindowsブラウザで開いてください:")
        print(f"\n🔗 {auth_url}\n")
        print("2. Googleアカウントでログイン")
        print("3. アプリケーションへのアクセスを許可")
        print("4. リダイレクト後のURL全体をコピー")
        print("   (例: http://localhost:8080/?code=4/0AX4XfWh...&scope=...)")
        
        # 認証コードまたはリダイレクトURLの入力を待機
        response_input = input("\n📝 リダイレクトURL全体または認証コードを入力してください: ").strip()
        
        if not response_input:
            print("❌ 入力がありません")
            return False
        
        # URLからコードを抽出するか、直接コードとして使用
        if response_input.startswith('http://localhost:8080'):
            # URLからコードを抽出
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(response_input)
            query_params = parse_qs(parsed_url.query)
            
            if 'code' not in query_params:
                print("❌ URLに認証コードが含まれていません")
                return False
            
            auth_code = query_params['code'][0]
        else:
            # 直接コードとして使用
            auth_code = response_input
        
        # 認証コードを使って認証情報を取得
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials
        
        # 認証情報を保存
        with open('google_photos_token.json', 'w') as token:
            token.write(credentials.to_json())
        
        print("✅ Google Photos認証完了！")
        print("📁 google_photos_token.json が作成されました")
        
        return True
        
    except Exception as e:
        print(f"❌ 認証エラー: {e}")
        print(f"詳細: {type(e).__name__}")
        return False

def test_authentication():
    """認証テスト"""
    print("\n🧪 認証テスト実行中...")
    
    try:
        from src.services.google_photos_service import GooglePhotosService
        
        service = GooglePhotosService()
        
        if service.service:
            print("✅ Google Photos API接続成功")
            return True
        else:
            print("❌ Google Photos API接続失敗")
            return False
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        return False

def main():
    """メイン処理"""
    print("🚀 WSL用 Google Photos認証セットアップ (Web Application)")
    print("=" * 60)
    
    # 認証ファイルの形式をチェック
    credentials_file = 'google_photos_credentials.json'
    if os.path.exists(credentials_file):
        with open(credentials_file, 'r') as f:
            creds_data = json.load(f)
            
        if 'web' not in creds_data:
            print("❌ 認証ファイルが 'web' タイプではありません")
            print("Google Cloud Console で 'Web application' タイプのクライアントを使用してください")
            return
        else:
            print("✅ Web application タイプの認証ファイルを確認")
    
    # 既存の認証ファイルをチェック
    if os.path.exists('google_photos_token.json'):
        print("📁 既存の認証ファイルが見つかりました")
        test_result = test_authentication()
        
        if test_result:
            print("🎉 認証は既に完了しています！")
            return
        else:
            print("⚠️  認証ファイルが無効です。再認証します...")
            os.remove('google_photos_token.json')
    
    # 手動認証を実行
    auth_result = manual_google_photos_auth()
    
    if auth_result:
        # 認証テスト
        test_result = test_authentication()
        
        if test_result:
            print("\n🎉 セットアップ完了！")
            print("\n📋 次のステップ:")
            print("1. システムを再起動: ./start.sh")
            print("2. LINEで画像付きメッセージを送信")
            print("3. Google Photosとはてなブログを確認")
        else:
            print("\n❌ 認証は完了しましたが、接続テストに失敗しました")
    else:
        print("\n❌ 認証に失敗しました")

if __name__ == "__main__":
    main()
