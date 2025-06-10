"""
Google Photos Service
Google Photos APIを使用した画像アップロード・管理サービス
"""

import logging
import os
import requests
import json
from typing import Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

class GooglePhotosService:
    """Google Photos API サービス"""
    
    # Google Photos APIスコープ（読み書き両方対応）
    SCOPES = [
        'https://www.googleapis.com/auth/photoslibrary.appendonly',
        'https://www.googleapis.com/auth/photoslibrary.readonly'
    ]
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self._setup_credentials()
    
    def _setup_credentials(self):
        """認証情報のセットアップ"""
        try:
            # 保存された認証情報を読み込み
            if os.path.exists('google_photos_token.json'):
                self.credentials = Credentials.from_authorized_user_file(
                    'google_photos_token.json', self.SCOPES
                )
            
            # 認証情報が無効または存在しない場合
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    # 初回認証が必要
                    logger.warning("Google Photos API認証が必要です")
                    return
            
            # Google Photos APIは直接REST APIを使用
            if self.credentials and self.credentials.valid:
                self.service = "authenticated"  # 認証済みマーカー
                logger.info("Google Photos API認証情報確認完了")
            else:
                logger.error("Google Photos認証情報が無効です")
            
        except Exception as e:
            logger.error(f"Google Photos認証エラー: {e}")
    
    def upload_image(self, image_path: str, title: str = "", description: str = "") -> Optional[Dict]:
        """画像をGoogle Photosにアップロード
        
        Args:
            image_path: アップロードする画像のパス
            title: 画像のタイトル
            description: 画像の説明
        
        Returns:
            dict: アップロード結果
        """
        try:
            if not self.service or not self.credentials or not self.credentials.valid:
                return {
                    "success": False,
                    "error": "Google Photos API not authenticated"
                }
            
            # 画像ファイルが存在するかチェック
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": f"Image file not found: {image_path}"
                }
            
            # 1. ファイルをアップロード
            upload_token = self._upload_bytes(image_path)
            if not upload_token:
                return {
                    "success": False,
                    "error": "Failed to upload image bytes"
                }
            
            # 2. メディアアイテムを作成
            new_media_item = {
                'description': description or f"Uploaded from LINE Bot: {title}",
                'simpleMediaItem': {
                    'uploadToken': upload_token
                }
            }
            
            # バッチでメディアアイテムを作成
            request_body = {
                'newMediaItems': [new_media_item]
            }
            
            # REST APIを直接呼び出し
            response = self._make_api_request(
                'POST',
                'https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate',
                json=request_body
            )
            
            if response and 'newMediaItemResults' in response and response['newMediaItemResults']:
                result = response['newMediaItemResults'][0]
                
                if result.get('status', {}).get('message') == 'Success':
                    media_item = result['mediaItem']
                    media_item_id = media_item['id']
                    
                    # レスポンスから直接baseUrlを取得（アップロード直後は有効）
                    base_url = media_item.get('baseUrl')
                    
                    # baseUrlが取得できない場合、代替として一時的な表示用URLを生成
                    if not base_url:
                        # 有効期限付きのbaseUrlを追加パラメータで要求
                        base_url = self._get_media_item_base_url(media_item_id)
                    
                    # はてなブログ用の画像URLとして使用
                    # baseUrlは短期間有効なので、すぐにブログ投稿に使用
                    image_url = base_url if base_url else f"https://photos.app.goo.gl/{media_item_id}"
                    
                    return {
                        "success": True,
                        "google_photos_url": image_url,
                        "share_url": image_url,  # 同じURLを共有用としても使用
                        "media_item_id": media_item_id,
                        "title": title,
                        "description": description,
                        "base_url_available": bool(base_url)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Media item creation failed: {result.get('status', {}).get('message', 'Unknown error')}"
                    }
            else:
                return {
                    "success": False,
                    "error": "No media items created"
                }
        
        except Exception as e:
            logger.error(f"Failed to upload to Google Photos: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _upload_bytes(self, image_path: str) -> Optional[str]:
        """画像ファイルをバイトとしてアップロード"""
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # アップロード用のエンドポイント
            upload_url = 'https://photoslibrary.googleapis.com/v1/uploads'
            
            headers = {
                'Authorization': f'Bearer {self.credentials.token}',
                'Content-type': 'application/octet-stream',
                'X-Goog-Upload-Protocol': 'raw',
                'X-Goog-Upload-File-Name': os.path.basename(image_path)
            }
            
            response = requests.post(upload_url, data=image_data, headers=headers)
            
            if response.status_code == 200:
                return response.text  # アップロードトークン
            else:
                logger.error(f"Upload bytes failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading bytes: {e}")
            return None
    
    def _get_media_item_base_url(self, media_item_id: str) -> Optional[str]:
        """メディアアイテムのbaseURLを取得"""
        try:
            url = f'https://photoslibrary.googleapis.com/v1/mediaItems/{media_item_id}'
            response = self._make_api_request('GET', url)
            
            if response:
                return response.get('baseUrl')
            return None
            
        except Exception as e:
            logger.error(f"Error getting media item base URL: {e}")
            return None
    
    def _make_api_request(self, method: str, url: str, **kwargs) -> Optional[dict]:
        """Google Photos APIリクエストを実行"""
        try:
            headers = {
                'Authorization': f'Bearer {self.credentials.token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.request(method, url, headers=headers, **kwargs)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error making API request: {e}")
            return None
    
    def setup_authentication(self, client_secrets_file: str = 'google_photos_credentials.json'):
        """初回認証のセットアップ（手動実行用）"""
        try:
            if not os.path.exists(client_secrets_file):
                print(f"❌ {client_secrets_file}が見つかりません")
                print("Google Cloud Consoleから認証ファイルをダウンロードしてください")
                return False
            
            # Web Application フローを使用
            flow = Flow.from_client_secrets_file(
                client_secrets_file, 
                scopes=self.SCOPES,
                redirect_uri='http://localhost:8080'
            )
            
            # 手動認証フロー
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"認証URL: {auth_url}")
            
            auth_code = input("認証コードを入力してください: ")
            flow.fetch_token(code=auth_code)
            
            credentials = flow.credentials
            
            # 認証情報を保存
            with open('google_photos_token.json', 'w') as token:
                token.write(credentials.to_json())
            
            print("✅ Google Photos認証完了")
            self.credentials = credentials
            self.service = "authenticated"
            
            return True
            
        except Exception as e:
            logger.error(f"Authentication setup error: {e}")
            return False

# 認証セットアップ用スクリプト
if __name__ == "__main__":
    service = GooglePhotosService()
    service.setup_authentication()
