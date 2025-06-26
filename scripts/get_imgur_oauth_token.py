#!/usr/bin/env python3
"""
Imgur OAuth トークン取得スクリプト
個人アカウントに画像を紐付けるためのアクセストークンを取得
"""

import webbrowser
import urllib.parse
import requests
import json
import os  # 追加
from dotenv import load_dotenv  # 追加

load_dotenv()  # 追加

# Imgur アプリケーション情報（環境変数から読み込むように変更）
CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")  # 変更
CLIENT_SECRET = os.getenv("IMGUR_CLIENT_SECRET")  # 変更

def get_imgur_oauth_token():
    """Imgur OAuth トークンを取得"""

    print("🔑 Imgur OAuth認証手順")
    print("=" * 50)

    # Step 1: 認証URLを生成
    auth_url = (
        f"https://api.imgur.com/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=token"
        f"&state=application_state"
    )

    print("1. 以下の認証URLをコピーし、お使いのウェブブラウザで開いてください：") # 変更
    print(f"   {auth_url}")
    print()
    print("2. Imgurにログインし、このアプリケーション（My Hatena Blog Integration）の利用を承認してください。") # 追加
    print()
    print("3. 承認後、ブラウザのアドレスバーに表示されているURL全体をコピーしてください。") # 追加
    print("   （例: https://localhost/?state=...#access_token=...&... のようなURLです）") # 追加
    print()
    # ブラウザを自動で開く処理をコメントアウト
    # try:
    #     webbrowser.open(auth_url)
    #     print("✅ ブラウザを開きました")
    # except:
    #     print("❌ ブラウザを開けませんでした。上記URLを手動でコピーしてください")

    # print() # 削除 (重複を避けるため)
    # print("2. Imgurにログインして、アプリケーションの利用を承認してください") # 削除 (上に移動)
    # print() # 削除 (重複を避けるため)
    # print("3. リダイレクト後のURLをコピーして、下記に貼り付けてください") # 削除 (上に移動)
    # print("   例: https://example.com#access_token=abc123&expires_in=315360000&token_type=bearer&account_id=123456789&account_username=yourusername") # 削除 (上に移動)
    # print() # 削除 (重複を避けるため)

    # ユーザー入力を待つ
    input("上記の手順が完了したら、Enterキーを押して次に進んでください...") # 追加: 一時停止
    redirect_url = input("コピーしたリダイレクトURLをここに貼り付けてください: ").strip() # プロンプト変更

    if not redirect_url:
        print("❌ URLが入力されませんでした")
        return None

    # URLからトークンを抽出
    try:
        # フラグメントを取得
        if '#' in redirect_url:
            fragment = redirect_url.split('#')[1]
        else:
            print("❌ 不正なURL形式です")
            return None

        # パラメータをパース
        params = urllib.parse.parse_qs(fragment)

        access_token = params.get('access_token', [None])[0]
        expires_in = params.get('expires_in', [None])[0]
        account_username = params.get('account_username', [None])[0]
        account_id = params.get('account_id', [None])[0]

        if not access_token:
            print("❌ アクセストークンが見つかりません")
            return None

        print()
        print("✅ OAuth認証成功！")
        print("=" * 50)
        print(f"アクセストークン: {access_token}")
        print(f"有効期限: {expires_in}秒 ({int(expires_in)//86400}日)")
        print(f"アカウント名: {account_username}")
        print(f"アカウントID: {account_id}")
        print()

        # 環境変数の設定方法を表示
        print("🔧 環境変数の設定")
        print("=" * 50)
        print("以下のコマンドを実行してください：")
        print()
        print(f"export IMGUR_ACCESS_TOKEN='{access_token}'")
        print(f"export IMGUR_ACCOUNT_USERNAME='{account_username}'")
        print(f"export IMGUR_ACCOUNT_ID='{account_id}'")
        print()
        print("または、.envファイルに追加：")
        print(f"IMGUR_ACCESS_TOKEN={access_token}")
        print(f"IMGUR_ACCOUNT_USERNAME={account_username}")
        print(f"IMGUR_ACCOUNT_ID={account_id}")
        print()

        # .envファイルに保存するか確認
        save_to_env = input("この情報を.envファイルに保存しますか？ (y/n): ").strip().lower()

        if save_to_env == 'y':
            try:
                with open('.env', 'a') as f:
                    f.write(f"\n# Imgur OAuth認証情報\n")
                    f.write(f"IMGUR_ACCESS_TOKEN={access_token}\n")
                    f.write(f"IMGUR_ACCOUNT_USERNAME={account_username}\n")
                    f.write(f"IMGUR_ACCOUNT_ID={account_id}\n")
                print("✅ .envファイルに保存しました")
            except Exception as e:
                print(f"❌ .envファイル保存エラー: {e}")

        return {
            'access_token': access_token,
            'expires_in': expires_in,
            'account_username': account_username,
            'account_id': account_id
        }

    except Exception as e:
        print(f"❌ URLパースエラー: {e}")
        return None

def test_oauth_token(access_token):
    """OAuth トークンをテスト"""
    try:
        print("🧪 OAuth トークンのテスト")
        print("=" * 50)

        # アカウント情報を取得
        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.get(
            'https://api.imgur.com/3/account/me',
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            account_info = data.get('data', {})

            print("✅ OAuth認証トークンが正常に動作しています")
            print(f"アカウントURL: {account_info.get('url')}")
            print(f"登録日: {account_info.get('created')}")
            print(f"画像数: {account_info.get('total_images', 0)}")
            print(f"アルバム数: {account_info.get('total_albums', 0)}")

            return True
        else:
            print(f"❌ OAuth認証エラー: HTTP {response.status_code}")
            print(f"レスポンス: {response.text}")
            return False

    except Exception as e:
        print(f"❌ OAuth テストエラー: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Imgur OAuth認証設定スクリプト")
    print()

    # OAuth トークンを取得
    token_info = get_imgur_oauth_token()

    if token_info:
        # トークンをテスト
        success = test_oauth_token(token_info['access_token'])

        if success:
            print()
            print("🎉 設定完了！")
            print("これで個人アカウントに画像がアップロードされます。")
        else:
            print()
            print("❌ 設定に問題があります。もう一度お試しください。")
    else:
        print("❌ OAuth認証に失敗しました。")
