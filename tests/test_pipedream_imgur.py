#!/usr/bin/env python3
"""
Pipedream Imgur MCP テストスクリプト
"""

import asyncio
import os
import sys
import logging

# パスを追加
sys.path.append('/home/moto/line-gemini-hatena-integration')

from src.services.pipedream_imgur_service import PipedreamImgurService

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_pipedream_imgur():
    """Pipedream Imgur MCP のテスト"""
    try:
        logger.info("=== Pipedream Imgur MCP テスト開始 ===")
        
        # サービス初期化
        service = PipedreamImgurService()
        
        # ヘルスチェック
        logger.info("1. ヘルスチェック実行")
        health_result = await service.health_check()
        print(f"ヘルスチェック結果: {health_result}")
        
        # 画像アップロードテスト
        logger.info("2. 画像アップロードテスト")
        
        # テスト画像を探す
        test_images = [
            "/home/moto/line-gemini-hatena-integration/uploads/564948801136361784.jpg",
            "/home/moto/line-gemini-hatena-integration/uploads/564937817109823905.jpg"
        ]
        
        test_image = None
        for img_path in test_images:
            if os.path.exists(img_path):
                test_image = img_path
                break
        
        if test_image:
            logger.info(f"テスト画像: {test_image}")
            
            upload_result = await service.upload_image(
                image_path=test_image,
                title="Pipedream MCP テスト画像",
                description="Pipedream Imgur MCP の動作確認用画像",
                privacy="hidden"
            )
            
            print(f"アップロード結果: {upload_result}")
            
            if upload_result.get('success'):
                logger.info(f"✅ アップロード成功: {upload_result.get('url')}")
                logger.info(f"✅ 個人アカウント紐付け: {upload_result.get('imgur_id')}")
                
                # アカウント画像一覧テスト
                logger.info("3. アカウント画像一覧テスト")
                account_images = await service.get_account_images(limit=5)
                print(f"アカウント画像一覧: {account_images}")
                
            else:
                logger.error(f"❌ アップロード失敗: {upload_result.get('error')}")
        else:
            logger.warning("テスト用画像が見つかりません")
            logger.info("利用可能な画像:")
            uploads_dir = "/home/moto/line-gemini-hatena-integration/uploads"
            if os.path.exists(uploads_dir):
                for file in os.listdir(uploads_dir):
                    if file.endswith(('.jpg', '.png', '.gif')):
                        print(f"  - {file}")
        
        logger.info("=== テスト完了 ===")
        
    except Exception as e:
        logger.error(f"テスト中にエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # テスト実行
    asyncio.run(test_pipedream_imgur())