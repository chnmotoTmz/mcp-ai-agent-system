#!/usr/bin/env python3
"""
Gemini HTML出力テスト
修正されたGeminiサービスがHTML形式で出力するかを確認
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.gemini_service import GeminiService
from src.services.enhancement_gemini_service import EnhancementGeminiService
import logging

# ログレベルを設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gemini_html_output():
    """GeminiサービスのHTML出力テスト"""
    print("=" * 60)
    print("Gemini HTML出力テスト")
    print("=" * 60)
    
    try:
        gemini_service = GeminiService()
        
        # テストメッセージ
        test_message = "今日は美味しいパスタを作りました。トマトソースとチーズがとても良い組み合わせで、家族みんなに好評でした。"
        
        print(f"📝 テストメッセージ: {test_message}")
        print("\n🤖 Gemini生成中...")
        
        result = gemini_service.generate_content(test_message)
        
        if result:
            print("✅ 生成成功!")
            print(f"📄 生成内容:")
            print("-" * 40)
            print(result)
            print("-" * 40)
            
            # HTML形式かチェック
            has_html_tags = any(tag in result for tag in ['<p>', '<br>', '<strong>', '<em>', '<h2>', '<h3>', '<ul>', '<li>'])
            has_markdown = any(md in result for md in ['##', '**', '- ', '* ', '1. '])
            
            print(f"\n📊 出力分析:")
            print(f"HTMLタグ検出: {'✅ あり' if has_html_tags else '❌ なし'}")
            print(f"マークダウン検出: {'❌ あり' if has_markdown else '✅ なし'}")
            
            if has_html_tags and not has_markdown:
                print("🎉 HTML形式での出力が成功しています！")
                return True
            else:
                print("⚠️  まだマークダウン形式で出力されています")
                return False
        else:
            print("❌ 生成失敗")
            return False
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        return False

def test_enhancement_gemini():
    """EnhancementGeminiサービスのテスト"""
    print("\n" + "=" * 60)
    print("Enhancement Gemini HTML出力テスト")
    print("=" * 60)
    
    try:
        enhancement_service = EnhancementGeminiService()
        
        # テスト用コンテンツ（マークダウン形式）
        test_content = """
## 美味しいパスタの作り方

今日は**美味しいパスタ**を作りました。

### 材料
- パスタ 200g
- トマトソース
- チーズ

### 作り方
1. パスタを茹でる
2. ソースを温める  
3. チーズをかける

とても美味しくできました！
"""
        
        print(f"📝 テストコンテンツ（マークダウン形式）:")
        print(test_content)
        print("\n🤖 品質向上処理中...")
        
        result = enhancement_service.improve_text_quality(test_content)
        
        if result:
            print("✅ 品質向上成功!")
            print(f"📄 改善結果:")
            print("-" * 40)
            print(result)
            print("-" * 40)
            
            # HTML形式かチェック
            has_html_tags = any(tag in result for tag in ['<p>', '<br>', '<strong>', '<em>', '<h2>', '<h3>', '<ul>', '<li>'])
            has_markdown = any(md in result for md in ['##', '**', '- ', '* ', '1. '])
            
            print(f"\n📊 出力分析:")
            print(f"HTMLタグ検出: {'✅ あり' if has_html_tags else '❌ なし'}")
            print(f"マークダウン検出: {'❌ あり' if has_markdown else '✅ なし'}")
            
            if has_html_tags and not has_markdown:
                print("🎉 HTML形式での出力が成功しています！")
                return True
            else:
                print("⚠️  まだマークダウン形式で出力されています")
                return False
        else:
            print("❌ 品質向上失敗")
            return False
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        return False

def main():
    """メイン実行関数"""
    print("Gemini HTML出力テストスクリプト")
    print("=" * 60)
    
    # 環境変数チェック
    if not os.getenv('GEMINI_API_KEY'):
        print("⚠️  GEMINI_API_KEY環境変数が設定されていません")
        print("環境変数を設定してから再実行してください。")
        return False
    
    # テスト実行
    test1_success = test_gemini_html_output()
    test2_success = test_enhancement_gemini()
    
    print("\n" + "=" * 60)
    print("最終結果")
    print("=" * 60)
    
    if test1_success and test2_success:
        print("🎉 すべてのテストが成功しました！")
        print("GeminiがHTML形式で出力するようになりました。")
        print("これで、みたままモードでも正しく表示されるはずです。")
    elif test1_success:
        print("✅ 基本のGeminiサービスは成功")
        print("⚠️  Enhancement Geminiサービスに問題があります")
    elif test2_success:
        print("⚠️  基本のGeminiサービスに問題があります") 
        print("✅ Enhancement Geminiサービスは成功")
    else:
        print("❌ 両方のテストが失敗しました")
        print("プロンプトの修正が不十分な可能性があります")
    
    return test1_success and test2_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)