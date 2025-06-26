#!/usr/bin/env python3
"""
MCP サーバー統合テスト
4つのMCPサーバー（LINE, Gemini, Imgur, Hatena）の動作確認
"""

import asyncio
import logging
import sys
import os
import json
import base64
from pathlib import Path
from datetime import datetime

# パスを追加
sys.path.append('/home/moto/line-gemini-hatena-integration')

# 設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPIntegrationTester:
    """MCP統合テスト実行クラス"""
    
    def __init__(self):
        self.test_results = {}
        
    async def run_all_tests(self):
        """すべてのMCPサーバーテストを実行"""
        logger.info("🧪 MCP統合テスト開始")
        
        # テスト順序（依存関係を考慮）
        tests = [
            ("Imgur MCP Server", self.test_imgur_mcp),
            ("Gemini MCP Server", self.test_gemini_mcp), 
            ("LINE MCP Server", self.test_line_mcp),
            ("Hatena MCP Server", self.test_hatena_mcp)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n📋 {test_name} テスト開始")
            try:
                result = await test_func()
                self.test_results[test_name] = {
                    "status": "PASS" if result else "FAIL",
                    "timestamp": datetime.now().isoformat()
                }
                logger.info(f"✅ {test_name}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                self.test_results[test_name] = {
                    "status": "ERROR", 
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                logger.error(f"❌ {test_name}: ERROR - {e}")
        
        # 結果レポート出力
        await self.generate_report()
    
    async def test_imgur_mcp(self):
        """Imgur MCP Server テスト"""
        try:
            # テスト用の小さな画像を作成
            test_image_data = self._create_test_image()
            
            # Imgur MCPサーバーをインポート
            from src.mcp_servers.imgur_server_fastmcp import get_imgur_service
            
            imgur_service = get_imgur_service()
            
            # ヘルスチェックテスト
            logger.info("  - Imgur ヘルスチェック")
            if not hasattr(imgur_service, 'upload_image'):
                logger.error("  - Imgur service does not have upload_image method")
                return False
            
            logger.info("  - Imgur MCP基本機能確認完了")
            return True
            
        except Exception as e:
            logger.error(f"  - Imgur MCP テストエラー: {e}")
            return False
    
    async def test_gemini_mcp(self):
        """Gemini MCP Server テスト"""
        try:
            # Gemini MCPサーバーをインポート
            from src.mcp_servers.gemini_server_fastmcp_fixed import get_gemini_service
            
            gemini_service = get_gemini_service()
            
            # ヘルスチェックテスト
            logger.info("  - Gemini ヘルスチェック")
            if not hasattr(gemini_service, 'generate_article'):
                logger.error("  - Gemini service does not have generate_article method")
                return False
            
            logger.info("  - Gemini MCP基本機能確認完了")
            return True
            
        except Exception as e:
            logger.error(f"  - Gemini MCP テストエラー: {e}")
            return False
    
    async def test_line_mcp(self):
        """LINE MCP Server テスト"""
        try:
            # LINE MCPサーバーをインポート
            from src.mcp_servers.line_server_fastmcp_fixed import get_line_service
            
            line_service = get_line_service()
            
            # ヘルスチェックテスト
            logger.info("  - LINE ヘルスチェック")
            if not hasattr(line_service, 'reply_message'):
                logger.error("  - LINE service does not have reply_message method")
                return False
            
            logger.info("  - LINE MCP基本機能確認完了") 
            return True
            
        except Exception as e:
            logger.error(f"  - LINE MCP テストエラー: {e}")
            return False
    
    async def test_hatena_mcp(self):
        """Hatena MCP Server テスト"""
        try:
            # Hatena MCPサーバーをインポート
            from src.mcp_servers.hatena_server_fastmcp_fixed import get_hatena_service
            
            hatena_service = get_hatena_service()
            
            # ヘルスチェックテスト
            logger.info("  - Hatena ヘルスチェック")
            if not hasattr(hatena_service, 'publish_article'):
                logger.error("  - Hatena service does not have publish_article method")
                return False
            
            logger.info("  - Hatena MCP基本機能確認完了")
            return True
            
        except Exception as e:
            logger.error(f"  - Hatena MCP テストエラー: {e}")
            return False
    
    def _create_test_image(self):
        """テスト用の小さな画像データを作成"""
        # 1x1ピクセルのPNG画像（Base64エンコード済み）
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    async def generate_report(self):
        """テスト結果レポートを生成"""
        logger.info("\n" + "="*60)
        logger.info("🧪 MCP統合テスト結果レポート")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        
        logger.info(f"📊 総テスト数: {total_tests}")
        logger.info(f"✅ 成功: {passed_tests}")
        logger.info(f"❌ 失敗: {failed_tests}")
        logger.info(f"📈 成功率: {(passed_tests/total_tests*100):.1f}%")
        
        logger.info("\n📋 詳細結果:")
        for test_name, result in self.test_results.items():
            status_emoji = "✅" if result["status"] == "PASS" else "❌"
            logger.info(f"  {status_emoji} {test_name}: {result['status']}")
            if "error" in result:
                logger.info(f"    エラー: {result['error']}")
        
        # JSON形式でも保存
        report_data = {
            "test_summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": passed_tests/total_tests*100
            },
            "test_results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        # レポートファイルを保存
        report_file = Path("mcp_integration_test_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📄 詳細レポート保存: {report_file}")
        
        # 統合成功判定
        if passed_tests == total_tests:
            logger.info("\n🎉 すべてのMCPサーバーテストが成功しました！")
            logger.info("次のステップ: LangGraphエージェント統合に進めます")
        else:
            logger.info(f"\n⚠️  {failed_tests}個のMCPサーバーで問題が検出されました")
            logger.info("問題を修正してから次のステップに進んでください")

async def main():
    """メイン実行関数"""
    tester = MCPIntegrationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
